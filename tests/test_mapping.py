from pathlib import Path

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mapping.mapper import SdcMieMapper
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer


def test_load_mapping() -> None:
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    assert mapping.version == "0.8-example"
    assert "150456" in mapping.by_code()


def test_map_dummy_metrics_has_mapped_and_unmapped_entries() -> None:
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    mapper = SdcMieMapper(mapping)
    device = DummySdcConsumer().get_snapshots()[0]
    metrics = mapper.map_device_metrics(device)
    assert any(metric.semantic_name == "heart_rate" for metric in metrics)
    assert any(metric.mapped is False for metric in metrics)
