from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import timedelta
from tempfile import TemporaryFile
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import SdcConsumer


class McpClientSmokeTestError(RuntimeError):
    pass


class MissingMcpClientDependency(RuntimeError):
    pass


@dataclass(frozen=True)
class McpClientSmokeTestConfig:
    config_path: Path
    mie_path: Path
    cwd: Path | None = None
    timeout_s: float = 15.0



def _read_stderr_tail(errlog: Any) -> str:
    try:
        errlog.flush()
        errlog.seek(0)
        return str(errlog.read())[-2000:]
    except Exception:
        return ""

def _extract_text_content(read_resource_result: Any) -> str:
    contents = getattr(read_resource_result, "contents", None)
    if not contents:
        raise McpClientSmokeTestError("read_resource returned no contents")
    first = contents[0]
    text = getattr(first, "text", None)
    if text is None:
        raise McpClientSmokeTestError("read_resource did not return text content")
    return str(text)


def _json_from_text_resource(read_resource_result: Any) -> dict[str, Any]:
    text = _extract_text_content(read_resource_result)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise McpClientSmokeTestError(f"resource content is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise McpClientSmokeTestError("resource content JSON is not an object")
    return parsed


def _server_args(config_path: Path, mie_path: Path) -> list[str]:
    return [
        "-m",
        "sdc_mcp_gateway.main",
        "serve",
        "--config",
        str(config_path),
        "--mie",
        str(mie_path),
    ]


def run_mcp_client_smoke_test(test_config: McpClientSmokeTestConfig) -> dict[str, Any]:
    """Run an end-to-end MCP client smoke test against the gateway server.

    The test starts the gateway's stdio MCP server as a subprocess and interacts
    with it through the MCP Python SDK. It is intentionally read-only: it lists
    resources, reads selected resources, and verifies that no tools are exposed.
    """

    try:
        import anyio
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise MissingMcpClientDependency(
            "The MCP Python SDK is not installed. Install with: pip install -e '.[mcp]'"
        ) from exc

    async def _run() -> dict[str, Any]:
        errlog = TemporaryFile(mode="w+t", encoding="utf-8")
        server_params = StdioServerParameters(
            command=sys.executable,
            args=_server_args(test_config.config_path, test_config.mie_path),
            cwd=str(test_config.cwd) if test_config.cwd is not None else None,
        )

        checks: list[dict[str, Any]] = []
        failures: list[str] = []

        def add_check(name: str, ok: bool, details: dict[str, Any] | None = None) -> None:
            checks.append({"name": name, "ok": ok, "details": details or {}})
            if not ok:
                failures.append(name)

        async with stdio_client(server_params, errlog=errlog) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=test_config.timeout_s),
            ) as session:
                init_result = await session.initialize()
                add_check(
                    "client_initialized",
                    True,
                    {
                        "protocol_version": getattr(init_result, "protocolVersion", None),
                        "server_name": getattr(getattr(init_result, "serverInfo", None), "name", None),
                    },
                )

                resources_result = await session.list_resources()
                resource_uris = [str(resource.uri) for resource in resources_result.resources]
                add_check(
                    "mcp_list_resources",
                    len(resource_uris) > 0,
                    {"resource_count": len(resource_uris), "sample_resources": resource_uris[:5]},
                )

                templates_result = await session.list_resource_templates()
                template_uris = [str(template.uriTemplate) for template in templates_result.resourceTemplates]
                add_check(
                    "mcp_list_resource_templates",
                    True,
                    {"template_count": len(template_uris), "templates": template_uris},
                )

                expected_static = {"sdc://health", "sdc://resources", "sdc://devices", "sdc://mapping"}
                add_check(
                    "static_resources_present",
                    expected_static.issubset(set(resource_uris)),
                    {"missing": sorted(expected_static.difference(resource_uris))},
                )

                health_payload = _json_from_text_resource(await session.read_resource("sdc://health"))
                health_data = health_payload.get("data", {})
                add_check(
                    "mcp_read_health",
                    bool(health_data.get("status") == "ok" and health_data.get("mode") == "read-only"),
                    {
                        "status": health_data.get("status"),
                        "mode": health_data.get("mode"),
                        "resource_count": health_data.get("resource_count"),
                    },
                )
                add_check(
                    "mcp_read_only_safety_boundary",
                    bool(
                        health_data.get("tools_exported") is False
                        and health_data.get("write_operations_allowed") is False
                    ),
                    {
                        "tools_exported": health_data.get("tools_exported"),
                        "write_operations_allowed": health_data.get("write_operations_allowed"),
                    },
                )

                catalogue_payload = _json_from_text_resource(await session.read_resource("sdc://resources"))
                catalogue_data = catalogue_payload.get("data", [])
                catalogue_uris = [entry.get("uri") for entry in catalogue_data if isinstance(entry, dict)]
                add_check(
                    "mcp_read_resource_catalogue",
                    isinstance(catalogue_data, list) and len(catalogue_data) >= len(resource_uris),
                    {"catalogue_entries": len(catalogue_data), "catalogue_sample": catalogue_uris[:5]},
                )

                device_payload = _json_from_text_resource(await session.read_resource("sdc://devices"))
                devices = device_payload.get("data", [])
                add_check(
                    "mcp_read_devices",
                    isinstance(devices, list) and len(devices) > 0,
                    {"device_count": len(devices) if isinstance(devices, list) else None},
                )

                sampled_device_metric_uris = [
                    uri for uri in catalogue_uris if isinstance(uri, str) and uri.endswith("/metrics")
                ][:2]
                metric_results: list[dict[str, Any]] = []
                metric_ok = len(sampled_device_metric_uris) > 0
                for uri in sampled_device_metric_uris:
                    payload = _json_from_text_resource(await session.read_resource(uri))
                    metrics = payload.get("data", [])
                    metric_results.append(
                        {
                            "uri": uri,
                            "metric_count": len(metrics) if isinstance(metrics, list) else None,
                            "all_mapped": all(
                                isinstance(metric, dict) and metric.get("mapped") is True
                                for metric in metrics
                            )
                            if isinstance(metrics, list)
                            else False,
                        }
                    )
                    metric_ok = metric_ok and isinstance(metrics, list) and len(metrics) > 0
                add_check("mcp_read_sample_device_metrics", metric_ok, {"samples": metric_results})

                tools_result = await session.list_tools()
                tools = getattr(tools_result, "tools", [])
                add_check("mcp_no_tools_exported", len(tools) == 0, {"tool_count": len(tools)})

        status = "ok" if not failures else "failed"
        return {
            "status": status,
            "config": str(test_config.config_path),
            "mie": str(test_config.mie_path),
            "command": sys.executable,
            "args": _server_args(test_config.config_path, test_config.mie_path),
            "checks": checks,
            "server_stderr_tail": _read_stderr_tail(errlog),
        }

    return anyio.run(_run)
