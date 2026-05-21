from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.main import app
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer


runner = CliRunner()


def make_registry() -> ResourceRegistry:
    return ResourceRegistry(
        devices=DummySdcConsumer().get_snapshots(),
        mapping=load_mapping(Path("config/sdc_mie.yaml")),
        recorder=None,
    )


def test_resource_catalog_is_exposed_as_resource() -> None:
    registry = make_registry()
    payload = registry.read("sdc://resources")
    assert isinstance(payload.data, list)
    uris = {item["uri"] for item in payload.data}
    assert "sdc://health" in uris
    assert "sdc://resources" in uris
    assert "sdc://devices/dummy-monitor-1/metrics" in uris


def test_health_reports_resource_count_and_read_only_boundary() -> None:
    registry = make_registry()
    payload = registry.read("sdc://health")
    assert payload.data["mode"] == "read-only"
    assert payload.data["tools_exported"] is False
    assert payload.data["write_operations_allowed"] is False
    assert payload.data["resource_count"] == len(registry.list_resource_descriptors())


def test_cli_list_resources_simulated_config() -> None:
    result = runner.invoke(
        app,
        [
            "list-resources",
            "--config",
            "config/gateway.simulated.example.yaml",
            "--mie",
            "config/sdc_mie.yaml",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "sdc://devices/sim-monitor-1/metrics" in result.output
    assert "sdc://devices/sim-ventilator-1/metrics" in result.output


def test_cli_read_single_resource() -> None:
    result = runner.invoke(
        app,
        [
            "read-resource",
            "sdc://health",
            "--config",
            "config/gateway.simulated.example.yaml",
            "--mie",
            "config/sdc_mie.yaml",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"write_operations_allowed": false' in result.output
