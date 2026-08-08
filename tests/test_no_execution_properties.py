from __future__ import annotations

import hashlib
import json

from hypothesis import given, settings, strategies as st

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.safety.no_execution import DeviceWriteSpy
from sdc_mcp_gateway.safety.state_machine import (
    BoundaryEvent,
    BoundaryState,
    NoExecutionTransitionSystem,
)
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer, WriteSpySdcConsumer
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies


JSON_SCALAR = st.none() | st.booleans() | st.integers() | st.floats(allow_nan=True) | st.text()
JSON_VALUE = st.recursive(
    JSON_SCALAR,
    lambda children: st.lists(children, max_size=5)
    | st.dictionaries(st.text(max_size=20), children, max_size=5),
    max_leaves=15,
)


def _system() -> tuple[DeviceWriteSpy, ResourceRegistry, DryRunToolRegistry]:
    spy = DeviceWriteSpy()
    consumer = WriteSpySdcConsumer(
        SimulatedSdcConsumer("config/sim.high-airway-pressure.yaml", elapsed_s=100.0),
        spy,
    )
    registry = ResourceRegistry(
        devices=consumer.get_snapshots(),
        mapping=load_mapping("config/sdc_mie.yaml"),
        tools_exported=True,
        tool_mode="dry-run",
        gateway_mode="dry-run-tools",
    )
    tools = DryRunToolRegistry(
        resource_registry=registry,
        policies=load_tool_policies("config/tool_policies.yaml"),
        tools_enabled=True,
    )
    return spy, registry, tools


def _digest(registry: ResourceRegistry) -> str:
    state = [item.model_dump(mode="json") for item in registry.devices.values()]
    return hashlib.sha256(json.dumps(state, sort_keys=True).encode("utf-8")).hexdigest()


@settings(max_examples=200, deadline=None)
@given(
    tool_name=st.sampled_from(
        ["prepare_set_fio2", "prepare_set_peep", "prepare_acknowledge_alarm", "unknown"]
    ),
    arguments=JSON_VALUE,
)
def test_arbitrary_json_tool_calls_never_execute(tool_name: str, arguments: object) -> None:
    spy, registry, tools = _system()
    before = _digest(registry)
    result = tools.call_tool(tool_name, arguments)
    assert result.dry_run is True
    assert result.executed is False
    assert result.write_operations_allowed is False
    assert spy.device_write_count == 0
    assert _digest(registry) == before


@settings(max_examples=150, deadline=None)
@given(uri=st.text(max_size=120))
def test_arbitrary_resource_reads_never_write(uri: str) -> None:
    spy, registry, _ = _system()
    before = _digest(registry)
    try:
        registry.read(uri)
    except KeyError:
        pass
    assert spy.device_write_count == 0
    assert _digest(registry) == before


@settings(max_examples=200, deadline=None)
@given(events=st.lists(st.sampled_from(list(BoundaryEvent)), max_size=50))
def test_arbitrary_transition_sequences_have_no_device_effect(events: list[BoundaryEvent]) -> None:
    system = NoExecutionTransitionSystem()
    state = BoundaryState.IDLE
    for event in events:
        transition = system.transition(state, event)
        if transition is None:
            continue
        assert transition.device_effect is False
        state = transition.target
    assert "execut" not in state.value


@settings(max_examples=100, deadline=None)
@given(
    actions=st.lists(
        st.sampled_from(
            [
                "read_health",
                "read_metrics",
                "read_unknown",
                "fio2_valid",
                "fio2_invalid",
                "peep_valid",
                "acknowledge",
                "unknown_tool",
            ]
        ),
        max_size=40,
    )
)
def test_arbitrary_mixed_mcp_interaction_sequences_never_execute(actions: list[str]) -> None:
    spy, registry, tools = _system()
    before = _digest(registry)
    operations = {
        "read_health": lambda: registry.read("sdc://health"),
        "read_metrics": lambda: registry.read("sdc://devices/sim-ventilator-1/metrics"),
        "read_unknown": lambda: registry.read("sdc://devices/unknown/metrics"),
        "fio2_valid": lambda: tools.call_tool(
            "prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 45.0}
        ),
        "fio2_invalid": lambda: tools.call_tool(
            "prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": float("nan")}
        ),
        "peep_valid": lambda: tools.call_tool(
            "prepare_set_peep", {"device_id": "sim-ventilator-1", "value": 10.0}
        ),
        "acknowledge": lambda: tools.call_tool(
            "prepare_acknowledge_alarm",
            {"device_id": "sim-ventilator-1", "alarm_handle": "alarm.airway_pressure.high"},
        ),
        "unknown_tool": lambda: tools.call_tool("unknown", {}),
    }
    for action in actions:
        try:
            operations[action]()
        except KeyError:
            pass
        assert spy.device_write_count == 0
        assert _digest(registry) == before
