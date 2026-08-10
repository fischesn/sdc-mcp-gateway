from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.safety.authorization import (
    AuthorizationContext,
    NonExecutingAuthorizationWorkflow,
    snapshot_sha256,
)
from sdc_mcp_gateway.safety.no_execution import DeviceWriteSpy
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer, WriteSpySdcConsumer
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies


class SyntheticAuthorizationCase(BaseModel):
    case_id: str
    title: str
    proposal_id: str
    tool: str
    parameters: dict[str, Any]
    proposer: str
    expiry_seconds: int = Field(gt=0)
    decision_offset_seconds: int = Field(ge=0)
    action: Literal["approve", "deny"]
    authorization: AuthorizationContext | None = None
    pre_decision_mutation: Literal["none", "stale", "device_state_changed"] = "none"
    repeat_action: Literal["approve", "deny"] | None = None
    expected_repeat_reason: str | None = None
    expected_state: str
    expected_reason: str
    review_prompt: str


class AuthorizationEvidenceSuite(BaseModel):
    schema_version: str
    evaluation_id: str
    base_time: datetime
    description: str
    expert_review: dict[str, Any]
    cases: list[SyntheticAuthorizationCase]

    @classmethod
    def from_file(cls, path: str | Path) -> "AuthorizationEvidenceSuite":
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return cls.model_validate(data)


def run_human_authorization_evidence(
    *,
    suite_path: str | Path,
    gateway_config_path: str | Path,
    mapping_path: str | Path,
    policy_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Run the deterministic WP10 workflow cases without a network or model call."""

    suite_file = Path(suite_path)
    gateway_file = Path(gateway_config_path)
    mapping_file = Path(mapping_path)
    policy_file = Path(policy_path)
    runner_file = Path(__file__)
    workflow_file = runner_file.parents[1] / "safety" / "authorization.py"
    suite = AuthorizationEvidenceSuite.from_file(suite_file)
    gateway_config = GatewayConfig.from_file(gateway_file)
    mapping = load_mapping(mapping_file)
    policies = load_tool_policies(policy_file)

    rows: list[dict[str, Any]] = []
    total_write_count = 0
    for case in suite.cases:
        spy = DeviceWriteSpy()
        consumer = WriteSpySdcConsumer(
            SimulatedSdcConsumer(
                scenario_path=gateway_config.sdc.simulation_config or "",
                elapsed_s=gateway_config.sdc.simulation_elapsed_s,
                recorder=None,
            ),
            spy,
        )
        registry = ResourceRegistry(
            devices=consumer.get_snapshots(),
            mapping=mapping,
            recorder=None,
            tools_exported=True,
            tool_mode="dry-run",
            write_operations_allowed=False,
            gateway_mode="dry-run-tools",
        )
        tools = DryRunToolRegistry(
            resource_registry=registry,
            policies=policies,
            recorder=None,
            tools_enabled=True,
            write_operations_allowed=False,
        )
        workflow = NonExecutingAuthorizationWorkflow(tools)
        base_time = suite.base_time
        proposal = workflow.propose(
            proposal_id=case.proposal_id,
            tool=case.tool,
            parameters=case.parameters,
            proposer=case.proposer,
            expires_at=base_time + timedelta(seconds=case.expiry_seconds),
            now=base_time,
        )

        _apply_mutation(registry, proposal.target_device_id, case.pre_decision_mutation)
        before_decision = snapshot_sha256(registry.devices[proposal.target_device_id])
        decision = workflow.decide(
            proposal.proposal_id,
            action=case.action,
            authorization=case.authorization,
            now=base_time + timedelta(seconds=case.decision_offset_seconds),
        )
        repeated_reason: str | None = None
        if case.repeat_action is not None:
            repeated = workflow.decide(
                proposal.proposal_id,
                action=case.repeat_action,
                authorization=case.authorization,
                now=base_time + timedelta(seconds=case.decision_offset_seconds + 1),
            )
            repeated_reason = repeated.reason
        final = workflow.get(proposal.proposal_id)
        after_decision = snapshot_sha256(registry.devices[proposal.target_device_id])
        passed = (
            final.state.value == case.expected_state
            and decision.reason == case.expected_reason
            and before_decision == after_decision
            and spy.device_write_count == 0
            and final.executed is False
            and final.write_operations_allowed is False
            and repeated_reason == case.expected_repeat_reason
        )
        rows.append(
            {
                "case_id": case.case_id,
                "title": case.title,
                "expected_state": case.expected_state,
                "observed_state": final.state.value,
                "expected_reason": case.expected_reason,
                "observed_reason": decision.reason,
                "repeat_reason": repeated_reason,
                "expected_repeat_reason": case.expected_repeat_reason,
                "transition_states": [item.state.value for item in final.transitions],
                "bound": {
                    "target_device_id": final.target_device_id,
                    "operation": final.operation,
                    "parameters": final.parameters,
                    "policy_version": final.policy_version,
                    "unit": final.unit,
                    "allowed_range": final.allowed_range,
                    "snapshot_version": final.snapshot_version,
                    "snapshot_sha256": final.snapshot_sha256,
                    "freshness_state": final.freshness_state,
                    "proposer": final.proposer,
                    "expires_at": final.expires_at.isoformat(),
                    "approval_identity": final.approval_identity,
                    "approval_reference": final.approval_reference,
                },
                "decision_recorded": decision.decision_recorded,
                "dry_run": final.dry_run,
                "executed": final.executed,
                "write_operations_allowed": final.write_operations_allowed,
                "device_write_count": spy.device_write_count,
                "device_state_unchanged_by_decision": before_decision == after_decision,
                "review_prompt": case.review_prompt,
                "passed": passed,
            }
        )
        total_write_count += spy.device_write_count

    passed_cases = sum(1 for row in rows if row["passed"])
    report = {
        "schema_version": suite.schema_version,
        "evaluation_id": suite.evaluation_id,
        "status": "ok" if passed_cases == len(rows) else "failed",
        "scope": (
            "Deterministic non-executing workflow evaluation with synthetic proposals; "
            "not expert feedback, clinical validation, or device-control evidence."
        ),
        "input_sha256": {
            "suite": _sha256_file(suite_file),
            "gateway_config": _sha256_file(gateway_file),
            "mapping": _sha256_file(mapping_file),
            "policy": _sha256_file(policy_file),
            "workflow_implementation": _sha256_file(workflow_file),
            "evidence_runner": _sha256_file(runner_file),
        },
        "expert_review": suite.expert_review,
        "summary": {
            "cases": len(rows),
            "passed": passed_cases,
            "failed": len(rows) - passed_cases,
            "approved": sum(row["observed_state"] == "approved" for row in rows),
            "denied": sum(row["observed_state"] == "denied" for row in rows),
            "expired": sum(row["observed_state"] == "expired" for row in rows),
            "pending_approval": sum(
                row["observed_state"] == "pending_approval" for row in rows
            ),
            "device_write_count": total_write_count,
            "all_results_non_executing": all(
                row["dry_run"] is True
                and row["executed"] is False
                and row["write_operations_allowed"] is False
                for row in rows
            ),
            "all_decisions_preserved_device_state": all(
                row["device_state_unchanged_by_decision"] for row in rows
            ),
        },
        "cases": rows,
    }
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def _apply_mutation(
    registry: ResourceRegistry,
    device_id: str,
    mutation: str,
) -> None:
    if mutation == "none":
        return
    device = registry.devices[device_id]
    if mutation == "stale":
        registry.devices[device_id] = device.model_copy(
            update={"freshness": "stale", "freshness_reason": "wp10_stale_before_approval"},
            deep=True,
        )
        return
    if mutation == "device_state_changed":
        metrics = [metric.model_copy(deep=True) for metric in device.metrics]
        if not metrics:
            raise ValueError(f"Cannot mutate device without metrics: {device_id}")
        current = metrics[0].value
        metrics[0] = metrics[0].model_copy(
            update={"value": float(current) + 1.0 if isinstance(current, (int, float)) else "changed"}
        )
        registry.devices[device_id] = device.model_copy(update={"metrics": metrics}, deep=True)
        return
    raise ValueError(f"Unsupported pre-decision mutation: {mutation}")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the non-executing WP10 human-authorization workflow."
    )
    parser.add_argument("--suite", default="config/bhi2026_wp10_authorization.yaml")
    parser.add_argument(
        "--config",
        default="config/gateway.simulated.dryrun.high-airway-pressure.example.yaml",
    )
    parser.add_argument("--mie", default="config/sdc_mie.yaml")
    parser.add_argument("--tool-policy", default="config/tool_policies.yaml")
    parser.add_argument(
        "--output",
        default=(
            "data/revision/authorization/"
            "bhi2026-wp10-authorization-v1/workflow-evidence.json"
        ),
    )
    args = parser.parse_args()
    report = run_human_authorization_evidence(
        suite_path=args.suite,
        gateway_config_path=args.config,
        mapping_path=args.mie,
        policy_path=args.tool_policy,
        output_path=args.output,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
