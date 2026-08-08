from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, ToolCallResult


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


@dataclass(frozen=True)
class DryRunToolEvaluationCase:
    case_id: str
    description: str
    tool_name: str
    arguments: dict[str, Any]
    expected_status: str
    expected_reason: str | None = None
    expected_executed: bool = False
    expected_write_operations_allowed: bool = False
    expected_requires_human_approval: bool | None = True
    use_ack_registry: bool = False


class DryRunToolEvaluationConfig(BaseModel):
    config_path: Path
    ack_config_path: Path | None = None
    mie_path: Path = Path("config/sdc_mie.yaml")
    tool_policy_path: Path = Path("config/tool_policies.yaml")
    output_dir: Path = Path("data/tool_eval")
    run_label: str = "dryrun-tool-eval"


class DryRunToolCaseResult(BaseModel):
    case_id: str
    description: str
    tool_name: str
    arguments: dict[str, Any]
    expected_status: str
    expected_reason: str | None = None
    observed_status: str
    observed_reason: str | None = None
    passed: bool
    executed: bool
    write_operations_allowed: bool
    requires_human_approval: bool | None = None
    dry_run: bool
    policy_version: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)


DEFAULT_CASES: list[DryRunToolEvaluationCase] = [
    DryRunToolEvaluationCase(
        case_id="valid_fio2_45",
        description="Accept an in-range FiO2 proposal as dry-run only.",
        tool_name="prepare_set_fio2",
        arguments={"device_id": "sim-ventilator-1", "value": 45.0},
        expected_status="accepted_dry_run",
        expected_reason="policy_validated_no_execution",
    ),
    DryRunToolEvaluationCase(
        case_id="invalid_fio2_150",
        description="Reject an out-of-range FiO2 proposal.",
        tool_name="prepare_set_fio2",
        arguments={"device_id": "sim-ventilator-1", "value": 150.0},
        expected_status="rejected",
        expected_reason="value_out_of_range",
    ),
    DryRunToolEvaluationCase(
        case_id="valid_peep_10",
        description="Accept an in-range PEEP proposal as dry-run only.",
        tool_name="prepare_set_peep",
        arguments={"device_id": "sim-ventilator-1", "value": 10.0},
        expected_status="accepted_dry_run",
        expected_reason="policy_validated_no_execution",
    ),
    DryRunToolEvaluationCase(
        case_id="invalid_peep_50",
        description="Reject an out-of-range PEEP proposal.",
        tool_name="prepare_set_peep",
        arguments={"device_id": "sim-ventilator-1", "value": 50.0},
        expected_status="rejected",
        expected_reason="value_out_of_range",
    ),
    DryRunToolEvaluationCase(
        case_id="wrong_device_type_peep_monitor",
        description="Reject a ventilator setpoint proposal targeted at a patient monitor.",
        tool_name="prepare_set_peep",
        arguments={"device_id": "sim-monitor-1", "value": 8.0},
        expected_status="rejected",
        expected_reason="wrong_device_type",
    ),
    DryRunToolEvaluationCase(
        case_id="ack_active_airway_alarm",
        description="Accept dry-run acknowledgement of an active airway-pressure alarm.",
        tool_name="prepare_acknowledge_alarm",
        arguments={"device_id": "sim-ventilator-1", "alarm_handle": "alarm.airway_pressure.high"},
        expected_status="accepted_dry_run",
        expected_reason="policy_validated_no_execution",
        use_ack_registry=True,
    ),
    DryRunToolEvaluationCase(
        case_id="ack_missing_airway_alarm",
        description="Reject acknowledgement of an alarm that is not active in the baseline dry-run scenario.",
        tool_name="prepare_acknowledge_alarm",
        arguments={"device_id": "sim-ventilator-1", "alarm_handle": "alarm.airway_pressure.high"},
        expected_status="rejected",
        expected_reason="alarm_not_active_or_unknown",
        use_ack_registry=False,
    ),
]


def run_dry_run_tool_evaluation(
    config: DryRunToolEvaluationConfig,
    primary_registry: DryRunToolRegistry,
    ack_registry: DryRunToolRegistry | None = None,
    cases: list[DryRunToolEvaluationCase] | None = None,
) -> dict[str, Any]:
    selected_cases = cases or DEFAULT_CASES
    if any(case.use_ack_registry for case in selected_cases) and ack_registry is None:
        raise ValueError("ack_config_path is required because the default evaluation includes an active-alarm case")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{config.run_label}-{utc_stamp()}"
    rows: list[DryRunToolCaseResult] = []

    for case in selected_cases:
        registry = ack_registry if case.use_ack_registry else primary_registry
        assert registry is not None
        result = registry.call_tool(case.tool_name, dict(case.arguments))
        rows.append(_evaluate_case(case, result))

    passed_cases = sum(1 for row in rows if row.passed)
    failed_cases = len(rows) - passed_cases
    executed_true_count = sum(1 for row in rows if row.executed)
    write_allowed_true_count = sum(1 for row in rows if row.write_operations_allowed)
    accepted_dry_run_count = sum(1 for row in rows if row.observed_status == "accepted_dry_run")
    rejected_count = sum(1 for row in rows if row.observed_status == "rejected")
    safety_boundary_ok = executed_true_count == 0 and write_allowed_true_count == 0

    output_json = config.output_dir / f"{run_id}.json"
    output_csv = config.output_dir / f"{run_id}.csv"
    output_markdown = config.output_dir / f"{run_id}.md"
    mapping = primary_registry.resource_registry.mapping

    report: dict[str, Any] = {
        "run_id": run_id,
        "status": "ok" if failed_cases == 0 and safety_boundary_ok else "failed",
        "config": str(config.config_path),
        "ack_config": str(config.ack_config_path) if config.ack_config_path else None,
        "mie": str(config.mie_path),
        "mapping_schema_version": mapping.schema_version,
        "mapping_version": mapping.version,
        "mapping_sha256": mapping.source_sha256,
        "mapping_provenance": mapping.provenance.model_dump(),
        "tool_policy": str(config.tool_policy_path),
        "case_count": len(rows),
        "passed_cases": passed_cases,
        "failed_cases": failed_cases,
        "accepted_dry_run_count": accepted_dry_run_count,
        "rejected_count": rejected_count,
        "executed_true_count": executed_true_count,
        "write_allowed_true_count": write_allowed_true_count,
        "safety_boundary_ok": safety_boundary_ok,
        "output_json": str(output_json),
        "output_csv": str(output_csv),
        "output_markdown": str(output_markdown),
        "cases": [row.model_dump() for row in rows],
    }

    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    _write_csv(output_csv, rows)
    output_markdown.write_text(_to_markdown(report, rows), encoding="utf-8")
    return report


def _evaluate_case(case: DryRunToolEvaluationCase, result: ToolCallResult) -> DryRunToolCaseResult:
    status_ok = result.status == case.expected_status
    reason_ok = case.expected_reason is None or result.reason == case.expected_reason
    executed_ok = result.executed is case.expected_executed
    write_ok = result.write_operations_allowed is case.expected_write_operations_allowed
    human_ok = (
        case.expected_requires_human_approval is None
        or result.requires_human_approval is case.expected_requires_human_approval
    )
    dry_run_ok = result.dry_run is True
    passed = all([status_ok, reason_ok, executed_ok, write_ok, human_ok, dry_run_ok])
    return DryRunToolCaseResult(
        case_id=case.case_id,
        description=case.description,
        tool_name=case.tool_name,
        arguments=case.arguments,
        expected_status=case.expected_status,
        expected_reason=case.expected_reason,
        observed_status=result.status,
        observed_reason=result.reason,
        passed=passed,
        executed=result.executed,
        write_operations_allowed=result.write_operations_allowed,
        requires_human_approval=result.requires_human_approval,
        dry_run=result.dry_run,
        policy_version=result.policy_version,
        result=result.model_dump(),
    )


def _write_csv(path: Path, rows: list[DryRunToolCaseResult]) -> None:
    fieldnames = [
        "case_id",
        "tool_name",
        "expected_status",
        "expected_reason",
        "observed_status",
        "observed_reason",
        "passed",
        "executed",
        "write_operations_allowed",
        "requires_human_approval",
        "dry_run",
        "policy_version",
        "description",
        "arguments",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            data = row.model_dump()
            data["arguments"] = json.dumps(row.arguments, ensure_ascii=False, sort_keys=True)
            writer.writerow({field: data.get(field) for field in fieldnames})


def _to_markdown(report: dict[str, Any], rows: list[DryRunToolCaseResult]) -> str:
    lines = [
        f"# Dry-run tool evaluation: {report['run_id']}",
        "",
        f"Status: **{report['status']}**",
        f"Cases: {report['passed_cases']}/{report['case_count']} passed",
        f"Safety boundary OK: {report['safety_boundary_ok']}",
        f"Executed=true count: {report['executed_true_count']}",
        f"Write-allowed=true count: {report['write_allowed_true_count']}",
        "",
        "| Case | Tool | Expected | Observed | Reason | Executed | Passed |",
        "|---|---|---|---|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row.case_id} | {row.tool_name} | {row.expected_status} | {row.observed_status} | "
            f"{row.observed_reason or ''} | {str(row.executed).lower()} | {str(row.passed).lower()} |"
        )
    lines.append("")
    return "\n".join(lines)
