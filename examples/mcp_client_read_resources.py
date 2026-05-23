"""Minimal MCP client example: list and read SDC-MCP resources.

Run from the repository root after installing the package with MCP support:

  python examples/mcp_client_read_resources.py

The script starts `sdc-mcp-gateway serve` as a stdio MCP subprocess, lists
resources, reads `sdc://health`, reads `sdc://devices`, and reads the first
available metrics resource.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from mcp_client_common import GatewayServerConfig, gateway_session, json_from_content_result, print_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read SDC-MCP resources through an MCP client.")
    parser.add_argument("--config", default="config/gateway.simulated.example.yaml")
    parser.add_argument("--mie", default="config/sdc_mie.yaml")
    parser.add_argument("--resource", default=None, help="Optional extra resource URI to read.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    server_config = GatewayServerConfig(config=Path(args.config), mie=Path(args.mie), cwd=Path.cwd())

    async with gateway_session(server_config) as session:
        resources_result = await session.list_resources()
        resource_uris = [str(resource.uri) for resource in resources_result.resources]

        print("\nAvailable resources:")
        for uri in resource_uris:
            print(f"  - {uri}")

        print("\nHealth resource:")
        print_json(json_from_content_result(await session.read_resource("sdc://health")))

        print("\nDevices resource:")
        print_json(json_from_content_result(await session.read_resource("sdc://devices")))

        metrics_uri = args.resource or next((uri for uri in resource_uris if uri.endswith("/metrics")), None)
        if metrics_uri is not None:
            print(f"\nMetrics resource: {metrics_uri}")
            print_json(json_from_content_result(await session.read_resource(metrics_uri)))


if __name__ == "__main__":
    asyncio.run(main())
