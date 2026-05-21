from __future__ import annotations

from abc import ABC, abstractmethod
from time import monotonic
from typing import Any

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.models import AlarmState, AuditRecord, ContextState, DeviceSnapshot, MetricState
from sdc_mcp_gateway.sdc.extractor import MdibSnapshotExtractor


class SdcConsumer(ABC):
    """Abstract SDC consumer interface used by the gateway."""

    @abstractmethod
    def discover(self) -> list[str]:
        """Return provider identifiers discovered by the adapter."""

    @abstractmethod
    def get_snapshots(self) -> list[DeviceSnapshot]:
        """Return the latest known snapshots for all discovered providers."""


class DummySdcConsumer(SdcConsumer):
    """Deterministic dummy SDC consumer for development and tests."""

    def __init__(self) -> None:
        self._device = DeviceSnapshot(
            device_id="dummy-monitor-1",
            display_name="Dummy ICU Monitor",
            manufacturer="Research Prototype",
            model="DummySDC-v0.2",
            metrics=[
                MetricState(handle="metric.hr", code="150456", value=72, unit="beats/min", validity="valid"),
                MetricState(handle="metric.spo2", code="150452", value=98, unit="%", validity="valid"),
                MetricState(handle="metric.unmapped", code="999999", value=12.3, unit="arb", validity="valid"),
            ],
            alarms=[
                AlarmState(
                    handle="alarm.tachycardia",
                    code="alarm.hr.high",
                    presence=False,
                    priority="medium",
                    kind="physiological",
                )
            ],
            context=ContextState(
                patient_ref="dummy-patient-redacted",
                location_ref="lab-bed-1",
                raw={"note": "Dummy context; no personal data."},
            ),
            raw_mdib={
                "kind": "dummy-normalized-mdib",
                "warning": "This is not a real SDC MDIB.",
            },
        )

    def discover(self) -> list[str]:
        return [self._device.device_id]

    def get_snapshots(self) -> list[DeviceSnapshot]:
        return [self._device]


class MissingSdc11073Dependency(RuntimeError):
    """Raised when the optional sdc11073 dependency is not installed."""


class Sdc11073Consumer(SdcConsumer):
    """Read-only sdc11073 adapter for provider discovery and MDIB snapshots.

    v0.2 connects to SDC providers, initializes a ConsumerMdib, extracts a normalized
    read-only snapshot, and then disconnects again. It deliberately does not subscribe
    to events and does not execute SDC operations. Event streaming is scheduled for v0.3.
    """

    def __init__(
        self,
        discovery_timeout_s: int = 5,
        provider_whitelist: list[str] | None = None,
        local_ip: str = "127.0.0.1",
        max_devices: int | None = None,
        recorder: JsonlRecorder | None = None,
    ) -> None:
        self.discovery_timeout_s = discovery_timeout_s
        self.provider_whitelist = provider_whitelist or []
        self.local_ip = local_ip
        self.max_devices = max_devices
        self.recorder = recorder
        self.extractor = MdibSnapshotExtractor()

    def discover(self) -> list[str]:
        services = self._discover_services()
        return [self._service_epr(service) for service in services]

    def get_snapshots(self) -> list[DeviceSnapshot]:
        start = monotonic()
        services = self._discover_services()
        snapshots: list[DeviceSnapshot] = []
        for service in services:
            service_epr = self._service_epr(service)
            connect_start = monotonic()
            client: Any | None = None
            try:
                mdib, client = self._connect_and_init_mdib(service)
                snapshots.append(self.extractor.extract(mdib, provider_epr=service_epr))
                self._record(
                    "sdc_mdib_snapshot",
                    "ok",
                    {
                        "provider_epr": service_epr,
                        "duration_ms": round((monotonic() - connect_start) * 1000.0, 3),
                    },
                )
            except Exception as exc:
                self._record(
                    "sdc_mdib_snapshot",
                    "error",
                    {"provider_epr": service_epr, "error": str(exc)},
                )
            finally:
                self._stop_client(client)
        self._record(
            "sdc_snapshot_run",
            "ok",
            {
                "device_count": len(snapshots),
                "duration_ms": round((monotonic() - start) * 1000.0, 3),
            },
        )
        return snapshots

    def _discover_services(self) -> list[Any]:
        imports = self._imports()
        start = monotonic()
        with imports["WSDiscovery"](self.local_ip) as discovery:
            search = discovery.search_services
            try:
                services = search(
                    types=imports["SdcV1Definitions"].MedicalDeviceTypesFilter,
                    timeout=self.discovery_timeout_s,
                )
            except TypeError:
                services = search(types=imports["SdcV1Definitions"].MedicalDeviceTypesFilter)
        filtered = [service for service in services if self._provider_allowed(self._service_epr(service))]
        if self.max_devices is not None:
            filtered = filtered[: self.max_devices]
        self._record(
            "sdc_discovery",
            "ok",
            {
                "local_ip": self.local_ip,
                "discovered_count": len(services),
                "accepted_count": len(filtered),
                "duration_ms": round((monotonic() - start) * 1000.0, 3),
            },
        )
        return filtered

    def _connect_and_init_mdib(self, service: Any) -> tuple[Any, Any]:
        imports = self._imports()
        client = imports["SdcConsumer"].from_wsd_service(service, ssl_context_container=None)
        try:
            client.start_all(not_subscribed_actions=imports["periodic_actions"])
        except TypeError:
            client.start_all()
        mdib = imports["ConsumerMdib"](client)
        mdib.init_mdib()
        return mdib, client

    def _provider_allowed(self, epr: str) -> bool:
        if not self.provider_whitelist:
            return True
        return any(allowed == epr or allowed in epr for allowed in self.provider_whitelist)

    def _service_epr(self, service: Any) -> str:
        return str(getattr(service, "epr", service))

    def _stop_client(self, client: Any | None) -> None:
        if client is None:
            return
        for method_name in ("stop_all", "stop"):
            method = getattr(client, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception:
                    pass
                return

    def _record(self, event_type: str, status: str, details: dict[str, Any]) -> None:
        if self.recorder is None:
            return
        self.recorder.write(AuditRecord(event_type=event_type, status=status, details=details))

    def _imports(self) -> dict[str, Any]:
        try:
            from sdc11073.consumer.consumerimpl import SdcConsumer as RealSdcConsumer  # type: ignore
            from sdc11073.definitions_sdc import SdcV1Definitions  # type: ignore
            from sdc11073.mdib import ConsumerMdib  # type: ignore
            from sdc11073.wsdiscovery import WSDiscovery  # type: ignore
            from sdc11073.xml_types.actions import periodic_actions  # type: ignore
        except Exception as exc:  # pragma: no cover - triggered only without optional dependency
            raise MissingSdc11073Dependency(
                "The optional sdc11073 dependency is not installed. Install with: "
                "pip install -e '.[sdc]' or pip install -e '.[all]'."
            ) from exc
        return {
            "SdcConsumer": RealSdcConsumer,
            "SdcV1Definitions": SdcV1Definitions,
            "ConsumerMdib": ConsumerMdib,
            "WSDiscovery": WSDiscovery,
            "periodic_actions": periodic_actions,
        }
