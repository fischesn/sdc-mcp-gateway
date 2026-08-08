from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.models import MappingDocument
from sdc_mcp_gateway.safety.no_execution import DeviceWriteSpy
from sdc_mcp_gateway.safety.state_machine import NoExecutionTransitionSystem
from sdc_mcp_gateway.safety.static_check import scan_agent_facing_boundary
from sdc_mcp_gateway.sdc.consumer import SdcConsumer, WriteSpySdcConsumer
from sdc_mcp_gateway.tools.dry_run import (
    DryRunToolRegistry,
    ToolDescriptor,
    ToolPolicyDocument,
    infer_device_type,
)


def run_no_execution_evidence(
    *,
    config: GatewayConfig,
    mapping: MappingDocument,
    consumer: SdcConsumer,
    policies: ToolPolicyDocument | None,
    package_root: Path,
) -> dict[str, Any]:
    """Exercise the public resource/tool surface with an independent write spy."""

    spy = DeviceWriteSpy()
    monitored_consumer = WriteSpySdcConsumer(consumer, spy)
    snapshots = monitored_consumer.get_snapshots()
    registry = ResourceRegistry(
        devices=snapshots,
        mapping=mapping,
        recorder=None,
        tools_exported=config.gateway.allow_tools,
        tool_mode="dry-run" if config.gateway.allow_tools else None,
        write_operations_allowed=False,
        gateway_mode=config.gateway.mode,
    )
    before = _snapshot_digest(registry)
    resource_uris = registry.list_resource_uris()
    for uri in resource_uris:
        registry.read(uri)

    tool_results: list[dict[str, Any]] = []
    tool_registry: DryRunToolRegistry | None = None
    if config.gateway.allow_tools:
        if policies is None:
            raise ValueError("Tool policies are required when dry-run tools are enabled")
        tool_registry = DryRunToolRegistry(
            resource_registry=registry,
            policies=policies,
            recorder=None,
            tools_enabled=True,
            write_operations_allowed=False,
        )
        for descriptor in tool_registry.list_tool_descriptors():
            for arguments in ({}, _representative_arguments(descriptor, registry)):
                result = tool_registry.call_tool(descriptor.name, arguments)
                tool_results.append(result.model_dump(mode="json"))
        tool_results.append(tool_registry.call_tool("__unknown_tool__", {}).model_dump(mode="json"))

    after = _snapshot_digest(registry)
    results_are_bounded = all(
        result["dry_run"] is True
        and result["executed"] is False
        and result["write_operations_allowed"] is False
        for result in tool_results
    )
    static_report = scan_agent_facing_boundary(package_root)
    state_report = NoExecutionTransitionSystem().verify()
    dynamic_ok = (
        spy.device_write_count == 0
        and before == after
        and results_are_bounded
        and len(resource_uris) > 0
    )
    ok = dynamic_ok and static_report["status"] == "ok" and state_report["status"] == "ok"
    return {
        "status": "ok" if ok else "failed",
        "claim": "device_write_count == 0 and device_state_digest_before == device_state_digest_after",
        "dynamic": {
            "status": "ok" if dynamic_ok else "failed",
            "resources_exercised": len(resource_uris),
            "tool_interactions_exercised": len(tool_results),
            "device_write_count": spy.device_write_count,
            "device_state_unchanged": before == after,
            "bounded_tool_results": results_are_bounded,
            "device_state_digest_before": before,
            "device_state_digest_after": after,
        },
        "static": static_report,
        "transition_system": state_report,
    }


def _snapshot_digest(registry: ResourceRegistry) -> str:
    payload = [
        registry.devices[device_id].model_dump(mode="json")
        for device_id in sorted(registry.devices)
    ]
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _representative_arguments(
    descriptor: ToolDescriptor,
    registry: ResourceRegistry,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {}
    for parameter in descriptor.parameters:
        if parameter.name == "device_id":
            arguments[parameter.name] = _matching_device_id(descriptor, registry)
        elif parameter.name == "alarm_handle":
            arguments[parameter.name] = _alarm_handle(arguments.get("device_id"), registry)
        elif parameter.type == "number":
            arguments[parameter.name] = 1.0
        elif parameter.type == "string":
            arguments[parameter.name] = "evidence-value"
    return arguments


def _matching_device_id(descriptor: ToolDescriptor, registry: ResourceRegistry) -> str:
    for device_id, device in registry.devices.items():
        actual = infer_device_type(device_id, device.display_name, device.model)
        if descriptor.target_device_type is None or actual == descriptor.target_device_type:
            return device_id
    return "__missing_device__"


def _alarm_handle(device_id: str | None, registry: ResourceRegistry) -> str:
    device = registry.devices.get(device_id or "")
    if device is not None:
        for alarm in device.alarms:
            if alarm.presence:
                return alarm.handle
    return "__missing_alarm__"
