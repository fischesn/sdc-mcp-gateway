"""Shared helpers for the SDC-MCP Gateway example MCP clients.

The examples use the stdio MCP transport: the client starts
`sdc-mcp-gateway serve` as a subprocess and communicates over stdin/stdout.
This is the local MCP mode supported by the current artifact. Network server
transport is intentionally out of scope for v0.10.x.
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryFile
from typing import Any, AsyncIterator

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except Exception as exc:  # pragma: no cover - import depends on optional MCP SDK
    raise SystemExit(
        "The MCP Python SDK is required for these examples. Install with:\n"
        "  python -m pip install -e '.[mcp]'\n"
        "or:\n"
        "  python -m pip install -e '.[all]'"
    ) from exc


@dataclass(frozen=True)
class GatewayServerConfig:
    """Configuration for starting the gateway as a stdio MCP subprocess."""

    config: Path
    mie: Path = Path("config/sdc_mie.yaml")
    cwd: Path | None = None
    timeout_s: float = 15.0


def server_args(server_config: GatewayServerConfig) -> list[str]:
    """Return Python module arguments for the stdio MCP gateway server."""

    return [
        "-m",
        "sdc_mcp_gateway.main",
        "serve",
        "--config",
        str(server_config.config),
        "--mie",
        str(server_config.mie),
    ]


@asynccontextmanager
async def gateway_session(server_config: GatewayServerConfig) -> AsyncIterator[Any]:
    """Start the gateway MCP server and yield an initialized ClientSession."""

    errlog = TemporaryFile(mode="w+t", encoding="utf-8")
    params = StdioServerParameters(
        command=sys.executable,
        args=server_args(server_config),
        cwd=str(server_config.cwd) if server_config.cwd is not None else None,
    )

    try:
        async with stdio_client(params, errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=server_config.timeout_s),
            ) as session:
                await session.initialize()
                yield session
    except Exception as exc:
        errlog.flush()
        errlog.seek(0)
        stderr_tail = errlog.read()[-2000:]
        if stderr_tail:
            raise RuntimeError(f"MCP client example failed. Server stderr tail:\n{stderr_tail}") from exc
        raise


def text_from_content_result(result: Any) -> str:
    """Extract text from an MCP read_resource or call_tool result."""

    contents = getattr(result, "contents", None)
    if contents is None:
        contents = getattr(result, "content", None)
    if not contents:
        raise ValueError("MCP result contains no text content")

    first = contents[0]
    text = getattr(first, "text", None)
    if text is None:
        raise ValueError("MCP result content is not text")
    return str(text)


def json_from_content_result(result: Any) -> Any:
    """Parse JSON text returned by an MCP resource or dry-run tool."""

    return json.loads(text_from_content_result(result))


def print_json(data: Any) -> None:
    """Pretty-print JSON-compatible data."""

    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))
