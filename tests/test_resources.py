from pathlib import Path

import pytest

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer


def make_registry() -> ResourceRegistry:
    return ResourceRegistry(
        devices=DummySdcConsumer().get_snapshots(),
        mapping=load_mapping(Path("config/sdc_mie.yaml")),
        recorder=None,
    )


def test_resource_uris_include_expected_dummy_resources() -> None:
    registry = make_registry()
    uris = registry.list_resource_uris()
    assert "sdc://health" in uris
    assert "sdc://devices" in uris
    assert "sdc://devices/dummy-monitor-1/metrics" in uris
    assert "sdc://devices/dummy-monitor-1/mdib/raw" in uris


def test_read_metrics_resource() -> None:
    registry = make_registry()
    payload = registry.read("sdc://devices/dummy-monitor-1/metrics")
    data = payload.data
    assert isinstance(data, list)
    assert any(item["semantic_name"] == "heart_rate" for item in data)


def test_unknown_device_raises_key_error() -> None:
    registry = make_registry()
    with pytest.raises(KeyError):
        registry.read("sdc://devices/missing/metrics")
