from __future__ import annotations

from pathlib import Path

import pytest

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.extractor import MdibSnapshotExtractor
from sdc_mcp_gateway.sdc.protocol_testbed import ProtocolTestbedConfig, run_protocol_testbed
from sdc_mcp_gateway.sdc.reference_provider import (
    PROFILE_VALUES,
    _initialize_metric_values,
    profile_mdib_path,
)


@pytest.mark.parametrize("profile", sorted(PROFILE_VALUES))
def test_reference_profile_is_schema_valid_and_extractable(profile: str) -> None:
    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.mdib import ProviderMdib

    mdib = ProviderMdib.from_mdib_file(str(profile_mdib_path(profile)), SdcV1Definitions)
    _initialize_metric_values(mdib, profile)
    snapshot = MdibSnapshotExtractor().extract(mdib, provider_epr=f"urn:uuid:test-{profile}")

    assert len(snapshot.metrics) == len(PROFILE_VALUES[profile])
    assert snapshot.raw_mdib["descriptor_count"] > 0
    assert snapshot.raw_mdib["state_count"] > 0


@pytest.mark.parametrize(
    ("profile", "mapped", "total"),
    [("monitor", 3, 4), ("ventilator", 3, 4), ("heterogeneous", 1, 3)],
)
def test_profile_mapping_coverage_is_explicit(profile: str, mapped: int, total: int) -> None:
    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.mdib import ProviderMdib

    mdib = ProviderMdib.from_mdib_file(str(profile_mdib_path(profile)), SdcV1Definitions)
    _initialize_metric_values(mdib, profile)
    snapshot = MdibSnapshotExtractor().extract(mdib, provider_epr=f"urn:uuid:test-{profile}")
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    registry = ResourceRegistry(devices=[snapshot], mapping=mapping)
    metrics = registry.mapper.map_device_metrics(snapshot)

    assert len(metrics) == total
    assert sum(metric.mapped for metric in metrics) == mapped
    assert len(registry.list_resource_uris()) == 8


def test_protocol_testbed_rejects_unknown_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unknown profiles"):
        run_protocol_testbed(
            ProtocolTestbedConfig(
                mapping_path=Path("config/sdc_mie.yaml"),
                output_path=tmp_path / "report.json",
                profiles=("not-a-profile",),
                repetitions=1,
            )
        )
