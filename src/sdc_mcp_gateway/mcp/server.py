from __future__ import annotations

import json
from typing import Any

from sdc_mcp_gateway.mcp.resources import ResourceRegistry


class MissingMcpDependency(RuntimeError):
    pass


def create_mcp_server(registry: ResourceRegistry, server_name: str = "sdc-mcp-gateway") -> Any:
    """Create a FastMCP server exposing the read-only resource surface.

    The server registers every currently advertised gateway resource as a concrete
    MCP resource. This makes `list_resources` useful for clients and avoids forcing
    clients to infer device-specific URIs from templates. No MCP tools are exposed
    in the read-only prototype.

    The MCP SDK is imported lazily so snapshot mode and unit tests can run without
    the optional dependency installed.
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

    return mcp


def _register_concrete_resource(mcp: Any, registry: ResourceRegistry, descriptor: Any) -> None:
    uri = str(descriptor.uri)
    name = str(descriptor.name)
    description = str(descriptor.description)
    mime_type = str(descriptor.mime_type)

    def reader() -> str:
        return _json(registry.read(uri).model_dump())

    # Give the function a unique name for easier debugging/introspection.
    reader.__name__ = "read_" + uri.replace("://", "_").replace("/", "_").replace("-", "_")
    reader.__doc__ = description
    mcp.resource(uri, name=name, description=description, mime_type=mime_type)(reader)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
