from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from sdc_mcp_gateway.models import MappingDocument


def load_mapping(path: str | Path) -> MappingDocument:
    """Load an SDC-MIE YAML mapping document."""

    with Path(path).open("r", encoding="utf-8") as handle:
        data: Any = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping document at {path}")
    return MappingDocument.model_validate(data)
