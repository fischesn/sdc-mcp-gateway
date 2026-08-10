from __future__ import annotations

from pathlib import Path

from sdc_mcp_gateway.revision.representation_ablation import (
    AblationConfig,
    _build_registry,
    build_ablation_lock,
    build_representation_context,
    context_stats,
    validate_ablation_plan,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/bhi2026_wp8_ablation.yaml"


def _metric_facts(context: dict, representation: str) -> set[tuple]:
    if representation == "raw_normalized_sdc":
        metrics = [
            (device["device_id"], metric)
            for device in context["normalized_sdc_snapshots"]
            for metric in device["metrics"]
        ]
    else:
        metrics = [
            (device_id, metric)
            for device_id, values in context["metrics_by_device"].items()
            for metric in values
        ]
    return {
        (device_id, metric.get("handle"), metric.get("code"), metric.get("value"), metric.get("unit"))
        for device_id, metric in metrics
    }


def test_context_variants_keep_source_facts_but_remove_enrichment() -> None:
    config = AblationConfig.from_file(CONFIG)
    scenario = next(item for item in config.scenarios if item.id == "holdout-multidevice-alarm")
    registry = _build_registry(config, scenario)
    raw = build_representation_context(registry, "raw_normalized_sdc")
    generic = build_representation_context(registry, "generic_mcp")
    enriched = build_representation_context(registry, "sdc_mie_enriched")

    assert _metric_facts(raw, "raw_normalized_sdc") == _metric_facts(generic, "generic_mcp")
    assert _metric_facts(generic, "generic_mcp") == _metric_facts(
        enriched, "sdc_mie_enriched"
    )
    assert "resources" not in raw
    assert all("semantic_name" not in metric for values in generic["metrics_by_device"].values() for metric in values)
    assert any(
        metric.get("semantic_name")
        for values in enriched["metrics_by_device"].values()
        for metric in values
    )
    assert {item["uri"] for item in generic["resources"]} == {
        item["uri"] for item in enriched["resources"]
    }


def test_context_complexity_is_deterministic_and_nonzero() -> None:
    config = AblationConfig.from_file(CONFIG)
    registry = _build_registry(config, config.scenarios[0])
    context = build_representation_context(registry, "generic_mcp")
    first = context_stats(context)
    second = context_stats(context)
    assert first == second
    assert first.utf8_bytes > 0
    assert first.scalar_fields > 0
    assert first.maximum_depth >= 2


def test_wp8_plan_has_matched_case_counts_and_anonymous_lock() -> None:
    plan = validate_ablation_plan(CONFIG)
    assert plan["scenario_count"] == 5
    assert plan["matched_task_count"] == 28
    assert plan["new_external_case_count"] == 168
    assert plan["reused_proposed_case_count"] == 84
    lock = build_ablation_lock(CONFIG)
    assert len(lock["input_set_sha256"]) == 64
    assert lock["execution_plan"]["reused_source"] == "frozen_wp7_reports"
