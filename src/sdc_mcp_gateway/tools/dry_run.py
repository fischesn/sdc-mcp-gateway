from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.models import AuditRecord, utc_now_iso


class ToolParameter(BaseModel):
    name: str
    type: str = "string"
    required: bool = True
    description: str = ""


class ToolPolicy(BaseModel):
    name: str
    operation: str
    description: str
    dry_run_only: bool = True
    target_device_type: str | None = None
    semantic_name: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None
    requires_human_approval: bool = True
    parameters: list[ToolParameter] = Field(default_factory=list)


class ToolPolicyDocument(BaseModel):
    version: str
    description: str | None = None
    tools: list[ToolPolicy] = Field(default_factory=list)

    def by_name(self) -> dict[str, ToolPolicy]:
        return {tool.name: tool for tool in self.tools}


class ToolDescriptor(BaseModel):
    name: str
    description: str
    dry_run_only: bool = True
    requires_human_approval: bool = True
    target_device_type: str | None = None
    semantic_name: str | None = None
    unit: str | None = None
    parameters: list[ToolParameter] = Field(default_factory=list)


class ToolCallResult(BaseModel):
    tool: str
    operation: str | None = None
    status: str
    reason: str | None = None
    device_id: str | None = None
    requested_value: float | None = None
    allowed_range: list[float | None] | None = None
    unit: str | None = None
    requires_human_approval: bool = True
    dry_run: bool = True
    executed: bool = False
    write_operations_allowed: bool = False
    policy_version: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)
    details: dict[str, Any] = Field(default_factory=dict)


def load_tool_policies(path: str | Path) -> ToolPolicyDocument:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping at {path}")
    return ToolPolicyDocument.model_validate(data)


class DryRunToolRegistry:
    """Policy-checked dry-run MCP tool surface.

    The registry exposes action-like affordances but never executes SDC operations.
    It validates arguments, checks the target device, applies configured value
    ranges, records an audit event, and returns an explicit dry-run result.
    """

    def __init__(
        self,
        resource_registry: ResourceRegistry,
        policies: ToolPolicyDocument,
        recorder: JsonlRecorder | None = None,
        tools_enabled: bool = False,
        write_operations_allowed: bool = False,
    ) -> None:
        self.resource_registry = resource_registry
        self.policies = policies
        self.recorder = recorder
        self.tools_enabled = tools_enabled
        self.write_operations_allowed = write_operations_allowed
        if write_operations_allowed:
            # This prototype intentionally never enters this state.
            raise ValueError("Dry-run tool registry does not support write_operations_allowed=true")

    def list_tool_descriptors(self) -> list[ToolDescriptor]:
        if not self.tools_enabled:
            return []
        return [
            ToolDescriptor(
                name=policy.name,
                description=policy.description,
                dry_run_only=policy.dry_run_only,
                requires_human_approval=policy.requires_human_approval,
                target_device_type=policy.target_device_type,
                semantic_name=policy.semantic_name,
                unit=policy.unit,
                parameters=policy.parameters,
            )
            for policy in self.policies.tools
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        if not self.tools_enabled:
            result = ToolCallResult(
                tool=name,
                status="rejected",
                reason="tools_disabled",
                policy_version=self.policies.version,
                details={"message": "Dry-run MCP tools are not enabled in this gateway configuration."},
            )
            self._audit(result, arguments)
            return result

        policy = self.policies.by_name().get(name)
        if policy is None:
            result = ToolCallResult(
                tool=name,
                status="rejected",
                reason="unknown_tool",
                policy_version=self.policies.version,
            )
            self._audit(result, arguments)
            return result

        if not policy.dry_run_only:
            result = ToolCallResult(
                tool=name,
                operation=policy.operation,
                status="rejected",
                reason="non_dry_run_policy_not_supported",
                policy_version=self.policies.version,
            )
            self._audit(result, arguments)
            return result

        if name in {"prepare_set_fio2", "prepare_set_peep"}:
            result = self._call_numeric_setpoint(policy, name, arguments)
        elif name == "prepare_acknowledge_alarm":
            result = self._call_acknowledge_alarm(policy, name, arguments)
        else:
            result = ToolCallResult(
                tool=name,
                operation=policy.operation,
                status="rejected",
                reason="unsupported_tool_implementation",
                policy_version=self.policies.version,
            )
        self._audit(result, arguments)
        return result

    def _call_numeric_setpoint(self, policy: ToolPolicy, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        device_id = str(arguments.get("device_id", ""))
        raw_value = arguments.get("value")
        base = self._base_result(policy, name, device_id=device_id)
        if not device_id:
            return base.model_copy(update={"status": "rejected", "reason": "missing_device_id"})
        device = self.resource_registry.devices.get(device_id)
        if device is None:
            return base.model_copy(update={"status": "rejected", "reason": "unknown_device"})
        actual_type = infer_device_type(device_id, device.display_name, device.model)
        if policy.target_device_type and actual_type != policy.target_device_type:
            return base.model_copy(
                update={
                    "status": "rejected",
                    "reason": "wrong_device_type",
                    "details": {"expected_device_type": policy.target_device_type, "actual_device_type": actual_type},
                }
            )
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return base.model_copy(update={"status": "rejected", "reason": "invalid_value"})
        allowed_range = [policy.min_value, policy.max_value]
        if policy.min_value is not None and value < policy.min_value:
            return base.model_copy(
                update={
                    "status": "rejected",
                    "reason": "value_out_of_range",
                    "requested_value": value,
                    "allowed_range": allowed_range,
                }
            )
        if policy.max_value is not None and value > policy.max_value:
            return base.model_copy(
                update={
                    "status": "rejected",
                    "reason": "value_out_of_range",
                    "requested_value": value,
                    "allowed_range": allowed_range,
                }
            )
        return base.model_copy(
            update={
                "status": "accepted_dry_run",
                "reason": "policy_validated_no_execution",
                "requested_value": value,
                "allowed_range": allowed_range,
                "details": {"device_type": actual_type, "semantic_name": policy.semantic_name},
            }
        )

    def _call_acknowledge_alarm(self, policy: ToolPolicy, name: str, arguments: dict[str, Any]) -> ToolCallResult:
        device_id = str(arguments.get("device_id", ""))
        alarm_handle = str(arguments.get("alarm_handle", ""))
        base = self._base_result(policy, name, device_id=device_id)
        if not device_id:
            return base.model_copy(update={"status": "rejected", "reason": "missing_device_id"})
        device = self.resource_registry.devices.get(device_id)
        if device is None:
            return base.model_copy(update={"status": "rejected", "reason": "unknown_device"})
        if not alarm_handle:
            return base.model_copy(update={"status": "rejected", "reason": "missing_alarm_handle"})
        active_alarm_handles = {alarm.handle for alarm in device.alarms if alarm.presence is True}
        if alarm_handle not in active_alarm_handles:
            return base.model_copy(
                update={
                    "status": "rejected",
                    "reason": "alarm_not_active_or_unknown",
                    "details": {"active_alarm_handles": sorted(active_alarm_handles)},
                }
            )
        return base.model_copy(
            update={
                "status": "accepted_dry_run",
                "reason": "policy_validated_no_execution",
                "details": {"alarm_handle": alarm_handle},
            }
        )

    def _base_result(self, policy: ToolPolicy, name: str, device_id: str | None = None) -> ToolCallResult:
        return ToolCallResult(
            tool=name,
            operation=policy.operation,
            device_id=device_id or None,
            status="rejected",
            reason=None,
            unit=policy.unit,
            requires_human_approval=policy.requires_human_approval,
            dry_run=True,
            executed=False,
            write_operations_allowed=False,
            policy_version=self.policies.version,
        )

    def _audit(self, result: ToolCallResult, arguments: dict[str, Any]) -> None:
        if self.recorder is None:
            return
        self.recorder.write(
            AuditRecord(
                event_type="tool_dry_run",
                status=result.status,
                mapping_version=self.resource_registry.mapping.version,
                details={"tool": result.tool, "arguments": _redact(arguments), "result": result.model_dump()},
            )
        )


def infer_device_type(device_id: str, display_name: str | None, model: str | None) -> str:
    text = " ".join(part for part in [device_id, display_name or "", model or ""] if part).lower()
    if "ventilator" in text or "vent" in text:
        return "ventilator"
    if "monitor" in text or "patient" in text:
        return "patient_monitor"
    return "unknown"


def _redact(arguments: dict[str, Any]) -> dict[str, Any]:
    # No patient identifiers should be passed to dry-run tools. Keep hook for future hardening.
    return dict(arguments)


def tool_result_json(result: ToolCallResult) -> str:
    return json.dumps(result.model_dump(), ensure_ascii=False, indent=2, sort_keys=True)
