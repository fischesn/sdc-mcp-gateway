from __future__ import annotations

from abc import ABC, abstractmethod

from sdc_mcp_gateway.models import AlarmState, ContextState, DeviceSnapshot, MetricState


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
            model="DummySDC-v0.1",
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


class Sdc11073Consumer(SdcConsumer):
    """Adapter placeholder for the real sdc11073-based implementation.

    v0.1 intentionally does not implement real-device discovery. The class exists so that
    the repository structure and CLI remain stable when v0.2 adds real SDC discovery and
    MDIB extraction.
    """

    def __init__(self, discovery_timeout_s: int = 5, provider_whitelist: list[str] | None = None) -> None:
        self.discovery_timeout_s = discovery_timeout_s
        self.provider_whitelist = provider_whitelist or []

    def discover(self) -> list[str]:
        raise NotImplementedError("Real sdc11073 discovery is scheduled for v0.2.")

    def get_snapshots(self) -> list[DeviceSnapshot]:
        raise NotImplementedError("Real sdc11073 MDIB snapshot extraction is scheduled for v0.2.")
