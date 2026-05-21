from __future__ import annotations

import json
from typing import Any

from sdc_mcp_gateway.mcp.resources import ResourceRegistry


class MissingMcpDependency(RuntimeError):
    pass


def create_mcp_server(registry: ResourceRegistry, server_name: str = "sdc-mcp-gateway") -> Any:
    """Create a FastMCP server exposing the read-only resource surface.

    This function imports the MCP SDK lazily so that unit tests and snapshot mode work
    without the optional `mcp` dependency installed.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception as exc:  # pragma: no cover - only triggered without optional dependency
        raise MissingMcpDependency(
            "The MCP Python SDK is not installed. Install with: pip install -e '.[mcp]'"
        ) from exc

    mcp = FastMCP(server_name)

    @mcp.resource("sdc://health")
    def health() -> str:
        return _json(registry.read("sdc://health").model_dump())

    @mcp.resource("sdc://resources")
    def resources() -> str:
        return _json(registry.read("sdc://resources").model_dump())

    @mcp.resource("sdc://devices")
    def devices() -> str:
        return _json(registry.read("sdc://devices").model_dump())

    @mcp.resource("sdc://mapping")
    def mapping() -> str:
        return _json(registry.read("sdc://mapping").model_dump())

    @mcp.resource("sdc://devices/{device_id}/metrics")
    def device_metrics(device_id: str) -> str:
        return _json(registry.read(f"sdc://devices/{device_id}/metrics").model_dump())

    @mcp.resource("sdc://devices/{device_id}/alarms")
    def device_alarms(device_id: str) -> str:
        return _json(registry.read(f"sdc://devices/{device_id}/alarms").model_dump())

    @mcp.resource("sdc://devices/{device_id}/context")
    def device_context(device_id: str) -> str:
        return _json(registry.read(f"sdc://devices/{device_id}/context").model_dump())

    @mcp.resource("sdc://devices/{device_id}/mdib/raw")
    def device_raw_mdib(device_id: str) -> str:
        return _json(registry.read(f"sdc://devices/{device_id}/mdib/raw").model_dump())

    return mcp


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
