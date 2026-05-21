from __future__ import annotations

from sdc_mcp_gateway.models import DeviceSnapshot, MappedMetric, MappingDocument


class SdcMieMapper:
    """Maps normalized SDC objects into agent-readable semantic representations."""

    def __init__(self, mapping: MappingDocument) -> None:
        self.mapping = mapping
        self._by_code = mapping.by_code()

    def map_metric(self, metric_handle: str, metric_code: str | None, value: object, unit: str | None, timestamp: str) -> MappedMetric:
        if metric_code and metric_code in self._by_code:
            entry = self._by_code[metric_code]
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
                timestamp=timestamp,
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
            timestamp=timestamp,
        )

    def map_device_metrics(self, device: DeviceSnapshot) -> list[MappedMetric]:
        return [
            self.map_metric(
                metric_handle=metric.handle,
                metric_code=metric.code,
                value=metric.value,
                unit=metric.unit,
                timestamp=metric.timestamp,
            )
            for metric in device.metrics
        ]
