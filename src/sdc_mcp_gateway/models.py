from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class MetricState(BaseModel):
    """Normalized read-only representation of an SDC metric state."""

    handle: str
    code: str | None = None
    value: float | int | str | None = None
    unit: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)
    validity: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class AlarmState(BaseModel):
    """Normalized read-only representation of an SDC alarm state."""

    handle: str
    code: str | None = None
    presence: bool | None = None
    priority: str | None = None
    kind: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)
    raw: dict[str, Any] = Field(default_factory=dict)


class ContextState(BaseModel):
    """Normalized read-only representation of selected SDC context state."""

    patient_ref: str | None = None
    location_ref: str | None = None
    operator_ref: str | None = None
    workflow_ref: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class DeviceSnapshot(BaseModel):
    """Latest known normalized state of one SDC provider."""

    device_id: str
    display_name: str
    manufacturer: str | None = None
    model: str | None = None
    metrics: list[MetricState] = Field(default_factory=list)
    alarms: list[AlarmState] = Field(default_factory=list)
    context: ContextState = Field(default_factory=ContextState)
    raw_mdib: dict[str, Any] = Field(default_factory=dict)
    observed_at: str = Field(default_factory=utc_now_iso)


class MappingEntry(BaseModel):
    """One semantic mapping entry loaded from the SDC-MIE YAML file."""

    code: str
    semantic_name: str
    label: str
    unit: str | None = None
    access: Literal["read-only", "read-write"] = "read-only"
    safety_class: str = "informational"
    min_value: float | None = None
    max_value: float | None = None
    requires_human_approval: bool = False
    description: str = ""


class MappingDocument(BaseModel):
    version: str
    description: str | None = None
    mappings: list[MappingEntry] = Field(default_factory=list)

    def by_code(self) -> dict[str, MappingEntry]:
        return {entry.code: entry for entry in self.mappings}


class MappedMetric(BaseModel):
    handle: str
    code: str | None = None
    semantic_name: str | None = None
    label: str | None = None
    value: float | int | str | None = None
    unit: str | None = None
    safety_class: str | None = None
    description: str | None = None
    mapped: bool
    timestamp: str


class ResourcePayload(BaseModel):
    uri: str
    generated_at: str = Field(default_factory=utc_now_iso)
    mapping_version: str | None = None
    data: Any


class AuditRecord(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    event_type: str
    resource_uri: str | None = None
    status: str
    mapping_version: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
