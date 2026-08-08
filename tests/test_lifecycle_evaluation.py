from pathlib import Path

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.simulation.lifecycle import (
    FreshnessAwareStateCache,
    LifecycleStep,
    run_lifecycle_evaluation,
)
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies


SUITE = Path("config/wp4_lifecycle_scenarios.yaml")
MAPPING = Path("config/sdc_mie.yaml")
POLICIES = Path("config/tool_policies.yaml")


def _update(
    *,
    at_s: float,
    source_s: float,
    mdib_version: int,
    update_sequence: int,
) -> LifecycleStep:
    return LifecycleStep(
        kind="update",
        at_s=at_s,
        source_s=source_s,
        mdib_version=mdib_version,
        update_sequence=update_sequence,
    )


def test_wp4_lifecycle_suite_passes_all_declared_cases(tmp_path: Path) -> None:
    output = tmp_path / "wp4.json"
    report = run_lifecycle_evaluation(SUITE, MAPPING, POLICIES, output)
    assert report["status"] == "ok"
    assert report["case_count"] == 14
    assert report["passed_cases"] == 14
    assert report["failed_cases"] == 0
    assert output.exists()


def test_duplicate_and_out_of_order_updates_do_not_replace_current_state() -> None:
    cache = FreshnessAwareStateCache(stale_after_s=5.0)
    cache.apply_update(_update(at_s=2, source_s=2, mdib_version=2, update_sequence=2))
    duplicate = LifecycleStep(
        kind="update",
        at_s=3,
        source_s=3,
        mdib_version=2,
        update_sequence=2,
        metric_value=98,
    )
    old = LifecycleStep(
        kind="update",
        at_s=4,
        source_s=4,
        mdib_version=1,
        update_sequence=1,
        metric_value=99,
    )
    assert cache.apply_update(duplicate) == "duplicate_ignored"
    assert cache.apply_update(old) == "out_of_order_ignored"
    assert cache.snapshot is not None
    assert cache.snapshot.mdib_version == 2
    assert cache.snapshot.metrics[0].value == 40.0


def test_device_resource_exposes_freshness_and_version_metadata() -> None:
    cache = FreshnessAwareStateCache(stale_after_s=5.0)
    cache.apply_update(_update(at_s=1, source_s=0, mdib_version=7, update_sequence=9))
    assert cache.snapshot is not None
    registry = ResourceRegistry([cache.snapshot], load_mapping(MAPPING))
    state = registry.read("sdc://devices").data[0]
    assert state["source_timestamp"] == "2026-01-01T00:00:00Z"
    assert state["gateway_received_at"] == "2026-01-01T00:00:01Z"
    assert state["age_of_information_ms"] == 1000.0
    assert state["freshness"] == "fresh"
    assert state["mdib_version"] == 7
    assert state["update_sequence"] == 9


def test_stale_and_obsolete_proposals_fail_closed() -> None:
    cache = FreshnessAwareStateCache(stale_after_s=5.0)
    cache.apply_update(_update(at_s=0, source_s=0, mdib_version=3, update_sequence=3))
    assert cache.snapshot is not None
    registry = ResourceRegistry([cache.snapshot], load_mapping(MAPPING))
    tools = DryRunToolRegistry(registry, load_tool_policies(POLICIES), tools_enabled=True)
    obsolete = tools.call_tool(
        "prepare_set_fio2",
        {"device_id": "wp4-ventilator", "value": 45, "snapshot_version": 2},
    )
    assert obsolete.status == "rejected"
    assert obsolete.reason == "obsolete_snapshot"

    cache.advance(6)
    assert cache.snapshot is not None
    stale_registry = ResourceRegistry([cache.snapshot], load_mapping(MAPPING))
    stale_tools = DryRunToolRegistry(
        stale_registry, load_tool_policies(POLICIES), tools_enabled=True
    )
    stale = stale_tools.call_tool(
        "prepare_set_fio2",
        {"device_id": "wp4-ventilator", "value": 45, "snapshot_version": 3},
    )
    assert stale.status == "rejected"
    assert stale.reason == "stale_snapshot"


def test_recovery_requires_a_newer_valid_update() -> None:
    cache = FreshnessAwareStateCache(stale_after_s=5.0)
    cache.apply_update(_update(at_s=0, source_s=0, mdib_version=1, update_sequence=1))
    cache.mark_unavailable(1, "disconnected")
    assert cache.snapshot is not None
    assert cache.snapshot.freshness == "unavailable"
    cache.apply_update(_update(at_s=2, source_s=2, mdib_version=2, update_sequence=2))
    recovered = cache.snapshot
    assert recovered is not None
    assert recovered.freshness == "recovered"
    assert recovered.provider_status == "connected"
