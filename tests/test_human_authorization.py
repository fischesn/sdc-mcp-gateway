from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.revision.human_authorization import run_human_authorization_evidence
from sdc_mcp_gateway.safety.authorization import (
    ActionProposal,
    AuthorizationContext,
    NonExecutingAuthorizationWorkflow,
    ProposalState,
    snapshot_sha256,
)
from sdc_mcp_gateway.safety.no_execution import DeviceWriteSpy
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer, WriteSpySdcConsumer
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies


NOW = datetime(2026, 8, 10, 10, 0, tzinfo=UTC)
AUTHORIZATION = AuthorizationContext(
    identity="synthetic-supervisor",
    reference="synthetic-authorization-001",
    role="domain-reviewer",
)


def _workflow() -> tuple[
    NonExecutingAuthorizationWorkflow,
    ResourceRegistry,
    DeviceWriteSpy,
]:
    spy = DeviceWriteSpy()
    consumer = WriteSpySdcConsumer(
        SimulatedSdcConsumer("config/sim.high-airway-pressure.yaml", elapsed_s=100.0),
        spy,
    )
    resources = ResourceRegistry(
        devices=consumer.get_snapshots(),
        mapping=load_mapping("config/sdc_mie.yaml"),
        recorder=None,
        tools_exported=True,
        tool_mode="dry-run",
        write_operations_allowed=False,
        gateway_mode="dry-run-tools",
    )
    tools = DryRunToolRegistry(
        resource_registry=resources,
        policies=load_tool_policies("config/tool_policies.yaml"),
        recorder=None,
        tools_enabled=True,
        write_operations_allowed=False,
    )
    return NonExecutingAuthorizationWorkflow(tools), resources, spy


def _propose(
    workflow: NonExecutingAuthorizationWorkflow,
    proposal_id: str = "proposal-1",
):
    return workflow.propose(
        proposal_id=proposal_id,
        tool="prepare_set_fio2",
        parameters={"device_id": "sim-ventilator-1", "value": 45.0},
        proposer="synthetic-agent",
        expires_at=NOW + timedelta(minutes=2),
        now=NOW,
    )


def test_approval_records_full_binding_and_remains_non_executing() -> None:
    workflow, resources, spy = _workflow()
    before = snapshot_sha256(resources.devices["sim-ventilator-1"])
    proposal = _propose(workflow)
    assert proposal.state is ProposalState.PENDING_APPROVAL
    assert proposal.parameters["snapshot_version"] == proposal.snapshot_version
    assert proposal.snapshot_sha256 == before
    assert proposal.freshness_state in {"fresh", "recovered"}
    assert proposal.unit == "%"
    assert proposal.allowed_range == (21.0, 100.0)

    result = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=10),
    )

    assert result.decision_recorded is True
    assert result.proposal.state is ProposalState.APPROVED
    assert [item.state for item in result.proposal.transitions] == [
        ProposalState.PROPOSED,
        ProposalState.POLICY_VALIDATED,
        ProposalState.PENDING_APPROVAL,
        ProposalState.APPROVED,
    ]
    assert result.proposal.approval_identity == AUTHORIZATION.identity
    assert result.proposal.approval_reference == AUTHORIZATION.reference
    assert result.executed is False
    assert result.write_operations_allowed is False
    assert snapshot_sha256(resources.devices["sim-ventilator-1"]) == before
    assert spy.device_write_count == 0


def test_denial_is_terminal_and_non_executing() -> None:
    workflow, resources, spy = _workflow()
    before = snapshot_sha256(resources.devices["sim-ventilator-1"])
    proposal = _propose(workflow)
    result = workflow.decide(
        proposal.proposal_id,
        action="deny",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=10),
    )
    assert result.proposal.state is ProposalState.DENIED
    assert result.reason == "human_authorization_denied"
    assert snapshot_sha256(resources.devices["sim-ventilator-1"]) == before
    assert spy.device_write_count == 0


def test_expired_proposal_cannot_be_approved() -> None:
    workflow, _, spy = _workflow()
    proposal = _propose(workflow)
    result = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(minutes=2),
    )
    assert result.decision_recorded is False
    assert result.proposal.state is ProposalState.EXPIRED
    assert result.reason == "authorization_window_expired"
    assert spy.device_write_count == 0


def test_duplicate_approval_is_rejected_without_new_transition() -> None:
    workflow, _, spy = _workflow()
    proposal = _propose(workflow)
    first = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=10),
    )
    second = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=11),
    )
    assert first.proposal.state is ProposalState.APPROVED
    assert second.decision_recorded is False
    assert second.reason == "already_terminal:approved"
    assert len(second.proposal.transitions) == len(first.proposal.transitions)
    assert spy.device_write_count == 0


def test_stale_snapshot_cannot_be_overridden_by_approval() -> None:
    workflow, resources, spy = _workflow()
    proposal = _propose(workflow)
    device = resources.devices[proposal.target_device_id]
    resources.devices[proposal.target_device_id] = device.model_copy(
        update={"freshness": "stale", "freshness_reason": "test_stale"},
        deep=True,
    )
    result = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=10),
    )
    assert result.proposal.state is ProposalState.EXPIRED
    assert result.reason == "revalidation_failed:stale_snapshot"
    assert spy.device_write_count == 0


def test_changed_device_state_invalidates_bound_proposal() -> None:
    workflow, resources, spy = _workflow()
    proposal = _propose(workflow)
    device = resources.devices[proposal.target_device_id]
    changed_metrics = [item.model_copy(deep=True) for item in device.metrics]
    changed_metrics[0] = changed_metrics[0].model_copy(update={"value": 99.0})
    resources.devices[proposal.target_device_id] = device.model_copy(
        update={"metrics": changed_metrics},
        deep=True,
    )
    result = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=AUTHORIZATION,
        now=NOW + timedelta(seconds=10),
    )
    assert result.proposal.state is ProposalState.EXPIRED
    assert result.reason == "revalidation_failed:device_state_changed"
    assert spy.device_write_count == 0


def test_missing_authorization_context_leaves_proposal_pending() -> None:
    workflow, _, spy = _workflow()
    proposal = _propose(workflow)
    result = workflow.decide(
        proposal.proposal_id,
        action="approve",
        authorization=None,
        now=NOW + timedelta(seconds=10),
    )
    assert result.decision_recorded is False
    assert result.proposal.state is ProposalState.PENDING_APPROVAL
    assert result.reason == "missing_authorization_context"
    assert result.proposal.approval_identity is None
    assert spy.device_write_count == 0


def test_blank_authorization_identity_or_reference_is_invalid() -> None:
    with pytest.raises(ValidationError, match="must not be blank"):
        AuthorizationContext(identity=" ", reference="synthetic-reference")
    with pytest.raises(ValidationError, match="must not be blank"):
        AuthorizationContext(identity="synthetic-identity", reference=" ")


def test_proposal_model_cannot_represent_execution() -> None:
    workflow, _, _ = _workflow()
    proposal = _propose(workflow)
    payload = proposal.model_dump()
    payload["executed"] = True
    with pytest.raises(ValidationError, match="fail-closed"):
        ActionProposal.model_validate(payload)


def test_wp10_evidence_suite_passes_and_writes_anonymous_artifact(tmp_path: Path) -> None:
    output = tmp_path / "workflow-evidence.json"
    report = run_human_authorization_evidence(
        suite_path="config/bhi2026_wp10_authorization.yaml",
        gateway_config_path="config/gateway.simulated.dryrun.high-airway-pressure.example.yaml",
        mapping_path="config/sdc_mie.yaml",
        policy_path="config/tool_policies.yaml",
        output_path=output,
    )
    assert report["status"] == "ok"
    assert report["summary"] == {
        "cases": 7,
        "passed": 7,
        "failed": 0,
        "approved": 2,
        "denied": 1,
        "expired": 3,
        "pending_approval": 1,
        "device_write_count": 0,
        "all_results_non_executing": True,
        "all_decisions_preserved_device_state": True,
    }
    assert report["expert_review"]["status"] == "not_conducted"
    assert report["expert_review"]["participant_count"] == 0
    assert output.exists()
