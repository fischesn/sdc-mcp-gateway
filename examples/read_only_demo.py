from __future__ import annotations

from pathlib import Path

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer


def main() -> None:
    config = GatewayConfig.from_file(Path("config/gateway.yaml"))
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    devices = DummySdcConsumer().get_snapshots()
    registry = ResourceRegistry(devices, mapping, JsonlRecorder(config.gateway.log_file))
    for uri in registry.list_resource_uris():
        print("\n==", uri)
        print(registry.read(uri).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
