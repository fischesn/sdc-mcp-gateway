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
        tools_exported: bool = False,
        tool_mode: str | None = None,
        write_operations_allowed: bool = False,
        gateway_mode: str = "read-only",
    ) -> None:
        self.devices = {device.device_id: device for device in devices}
        self.mapping = mapping
        self.mapper = SdcMieMapper(mapping)
        self.recorder = recorder
        self.tools_exported = tools_exported
        self.tool_mode = tool_mode
        self.write_operations_allowed = write_operations_allowed
        self.gateway_mode = gateway_mode

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
            non_current = [
                device
                for device in self.devices.values()
                if device.freshness not in {"fresh", "recovered"}
                or device.provider_status != "connected"
            ]
            return self._payload(
                uri,
                {
                    "status": "degraded" if non_current else "ok",
                    "mode": self.gateway_mode,
                    "device_count": len(self.devices),
                    "mapping_version": self.mapping.version,
                    "mapping_schema_version": self.mapping.schema_version,
                    "mapping_sha256": self.mapping.source_sha256,
                    "resource_count": len(self.list_resource_descriptors()),
                    "tools_exported": self.tools_exported,
                    "tool_mode": self.tool_mode,
                    "write_operations_allowed": self.write_operations_allowed,
                    "non_current_device_count": len(non_current),
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
                        "source_timestamp": device.source_timestamp,
                        "gateway_received_at": device.gateway_received_at,
                        "age_of_information_ms": device.age_of_information_ms,
                        "provider_status": device.provider_status,
                        "sequence_id": device.sequence_id,
                        "mdib_version": device.mdib_version,
                        "update_sequence": device.update_sequence,
                        "freshness": device.freshness,
                        "freshness_reason": device.freshness_reason,
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
        return ResourcePayload(
            uri=uri,
            mapping_version=self.mapping.version,
            mapping_sha256=self.mapping.source_sha256,
            data=data,
        )

    def _audit(self, uri: str, status: str, details: dict[str, Any] | None = None) -> None:
        if self.recorder is None:
            return
        self.recorder.write(
            AuditRecord(
                event_type="resource_read",
                resource_uri=uri,
                status=status,
                mapping_version=self.mapping.version,
                mapping_sha256=self.mapping.source_sha256,
                details=details or {},
            )
        )
