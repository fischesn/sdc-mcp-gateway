from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.models import AuditRecord, DeviceSnapshot
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry


class ProposalState(str, Enum):
    PROPOSED = "proposed"
    POLICY_VALIDATED = "policy_validated"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


TERMINAL_PROPOSAL_STATES = frozenset(
    {ProposalState.APPROVED, ProposalState.DENIED, ProposalState.EXPIRED}
)


class AuthorizationContext(BaseModel):
    """Authenticated identity information supplied by a supervising workflow."""

    identity: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    role: str | None = None

    @field_validator("identity", "reference")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("authorization identity and reference must not be blank")
        return stripped


class ProposalTransition(BaseModel):
    state: ProposalState
    timestamp: datetime
    reason: str


class ActionProposal(BaseModel):
    """A state- and policy-bound proposal that can never represent a device effect."""

    proposal_id: str = Field(min_length=1)
    target_device_id: str = Field(min_length=1)
    tool: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    parameters: dict[str, Any]
    policy_version: str = Field(min_length=1)
    unit: str | None = None
    allowed_range: tuple[float | None, float | None] | None = None
    snapshot_version: int
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    freshness_state: str = Field(min_length=1)
    proposer: str = Field(min_length=1)
    proposed_at: datetime
    expires_at: datetime
    state: ProposalState
    approval_identity: str | None = None
    approval_reference: str | None = None
    decision_reason: str | None = None
    transitions: list[ProposalTransition] = Field(default_factory=list)
    dry_run: bool = True
    executed: bool = False
    write_operations_allowed: bool = False

    @model_validator(mode="after")
    def enforce_non_execution(self) -> "ActionProposal":
        if not self.dry_run or self.executed or self.write_operations_allowed:
            raise ValueError(
                "Authorization proposals are fail-closed: dry_run=true, executed=false, "
                "and write_operations_allowed=false are mandatory"
            )
        if _as_utc(self.expires_at) <= _as_utc(self.proposed_at):
            raise ValueError("expires_at must be later than proposed_at")
        return self


class AuthorizationDecision(BaseModel):
    proposal: ActionProposal
    decision_recorded: bool
    reason: str
    dry_run: bool = True
    executed: bool = False
    write_operations_allowed: bool = False

    @model_validator(mode="after")
    def enforce_non_execution(self) -> "AuthorizationDecision":
        if not self.dry_run or self.executed or self.write_operations_allowed:
            raise ValueError("Authorization decisions cannot represent device execution")
        return self


class NonExecutingAuthorizationWorkflow:
    """Human-authorization lifecycle layered over the existing dry-run policy registry.

    Approval is a terminal documentation state only. It does not dispatch an SDC
    operation, and the proposal is revalidated against the current policy and device
    snapshot before that state can be reached.
    """

    def __init__(
        self,
        tool_registry: DryRunToolRegistry,
        recorder: JsonlRecorder | None = None,
    ) -> None:
        self.tool_registry = tool_registry
        self.recorder = recorder
        self._proposals: dict[str, ActionProposal] = {}

    def propose(
        self,
        *,
        proposal_id: str,
        tool: str,
        parameters: dict[str, Any],
        proposer: str,
        expires_at: datetime,
        now: datetime | None = None,
    ) -> ActionProposal:
        if proposal_id in self._proposals:
            raise ValueError(f"Duplicate proposal_id: {proposal_id}")
        proposed_at = _as_utc(now or datetime.now(UTC))
        expiry = _as_utc(expires_at)
        if not proposer.strip():
            raise ValueError("proposer must not be empty")
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be an object")

        policy = self.tool_registry.policies.by_name().get(tool)
        if policy is None:
            raise ValueError(f"Unknown proposal tool: {tool}")
        target_device_id = parameters.get("device_id")
        if not isinstance(target_device_id, str) or not target_device_id:
            raise ValueError("A proposal must bind a non-empty device_id")
        device = self.tool_registry.resource_registry.devices.get(target_device_id)
        if device is None:
            raise ValueError(f"Unknown target device: {target_device_id}")

        bound_parameters = dict(parameters)
        bound_parameters.setdefault("snapshot_version", device.mdib_version)
        proposal = ActionProposal(
            proposal_id=proposal_id,
            target_device_id=target_device_id,
            tool=tool,
            operation=policy.operation,
            parameters=bound_parameters,
            policy_version=self.tool_registry.policies.version,
            unit=policy.unit,
            allowed_range=(policy.min_value, policy.max_value)
            if policy.min_value is not None or policy.max_value is not None
            else None,
            snapshot_version=device.mdib_version,
            snapshot_sha256=snapshot_sha256(device),
            freshness_state=device.freshness,
            proposer=proposer,
            proposed_at=proposed_at,
            expires_at=expiry,
            state=ProposalState.PROPOSED,
            transitions=[
                ProposalTransition(
                    state=ProposalState.PROPOSED,
                    timestamp=proposed_at,
                    reason="proposal_recorded_no_execution",
                )
            ],
        )
        self._store_and_audit(proposal, "proposal_recorded_no_execution")

        validation = self.tool_registry.call_tool(tool, bound_parameters)
        if validation.status != "accepted_dry_run":
            proposal = self._transition(
                proposal,
                ProposalState.DENIED,
                proposed_at,
                f"policy_rejected:{validation.reason or 'unspecified'}",
            )
            return proposal.model_copy(deep=True)

        proposal = self._transition(
            proposal,
            ProposalState.POLICY_VALIDATED,
            proposed_at,
            "policy_validated_no_execution",
        )
        proposal = self._transition(
            proposal,
            ProposalState.PENDING_APPROVAL,
            proposed_at,
            "human_authorization_required",
        )
        return proposal.model_copy(deep=True)

    def decide(
        self,
        proposal_id: str,
        *,
        action: str,
        authorization: AuthorizationContext | None,
        now: datetime | None = None,
    ) -> AuthorizationDecision:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise KeyError(f"Unknown proposal_id: {proposal_id}")
        decision_time = _as_utc(now or datetime.now(UTC))

        if proposal.state in TERMINAL_PROPOSAL_STATES:
            return self._decision(
                proposal,
                False,
                f"already_terminal:{proposal.state.value}",
            )
        if proposal.state != ProposalState.PENDING_APPROVAL:
            return self._decision(proposal, False, f"not_pending:{proposal.state.value}")
        if decision_time >= _as_utc(proposal.expires_at):
            if authorization is not None:
                proposal = self._with_authorization(proposal, authorization)
            proposal = self._transition(
                proposal,
                ProposalState.EXPIRED,
                decision_time,
                "authorization_window_expired",
            )
            return self._decision(proposal, False, "authorization_window_expired")
        if authorization is None:
            self._audit(proposal, "missing_authorization_context")
            return self._decision(proposal, False, "missing_authorization_context")
        if action not in {"approve", "deny"}:
            self._audit(proposal, "unsupported_authorization_action")
            return self._decision(proposal, False, "unsupported_authorization_action")

        if action == "deny":
            proposal = self._with_authorization(proposal, authorization)
            proposal = self._transition(
                proposal,
                ProposalState.DENIED,
                decision_time,
                "human_authorization_denied",
            )
            return self._decision(proposal, True, "human_authorization_denied")

        revalidation_reason = self._revalidate(proposal)
        if revalidation_reason is not None:
            proposal = self._with_authorization(proposal, authorization)
            proposal = self._transition(
                proposal,
                ProposalState.EXPIRED,
                decision_time,
                revalidation_reason,
            )
            return self._decision(proposal, False, revalidation_reason)

        proposal = self._with_authorization(proposal, authorization)
        proposal = self._transition(
            proposal,
            ProposalState.APPROVED,
            decision_time,
            "human_authorization_recorded_no_execution",
        )
        return self._decision(proposal, True, "human_authorization_recorded_no_execution")

    def get(self, proposal_id: str) -> ActionProposal:
        try:
            return self._proposals[proposal_id].model_copy(deep=True)
        except KeyError as exc:
            raise KeyError(f"Unknown proposal_id: {proposal_id}") from exc

    def _revalidate(self, proposal: ActionProposal) -> str | None:
        if self.tool_registry.policies.version != proposal.policy_version:
            return "revalidation_failed:policy_version_changed"
        device = self.tool_registry.resource_registry.devices.get(proposal.target_device_id)
        if device is None:
            return "revalidation_failed:target_device_unavailable"

        validation = self.tool_registry.call_tool(proposal.tool, dict(proposal.parameters))
        if validation.status != "accepted_dry_run":
            return f"revalidation_failed:{validation.reason or 'policy_rejected'}"
        if device.mdib_version != proposal.snapshot_version:
            return "revalidation_failed:snapshot_version_changed"
        if device.freshness != proposal.freshness_state:
            return "revalidation_failed:freshness_changed"
        if snapshot_sha256(device) != proposal.snapshot_sha256:
            return "revalidation_failed:device_state_changed"
        return None

    def _with_authorization(
        self,
        proposal: ActionProposal,
        authorization: AuthorizationContext,
    ) -> ActionProposal:
        updated = proposal.model_copy(
            update={
                "approval_identity": authorization.identity,
                "approval_reference": authorization.reference,
            },
            deep=True,
        )
        self._proposals[proposal.proposal_id] = updated
        return updated

    def _transition(
        self,
        proposal: ActionProposal,
        state: ProposalState,
        timestamp: datetime,
        reason: str,
    ) -> ActionProposal:
        transitions = list(proposal.transitions)
        transitions.append(ProposalTransition(state=state, timestamp=timestamp, reason=reason))
        updated = proposal.model_copy(
            update={"state": state, "decision_reason": reason, "transitions": transitions},
            deep=True,
        )
        self._store_and_audit(updated, reason)
        return updated

    def _store_and_audit(self, proposal: ActionProposal, reason: str) -> None:
        self._proposals[proposal.proposal_id] = proposal
        self._audit(proposal, reason)

    def _audit(self, proposal: ActionProposal, reason: str) -> None:
        if self.recorder is None:
            return
        self.recorder.write(
            AuditRecord(
                event_type="human_authorization_workflow",
                status=proposal.state.value,
                mapping_version=self.tool_registry.resource_registry.mapping.version,
                mapping_sha256=self.tool_registry.resource_registry.mapping.source_sha256,
                details={
                    "proposal_id": proposal.proposal_id,
                    "reason": reason,
                    "proposal": proposal.model_dump(mode="json"),
                },
            )
        )

    @staticmethod
    def _decision(
        proposal: ActionProposal,
        decision_recorded: bool,
        reason: str,
    ) -> AuthorizationDecision:
        return AuthorizationDecision(
            proposal=proposal.model_copy(deep=True),
            decision_recorded=decision_recorded,
            reason=reason,
        )


def snapshot_sha256(device: DeviceSnapshot) -> str:
    encoded = json.dumps(
        device.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("Workflow timestamps must include a timezone")
    return value.astimezone(UTC)
