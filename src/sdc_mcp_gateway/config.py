from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class GatewaySection(BaseModel):
    name: str = "sdc-to-mcp-gateway"
    mode: str = "read-only"
    log_file: str = "data/logs/gateway.jsonl"
    expose_raw_mdib: bool = True
    allow_tools: bool = False
    allow_write_operations: bool = False


class SdcSection(BaseModel):
    adapter: str = "dummy"
    discovery_timeout_s: int = 5
    provider_whitelist: list[str] = Field(default_factory=list)
    local_ip: str = "127.0.0.1"
    max_devices: int | None = None
    simulation_config: str | None = None
    simulation_elapsed_s: float = 0.0


class McpSection(BaseModel):
    server_name: str = "sdc-mcp-gateway"
    transport: str = "stdio"


class GatewayConfig(BaseModel):
    gateway: GatewaySection = Field(default_factory=GatewaySection)
    sdc: SdcSection = Field(default_factory=SdcSection)
    mcp: McpSection = Field(default_factory=McpSection)

    @classmethod
    def from_file(cls, path: str | Path) -> "GatewayConfig":
        data = _load_yaml(path)
        return cls.model_validate(data)


def _load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a YAML mapping at {path}")
    return loaded
