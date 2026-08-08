from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from sdc_mcp_gateway.mapping.mie_loader import MappingValidationError, load_mapping
from sdc_mcp_gateway.mapping.mapper import SdcMieMapper
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer


def test_load_mapping() -> None:
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    assert mapping.schema_version == "1.0"
    assert mapping.version == "1.0.0"
    assert "150456" in mapping.by_code()
    assert mapping.by_handle()["metric.hr"].code == "150456"
    assert mapping.source_sha256 is not None
    assert len(mapping.source_sha256) == 64


def test_map_dummy_metrics_has_mapped_and_unmapped_entries() -> None:
    mapping = load_mapping(Path("config/sdc_mie.yaml"))
    mapper = SdcMieMapper(mapping)
    device = DummySdcConsumer().get_snapshots()[0]
    metrics = mapper.map_device_metrics(device)
    assert any(metric.semantic_name == "heart_rate" for metric in metrics)
    assert any(metric.mapped is False for metric in metrics)
    assert {metric.mapping_state for metric in metrics} >= {"mapped", "unmapped"}


def _mapping_data() -> dict[str, object]:
    data = yaml.safe_load(Path("config/sdc_mie.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _write_mapping(tmp_path: Path, data: dict[str, object]) -> Path:
    path = tmp_path / "mapping.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def test_duplicate_codes_fail_closed(tmp_path: Path) -> None:
    data = _mapping_data()
    mappings = data["mappings"]
    assert isinstance(mappings, list)
    duplicate = deepcopy(mappings[0])
    assert isinstance(duplicate, dict)
    duplicate["handles"] = ["metric.duplicate"]
    mappings.append(duplicate)
    with pytest.raises(MappingValidationError, match="duplicate mapping codes"):
        load_mapping(_write_mapping(tmp_path, data))


def test_duplicate_handles_fail_closed(tmp_path: Path) -> None:
    data = _mapping_data()
    mappings = data["mappings"]
    assert isinstance(mappings, list)
    first = mappings[0]
    second = mappings[1]
    assert isinstance(first, dict) and isinstance(second, dict)
    second["handles"] = deepcopy(first["handles"])
    with pytest.raises(MappingValidationError, match="duplicate mapping handles"):
        load_mapping(_write_mapping(tmp_path, data))


def test_conflicting_units_for_same_semantic_name_fail_closed(tmp_path: Path) -> None:
    data = _mapping_data()
    mappings = data["mappings"]
    assert isinstance(mappings, list)
    conflicting = deepcopy(mappings[0])
    assert isinstance(conflicting, dict)
    conflicting.update(code="alias.hr", handles=["metric.hr.alias"], unit="bpm")
    mappings.append(conflicting)
    with pytest.raises(MappingValidationError, match="conflicting units"):
        load_mapping(_write_mapping(tmp_path, data))


def test_invalid_bounds_fail_closed(tmp_path: Path) -> None:
    data = _mapping_data()
    mappings = data["mappings"]
    assert isinstance(mappings, list) and isinstance(mappings[3], dict)
    mappings[3]["min_value"] = 101
    mappings[3]["max_value"] = 100
    with pytest.raises(MappingValidationError, match="min_value"):
        load_mapping(_write_mapping(tmp_path, data))


@pytest.mark.parametrize("mutation", ["missing_description", "unknown_field"])
def test_json_schema_rejects_incomplete_or_unknown_fields(tmp_path: Path, mutation: str) -> None:
    data = _mapping_data()
    mappings = data["mappings"]
    assert isinstance(mappings, list) and isinstance(mappings[0], dict)
    if mutation == "missing_description":
        mappings[0].pop("description")
    else:
        mappings[0]["vendor_extension"] = "not allowed"
    with pytest.raises(MappingValidationError, match="JSON Schema validation failed"):
        load_mapping(_write_mapping(tmp_path, data))


def test_unknown_schema_version_fails_closed(tmp_path: Path) -> None:
    data = _mapping_data()
    data["schema_version"] = "2.0"
    with pytest.raises(MappingValidationError, match="Unsupported SDC-MIE schema_version"):
        load_mapping(_write_mapping(tmp_path, data))


def test_observed_unit_conflict_is_explicit() -> None:
    mapper = SdcMieMapper(load_mapping("config/sdc_mie.yaml"))
    metric = mapper.map_metric(
        metric_handle="metric.hr",
        metric_code="150456",
        value=72,
        unit="bpm",
        timestamp="2026-01-01T00:00:00Z",
    )
    assert metric.mapped is False
    assert metric.mapping_state == "conflicting"
    assert "differs" in metric.mapping_reason


def test_unsupported_metric_state_is_explicit() -> None:
    mapper = SdcMieMapper(load_mapping("config/sdc_mie.yaml"))
    metric = mapper.map_metric(
        metric_handle="metric.vendor",
        metric_code="vendor.unknown",
        value="x",
        unit="1",
        timestamp="2026-01-01T00:00:00Z",
        unsupported=True,
    )
    assert metric.mapping_state == "unsupported"
