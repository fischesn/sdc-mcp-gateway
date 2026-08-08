from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from sdc_mcp_gateway.main import app
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.mcp.server import _register_concrete_resource, _register_dry_run_tools
from sdc_mcp_gateway.safety.no_execution import DeviceWriteSpy, ForbiddenDeviceOperation
from sdc_mcp_gateway.safety.state_machine import NoExecutionTransitionSystem
from sdc_mcp_gateway.safety.static_check import scan_agent_facing_boundary
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer, SdcConsumer, WriteSpySdcConsumer
from sdc_mcp_gateway.tools.dry_run import (
    DryRunToolRegistry,
    ToolCallResult,
    ToolPolicyDocument,
    load_tool_policies,
)


runner = CliRunner()


def _instrumented_registries() -> tuple[DeviceWriteSpy, ResourceRegistry, DryRunToolRegistry]:
    spy = DeviceWriteSpy()
    consumer = WriteSpySdcConsumer(
        SimulatedSdcConsumer("config/sim.high-airway-pressure.yaml", elapsed_s=100.0),
        spy,
    )
    registry = ResourceRegistry(
        devices=consumer.get_snapshots(),
        mapping=load_mapping("config/sdc_mie.yaml"),
        recorder=None,
        tools_exported=True,
        tool_mode="dry-run",
        write_operations_allowed=False,
        gateway_mode="dry-run-tools",
    )
    tools = DryRunToolRegistry(
        resource_registry=registry,
        policies=load_tool_policies("config/tool_policies.yaml"),
        recorder=None,
        tools_enabled=True,
        write_operations_allowed=False,
    )
    return spy, registry, tools


def _state_digest(registry: ResourceRegistry) -> str:
    payload = [
        registry.devices[device_id].model_dump(mode="json")
        for device_id in sorted(registry.devices)
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def test_sdc_consumer_contract_is_observation_only() -> None:
    public_methods = {
        name
        for name, value in vars(SdcConsumer).items()
        if callable(value) and not name.startswith("_")
    }
    assert public_methods == {"discover", "get_snapshots"}


def test_write_spy_detects_and_blocks_forbidden_operation_families() -> None:
    set_spy = WriteSpySdcConsumer(SimulatedSdcConsumer("config/sim.patient-monitor.yaml"))
    with pytest.raises(ForbiddenDeviceOperation, match="SetService"):
        set_spy.attempt_set_service("sim-monitor-1")
    assert set_spy.spy.device_write_count == 1

    activate_spy = WriteSpySdcConsumer(SimulatedSdcConsumer("config/sim.patient-monitor.yaml"))
    with pytest.raises(ForbiddenDeviceOperation, match="ActivateOperation"):
        activate_spy.attempt_activate_operation("sim-monitor-1")
    assert activate_spy.spy.device_write_count == 1


def test_every_exported_resource_and_tool_preserves_device_state_and_zero_writes() -> None:
    spy, registry, tools = _instrumented_registries()
    before = _state_digest(registry)

    for uri in registry.list_resource_uris():
        registry.read(uri)
    with pytest.raises(KeyError):
        registry.read("sdc://devices/unknown/metrics")

    cases = [
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 45.0}),
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 150.0}),
        ("prepare_set_peep", {"device_id": "sim-ventilator-1", "value": 10.0}),
        (
            "prepare_acknowledge_alarm",
            {"device_id": "sim-ventilator-1", "alarm_handle": "alarm.airway_pressure.high"},
        ),
        ("prepare_acknowledge_alarm", {}),
        ("__unknown_tool__", {}),
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": float("nan")}),
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": float("inf")}),
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": True}),
        ("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 45, "extra": 1}),
        ("prepare_set_fio2", ["not", "an", "object"]),
    ]
    for name, arguments in cases:
        result = tools.call_tool(name, arguments)
        assert result.dry_run is True
        assert result.executed is False
        assert result.write_operations_allowed is False

    assert {descriptor.name for descriptor in tools.list_tool_descriptors()} == {
        "prepare_set_fio2",
        "prepare_set_peep",
        "prepare_acknowledge_alarm",
    }
    assert spy.device_write_count == 0
    assert _state_digest(registry) == before


def test_every_fastmcp_wrapper_preserves_zero_writes_and_device_state() -> None:
    class CapturingMcp:
        def __init__(self) -> None:
            self.resources: dict[str, object] = {}
            self.tools: dict[str, object] = {}

        def resource(self, uri: str, **_: object):
            def decorator(function: object) -> object:
                self.resources[uri] = function
                return function

            return decorator

        def tool(self, name: str, **_: object):
            def decorator(function: object) -> object:
                self.tools[name] = function
                return function

            return decorator

    spy, registry, tools = _instrumented_registries()
    before = _state_digest(registry)
    mcp = CapturingMcp()
    for descriptor in registry.list_resource_descriptors():
        _register_concrete_resource(mcp, registry, descriptor)
    _register_dry_run_tools(mcp, tools)

    assert set(mcp.resources) == set(registry.list_resource_uris())
    for reader in mcp.resources.values():
        payload = json.loads(reader())  # type: ignore[operator]
        assert payload["uri"].startswith("sdc://")

    assert set(mcp.tools) == {
        "prepare_set_fio2",
        "prepare_set_peep",
        "prepare_acknowledge_alarm",
    }
    tool_calls = {
        "prepare_set_fio2": ("sim-ventilator-1", 45.0),
        "prepare_set_peep": ("sim-ventilator-1", 10.0),
        "prepare_acknowledge_alarm": (
            "sim-ventilator-1",
            "alarm.airway_pressure.high",
        ),
    }
    for name, arguments in tool_calls.items():
        result = json.loads(mcp.tools[name](*arguments))  # type: ignore[operator]
        assert result["dry_run"] is True
        assert result["executed"] is False
        assert result["write_operations_allowed"] is False

    assert spy.device_write_count == 0
    assert _state_digest(registry) == before


def test_tool_result_model_cannot_represent_execution() -> None:
    with pytest.raises(ValidationError, match="fail-closed"):
        ToolCallResult(tool="forbidden", status="accepted", executed=True)
    with pytest.raises(ValidationError, match="fail-closed"):
        ToolCallResult(tool="forbidden", status="accepted", write_operations_allowed=True)
    with pytest.raises(ValidationError, match="fail-closed"):
        ToolCallResult(tool="forbidden", status="accepted", dry_run=False)


def test_non_dry_run_policy_cannot_load() -> None:
    with pytest.raises(ValidationError, match="every tool policy must set dry_run_only=true"):
        ToolPolicyDocument.model_validate(
            {
                "version": "test",
                "tools": [
                    {
                        "name": "execute_setpoint",
                        "operation": "set_value",
                        "description": "forbidden",
                        "dry_run_only": False,
                    }
                ],
            }
        )


def test_static_agent_boundary_contains_no_device_write_api() -> None:
    package_root = Path("src/sdc_mcp_gateway")
    report = scan_agent_facing_boundary(package_root)
    assert report["status"] == "ok", report
    assert report["files_scanned"] > 0
    assert report["violations"] == []


def test_abstract_transition_system_has_no_execution_edge() -> None:
    report = NoExecutionTransitionSystem().verify()
    assert report["status"] == "ok", report
    assert report["device_effect_edges"] == 0
    assert report["execution_named_states_or_events"] == []


def test_cli_generates_reproducible_no_execution_evidence() -> None:
    result = runner.invoke(
        app,
        [
            "verify-no-execution",
            "--config",
            "config/gateway.simulated.dryrun.high-airway-pressure.example.yaml",
            "--mie",
            "config/sdc_mie.yaml",
            "--tool-policy",
            "config/tool_policies.yaml",
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["status"] == "ok"
    assert report["dynamic"]["device_write_count"] == 0
    assert report["dynamic"]["device_state_unchanged"] is True
    assert report["static"]["violations"] == []
    assert report["transition_system"]["device_effect_edges"] == 0
