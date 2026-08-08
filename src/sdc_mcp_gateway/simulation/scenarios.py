from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from sdc_mcp_gateway.models import (
    AlarmState,
    ContextState,
    DeviceSnapshot,
    FreshnessState,
    MetricState,
)


class SimMetricEventConfig(BaseModel):
    """Time-dependent modifier for one simulated metric.

    Events allow a scenario author to create clinically meaningful trajectories
    such as tachycardia, oxygen desaturation, or high airway pressure without
    changing the simulator code.
    """

    kind: Literal["step", "ramp", "pulse"] = "step"
    start_s: float = 0.0
    end_s: float | None = None
    target: float | None = None
    delta: float | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _validate_event(self) -> "SimMetricEventConfig":
        if self.end_s is not None and self.end_s < self.start_s:
            raise ValueError("event end_s must be greater than or equal to start_s")
        if self.target is None and self.delta is None:
            raise ValueError("event must define either target or delta")
        return self


class SimMetricConfig(BaseModel):
    """Configuration for one simulated metric."""

    handle: str
    code: str | None = None
    unit: str | None = None
    baseline: float = 0.0
    amplitude: float = 0.0
    period_s: float = 60.0
    noise: float = 0.0
    min_value: float | None = None
    max_value: float | None = None
    validity: str = "valid"
    freshness: FreshnessState = "fresh"
    events: list[SimMetricEventConfig] = Field(default_factory=list)


class SimAlarmConfig(BaseModel):
    """Configuration for one simulated alarm condition."""

    handle: str
    code: str | None = None
    metric_handle: str | None = None
    high_threshold: float | None = None
    low_threshold: float | None = None
    priority: str = "medium"
    kind: str = "physiological"


class SimDeviceConfig(BaseModel):
    """Configuration for one simulated SDC-like device."""

    device_id: str
    display_name: str
    manufacturer: str = "Research Prototype"
    model: str = "Simulated-SDC-Device"
    location_ref: str = "simulation-lab"
    patient_ref: str | None = "simulated-patient-redacted"
    metrics: list[SimMetricConfig] = Field(default_factory=list)
    alarms: list[SimAlarmConfig] = Field(default_factory=list)


class SimulationScenario(BaseModel):
    """A reproducible scenario containing one or more simulated device snapshots."""

    version: str = "0.7"
    description: str | None = None
    random_seed: int = 42
    start_time: str = "2026-01-01T00:00:00Z"
    devices: list[SimDeviceConfig] = Field(default_factory=list)

    @classmethod
    def from_file(cls, path: str | Path) -> "SimulationScenario":
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected a YAML mapping at {path}")
        return cls.model_validate(data)


@dataclass
class SimulationEngine:
    """Deterministic in-process simulation of SDC-like device state.

    This intentionally does not open a real IEEE 11073 SDC network endpoint. It
    produces normalized snapshots with the same internal data model used by the
    gateway. The purpose is to develop and test mapping, MCP resources, logging,
    and later policy logic before real SDC devices are available.
    """

    scenario: SimulationScenario

    def snapshot(self, elapsed_s: float = 0.0) -> list[DeviceSnapshot]:
        rng = random.Random(self.scenario.random_seed + int(elapsed_s * 1000))
        return [self._device_snapshot(device, elapsed_s, rng) for device in self.scenario.devices]

    def _device_snapshot(
        self, device: SimDeviceConfig, elapsed_s: float, rng: random.Random
    ) -> DeviceSnapshot:
        source_timestamp = self._scenario_timestamp(elapsed_s)
        update_sequence = max(1, int(round(elapsed_s * 1000.0)) + 1)
        metrics: list[MetricState] = []
        values_by_handle: dict[str, float] = {}
        for metric in device.metrics:
            value = self._metric_value(metric, elapsed_s, rng)
            values_by_handle[metric.handle] = value
            metrics.append(
                MetricState(
                    handle=metric.handle,
                    code=metric.code,
                    value=round(value, 3),
                    unit=metric.unit,
                    timestamp=source_timestamp,
                    validity=metric.validity,
                    freshness=metric.freshness,
                    raw={
                        "source": "simulation",
                        "baseline": metric.baseline,
                        "amplitude": metric.amplitude,
                        "period_s": metric.period_s,
                        "event_count": len(metric.events),
                    },
                )
            )

        alarms = [
            self._alarm_state(alarm, values_by_handle, source_timestamp) for alarm in device.alarms
        ]
        return DeviceSnapshot(
            device_id=device.device_id,
            display_name=device.display_name,
            manufacturer=device.manufacturer,
            model=device.model,
            metrics=metrics,
            alarms=alarms,
            context=ContextState(
                patient_ref=device.patient_ref,
                location_ref=device.location_ref,
                raw={"source": "simulation", "scenario_version": self.scenario.version},
            ),
            raw_mdib={
                "kind": "simulated-normalized-mdib",
                "warning": "This is not a real IEEE 11073 SDC MDIB.",
                "generated_at": source_timestamp,
            },
            observed_at=source_timestamp,
            source_timestamp=source_timestamp,
            gateway_received_at=source_timestamp,
            age_of_information_ms=0.0,
            provider_status="connected",
            sequence_id=f"sim-{device.device_id}",
            mdib_version=update_sequence,
            update_sequence=update_sequence,
            freshness="fresh",
            freshness_reason="current_valid_state",
        )

    def _scenario_timestamp(self, elapsed_s: float) -> str:
        start = datetime.fromisoformat(self.scenario.start_time.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        timestamp = start.astimezone(UTC) + timedelta(seconds=elapsed_s)
        return timestamp.isoformat().replace("+00:00", "Z")

    def _metric_value(self, metric: SimMetricConfig, elapsed_s: float, rng: random.Random) -> float:
        period = metric.period_s if metric.period_s > 0 else 60.0
        periodic = metric.amplitude * math.sin((2.0 * math.pi * elapsed_s) / period)
        noisy = rng.uniform(-metric.noise, metric.noise) if metric.noise else 0.0
        value = metric.baseline + periodic + noisy
        for event in metric.events:
            value = self._apply_event(value, metric.baseline, event, elapsed_s)
        if metric.min_value is not None:
            value = max(metric.min_value, value)
        if metric.max_value is not None:
            value = min(metric.max_value, value)
        return value

    def _apply_event(
        self, current_value: float, baseline: float, event: SimMetricEventConfig, elapsed_s: float
    ) -> float:
        if elapsed_s < event.start_s:
            return current_value

        if event.kind == "ramp":
            if event.end_s is None or event.end_s == event.start_s:
                return self._event_value(current_value, event)
            progress = (elapsed_s - event.start_s) / (event.end_s - event.start_s)
            # After the ramp end, the scenario remains at the fully applied
            # target/delta. This makes ramp scenarios useful for benchmark runs
            # that continue after the onset phase.
            progress = min(1.0, max(0.0, progress))
            target_value = self._event_value(baseline, event)
            return current_value + progress * (target_value - baseline)

        if event.end_s is not None and elapsed_s > event.end_s:
            return current_value

        if event.kind == "step":
            return self._event_value(current_value, event)

        if event.kind == "pulse":
            # A pulse behaves like a finite step between start_s and end_s. If no
            # end_s is given, it remains active after start_s.
            return self._event_value(current_value, event)

        return current_value

    def _event_value(self, current_value: float, event: SimMetricEventConfig) -> float:
        if event.target is not None:
            return event.target
        if event.delta is not None:
            return current_value + event.delta
        return current_value

    def _alarm_state(
        self,
        alarm: SimAlarmConfig,
        values_by_handle: dict[str, float],
        timestamp: str,
    ) -> AlarmState:
        value = values_by_handle.get(alarm.metric_handle or "")
        present = False
        if value is not None:
            if alarm.high_threshold is not None and value > alarm.high_threshold:
                present = True
            if alarm.low_threshold is not None and value < alarm.low_threshold:
                present = True
        return AlarmState(
            handle=alarm.handle,
            code=alarm.code,
            presence=present,
            priority=alarm.priority,
            kind=alarm.kind,
            timestamp=timestamp,
            lifecycle_state="active" if present else "inactive",
            raw={
                "source": "simulation",
                "metric_handle": alarm.metric_handle,
                "metric_value": value,
                "high_threshold": alarm.high_threshold,
                "low_threshold": alarm.low_threshold,
            },
        )
