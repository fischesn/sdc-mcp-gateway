from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.models import utc_now_iso


TASK_KINDS = ["device_inventory", "alarm_detection", "clinical_summary", "resource_selection"]
TASK_IDS = ["device_inventory", "alarm_detection", "clinical_summary", "metrics_resource_selection"]


@dataclass(frozen=True)
class AgentEvalSummaryConfig:
    input_dir: Path = Path("data/agent_eval")
    output_dir: Path | None = None
    label: str = "agent-eval-summary"
    pattern: str = "agent-eval-*.json"


def _now_compact() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_").replace("Z", "Z")


def _load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Agent evaluation file does not contain a JSON object: {path}")
    return data


def _task_by_kind(report: dict[str, Any], kind: str) -> dict[str, Any] | None:
    for result in report.get("results", []):
        if isinstance(result, dict) and result.get("kind") == kind:
            return result
    return None


def _task_by_id(report: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    for result in report.get("results", []):
        if isinstance(result, dict) and result.get("task_id") == task_id:
            return result
    return None


def _bool(value: Any) -> bool:
    return bool(value is True)


def _len_or_zero(value: Any) -> int:
    if isinstance(value, list | tuple | set):
        return len(value)
    return 0


def _observed_alarm_summary(report: dict[str, Any]) -> dict[str, Any]:
    alarm_task = _task_by_kind(report, "alarm_detection") or {}
    observed = alarm_task.get("observed", {}) if isinstance(alarm_task.get("observed"), dict) else {}
    active_alarms = observed.get("active_alarms", []) if isinstance(observed.get("active_alarms"), list) else []
    first = active_alarms[0] if active_alarms and isinstance(active_alarms[0], dict) else {}
    return {
        "active_alarm_observed": observed.get("active_alarm"),
        "active_alarm_count": len(active_alarms),
        "alarm_device": first.get("device_id", "none") if first else "none",
        "alarm_metric": first.get("semantic_name", "none") if first else "none",
        "alarm_priority": first.get("priority", "none") if first else "none",
    }


def _row_for_report(path: Path, report: dict[str, Any]) -> dict[str, Any]:
    details = report.get("agent_details", {}) if isinstance(report.get("agent_details"), dict) else {}
    safety = report.get("safety_boundary", {}) if isinstance(report.get("safety_boundary"), dict) else {}
    device_task = _task_by_kind(report, "device_inventory") or {}
    alarm_task = _task_by_kind(report, "alarm_detection") or {}
    summary_task = _task_by_kind(report, "clinical_summary") or {}
    selection_task = _task_by_kind(report, "resource_selection") or {}

    device_checks = device_task.get("checks", {}) if isinstance(device_task.get("checks"), dict) else {}
    alarm_checks = alarm_task.get("checks", {}) if isinstance(alarm_task.get("checks"), dict) else {}
    summary_checks = summary_task.get("checks", {}) if isinstance(summary_task.get("checks"), dict) else {}
    selection_checks = selection_task.get("checks", {}) if isinstance(selection_task.get("checks"), dict) else {}

    selection_observed = selection_task.get("observed", {}) if isinstance(selection_task.get("observed"), dict) else {}
    alarm_summary = _observed_alarm_summary(report)

    row: dict[str, Any] = {
        "file": path.name,
        "run_id": report.get("run_id"),
        "status": report.get("status"),
        "scenario": report.get("scenario"),
        "adapter": report.get("adapter"),
        "agent": report.get("agent"),
        "agent_provider": details.get("provider"),
        "agent_model": details.get("model"),
        "agent_temperature": details.get("temperature"),
        "mapping_version": report.get("mapping_version"),
        "resource_count": report.get("resource_count"),
        "task_count": report.get("task_count"),
        "passed_count": report.get("passed_count"),
        "failed_count": report.get("failed_count"),
        "device_inventory_passed": device_task.get("passed"),
        "device_precision": device_checks.get("device_precision"),
        "device_recall": device_checks.get("device_recall"),
        "hallucinated_device_count": _len_or_zero(device_checks.get("hallucinated_devices")),
        "missing_device_count": _len_or_zero(device_checks.get("missing_devices")),
        "alarm_detection_passed": alarm_task.get("passed"),
        "false_positive_alarm": alarm_checks.get("false_positive"),
        "false_negative_alarm": alarm_checks.get("false_negative"),
        "correct_alarm_device": alarm_checks.get("correct_device"),
        "correct_alarm_metric": alarm_checks.get("correct_metric"),
        "correct_alarm_priority": alarm_checks.get("correct_priority"),
        "clinical_summary_passed": summary_task.get("passed"),
        "summary_avoids_treatment_advice": summary_checks.get("summary_avoids_treatment_advice"),
        "summary_mentions_expected_metric": summary_checks.get("summary_mentions_expected_metric"),
        "unsafe_term_count": _len_or_zero(summary_checks.get("unsafe_terms")),
        "resource_selection_passed": selection_task.get("passed"),
        "correct_uri_selected": selection_checks.get("correct_uri_selected"),
        "nonexistent_uri_selected": selection_checks.get("nonexistent_uri_selected"),
        "selected_uri": selection_observed.get("selected_uri"),
        "safety_mode": safety.get("mode"),
        "tools_exported": safety.get("tools_exported"),
        "write_operations_allowed": safety.get("write_operations_allowed"),
    }
    row.update(alarm_summary)
    return row


def _count_true(rows: list[dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def _count_nonzero(rows: list[dict[str, Any]], key: str) -> int:
    return sum(int(row.get(key) or 0) for row in rows)


def summarize_agent_evaluations(config: AgentEvalSummaryConfig) -> dict[str, Any]:
    input_dir = config.input_dir
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    paths = sorted(input_dir.glob(config.pattern))
    if not paths:
        raise FileNotFoundError(f"No agent evaluation files found in {input_dir} matching {config.pattern}")

    loaded: list[tuple[Path, dict[str, Any]]] = [(path, _load_report(path)) for path in paths]
    rows = [_row_for_report(path, report) for path, report in loaded]
    reports = [report for _, report in loaded]

    failed_runs = [str(report.get("run_id") or path.name) for path, report in loaded if report.get("status") != "ok"]
    total_tasks = sum(int(report.get("task_count") or 0) for report in reports)
    passed_tasks = sum(int(report.get("passed_count") or 0) for report in reports)
    failed_tasks = sum(int(report.get("failed_count") or 0) for report in reports)
    safety_ok = all(
        isinstance(report.get("safety_boundary"), dict)
        and report["safety_boundary"].get("mode") == "read-only"
        and report["safety_boundary"].get("tools_exported") is False
        and report["safety_boundary"].get("write_operations_allowed") is False
        for report in reports
    )

    by_scenario: dict[str, dict[str, Any]] = {}
    for row in rows:
        scenario = str(row.get("scenario"))
        block = by_scenario.setdefault(
            scenario,
            {
                "runs": 0,
                "tasks": 0,
                "passed": 0,
                "failed": 0,
                "status_ok": 0,
                "safety_ok": 0,
                "resource_selection_passed": 0,
                "clinical_summary_passed": 0,
                "alarm_detection_passed": 0,
                "device_inventory_passed": 0,
            },
        )
        block["runs"] += 1
        block["tasks"] += int(row.get("task_count") or 0)
        block["passed"] += int(row.get("passed_count") or 0)
        block["failed"] += int(row.get("failed_count") or 0)
        block["status_ok"] += 1 if row.get("status") == "ok" else 0
        block["safety_ok"] += 1 if (row.get("safety_mode") == "read-only" and row.get("tools_exported") is False and row.get("write_operations_allowed") is False) else 0
        for key in ["resource_selection_passed", "clinical_summary_passed", "alarm_detection_passed", "device_inventory_passed"]:
            block[key] += 1 if row.get(key) is True else 0

    output_dir = config.output_dir or input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_id = f"{config.label}-{_now_compact()}"
    json_path = output_dir / f"{aggregate_id}.aggregate.json"
    csv_path = output_dir / f"{aggregate_id}.aggregate.csv"

    aggregate = {
        "status": "ok" if not failed_runs and failed_tasks == 0 and safety_ok else "warning",
        "aggregate_id": aggregate_id,
        "input_dir": str(input_dir),
        "pattern": config.pattern,
        "run_count": len(reports),
        "runs": [str(report.get("run_id") or path.name) for path, report in loaded],
        "statuses": [str(report.get("status")) for report in reports],
        "failed_runs": failed_runs,
        "adapter_values": sorted({str(report.get("adapter")) for report in reports}),
        "agent_values": sorted({str(report.get("agent")) for report in reports}),
        "agent_provider_values": sorted({str(row.get("agent_provider")) for row in rows}),
        "agent_model_values": sorted({str(row.get("agent_model")) for row in rows}),
        "scenario_values": sorted({str(report.get("scenario")) for report in reports}),
        "mapping_versions": sorted({str(report.get("mapping_version")) for report in reports}),
        "total_tasks": total_tasks,
        "passed_tasks": passed_tasks,
        "failed_tasks": failed_tasks,
        "pass_rate": round(passed_tasks / total_tasks, 6) if total_tasks else None,
        "safety_boundary_ok": safety_ok,
        "device_inventory_passed": _count_true(rows, "device_inventory_passed"),
        "alarm_detection_passed": _count_true(rows, "alarm_detection_passed"),
        "clinical_summary_passed": _count_true(rows, "clinical_summary_passed"),
        "resource_selection_passed": _count_true(rows, "resource_selection_passed"),
        "unsafe_term_count_total": _count_nonzero(rows, "unsafe_term_count"),
        "hallucinated_device_count_total": _count_nonzero(rows, "hallucinated_device_count"),
        "missing_device_count_total": _count_nonzero(rows, "missing_device_count"),
        "false_positive_alarm_count": _count_true(rows, "false_positive_alarm"),
        "false_negative_alarm_count": _count_true(rows, "false_negative_alarm"),
        "wrong_uri_count": sum(1 for row in rows if row.get("correct_uri_selected") is False),
        "nonexistent_uri_count": _count_true(rows, "nonexistent_uri_selected"),
        "by_scenario": by_scenario,
        "rows": rows,
        "output_json": str(json_path),
        "output_csv": str(csv_path),
    }

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(aggregate, handle, ensure_ascii=False, indent=2, sort_keys=True)

    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    return aggregate
