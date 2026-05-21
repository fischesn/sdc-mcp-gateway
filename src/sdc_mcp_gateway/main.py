from __future__ import annotations

import json
from pathlib import Path

import typer

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.mcp.server import MissingMcpDependency, create_mcp_server
from sdc_mcp_gateway.sdc.consumer import (
    DummySdcConsumer,
    MissingSdc11073Dependency,
    Sdc11073Consumer,
    SdcConsumer,
    SimulatedSdcConsumer,
)

app = typer.Typer(help="SDC-to-MCP Gateway research prototype")


def _make_recorder(config: GatewayConfig) -> JsonlRecorder:
    return JsonlRecorder(config.gateway.log_file)


def _make_consumer(config: GatewayConfig, recorder: JsonlRecorder | None = None) -> SdcConsumer:
    if config.sdc.adapter == "dummy":
        return DummySdcConsumer()
    if config.sdc.adapter == "simulated":
        if not config.sdc.simulation_config:
            raise typer.BadParameter("sdc.simulation_config must be set when adapter is simulated")
        return SimulatedSdcConsumer(
            scenario_path=config.sdc.simulation_config,
            elapsed_s=config.sdc.simulation_elapsed_s,
            recorder=recorder,
        )
    if config.sdc.adapter == "sdc11073":
        return Sdc11073Consumer(
            discovery_timeout_s=config.sdc.discovery_timeout_s,
            provider_whitelist=config.sdc.provider_whitelist,
            local_ip=config.sdc.local_ip,
            max_devices=config.sdc.max_devices,
            recorder=recorder,
        )
    raise typer.BadParameter(f"Unsupported SDC adapter: {config.sdc.adapter}")


def _make_registry(config_path: Path, mie_path: Path) -> ResourceRegistry:
    config = GatewayConfig.from_file(config_path)
    mapping = load_mapping(mie_path)
    recorder = _make_recorder(config)
    consumer = _make_consumer(config, recorder=recorder)
    devices = consumer.get_snapshots()
    return ResourceRegistry(devices=devices, mapping=mapping, recorder=recorder)


@app.command()
def discover(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
) -> None:
    """Discover SDC providers with the configured adapter and print provider identifiers."""

    gateway_config = GatewayConfig.from_file(config)
    recorder = _make_recorder(gateway_config)
    consumer = _make_consumer(gateway_config, recorder=recorder)
    try:
        providers = consumer.discover()
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    typer.echo(json.dumps({"providers": providers}, ensure_ascii=False, indent=2, sort_keys=True))


@app.command()
def snapshot(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Print all read-only resource payloads as JSON. Useful without an MCP client."""

    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    payloads = {uri: registry.read(uri).model_dump() for uri in registry.list_resource_uris()}
    typer.echo(json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("simulate-snapshot")
def simulate_snapshot(
    scenario: Path = typer.Option(Path("config/sim.patient-monitor.yaml"), help="Simulation scenario YAML file."),
    elapsed_s: float = typer.Option(0.0, help="Scenario time in seconds."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Generate a mapped snapshot from a simulation scenario without SDC networking."""

    from sdc_mcp_gateway.simulation.scenarios import SimulationEngine, SimulationScenario

    mapping = load_mapping(mie)
    scenario_doc = SimulationScenario.from_file(scenario)
    devices = SimulationEngine(scenario_doc).snapshot(elapsed_s=elapsed_s)
    registry = ResourceRegistry(devices=devices, mapping=mapping, recorder=None)
    payloads = {uri: registry.read(uri).model_dump() for uri in registry.list_resource_uris()}
    typer.echo(json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("list-resources")
def list_resources(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """List the read-only MCP resources exposed by the gateway."""

    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    descriptors = [descriptor.model_dump() for descriptor in registry.list_resource_descriptors()]
    typer.echo(json.dumps({"resources": descriptors}, ensure_ascii=False, indent=2, sort_keys=True))


@app.command("read-resource")
def read_resource(
    uri: str = typer.Argument(..., help="Resource URI, for example sdc://health."),
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Read one gateway resource without starting an external MCP client."""

    try:
        registry = _make_registry(config, mie)
        payload = registry.read(uri)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    except KeyError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(json.dumps(payload.model_dump(), ensure_ascii=False, indent=2, sort_keys=True))


@app.command("mcp-smoke-test")
def mcp_smoke_test(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
    require_mcp_sdk: bool = typer.Option(
        False,
        "--require-mcp-sdk/--no-require-mcp-sdk",
        help="Fail if the optional MCP Python SDK is not installed.",
    ),
) -> None:
    """Run a local smoke test of the read-only MCP resource surface.

    The command does not start a long-running stdio MCP server. It builds the same
    registry used by `serve`, verifies that all advertised resources can be read,
    checks the read-only safety boundary, and attempts to construct the FastMCP
    server when the optional MCP SDK is installed.
    """

    checks: list[dict[str, object]] = []
    failures: list[str] = []

    def add_check(name: str, ok: bool, details: dict[str, object] | None = None) -> None:
        checks.append({"name": name, "ok": ok, "details": details or {}})
        if not ok:
            failures.append(name)

    try:
        gateway_config = GatewayConfig.from_file(config)
        registry = _make_registry(config, mie)
        add_check("registry_created", True)
    except MissingSdc11073Dependency as exc:
        add_check("registry_created", False, {"error": str(exc)})
        typer.echo(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from exc
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        add_check("registry_created", False, {"error": str(exc)})
        typer.echo(json.dumps({"status": "failed", "checks": checks}, ensure_ascii=False, indent=2, sort_keys=True))
        raise typer.Exit(code=1) from exc

    descriptors = registry.list_resource_descriptors()
    resource_uris = [descriptor.uri for descriptor in descriptors]
    add_check("resources_listed", len(resource_uris) > 0, {"resource_count": len(resource_uris)})

    read_errors: list[dict[str, str]] = []
    for uri in resource_uris:
        try:
            registry.read(uri)
        except Exception as exc:  # pragma: no cover - defensive user-facing command
            read_errors.append({"uri": uri, "error": str(exc)})
    add_check(
        "all_advertised_resources_readable",
        len(read_errors) == 0,
        {"read_resource_count": len(resource_uris), "errors": read_errors},
    )

    health = registry.read("sdc://health").model_dump()
    health_data = health.get("data", {})
    add_check(
        "read_only_safety_boundary",
        bool(
            health_data.get("mode") == "read-only"
            and health_data.get("tools_exported") is False
            and health_data.get("write_operations_allowed") is False
        ),
        {
            "mode": health_data.get("mode"),
            "tools_exported": health_data.get("tools_exported"),
            "write_operations_allowed": health_data.get("write_operations_allowed"),
        },
    )
    add_check(
        "health_resource_count_matches_catalogue",
        health_data.get("resource_count") == len(resource_uris),
        {"health_resource_count": health_data.get("resource_count"), "catalogue_resource_count": len(resource_uris)},
    )

    resources_payload = registry.read("sdc://resources").model_dump()
    resources_data = resources_payload.get("data", [])
    add_check(
        "resource_catalogue_readable",
        isinstance(resources_data, list) and len(resources_data) == len(resource_uris),
        {"catalogue_entries": len(resources_data) if isinstance(resources_data, list) else None},
    )

    mcp_sdk_available = True
    server_constructed = False
    mcp_error: str | None = None
    try:
        create_mcp_server(registry, server_name=gateway_config.mcp.server_name)
        server_constructed = True
    except MissingMcpDependency as exc:
        mcp_sdk_available = False
        mcp_error = str(exc)
    except Exception as exc:  # pragma: no cover - defensive user-facing command
        mcp_error = str(exc)

    add_check(
        "fastmcp_server_constructed",
        server_constructed or (not require_mcp_sdk and not mcp_sdk_available),
        {
            "mcp_sdk_available": mcp_sdk_available,
            "server_constructed": server_constructed,
            "error": mcp_error,
            "required": require_mcp_sdk,
        },
    )

    status = "ok" if not failures else "failed"
    report = {
        "status": status,
        "config": str(config),
        "mie": str(mie),
        "adapter": gateway_config.sdc.adapter,
        "resource_count": len(resource_uris),
        "sample_resources": resource_uris[:5],
        "checks": checks,
    }
    typer.echo(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if failures:
        raise typer.Exit(code=1)


@app.command()
def serve(
    config: Path = typer.Option(Path("config/gateway.yaml"), help="Gateway YAML configuration."),
    mie: Path = typer.Option(Path("config/sdc_mie.yaml"), help="SDC-MIE YAML mapping file."),
) -> None:
    """Run the MCP server with the configured SDC adapter."""

    gateway_config = GatewayConfig.from_file(config)
    try:
        registry = _make_registry(config, mie)
    except MissingSdc11073Dependency as exc:
        raise typer.Exit(str(exc)) from exc
    try:
        mcp = create_mcp_server(registry, server_name=gateway_config.mcp.server_name)
    except MissingMcpDependency as exc:
        raise typer.Exit(str(exc)) from exc
    mcp.run()


if __name__ == "__main__":
    app()
