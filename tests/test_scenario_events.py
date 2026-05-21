from pathlib import Path

from sdc_mcp_gateway.simulation.scenarios import SimulationEngine, SimulationScenario


def _active_alarm_handles(scenario_path: str, elapsed_s: float) -> set[str]:
    scenario = SimulationScenario.from_file(Path(scenario_path))
    snapshots = SimulationEngine(scenario).snapshot(elapsed_s=elapsed_s)
    return {alarm.handle for device in snapshots for alarm in device.alarms if alarm.presence}


def _metric_value(scenario_path: str, elapsed_s: float, handle: str) -> float:
    scenario = SimulationScenario.from_file(Path(scenario_path))
    snapshots = SimulationEngine(scenario).snapshot(elapsed_s=elapsed_s)
    for device in snapshots:
        for metric in device.metrics:
            if metric.handle == handle:
                return float(metric.value)
    raise AssertionError(f"Metric {handle} not found")


def test_tachycardia_scenario_crosses_heart_rate_alarm() -> None:
    assert "alarm.hr.high" not in _active_alarm_handles("config/sim.tachycardia.yaml", 0)
    assert _metric_value("config/sim.tachycardia.yaml", 60, "metric.hr") > 120
    assert "alarm.hr.high" in _active_alarm_handles("config/sim.tachycardia.yaml", 60)


def test_spo2_drop_scenario_crosses_low_spo2_alarm() -> None:
    assert "alarm.spo2.low" not in _active_alarm_handles("config/sim.spo2-drop.yaml", 0)
    assert _metric_value("config/sim.spo2-drop.yaml", 70, "metric.spo2") < 90
    assert "alarm.spo2.low" in _active_alarm_handles("config/sim.spo2-drop.yaml", 70)


def test_high_airway_pressure_scenario_crosses_alarm() -> None:
    assert "alarm.airway_pressure.high" not in _active_alarm_handles(
        "config/sim.high-airway-pressure.yaml", 0
    )
    assert _metric_value("config/sim.high-airway-pressure.yaml", 60, "metric.airway_pressure") > 40
    assert "alarm.airway_pressure.high" in _active_alarm_handles(
        "config/sim.high-airway-pressure.yaml", 60
    )
