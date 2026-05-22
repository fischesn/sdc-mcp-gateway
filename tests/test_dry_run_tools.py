from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.main import app, _make_tool_registry

runner = CliRunner()

CONFIG = Path("config/gateway.simulated.dryrun.example.yaml")
MIE = Path("config/sdc_mie.yaml")
POLICY = Path("config/tool_policies.yaml")


def test_dry_run_tool_registry_lists_tools() -> None:
    registry = _make_tool_registry(CONFIG, MIE, POLICY)
    names = {descriptor.name for descriptor in registry.list_tool_descriptors()}
    assert {"prepare_set_fio2", "prepare_set_peep", "prepare_acknowledge_alarm"}.issubset(names)


def test_valid_fio2_is_accepted_without_execution() -> None:
    registry = _make_tool_registry(CONFIG, MIE, POLICY)
    result = registry.call_tool("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 45.0})
    assert result.status == "accepted_dry_run"
    assert result.executed is False
    assert result.write_operations_allowed is False
    assert result.requires_human_approval is True
    assert result.allowed_range == [21.0, 100.0]


def test_out_of_range_fio2_is_rejected() -> None:
    registry = _make_tool_registry(CONFIG, MIE, POLICY)
    result = registry.call_tool("prepare_set_fio2", {"device_id": "sim-ventilator-1", "value": 150.0})
    assert result.status == "rejected"
    assert result.reason == "value_out_of_range"
    assert result.executed is False


def test_wrong_device_type_is_rejected() -> None:
    registry = _make_tool_registry(CONFIG, MIE, POLICY)
    result = registry.call_tool("prepare_set_peep", {"device_id": "sim-monitor-1", "value": 8.0})
    assert result.status == "rejected"
    assert result.reason == "wrong_device_type"


def test_cli_tool_smoke_test() -> None:
    result = runner.invoke(
        app,
        [
            "tool-smoke-test",
            "--config",
            str(CONFIG),
            "--mie",
            str(MIE),
            "--tool-policy",
            str(POLICY),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"dry_run_safety_boundary"' in result.output


def test_cli_call_tool_rejects_out_of_range_without_cli_failure() -> None:
    result = runner.invoke(
        app,
        [
            "call-tool",
            "prepare_set_fio2",
            "--args-json",
            '{"device_id":"sim-ventilator-1","value":150}',
            "--config",
            str(CONFIG),
            "--mie",
            str(MIE),
            "--tool-policy",
            str(POLICY),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "rejected"' in result.output
    assert '"reason": "value_out_of_range"' in result.output


def test_cli_call_tool_accepts_args_file() -> None:
    result = runner.invoke(
        app,
        [
            "call-tool",
            "prepare_set_fio2",
            "--args-file",
            "config/tool_args/set_fio2_45.json",
            "--config",
            str(CONFIG),
            "--mie",
            str(MIE),
            "--tool-policy",
            str(POLICY),
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "accepted_dry_run"' in result.output
    assert '"executed": false' in result.output


def test_cli_call_tool_rejects_args_json_and_args_file_together() -> None:
    result = runner.invoke(
        app,
        [
            "call-tool",
            "prepare_set_fio2",
            "--args-json",
            '{"device_id":"sim-ventilator-1","value":45}',
            "--args-file",
            "config/tool_args/set_fio2_45.json",
            "--config",
            str(CONFIG),
        ],
    )
    assert result.exit_code != 0
    assert (
        "Use either --args-json or --args-file" in result.output
        or "Invalid value" in result.output
        or "args-json" in result.output
        or "args-file" in result.output
    )
    result.output
