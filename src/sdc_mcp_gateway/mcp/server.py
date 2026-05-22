from __future__ import annotations

import json
from typing import Any

from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry


class MissingMcpDependency(RuntimeError):
    pass


def create_mcp_server(
    registry: ResourceRegistry,
    server_name: str = "sdc-mcp-gateway",
    tool_registry: DryRunToolRegistry | None = None,
) -> Any:
    """Create a FastMCP server exposing resources and optional dry-run tools.

    The default server remains read-only and registers only MCP resources. If a
    dry-run tool registry is supplied by a configuration with allow_tools=true,
    policy-checked tools are registered as action proposal validators. These
    tools never execute SDC operations.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception as exc:  # pragma: no cover - only triggered without optional dependency
        raise MissingMcpDependency(
            "The MCP Python SDK is not installed. Install with: pip install -e '.[mcp]'"
        ) from exc

    mcp = FastMCP(server_name)

    for descriptor in registry.list_resource_descriptors():
        _register_concrete_resource(mcp, registry, descriptor)

    if tool_registry is not None:
        _register_dry_run_tools(mcp, tool_registry)

    return mcp


def _register_concrete_resource(mcp: Any, registry: ResourceRegistry, descriptor: Any) -> None:
    uri = str(descriptor.uri)
    name = str(descriptor.name)
    description = str(descriptor.description)
    mime_type = str(descriptor.mime_type)

    def reader() -> str:
        return _json(registry.read(uri).model_dump())

    reader.__name__ = "read_" + uri.replace("://", "_").replace("/", "_").replace("-", "_")
    reader.__doc__ = description
    mcp.resource(uri, name=name, description=description, mime_type=mime_type)(reader)


def _register_dry_run_tools(mcp: Any, tool_registry: DryRunToolRegistry) -> None:
    tool_names = {descriptor.name for descriptor in tool_registry.list_tool_descriptors()}

    if "prepare_set_fio2" in tool_names:
        def prepare_set_fio2(device_id: str, value: float) -> str:
            """Validate a dry-run proposal to set ventilator FiO2; no SDC operation is executed."""
            return _json(tool_registry.call_tool("prepare_set_fio2", {"device_id": device_id, "value": value}).model_dump())
        mcp.tool(name="prepare_set_fio2", description=prepare_set_fio2.__doc__)(prepare_set_fio2)

    if "prepare_set_peep" in tool_names:
        def prepare_set_peep(device_id: str, value: float) -> str:
            """Validate a dry-run proposal to set ventilator PEEP; no SDC operation is executed."""
            return _json(tool_registry.call_tool("prepare_set_peep", {"device_id": device_id, "value": value}).model_dump())
        mcp.tool(name="prepare_set_peep", description=prepare_set_peep.__doc__)(prepare_set_peep)

    if "prepare_acknowledge_alarm" in tool_names:
        def prepare_acknowledge_alarm(device_id: str, alarm_handle: str) -> str:
            """Validate a dry-run alarm acknowledgement proposal; no acknowledgement is sent."""
            return _json(
                tool_registry.call_tool(
                    "prepare_acknowledge_alarm", {"device_id": device_id, "alarm_handle": alarm_handle}
                ).model_dump()
            )
        mcp.tool(name="prepare_acknowledge_alarm", description=prepare_acknowledge_alarm.__doc__)(prepare_acknowledge_alarm)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
