from __future__ import annotations

import json
from pathlib import Path

from sdc_mcp_gateway.models import AuditRecord


class JsonlRecorder:
    """Small append-only JSONL recorder for audit and measurement events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: AuditRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False, sort_keys=True) + "\n")
