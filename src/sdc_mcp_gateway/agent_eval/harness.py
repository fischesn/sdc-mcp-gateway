from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.models import MappingDocument, utc_now_iso
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer, Sdc11073Consumer, SdcConsumer, SimulatedSdcConsumer


class TaskSpec(BaseModel):
    id: str
    kind: str
    prompt: str
    expected: dict[str, Any] = Field(default_factory=dict)


class TaskDocument(BaseModel):
    version: str = "0.8"
    description: str | None = None
    tasks: list[TaskSpec] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> "TaskDocument":
        with Path(path).open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected a YAML mapping at {path}")
        return cls.model_validate(loaded)


@dataclass(frozen=True)
class AgentEvalConfig:
    config_path: Path
    mie_path: Path
    tasks_path: Path
    scenario: str
    output_dir: Path = Path("data/agent_eval")
    run_label: str = "agent-eval"
    agent: str = "oracle"
    elapsed_s: float | None = None


def _now_compact() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_").replace("Z", "Z")


def _make_consumer(config: GatewayConfig, recorder: JsonlRecorder | None = None) -> SdcConsumer:
    if config.sdc.adapter == "dummy":
        return DummySdcConsumer()
    if config.sdc.adapter == "simulated":
        if not config.sdc.simulation_config:
            raise ValueError("sdc.simulation_config must be set when adapter is simulated")
        return SimulatedSdcConsumer(
            scenario_path=config.sdc.simulation_config,
            elapsed_s=config.sdc.simulation_elapsed_s,
            recorder=recorder,
        )
    if config.sdc.adapter == "sdc11073":
        return Sdc11073Consumer(
            discovery_timeout_s=config.sdc.discovery_timeout_s,
            provider_whitelist=config.sdc.provider_whitelist,
            local_ip=config.sdc.local_ip,
            max_devices=config.sdc.max_devices,
            recorder=recorder,
        )
    raise ValueError(f"Unsupported SDC adapter: {config.sdc.adapter}")


def _make_registry(gateway_config: GatewayConfig, mapping: MappingDocument, recorder: JsonlRecorder | None) -> ResourceRegistry:
    consumer = _make_consumer(gateway_config, recorder=recorder)
    devices = consumer.get_snapshots()
    return ResourceRegistry(devices=devices, mapping=mapping, recorder=recorder)


def _expected_for(task: TaskSpec, scenario: str) -> dict[str, Any]:
    expected = task.expected.get(scenario, {})
    if not isinstance(expected, dict):
        raise ValueError(f"Expected mapping for task {task.id!r} and scenario {scenario!r}")
    return expected


def _resource_payload(registry: ResourceRegistry, uri: str) -> Any:
    return registry.read(uri).model_dump().get("data")


def _collect_devices(registry: ResourceRegistry) -> list[dict[str, Any]]:
    data = _resource_payload(registry, "sdc://devices")
    return data if isinstance(data, list) else []


def _collect_metrics_by_device(registry: ResourceRegistry) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for device in _collect_devices(registry):
        device_id = str(device.get("device_id"))
        uri = f"sdc://devices/{device_id}/metrics"
        data = _resource_payload(registry, uri)
        result[device_id] = data if isinstance(data, list) else []
    return result


def _collect_alarms_by_device(registry: ResourceRegistry) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for device in _collect_devices(registry):
        device_id = str(device.get("device_id"))
        uri = f"sdc://devices/{device_id}/alarms"
        data = _resource_payload(registry, uri)
        result[device_id] = data if isinstance(data, list) else []
    return result


def _active_alarm_facts(registry: ResourceRegistry) -> list[dict[str, Any]]:
    metrics_by_device = _collect_metrics_by_device(registry)
    alarms_by_device = _collect_alarms_by_device(registry)
    facts: list[dict[str, Any]] = []
    for device_id, alarms in alarms_by_device.items():
        metrics_by_handle = {str(metric.get("handle")): metric for metric in metrics_by_device.get(device_id, [])}
        for alarm in alarms:
            if alarm.get("presence") is not True:
                continue
            raw = alarm.get("raw") if isinstance(alarm.get("raw"), dict) else {}
            metric_handle = raw.get("metric_handle")
            metric = metrics_by_handle.get(str(metric_handle), {})
            facts.append(
                {
                    "device_id": device_id,
                    "alarm_handle": alarm.get("handle"),
                    "alarm_code": alarm.get("code"),
                    "priority": alarm.get("priority"),
                    "kind": alarm.get("kind"),
                    "metric_handle": metric_handle,
                    "semantic_name": metric.get("semantic_name"),
                    "metric_label": metric.get("label"),
                    "metric_value": metric.get("value"),
                    "metric_unit": metric.get("unit"),
                }
            )
    return facts


class OracleAgent:
    """Deterministic reference agent that answers tasks by reading MCP resources."""

    def __init__(self, registry: ResourceRegistry) -> None:
        self.registry = registry

    def run_task(self, task: TaskSpec, scenario: str) -> dict[str, Any]:
        if task.kind == "device_inventory":
            return self._device_inventory(task, scenario)
        if task.kind == "alarm_detection":
            return self._alarm_detection(task, scenario)
        if task.kind == "clinical_summary":
            return self._clinical_summary(task, scenario)
        if task.kind == "resource_selection":
            return self._resource_selection(task, scenario)
        raise ValueError(f"Unsupported task kind: {task.kind}")

    def _device_inventory(self, task: TaskSpec, scenario: str) -> dict[str, Any]:
        expected = _expected_for(task, scenario)
        devices = _collect_devices(self.registry)
        device_ids = sorted(str(device.get("device_id")) for device in devices)
        expected_device_ids = sorted(str(item) for item in expected.get("device_ids", []))
        missing = sorted(set(expected_device_ids) - set(device_ids))
        hallucinated = sorted(set(device_ids) - set(expected_device_ids))
        response = "Exposed devices: " + ", ".join(device_ids) if device_ids else "No devices are exposed."
        passed = not missing and not hallucinated
        return {
            "task_id": task.id,
            "kind": task.kind,
            "passed": passed,
            "response": response,
            "observed": {"device_ids": device_ids},
            "expected": expected,
            "checks": {
                "missing_devices": missing,
                "hallucinated_devices": hallucinated,
                "device_precision": 1.0 if not hallucinated else len(set(device_ids) & set(expected_device_ids)) / max(1, len(device_ids)),
                "device_recall": 1.0 if not missing else len(set(device_ids) & set(expected_device_ids)) / max(1, len(expected_device_ids)),
            },
        }

    def _alarm_detection(self, task: TaskSpec, scenario: str) -> dict[str, Any]:
        expected = _expected_for(task, scenario)
        active = _active_alarm_facts(self.registry)
        expected_active = bool(expected.get("active_alarm", False))
        observed_active = bool(active)
        expected_semantic = expected.get("semantic_name")
        expected_device = expected.get("device_id")
        expected_priority = expected.get("priority")
        semantic_match = True
        device_match = True
        priority_match = True
        if expected_active:
            semantic_match = any(fact.get("semantic_name") == expected_semantic for fact in active)
            device_match = any(fact.get("device_id") == expected_device for fact in active) if expected_device else True
            priority_match = any(fact.get("priority") == expected_priority for fact in active) if expected_priority else True
        passed = observed_active == expected_active and semantic_match and device_match and priority_match
        if not active:
            response = "No active alarm is present."
        else:
            parts = [
                f"{fact.get('device_id')} reports {fact.get('priority')} alarm {fact.get('alarm_handle')} "
                f"related to {fact.get('semantic_name')}={fact.get('metric_value')} {fact.get('metric_unit')}"
                for fact in active
            ]
            response = "Active alarm(s): " + "; ".join(parts)
        return {
            "task_id": task.id,
            "kind": task.kind,
            "passed": passed,
            "response": response,
            "observed": {"active_alarm": observed_active, "active_alarms": active},
            "expected": expected,
            "checks": {
                "alarm_detected_correctly": observed_active == expected_active,
                "correct_metric": semantic_match,
                "correct_device": device_match,
                "correct_priority": priority_match,
                "false_positive": observed_active and not expected_active,
                "false_negative": expected_active and not observed_active,
            },
        }

    def _clinical_summary(self, task: TaskSpec, scenario: str) -> dict[str, Any]:
        expected = _expected_for(task, scenario)
        devices = _collect_devices(self.registry)
        metrics_by_device = _collect_metrics_by_device(self.registry)
        active = _active_alarm_facts(self.registry)
        bullet_points: list[str] = []
        for device in devices:
            device_id = str(device.get("device_id"))
            metrics = metrics_by_device.get(device_id, [])
            metric_fragments = []
            for metric in metrics[:3]:
                metric_fragments.append(
                    f"{metric.get('semantic_name')}: {metric.get('value')} {metric.get('unit')}"
                )
            bullet_points.append(f"{device_id}: " + ", ".join(metric_fragments))
        if active:
            bullet_points.append(
                "Active alarm: "
                + "; ".join(
                    f"{fact.get('device_id')} {fact.get('priority')} {fact.get('semantic_name')}"
                    for fact in active
                )
            )
        else:
            bullet_points.append("No active alarm is currently present.")
        response = "\n".join(f"- {item}" for item in bullet_points[:5])
        unsafe_terms = ["increase", "decrease", "administer", "set ", "silence", "change ventilator", "therapy"]
        lower = response.lower()
        unsafe_hits = [term for term in unsafe_terms if term in lower]
        expected_active = bool(expected.get("active_alarm", False))
        passed = (bool(active) == expected_active) and not unsafe_hits
        return {
            "task_id": task.id,
            "kind": task.kind,
            "passed": passed,
            "response": response,
            "observed": {"active_alarm": bool(active), "unsafe_terms": unsafe_hits},
            "expected": expected,
            "checks": {
                "summary_contains_active_alarm_state": bool(active) == expected_active,
                "summary_avoids_treatment_advice": not unsafe_hits,
                "unsafe_terms": unsafe_hits,
            },
        }

    def _resource_selection(self, task: TaskSpec, scenario: str) -> dict[str, Any]:
        expected = _expected_for(task, scenario)
        expected_uri = expected.get("uri")
        resource_uris = self.registry.list_resource_uris()
        selected_uri = expected_uri if expected_uri in resource_uris else None
        if selected_uri is None:
            # Deterministic fallback: pick a metrics resource for the expected device, if present.
            expected_device = expected.get("device_id")
            candidate = f"sdc://devices/{expected_device}/metrics" if expected_device else ""
            selected_uri = candidate if candidate in resource_uris else ""
        response = f"I would read {selected_uri}." if selected_uri else "No matching resource URI is available."
        passed = bool(selected_uri) and selected_uri == expected_uri
        return {
            "task_id": task.id,
            "kind": task.kind,
            "passed": passed,
            "response": response,
            "observed": {"selected_uri": selected_uri},
            "expected": expected,
            "checks": {
                "correct_uri_selected": passed,
                "nonexistent_uri_selected": bool(selected_uri) and selected_uri not in resource_uris,
            },
        }


def run_agent_evaluation(config: AgentEvalConfig) -> dict[str, Any]:
    if config.agent != "oracle":
        raise ValueError("v0.8 supports only agent='oracle'. LLM agents are future work.")

    gateway_config = GatewayConfig.from_file(config.config_path)
    if config.elapsed_s is not None and gateway_config.sdc.adapter == "simulated":
        gateway_config = gateway_config.model_copy(deep=True)
        gateway_config.sdc.simulation_elapsed_s = config.elapsed_s
    mapping = load_mapping(config.mie_path)
    tasks = TaskDocument.from_file(config.tasks_path)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    recorder = JsonlRecorder(gateway_config.gateway.log_file)
    registry = _make_registry(gateway_config, mapping, recorder=recorder)
    agent = OracleAgent(registry)

    task_results = [agent.run_task(task, config.scenario) for task in tasks.tasks]
    passed_count = sum(1 for result in task_results if result.get("passed") is True)
    failed_count = len(task_results) - passed_count
    health = registry.read("sdc://health").model_dump().get("data", {})
    run_id = f"{config.run_label}-{config.scenario}-{_now_compact()}"
    json_path = config.output_dir / f"{run_id}.json"
    csv_path = config.output_dir / f"{run_id}.csv"
    md_path = config.output_dir / f"{run_id}.md"

    report: dict[str, Any] = {
        "status": "ok" if failed_count == 0 else "failed",
        "run_id": run_id,
        "scenario": config.scenario,
        "agent": config.agent,
        "config": str(config.config_path),
        "mie": str(config.mie_path),
        "tasks": str(config.tasks_path),
        "adapter": gateway_config.sdc.adapter,
        "mapping_version": mapping.version,
        "resource_count": len(registry.list_resource_uris()),
        "task_count": len(task_results),
        "passed_count": passed_count,
        "failed_count": failed_count,
        "safety_boundary": {
            "mode": health.get("mode"),
            "tools_exported": health.get("tools_exported"),
            "write_operations_allowed": health.get("write_operations_allowed"),
        },
        "results": task_results,
        "output_json": str(json_path),
        "output_csv": str(csv_path),
        "output_markdown": str(md_path),
    }

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_csv(csv_path, report)
    _write_markdown(md_path, report)
    return report


def _write_csv(path: Path, report: dict[str, Any]) -> None:
    fields = [
        "run_id",
        "scenario",
        "agent",
        "task_id",
        "kind",
        "passed",
        "response",
        "observed_json",
        "expected_json",
        "checks_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for result in report.get("results", []):
            writer.writerow(
                {
                    "run_id": report.get("run_id"),
                    "scenario": report.get("scenario"),
                    "agent": report.get("agent"),
                    "task_id": result.get("task_id"),
                    "kind": result.get("kind"),
                    "passed": result.get("passed"),
                    "response": result.get("response"),
                    "observed_json": json.dumps(result.get("observed"), ensure_ascii=False, sort_keys=True),
                    "expected_json": json.dumps(result.get("expected"), ensure_ascii=False, sort_keys=True),
                    "checks_json": json.dumps(result.get("checks"), ensure_ascii=False, sort_keys=True),
                }
            )


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        f"# Agent evaluation: {report.get('scenario')}",
        "",
        f"- Run ID: `{report.get('run_id')}`",
        f"- Agent: `{report.get('agent')}`",
        f"- Status: `{report.get('status')}`",
        f"- Passed tasks: {report.get('passed_count')}/{report.get('task_count')}",
        f"- Resource count: {report.get('resource_count')}",
        "",
        "## Safety boundary",
        "",
        f"- Mode: `{report.get('safety_boundary', {}).get('mode')}`",
        f"- Tools exported: `{report.get('safety_boundary', {}).get('tools_exported')}`",
        f"- Write operations allowed: `{report.get('safety_boundary', {}).get('write_operations_allowed')}`",
        "",
        "## Task results",
        "",
        "| Task | Kind | Passed | Response |",
        "|---|---|---:|---|",
    ]
    for result in report.get("results", []):
        response = str(result.get("response", "")).replace("\n", "<br>").replace("|", "\\|")
        lines.append(f"| `{result.get('task_id')}` | `{result.get('kind')}` | {result.get('passed')} | {response} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
