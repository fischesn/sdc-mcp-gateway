"""Small deterministic agent demo using the gateway through MCP.

This is not a generative LLM. It is a compact example of how an agent program can
use an MCP ClientSession to inspect resources and, if requested, call dry-run
MCP tools. It demonstrates the integration pattern for custom Python agents.

Examples:

  python examples/agent_mcp_client_demo.py --question "Is there an active alarm?"

  python examples/agent_mcp_client_demo.py \
    --config config/gateway.simulated.dryrun.example.yaml \
    --question "Prepare a dry-run proposal to set FiO2 to 45 percent."
"""

from __future__ import annotations

import argparse
import asyncio
import re
from pathlib import Path
from typing import Any

from mcp_client_common import GatewayServerConfig, gateway_session, json_from_content_result, print_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic agent demo using an MCP client.")
    parser.add_argument("--config", default="config/gateway.simulated.dryrun.example.yaml")
    parser.add_argument("--mie", default="config/sdc_mie.yaml")
    parser.add_argument(
        "--question",
        default="Is there an active alarm and which device is affected?",
        help="Natural-language-like question for the deterministic demo agent.",
    )
    return parser.parse_args()


def _extract_fio2_request(question: str) -> float | None:
    lowered = question.lower()
    if "fio2" not in lowered and "fi o2" not in lowered:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*%?", lowered)
    if match is None:
        return None
    return float(match.group(1))


def _active_alarms_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    data = payload.get("data", [])
    if not isinstance(data, list):
        return []
    return [alarm for alarm in data if isinstance(alarm, dict) and alarm.get("active") is True]


async def _read_json(session: Any, uri: str) -> Any:
    return json_from_content_result(await session.read_resource(uri))


async def main() -> None:
    args = parse_args()
    question = str(args.question)
    server_config = GatewayServerConfig(config=Path(args.config), mie=Path(args.mie), cwd=Path.cwd())

    async with gateway_session(server_config) as session:
        resources_result = await session.list_resources()
        resource_uris = [str(resource.uri) for resource in resources_result.resources]
        tools_result = await session.list_tools()
        tool_names = [tool.name for tool in tools_result.tools]

        print("Question:")
        print(f"  {question}")

        fio2_value = _extract_fio2_request(question)
        if fio2_value is not None and "prepare_set_fio2" in tool_names:
            result = await session.call_tool(
                "prepare_set_fio2",
                {"device_id": "sim-ventilator-1", "value": fio2_value},
            )
            print("\nAgent action:")
            print("  Calling dry-run MCP tool prepare_set_fio2")
            print("\nTool result:")
            print_json(json_from_content_result(result))
            return

        alarm_uris = [uri for uri in resource_uris if uri.endswith("/alarms")]
        active_alarms: list[dict[str, Any]] = []
        for uri in alarm_uris:
            payload = await _read_json(session, uri)
            active_alarms.extend(_active_alarms_from_payload(payload))

        print("\nAgent answer:")
        if active_alarms:
            for alarm in active_alarms:
                print(
                    "  Active alarm: "
                    f"device={alarm.get('device_id', 'unknown')}, "
                    f"semantic_name={alarm.get('semantic_name', 'unknown')}, "
                    f"priority={alarm.get('priority', 'unknown')}"
                )
        else:
            print("  No active alarm is currently exposed by the gateway.")

        print("\nSafety boundary:")
        health = await _read_json(session, "sdc://health")
        health_data = health.get("data", {}) if isinstance(health, dict) else {}
        print(f"  mode: {health_data.get('mode')}")
        print(f"  tools_exported: {health_data.get('tools_exported')}")
        print(f"  write_operations_allowed: {health_data.get('write_operations_allowed')}")


if __name__ == "__main__":
    asyncio.run(main())
