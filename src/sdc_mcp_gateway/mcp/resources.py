from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mapper import SdcMieMapper
from sdc_mcp_gateway.models import AuditRecord, DeviceSnapshot, MappingDocument, ResourcePayload


class ResourceDescriptor(BaseModel):
    """Machine-readable description of one read-only MCP resource."""

    uri: str
    name: str
    description: str
    mime_type: str = "application/json"
    read_only: bool = True


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
        return [descriptor.uri for descriptor in self.list_resource_descriptors()]

    def list_resource_descriptors(self) -> list[ResourceDescriptor]:
        descriptors = [
            ResourceDescriptor(
                uri="sdc://health",
                name="Gateway health",
                description="Read-only health and safety status of the SDC-to-MCP gateway.",
            ),
            ResourceDescriptor(
                uri="sdc://resources",
                name="Resource catalogue",
                description="Machine-readable catalogue of all currently exposed SDC MCP resources.",
            ),
            ResourceDescriptor(
                uri="sdc://devices",
                name="Device list",
                description="List of currently known SDC providers exposed by the gateway.",
            ),
            ResourceDescriptor(
                uri="sdc://mapping",
                name="SDC-MIE mapping",
                description="Semantic mapping document used to translate SDC/BICEPS codes into agent-readable labels.",
            ),
        ]
        for device_id, device in sorted(self.devices.items()):
            label = device.display_name or device_id
            descriptors.extend(
                [
                    ResourceDescriptor(
                        uri=f"sdc://devices/{device_id}/metrics",
                        name=f"Metrics for {label}",
                        description="Mapped read-only metric states for this SDC provider.",
                    ),
                    ResourceDescriptor(
                        uri=f"sdc://devices/{device_id}/alarms",
                        name=f"Alarms for {label}",
                        description="Read-only alarm states for this SDC provider.",
                    ),
                    ResourceDescriptor(
                        uri=f"sdc://devices/{device_id}/context",
                        name=f"Context for {label}",
                        description="Read-only patient, location, operator, and workflow context references.",
                    ),
                    ResourceDescriptor(
                        uri=f"sdc://devices/{device_id}/mdib/raw",
                        name=f"Raw MDIB-like snapshot for {label}",
                        description=(
                            "Raw or normalized MDIB snapshot payload. For simulated providers this is not a real "
                            "IEEE 11073 SDC MDIB."
                        ),
                    ),
                ]
            )
        return descriptors

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
                    "resource_count": len(self.list_resource_descriptors()),
                    "tools_exported": False,
                    "write_operations_allowed": False,
                },
            )
        if uri == "sdc://resources":
            return self._payload(
                uri,
                [descriptor.model_dump() for descriptor in self.list_resource_descriptors()],
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
