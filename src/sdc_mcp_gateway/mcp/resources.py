from __future__ import annotations

from typing import Any

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mapper import SdcMieMapper
from sdc_mcp_gateway.models import AuditRecord, DeviceSnapshot, MappingDocument, ResourcePayload


class ResourceRegistry:
    """Builds MCP resource payloads from local SDC gateway state."""

    def __init__(
        self,
        devices: list[DeviceSnapshot],
        mapping: MappingDocument,
        recorder: JsonlRecorder | None = None,
    ) -> None:
        self.devices = {device.device_id: device for device in devices}
        self.mapping = mapping
        self.mapper = SdcMieMapper(mapping)
        self.recorder = recorder

    def list_resource_uris(self) -> list[str]:
        uris = ["sdc://health", "sdc://devices", "sdc://mapping"]
        for device_id in sorted(self.devices):
            uris.extend(
                [
                    f"sdc://devices/{device_id}/metrics",
                    f"sdc://devices/{device_id}/alarms",
                    f"sdc://devices/{device_id}/context",
                    f"sdc://devices/{device_id}/mdib/raw",
                ]
            )
        return uris

    def read(self, uri: str) -> ResourcePayload:
        try:
            payload = self._read(uri)
            self._audit(uri, "ok")
            return payload
        except Exception as exc:
            self._audit(uri, "error", {"error": str(exc)})
            raise

    def _read(self, uri: str) -> ResourcePayload:
        if uri == "sdc://health":
            return self._payload(
                uri,
                {
                    "status": "ok",
                    "mode": "read-only",
                    "device_count": len(self.devices),
                    "mapping_version": self.mapping.version,
                    "tools_exported": False,
                    "write_operations_allowed": False,
                },
            )
        if uri == "sdc://devices":
            return self._payload(
                uri,
                [
                    {
                        "device_id": device.device_id,
                        "display_name": device.display_name,
                        "manufacturer": device.manufacturer,
                        "model": device.model,
                        "observed_at": device.observed_at,
                    }
                    for device in self.devices.values()
                ],
            )
        if uri == "sdc://mapping":
            return self._payload(uri, self.mapping.model_dump())

        parts = uri.removeprefix("sdc://").split("/")
        if len(parts) < 3 or parts[0] != "devices":
            raise KeyError(f"Unknown SDC resource URI: {uri}")
        device_id = parts[1]
        device = self._get_device(device_id)
        section = "/".join(parts[2:])

        if section == "metrics":
            return self._payload(uri, [metric.model_dump() for metric in self.mapper.map_device_metrics(device)])
        if section == "alarms":
            return self._payload(uri, [alarm.model_dump() for alarm in device.alarms])
        if section == "context":
            return self._payload(uri, device.context.model_dump())
        if section == "mdib/raw":
            return self._payload(uri, device.raw_mdib)
        raise KeyError(f"Unknown SDC device resource section: {section}")

    def _get_device(self, device_id: str) -> DeviceSnapshot:
        try:
            return self.devices[device_id]
        except KeyError as exc:
            raise KeyError(f"Unknown device_id: {device_id}") from exc

    def _payload(self, uri: str, data: Any) -> ResourcePayload:
        return ResourcePayload(uri=uri, mapping_version=self.mapping.version, data=data)

    def _audit(self, uri: str, status: str, details: dict[str, Any] | None = None) -> None:
        if self.recorder is None:
            return
        self.recorder.write(
            AuditRecord(
                event_type="resource_read",
                resource_uri=uri,
                status=status,
                mapping_version=self.mapping.version,
                details=details or {},
            )
        )
