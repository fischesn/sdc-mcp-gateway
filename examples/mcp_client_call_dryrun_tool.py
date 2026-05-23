"""Minimal MCP client example: call a dry-run MCP tool.

Run from the repository root after installing the package with MCP support:

  python examples/mcp_client_call_dryrun_tool.py

The script starts the gateway with the dry-run configuration, lists tools, and
calls `prepare_set_fio2` with an in-range value. The expected result is
`accepted_dry_run` and `executed=false`.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from mcp_client_common import GatewayServerConfig, gateway_session, json_from_content_result, print_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call SDC-MCP dry-run tools through an MCP client.")
    parser.add_argument("--config", default="config/gateway.simulated.dryrun.example.yaml")
    parser.add_argument("--mie", default="config/sdc_mie.yaml")
    parser.add_argument("--device-id", default="sim-ventilator-1")
    parser.add_argument("--fio2", type=float, default=45.0)
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    server_config = GatewayServerConfig(config=Path(args.config), mie=Path(args.mie), cwd=Path.cwd())

    async with gateway_session(server_config) as session:
        tools_result = await session.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]
        print("\nAvailable tools:")
        for name in tool_names:
            print(f"  - {name}")

        if "prepare_set_fio2" not in tool_names:
            raise RuntimeError("prepare_set_fio2 is not exposed. Use a dry-run gateway configuration.")

        result = await session.call_tool(
            "prepare_set_fio2",
            {"device_id": args.device_id, "value": args.fio2},
        )

        print("\nDry-run tool result:")
        print_json(json_from_content_result(result))


if __name__ == "__main__":
    asyncio.run(main())
