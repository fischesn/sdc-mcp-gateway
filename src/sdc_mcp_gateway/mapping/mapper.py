from __future__ import annotations

from sdc_mcp_gateway.models import DeviceSnapshot, FreshnessState, MappedMetric, MappingDocument


class SdcMieMapper:
    """Maps normalized SDC objects into agent-readable semantic representations."""

    def __init__(self, mapping: MappingDocument) -> None:
        self.mapping = mapping
        self._by_code = mapping.by_code()
        self._by_handle = mapping.by_handle()

    def map_metric(
        self,
        metric_handle: str,
        metric_code: str | None,
        value: object,
        unit: str | None,
        timestamp: str,
        validity: str | None = None,
        freshness: FreshnessState = "fresh",
        unsupported: bool = False,
    ) -> MappedMetric:
        code_entry = self._by_code.get(metric_code) if metric_code else None
        handle_entry = self._by_handle.get(metric_handle)
        if code_entry is not None and handle_entry is not None and code_entry is not handle_entry:
            return MappedMetric(
                handle=metric_handle,
                code=metric_code,
                semantic_name=None,
                label=None,
                value=value,  # type: ignore[arg-type]
                unit=unit,
                safety_class=None,
                description="Code and handle resolve to different SDC-MIE entries.",
                mapped=False,
                mapping_state="conflicting",
                mapping_reason=(
                    f"code maps to {code_entry.code!r}, handle maps to {handle_entry.code!r}"
                ),
                observed_unit=unit,
                timestamp=timestamp,
                validity=validity,
                freshness=freshness,
            )

        entry = code_entry or handle_entry
        if entry is not None:
            if unit is not None and entry.unit is not None and unit != entry.unit:
                return MappedMetric(
                    handle=metric_handle,
                    code=metric_code,
                    semantic_name=None,
                    label=None,
                    value=value,  # type: ignore[arg-type]
                    unit=unit,
                    safety_class=None,
                    description="Observed unit conflicts with the SDC-MIE mapping entry.",
                    mapped=False,
                    mapping_state="conflicting",
                    mapping_reason=f"observed unit {unit!r} differs from mapped unit {entry.unit!r}",
                    mapping_entry_code=entry.code,
                    observed_unit=unit,
                    timestamp=timestamp,
                    validity=validity,
                    freshness=freshness,
                )
            return MappedMetric(
                handle=metric_handle,
                code=metric_code,
                semantic_name=entry.semantic_name,
                label=entry.label,
                value=value,  # type: ignore[arg-type]
                unit=entry.unit or unit,
                safety_class=entry.safety_class,
                description=entry.description,
                mapped=True,
                mapping_state="mapped",
                mapping_reason="unique code/handle match with compatible unit",
                mapping_entry_code=entry.code,
                observed_unit=unit,
                timestamp=timestamp,
                validity=validity,
                freshness=freshness,
            )
        return MappedMetric(
            handle=metric_handle,
            code=metric_code,
            semantic_name=None,
            label=None,
            value=value,  # type: ignore[arg-type]
            unit=unit,
            safety_class=None,
            description="No SDC-MIE mapping entry found for this metric.",
            mapped=False,
            mapping_state="unsupported" if unsupported else "unmapped",
            mapping_reason="extractor marked element unsupported"
            if unsupported
            else "no code or handle mapping entry",
            observed_unit=unit,
            timestamp=timestamp,
            validity=validity,
            freshness=freshness,
        )

    def map_device_metrics(self, device: DeviceSnapshot) -> list[MappedMetric]:
        return [
            self.map_metric(
                metric_handle=metric.handle,
                metric_code=metric.code,
                value=metric.value,
                unit=metric.unit,
                timestamp=metric.timestamp,
                validity=metric.validity,
                freshness=metric.freshness,
                unsupported=bool(metric.raw.get("unsupported", False)),
            )
            for metric in device.metrics
        ]
