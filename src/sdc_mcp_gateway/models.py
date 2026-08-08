from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


FreshnessState = Literal["fresh", "stale", "invalid", "unavailable", "recovered"]
ProviderStatus = Literal["connected", "disconnected", "unavailable"]
MappingState = Literal["mapped", "unmapped", "unsupported", "conflicting"]


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
    freshness: FreshnessState = "fresh"
    raw: dict[str, Any] = Field(default_factory=dict)


class AlarmState(BaseModel):
    """Normalized read-only representation of an SDC alarm state."""

    handle: str
    code: str | None = None
    presence: bool | None = None
    priority: str | None = None
    kind: str | None = None
    timestamp: str = Field(default_factory=utc_now_iso)
    lifecycle_state: Literal[
        "inactive", "active", "latched", "acknowledged", "suppressed"
    ] = "inactive"
    acknowledged: bool = False
    latched: bool = False
    suppressed: bool = False
    transition_sequence: int = 0
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
    source_timestamp: str = Field(default_factory=utc_now_iso)
    gateway_received_at: str = Field(default_factory=utc_now_iso)
    age_of_information_ms: float = 0.0
    provider_status: ProviderStatus = "connected"
    sequence_id: str = "initial"
    mdib_version: int = 0
    update_sequence: int = 0
    freshness: FreshnessState = "fresh"
    freshness_reason: str = "current_valid_state"


class MappingEntry(BaseModel):
    """One semantic mapping entry loaded from the SDC-MIE YAML file."""

    model_config = ConfigDict(extra="forbid")

    code: str
    handles: list[str] = Field(default_factory=list)
    semantic_name: str
    label: str
    unit: str | None = None
    access: Literal["read-only", "read-write"] = "read-only"
    safety_class: str = "informational"
    min_value: float | None = None
    max_value: float | None = None
    requires_human_approval: bool = False
    description: str = ""
    provenance: str | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> MappingEntry:
        if (self.min_value is None) != (self.max_value is None):
            raise ValueError("min_value and max_value must either both be set or both be omitted")
        if self.min_value is not None and self.max_value is not None:
            if self.min_value > self.max_value:
                raise ValueError("min_value must be less than or equal to max_value")
        return self


class MappingProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    basis: list[str]
    scope: str
    license: str | None = None


class MappingDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    version: str
    description: str
    provenance: MappingProvenance
    mappings: list[MappingEntry] = Field(default_factory=list)
    source_sha256: str | None = None
    schema_id: str | None = None

    def by_code(self) -> dict[str, MappingEntry]:
        return {entry.code: entry for entry in self.mappings}

    def by_handle(self) -> dict[str, MappingEntry]:
        return {handle: entry for entry in self.mappings for handle in entry.handles}

    @model_validator(mode="after")
    def validate_uniqueness_and_consistency(self) -> MappingDocument:
        codes = [entry.code for entry in self.mappings]
        duplicate_codes = sorted({code for code in codes if codes.count(code) > 1})
        if duplicate_codes:
            raise ValueError(f"duplicate mapping codes: {duplicate_codes}")

        handles = [handle for entry in self.mappings for handle in entry.handles]
        duplicate_handles = sorted({handle for handle in handles if handles.count(handle) > 1})
        if duplicate_handles:
            raise ValueError(f"duplicate mapping handles: {duplicate_handles}")

        semantics: dict[str, MappingEntry] = {}
        for entry in self.mappings:
            previous = semantics.get(entry.semantic_name)
            if previous is not None and previous.unit != entry.unit:
                raise ValueError(
                    f"conflicting units for semantic_name {entry.semantic_name!r}: "
                    f"{previous.unit!r} versus {entry.unit!r}"
                )
            semantics[entry.semantic_name] = entry
        return self


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
    mapping_state: MappingState
    mapping_reason: str
    mapping_entry_code: str | None = None
    observed_unit: str | None = None
    timestamp: str
    validity: str | None = None
    freshness: FreshnessState = "fresh"


class ResourcePayload(BaseModel):
    uri: str
    generated_at: str = Field(default_factory=utc_now_iso)
    mapping_version: str | None = None
    mapping_sha256: str | None = None
    data: Any


class AuditRecord(BaseModel):
    timestamp: str = Field(default_factory=utc_now_iso)
    event_type: str
    resource_uri: str | None = None
    status: str
    mapping_version: str | None = None
    mapping_sha256: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
