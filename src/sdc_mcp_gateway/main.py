from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print

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
)

app = typer.Typer(help="SDC-to-MCP Gateway research prototype")


def _make_recorder(config: GatewayConfig) -> JsonlRecorder:
    return JsonlRecorder(config.gateway.log_file)


def _make_consumer(config: GatewayConfig, recorder: JsonlRecorder | None = None) -> SdcConsumer:
    if config.sdc.adapter == "dummy":
        return DummySdcConsumer()
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
    print(json.dumps({"providers": providers}, ensure_ascii=False, indent=2, sort_keys=True))


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
    print(json.dumps(payloads, ensure_ascii=False, indent=2, sort_keys=True))


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
