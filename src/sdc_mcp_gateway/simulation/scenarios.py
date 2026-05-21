from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.models import AlarmState, ContextState, DeviceSnapshot, MetricState, utc_now_iso


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

    version: str = "0.3"
    description: str | None = None
    random_seed: int = 42
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
                    validity=metric.validity,
                    raw={
                        "source": "simulation",
                        "baseline": metric.baseline,
                        "amplitude": metric.amplitude,
                        "period_s": metric.period_s,
                    },
                )
            )

        alarms = [self._alarm_state(alarm, values_by_handle) for alarm in device.alarms]
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
                "generated_at": utc_now_iso(),
            },
        )

    def _metric_value(self, metric: SimMetricConfig, elapsed_s: float, rng: random.Random) -> float:
        period = metric.period_s if metric.period_s > 0 else 60.0
        periodic = metric.amplitude * math.sin((2.0 * math.pi * elapsed_s) / period)
        noisy = rng.uniform(-metric.noise, metric.noise) if metric.noise else 0.0
        value = metric.baseline + periodic + noisy
        if metric.min_value is not None:
            value = max(metric.min_value, value)
        if metric.max_value is not None:
            value = min(metric.max_value, value)
        return value

    def _alarm_state(self, alarm: SimAlarmConfig, values_by_handle: dict[str, float]) -> AlarmState:
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
            raw={
                "source": "simulation",
                "metric_handle": alarm.metric_handle,
                "metric_value": value,
                "high_threshold": alarm.high_threshold,
                "low_threshold": alarm.low_threshold,
            },
        )
