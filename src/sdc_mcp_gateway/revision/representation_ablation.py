from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.agent_eval.harness import (
    JsonTaskLlmClient,
    LlmBackendError,
    LlmTaskAgent,
    TaskDocument,
    _agent_context,
    _make_gateway_config_with_elapsed,
    _make_registry,
)
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.revision.pipeline import assert_anonymous_payload


Representation = Literal[
    "raw_normalized_sdc",
    "generic_mcp",
    "sdc_mie_enriched",
]


class ScenarioSpec(BaseModel):
    id: str
    config: Path
    elapsed_s: float = 100.0


class ModelSpec(BaseModel):
    id: str
    provider: str
    model_id: str
    endpoint: str
    api_key_env: str
    repetitions: int = Field(default=3, ge=1)
    temperature: float = 0.0
    timeout_s: float = 60.0
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None


class AblationConfig(BaseModel):
    version: str
    study_id: str
    description: str
    tasks: Path
    mie: Path
    freeze_lock: Path
    output_dir: Path
    scenarios: list[ScenarioSpec]
    model: ModelSpec
    execute_representations: list[Representation]
    proposed_report_glob: str
    deterministic_report_glob: str
    tracked_files: list[Path]

    @classmethod
    def from_file(cls, path: str | Path) -> "AblationConfig":
        loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected a YAML mapping at {path}")
        config = cls.model_validate(loaded)
        if config.execute_representations != ["raw_normalized_sdc", "generic_mcp"]:
            raise ValueError(
                "WP8 execution is sealed to raw_normalized_sdc followed by generic_mcp"
            )
        return config


@dataclass(frozen=True)
class ContextStats:
    utf8_bytes: int
    scalar_fields: int
    maximum_depth: int


class FixedContextLlmTaskAgent(LlmTaskAgent):
    def __init__(
        self, registry: Any, client: JsonTaskLlmClient, context: dict[str, Any]
    ) -> None:
        super().__init__(registry, client)
        self.fixed_context = context

    def _context(self) -> dict[str, Any]:
        return self.fixed_context


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")


def _relative(path: Path) -> str:
    return path.resolve().relative_to(Path.cwd().resolve()).as_posix()


def _selected_reference_reports(config: AblationConfig) -> list[Path]:
    proposed = sorted(Path.cwd().glob(config.proposed_report_glob))
    deterministic = sorted(Path.cwd().glob(config.deterministic_report_glob))
    if len(proposed) != len(config.scenarios) * config.model.repetitions:
        raise ValueError(
            f"Expected {len(config.scenarios) * config.model.repetitions} proposed reports, "
            f"found {len(proposed)}"
        )
    if len(deterministic) != len(config.scenarios):
        raise ValueError(
            f"Expected {len(config.scenarios)} deterministic reports, found {len(deterministic)}"
        )
    return [*deterministic, *proposed]


def build_ablation_lock(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    config = AblationConfig.from_file(path)
    files = [path, config.tasks, config.mie, *config.tracked_files]
    files.extend(scenario.config for scenario in config.scenarios)
    files.extend(_selected_reference_reports(config))
    unique = sorted({item.resolve() for item in files}, key=lambda item: _relative(item))
    entries = [
        {"path": _relative(item), "bytes": item.stat().st_size, "sha256": _sha256(item)}
        for item in unique
    ]
    lock = {
        "schema_version": "1",
        "study_id": config.study_id,
        "version": config.version,
        "execution_plan": {
            "model_id": config.model.model_id,
            "temperature": config.model.temperature,
            "repetitions": config.model.repetitions,
            "new_representations": config.execute_representations,
            "reused_representation": "sdc_mie_enriched",
            "reused_source": "frozen_wp7_reports",
        },
        "input_files": entries,
    }
    lock["input_set_sha256"] = _canonical_hash(entries)
    assert_anonymous_payload(lock)
    return lock


def write_ablation_lock(config_path: str | Path) -> dict[str, Any]:
    config = AblationConfig.from_file(config_path)
    lock = build_ablation_lock(config_path)
    config.freeze_lock.parent.mkdir(parents=True, exist_ok=True)
    config.freeze_lock.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return lock


def verify_ablation_lock(config_path: str | Path) -> dict[str, Any]:
    config = AblationConfig.from_file(config_path)
    expected = json.loads(config.freeze_lock.read_text(encoding="utf-8"))
    actual = build_ablation_lock(config_path)
    if actual != expected:
        raise ValueError("WP8 ablation inputs do not match the frozen lock")
    return actual


def _raw_metric_facts(registry: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        device_id: [metric.model_dump(mode="json") for metric in device.metrics]
        for device_id, device in sorted(registry.devices.items())
    }


def _raw_alarm_facts(registry: Any) -> dict[str, list[dict[str, Any]]]:
    return {
        device_id: [alarm.model_dump(mode="json") for alarm in device.alarms]
        for device_id, device in sorted(registry.devices.items())
    }


def _generic_resources(registry: Any) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    for descriptor in registry.list_resource_descriptors():
        uri = descriptor.uri
        parts = uri.removeprefix("sdc://").split("/")
        device_id = parts[1] if len(parts) >= 3 and parts[0] == "devices" else None
        resource_kind = "/".join(parts[2:]) if device_id else "global"
        resources.append(
            {
                "uri": uri,
                "name": resource_kind.replace("/", " "),
                "description": "Read-only generic MCP resource",
                "mime_type": descriptor.mime_type,
                "device_id": device_id,
                "resource_kind": resource_kind,
            }
        )
    return resources


def _generic_active_alarms(registry: Any) -> list[dict[str, Any]]:
    metrics = _raw_metric_facts(registry)
    alarms = _raw_alarm_facts(registry)
    active: list[dict[str, Any]] = []
    for device_id, device_alarms in alarms.items():
        by_handle = {str(item.get("handle")): item for item in metrics.get(device_id, [])}
        for alarm in device_alarms:
            if alarm.get("presence") is not True:
                continue
            raw = alarm.get("raw") if isinstance(alarm.get("raw"), dict) else {}
            metric_handle = raw.get("metric_handle")
            metric = by_handle.get(str(metric_handle), {})
            active.append(
                {
                    "device_id": device_id,
                    "alarm_handle": alarm.get("handle"),
                    "alarm_code": alarm.get("code"),
                    "priority": alarm.get("priority"),
                    "kind": alarm.get("kind"),
                    "metric_handle": metric_handle,
                    "metric_code": metric.get("code"),
                    "metric_value": metric.get("value"),
                    "metric_unit": metric.get("unit"),
                }
            )
    return active


def build_representation_context(registry: Any, representation: Representation) -> dict[str, Any]:
    if representation == "sdc_mie_enriched":
        return _agent_context(registry)
    if representation == "raw_normalized_sdc":
        return {
            "normalized_sdc_snapshots": [
                device.model_dump(mode="json")
                for _, device in sorted(registry.devices.items())
            ]
        }
    if representation == "generic_mcp":
        health = registry.read("sdc://health").model_dump(mode="json").get("data", {})
        generic_health = {
            key: value
            for key, value in health.items()
            if key
            not in {
                "mapping_version",
                "mapping_schema_version",
                "mapping_sha256",
            }
        }
        return {
            "resources": _generic_resources(registry),
            "health": generic_health,
            "devices": registry.read("sdc://devices").model_dump(mode="json").get("data", []),
            "metrics_by_device": _raw_metric_facts(registry),
            "alarms_by_device": _raw_alarm_facts(registry),
            "active_alarms": _generic_active_alarms(registry),
        }
    raise ValueError(f"Unsupported representation: {representation}")


def _complexity(value: Any, depth: int = 0) -> tuple[int, int]:
    if isinstance(value, dict):
        totals = [_complexity(item, depth + 1) for item in value.values()]
        return len(value) + sum(item[0] for item in totals), max(
            [depth, *(item[1] for item in totals)]
        )
    if isinstance(value, list):
        totals = [_complexity(item, depth + 1) for item in value]
        return sum(item[0] for item in totals), max([depth, *(item[1] for item in totals)])
    return 1, depth


def context_stats(context: dict[str, Any]) -> ContextStats:
    rendered = json.dumps(context, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    fields, maximum_depth = _complexity(context)
    return ContextStats(
        utf8_bytes=len(rendered.encode("utf-8")),
        scalar_fields=fields,
        maximum_depth=maximum_depth,
    )


def _load_tasks(config: AblationConfig, scenario: ScenarioSpec) -> list[Any]:
    return [
        task
        for task in TaskDocument.from_file(config.tasks).tasks
        if task.scenarios is None or scenario.id in task.scenarios
    ]


def _build_registry(config: AblationConfig, scenario: ScenarioSpec) -> Any:
    gateway = _make_gateway_config_with_elapsed(scenario.config, scenario.elapsed_s)
    mapping = load_mapping(config.mie)
    return _make_registry(gateway, mapping, recorder=None)


def validate_ablation_plan(config_path: str | Path) -> dict[str, Any]:
    config = AblationConfig.from_file(config_path)
    scenarios: list[dict[str, Any]] = []
    total_tasks = 0
    for scenario in config.scenarios:
        registry = _build_registry(config, scenario)
        tasks = _load_tasks(config, scenario)
        total_tasks += len(tasks)
        contexts = {
            representation: build_representation_context(registry, representation)
            for representation in (
                "raw_normalized_sdc",
                "generic_mcp",
                "sdc_mie_enriched",
            )
        }
        scenarios.append(
            {
                "scenario": scenario.id,
                "task_count": len(tasks),
                "context_sha256": {
                    key: _canonical_hash(value) for key, value in contexts.items()
                },
                "context_stats": {
                    key: context_stats(value).__dict__ for key, value in contexts.items()
                },
            }
        )
    plan = {
        "status": "ready",
        "version": config.version,
        "model_id": config.model.model_id,
        "scenario_count": len(config.scenarios),
        "matched_task_count": total_tasks,
        "new_external_case_count": total_tasks
        * len(config.execute_representations)
        * config.model.repetitions,
        "reused_proposed_case_count": total_tasks * config.model.repetitions,
        "scenarios": scenarios,
    }
    assert_anonymous_payload(plan)
    return plan


def _run_report(
    config: AblationConfig,
    scenario: ScenarioSpec,
    representation: Representation,
    repetition: int,
    output_dir: Path,
) -> dict[str, Any]:
    registry = _build_registry(config, scenario)
    context = build_representation_context(registry, representation)
    client = JsonTaskLlmClient(
        provider=config.model.provider,
        model=config.model.model_id,
        endpoint=config.model.endpoint,
        api_key_env=config.model.api_key_env,
        timeout_s=config.model.timeout_s,
        temperature=config.model.temperature,
        input_usd_per_million=config.model.input_usd_per_million,
        output_usd_per_million=config.model.output_usd_per_million,
    )
    agent = FixedContextLlmTaskAgent(registry, client, context)
    results: list[dict[str, Any]] = []
    external_error: str | None = None
    for task in _load_tasks(config, scenario):
        if external_error is not None:
            results.append(
                {
                    "task_id": task.id,
                    "kind": task.kind,
                    "passed": None,
                    "evaluation_status": "not_evaluable_external_endpoint",
                    "external_error_class": external_error,
                }
            )
            continue
        try:
            results.append(agent.run_task(task, scenario.id))
        except LlmBackendError as exc:
            external_error = type(exc).__name__
            results.append(
                {
                    "task_id": task.id,
                    "kind": task.kind,
                    "passed": None,
                    "evaluation_status": "not_evaluable_external_endpoint",
                    "external_error_class": external_error,
                }
            )
    passed = sum(item.get("passed") is True for item in results)
    failed = sum(item.get("passed") is False for item in results)
    report = {
        "status": "external_endpoint_error"
        if external_error
        else ("ok" if failed == 0 else "failed"),
        "study_id": config.study_id,
        "version": config.version,
        "representation": representation,
        "source": "wp8_new_execution",
        "scenario": scenario.id,
        "repetition": repetition,
        "model": {
            "id": config.model.id,
            "provider": config.model.provider,
            "model_id": config.model.model_id,
            "temperature": config.model.temperature,
        },
        "context_sha256": _canonical_hash(context),
        "context_stats": context_stats(context).__dict__,
        "valid_resource_uris": registry.list_resource_uris(),
        "task_count": len(results),
        "evaluable_task_count": passed + failed,
        "passed_count": passed,
        "failed_count": failed,
        "external_error_count": len(results) - passed - failed,
        "results": results,
    }
    assert_anonymous_payload(report)
    output = output_dir / f"{representation}-{scenario.id}-r{repetition}.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def _wilson(passed: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    proportion = passed / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * ((proportion * (1 - proportion) / total + z * z / (4 * total * total)) ** 0.5) / denominator
    return [round(max(0.0, centre - margin), 6), round(min(1.0, centre + margin), 6)]


def _aggregate_reports(reports: list[dict[str, Any]]) -> dict[str, Any]:
    tasks = [item for report in reports for item in report.get("results", [])]
    evaluable = [item for item in tasks if item.get("passed") in {True, False}]
    passed = sum(item.get("passed") is True for item in evaluable)
    by_kind: dict[str, dict[str, int | float | None]] = {}
    by_task: dict[str, dict[str, int | float | None]] = {}
    for key_name, target in (("kind", by_kind), ("task_id", by_task)):
        for key in sorted({str(item.get(key_name)) for item in evaluable}):
            selected = [item for item in evaluable if str(item.get(key_name)) == key]
            selected_passed = sum(item.get("passed") is True for item in selected)
            target[key] = {
                "cases": len(selected),
                "passed": selected_passed,
                "pass_rate": round(selected_passed / len(selected), 6) if selected else None,
            }
    valid_uris = {
        str(uri) for report in reports for uri in report.get("valid_resource_uris", [])
    }
    selected_uris = [
        str(item.get("observed", {}).get("selected_uri") or "")
        for item in evaluable
        if isinstance(item.get("observed"), dict)
        and "selected_uri" in item.get("observed", {})
    ]
    hallucinated = [uri for uri in selected_uris if uri and uri not in valid_uris]
    unsafe = sum(
        bool(item.get("checks", {}).get("unsafe_terms"))
        for item in evaluable
        if isinstance(item.get("checks"), dict)
    )
    groups = {
        "device_metric_uri_selection": {
            "device_inventory",
            "metric_selection",
            "resource_selection",
            "prompt_injection_resistance",
        },
        "alarm_interpretation": {
            "alarm_detection",
            "alarm_set_interpretation",
            "clinical_summary",
        },
        "abstention_and_boundary": {
            "mapping_abstention",
            "availability_detection",
            "boundary_refusal",
        },
    }
    grouped: dict[str, Any] = {}
    for name, kinds in groups.items():
        selected = [item for item in evaluable if item.get("kind") in kinds]
        group_passed = sum(item.get("passed") is True for item in selected)
        grouped[name] = {
            "cases": len(selected),
            "passed": group_passed,
            "pass_rate": round(group_passed / len(selected), 6) if selected else None,
        }
    return {
        "report_count": len(reports),
        "scheduled_cases": len(tasks),
        "evaluable_cases": len(evaluable),
        "external_error_cases": len(tasks) - len(evaluable),
        "passed_cases": passed,
        "failed_cases": len(evaluable) - passed,
        "pass_rate": round(passed / len(evaluable), 6) if evaluable else None,
        "accuracy_95ci": _wilson(passed, len(evaluable)),
        "hallucinated_resource_uri_count": len(hallucinated),
        "unsafe_recommendation_count": unsafe,
        "by_task_kind": by_kind,
        "by_task": by_task,
        "metric_groups": grouped,
    }


def _reference_reports(config: AblationConfig, pattern: str) -> list[dict[str, Any]]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(Path.cwd().glob(pattern))]


def _representation_stats(plan: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for representation in (
        "raw_normalized_sdc",
        "generic_mcp",
        "sdc_mie_enriched",
    ):
        values = [row["context_stats"][representation] for row in plan["scenarios"]]
        result[representation] = {
            "scenario_count": len(values),
            "mean_utf8_bytes": round(
                sum(item["utf8_bytes"] for item in values) / len(values), 1
            ),
            "mean_scalar_fields": round(
                sum(item["scalar_fields"] for item in values) / len(values), 1
            ),
            "maximum_depth": max(item["maximum_depth"] for item in values),
            "per_scenario": values,
        }
    return result


def _write_summary(run_dir: Path, summary: dict[str, Any]) -> None:
    (run_dir / "wp8-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows = []
    for arm, values in summary["comparison_arms"].items():
        rows.append(
            {
                "arm": arm,
                "evaluable_cases": values["evaluable_cases"],
                "passed_cases": values["passed_cases"],
                "failed_cases": values["failed_cases"],
                "pass_rate": values["pass_rate"],
                "ci_low": values["accuracy_95ci"][0] if values["accuracy_95ci"] else None,
                "ci_high": values["accuracy_95ci"][1] if values["accuracy_95ci"] else None,
                "hallucinated_resource_uri_count": values["hallucinated_resource_uri_count"],
                "unsafe_recommendation_count": values["unsafe_recommendation_count"],
            }
        )
    with (run_dir / "wp8-summary.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# WP8 representation ablation",
        "",
        f"- Input lock: `{summary['input_set_sha256']}`",
        f"- Model: `{summary['model_id']}`",
        "- Proposed arm source: frozen WP7 reports (no re-execution)",
        "",
        "| Arm | Passed / evaluable | Rate | 95% Wilson CI | Invented URIs | Unsafe |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm, values in summary["comparison_arms"].items():
        interval = values["accuracy_95ci"] or [None, None]
        lines.append(
            f"| {arm} | {values['passed_cases']}/{values['evaluable_cases']} | "
            f"{values['pass_rate']:.3f} | {interval[0]:.3f}--{interval[1]:.3f} | "
            f"{values['hallucinated_resource_uri_count']} | {values['unsafe_recommendation_count']} |"
        )
    (run_dir / "wp8-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_ablation(config_path: str | Path) -> dict[str, Any]:
    config = AblationConfig.from_file(config_path)
    lock = verify_ablation_lock(config_path)
    if not os.environ.get(config.model.api_key_env):
        raise ValueError(f"Missing API key environment variable: {config.model.api_key_env}")
    run_dir = config.output_dir / f"{config.version}-ablation-{_utc_stamp()}"
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "input.lock.json").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    new_reports: dict[str, list[dict[str, Any]]] = {
        representation: [] for representation in config.execute_representations
    }
    for representation in config.execute_representations:
        for scenario in config.scenarios:
            for repetition in range(1, config.model.repetitions + 1):
                report = _run_report(
                    config,
                    scenario,
                    representation,
                    repetition,
                    reports_dir,
                )
                new_reports[representation].append(report)
    proposed = _reference_reports(config, config.proposed_report_glob)
    deterministic = _reference_reports(config, config.deterministic_report_glob)
    plan = validate_ablation_plan(config_path)
    comparison = {
        "deterministic_same_mcp_resources": _aggregate_reports(deterministic),
        "raw_normalized_sdc": _aggregate_reports(new_reports["raw_normalized_sdc"]),
        "generic_mcp": _aggregate_reports(new_reports["generic_mcp"]),
        "sdc_mie_enriched": _aggregate_reports(proposed),
    }
    summary = {
        "status": "ok"
        if all(values["external_error_cases"] == 0 for values in comparison.values())
        else "external_endpoint_error",
        "study_id": config.study_id,
        "version": config.version,
        "input_set_sha256": lock["input_set_sha256"],
        "model_id": config.model.model_id,
        "temperature": config.model.temperature,
        "repetitions": config.model.repetitions,
        "matched_task_count": plan["matched_task_count"],
        "comparison_arms": comparison,
        "representation_complexity": _representation_stats(plan),
        "method_note": (
            "The enriched arm reuses frozen WP7 reports. Raw and generic arms were "
            "executed after this WP8 input lock was written and were not used to tune "
            "prompts, graders, mappings, or representation transforms."
        ),
    }
    assert_anonymous_payload(summary)
    _write_summary(run_dir, summary)
    result = {
        "status": summary["status"],
        "run_dir": run_dir.as_posix(),
        "input_set_sha256": lock["input_set_sha256"],
        "new_report_count": sum(len(value) for value in new_reports.values()),
        "new_external_case_count": sum(
            report["task_count"] for values in new_reports.values() for report in values
        ),
        "reused_proposed_report_count": len(proposed),
        "reused_deterministic_report_count": len(deterministic),
    }
    assert_anonymous_payload(result)
    (run_dir / "pipeline-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result


def _main() -> None:
    parser = argparse.ArgumentParser(description="WP8 representation-ablation runner")
    parser.add_argument("command", choices=("plan", "freeze", "verify", "run"))
    parser.add_argument(
        "--config", type=Path, default=Path("config/bhi2026_wp8_ablation.yaml")
    )
    args = parser.parse_args()
    if args.command == "plan":
        result = validate_ablation_plan(args.config)
    elif args.command == "freeze":
        result = write_ablation_lock(args.config)
    elif args.command == "verify":
        result = verify_ablation_lock(args.config)
    else:
        result = run_ablation(args.config)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
