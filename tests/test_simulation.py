from pathlib import Path

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer
from sdc_mcp_gateway.simulation.scenarios import SimulationEngine, SimulationScenario


def test_simulation_scenario_loads_combined_devices() -> None:
    scenario = SimulationScenario.from_file(Path("config/sim.combined.yaml"))
    assert len(scenario.devices) == 2
    assert scenario.devices[0].device_id == "sim-monitor-1"
    assert scenario.devices[1].device_id == "sim-ventilator-1"


def test_simulation_engine_produces_metrics_and_alarms() -> None:
    scenario = SimulationScenario.from_file(Path("config/sim.patient-monitor.yaml"))
    snapshots = SimulationEngine(scenario).snapshot(elapsed_s=10.0)
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    assert snapshot.device_id == "sim-monitor-1"
    assert {metric.code for metric in snapshot.metrics} >= {"150456", "150452", "151562"}
    assert snapshot.alarms
    assert snapshot.raw_mdib["kind"] == "simulated-normalized-mdib"


def test_simulated_consumer_discovers_and_returns_snapshots() -> None:
    consumer = SimulatedSdcConsumer("config/sim.ventilator.yaml", elapsed_s=5.0)
    assert consumer.discover() == ["sim-ventilator-1"]
    snapshots = consumer.get_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].display_name == "Simulated Ventilator"


def test_simulated_gateway_config_loads() -> None:
    cfg = GatewayConfig.from_file("config/gateway.simulated.example.yaml")
    assert cfg.sdc.adapter == "simulated"
    assert cfg.sdc.simulation_config == "config/sim.combined.yaml"
    assert cfg.gateway.allow_tools is False
