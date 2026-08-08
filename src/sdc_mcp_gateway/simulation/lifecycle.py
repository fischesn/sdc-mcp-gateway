from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.models import (
    AlarmState,
    ContextState,
    DeviceSnapshot,
    FreshnessState,
    MetricState,
)
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _timestamp(seconds: float) -> str:
    return (_EPOCH + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


class AlarmAction(BaseModel):
    action: Literal[
        "activate", "clear", "escalate", "latch", "acknowledge", "suppress", "reactivate"
    ]
    handle: str
    priority: str = "medium"


class LifecycleStep(BaseModel):
    kind: Literal["update", "tick", "disconnect", "unavailable", "proposal"]
    at_s: float
    source_s: float | None = None
    mdib_version: int | None = None
    update_sequence: int | None = None
    metric_present: bool = True
    metric_validity: str = "valid"
    metric_value: float = 40.0
    alarm_actions: list[AlarmAction] = Field(default_factory=list)
    snapshot_version: int | Literal["current", "previous"] | None = None


class LifecycleExpectation(BaseModel):
    final_freshness: Literal["fresh", "stale", "invalid", "unavailable", "recovered"]
    final_provider_status: Literal["connected", "disconnected", "unavailable"] = "connected"
    dispositions: list[str]
    proposal_reasons: list[str]
    recovery_observed: bool = False
    alarm_states: dict[str, str] = Field(default_factory=dict)


class LifecycleCase(BaseModel):
    name: str
    description: str
    steps: list[LifecycleStep]
    expected: LifecycleExpectation


class LifecycleSuite(BaseModel):
    version: str
    stale_after_s: float = 5.0
    cases: list[LifecycleCase]

    @classmethod
    def from_file(cls, path: str | Path) -> LifecycleSuite:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected a YAML mapping at {path}")
        suite = cls.model_validate(data)
        names = [case.name for case in suite.cases]
        if len(names) != len(set(names)):
            raise ValueError("WP4 lifecycle case names must be unique")
        return suite


class FreshnessAwareStateCache:
    """Deterministic point-in-time cache for ordered simulated provider updates.

    It intentionally models delivery and cache semantics, not a production SDC
    subscription transport. Duplicate and out-of-order updates are retained as
    evidence dispositions but never replace the latest accepted snapshot.
    """

    def __init__(self, stale_after_s: float) -> None:
        self.stale_after_s = stale_after_s
        self.snapshot: DeviceSnapshot | None = None
        self.dispositions: list[str] = []
        self.freshness_history: list[str] = []

    def apply_update(self, step: LifecycleStep) -> str:
        if step.mdib_version is None or step.update_sequence is None:
            raise ValueError("Update steps require mdib_version and update_sequence")
        source_s = step.at_s if step.source_s is None else step.source_s
        if self.snapshot is not None:
            if (
                step.mdib_version == self.snapshot.mdib_version
                and step.update_sequence == self.snapshot.update_sequence
            ):
                self.advance(step.at_s)
                self.dispositions.append("duplicate_ignored")
                return "duplicate_ignored"
            if (
                step.mdib_version < self.snapshot.mdib_version
                or step.update_sequence < self.snapshot.update_sequence
            ):
                self.advance(step.at_s)
                self.dispositions.append("out_of_order_ignored")
                return "out_of_order_ignored"

        previous_freshness = self.snapshot.freshness if self.snapshot else None
        alarms = self._updated_alarms(step.alarm_actions, source_s)
        age_ms = max(0.0, (step.at_s - source_s) * 1000.0)
        if not step.metric_present:
            freshness: FreshnessState = "invalid"
            reason = "required_metric_missing"
        elif step.metric_validity.lower() != "valid":
            freshness = "invalid"
            reason = f"metric_validity_{step.metric_validity.lower()}"
        elif age_ms > self.stale_after_s * 1000.0:
            freshness = "stale"
            reason = "age_threshold_exceeded"
        elif previous_freshness in {"stale", "invalid", "unavailable"}:
            freshness = "recovered"
            reason = "newer_valid_update_after_fault"
        else:
            freshness = "fresh"
            reason = "current_valid_state"

        source_timestamp = _timestamp(source_s)
        gateway_timestamp = _timestamp(step.at_s)
        metric_freshness = freshness
        metrics = []
        if step.metric_present:
            metrics.append(
                MetricState(
                    handle="metric.fio2",
                    code="151688",
                    value=step.metric_value,
                    unit="%",
                    timestamp=source_timestamp,
                    validity=step.metric_validity,
                    freshness=metric_freshness,
                    raw={"source": "wp4-deterministic-lifecycle"},
                )
            )
        self.snapshot = DeviceSnapshot(
            device_id="wp4-ventilator",
            display_name="WP4 Simulated Ventilator",
            manufacturer="Anonymous Research Prototype",
            model="Deterministic Lifecycle Simulator",
            metrics=metrics,
            alarms=alarms,
            context=ContextState(location_ref="simulation-lab"),
            raw_mdib={"kind": "simulated-ordered-update", "streaming_claim": False},
            observed_at=gateway_timestamp,
            source_timestamp=source_timestamp,
            gateway_received_at=gateway_timestamp,
            age_of_information_ms=age_ms,
            provider_status="connected",
            sequence_id="wp4-sequence",
            mdib_version=step.mdib_version,
            update_sequence=step.update_sequence,
            freshness=freshness,
            freshness_reason=reason,
        )
        disposition = "accepted_recovery" if freshness == "recovered" else "accepted_update"
        self.dispositions.append(disposition)
        self.freshness_history.append(freshness)
        return disposition

    def advance(self, at_s: float) -> None:
        if self.snapshot is None:
            return
        source = datetime.fromisoformat(self.snapshot.source_timestamp.replace("Z", "+00:00"))
        now = _EPOCH + timedelta(seconds=at_s)
        age_ms = max(0.0, (now - source).total_seconds() * 1000.0)
        update: dict[str, Any] = {
            "gateway_received_at": _timestamp(at_s),
            "observed_at": _timestamp(at_s),
            "age_of_information_ms": age_ms,
        }
        if (
            age_ms > self.stale_after_s * 1000.0
            and self.snapshot.freshness in {"fresh", "recovered"}
        ):
            update.update(freshness="stale", freshness_reason="age_threshold_exceeded")
            update["metrics"] = [
                metric.model_copy(update={"freshness": "stale"}) for metric in self.snapshot.metrics
            ]
        self.snapshot = self.snapshot.model_copy(update=update)
        self.freshness_history.append(self.snapshot.freshness)

    def mark_unavailable(self, at_s: float, status: Literal["disconnected", "unavailable"]) -> None:
        if self.snapshot is None:
            raise ValueError("An initial update is required before a provider fault")
        self.advance(at_s)
        self.snapshot = self.snapshot.model_copy(
            update={
                "provider_status": status,
                "freshness": "unavailable",
                "freshness_reason": f"provider_{status}",
                "metrics": [
                    metric.model_copy(update={"freshness": "unavailable"})
                    for metric in self.snapshot.metrics
                ],
            }
        )
        self.dispositions.append(f"provider_{status}")
        self.freshness_history.append("unavailable")

    def _updated_alarms(self, actions: list[AlarmAction], source_s: float) -> list[AlarmState]:
        by_handle = {
            alarm.handle: alarm.model_copy(deep=True)
            for alarm in (self.snapshot.alarms if self.snapshot else [])
        }
        for action in actions:
            alarm = by_handle.get(
                action.handle,
                AlarmState(
                    handle=action.handle,
                    code="alarm-simulated",
                    priority=action.priority,
                    kind="physiological",
                    timestamp=_timestamp(source_s),
                ),
            )
            sequence = alarm.transition_sequence + 1
            common = {"timestamp": _timestamp(source_s), "transition_sequence": sequence}
            if action.action == "activate":
                alarm = alarm.model_copy(
                    update={
                        **common,
                        "presence": True,
                        "priority": action.priority,
                        "lifecycle_state": "active",
                        "acknowledged": False,
                        "suppressed": False,
                    }
                )
            elif action.action == "clear":
                alarm = alarm.model_copy(
                    update={
                        **common,
                        "presence": alarm.latched and not alarm.acknowledged,
                        "lifecycle_state": "latched"
                        if alarm.latched and not alarm.acknowledged
                        else "inactive",
                    }
                )
            elif action.action == "escalate":
                alarm = alarm.model_copy(
                    update={**common, "presence": True, "priority": action.priority, "lifecycle_state": "active"}
                )
            elif action.action == "latch":
                alarm = alarm.model_copy(
                    update={**common, "presence": True, "latched": True, "lifecycle_state": "latched"}
                )
            elif action.action == "acknowledge":
                alarm = alarm.model_copy(
                    update={**common, "acknowledged": True, "lifecycle_state": "acknowledged"}
                )
            elif action.action == "suppress":
                alarm = alarm.model_copy(
                    update={**common, "presence": False, "suppressed": True, "lifecycle_state": "suppressed"}
                )
            elif action.action == "reactivate":
                alarm = alarm.model_copy(
                    update={
                        **common,
                        "presence": True,
                        "suppressed": False,
                        "acknowledged": False,
                        "lifecycle_state": "active",
                    }
                )
            by_handle[action.handle] = alarm
        return [by_handle[handle] for handle in sorted(by_handle)]


def run_lifecycle_evaluation(
    suite_path: str | Path,
    mapping_path: str | Path,
    policy_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    suite = LifecycleSuite.from_file(suite_path)
    mapping = load_mapping(mapping_path)
    policies = load_tool_policies(policy_path)
    case_reports: list[dict[str, Any]] = []

    for case in suite.cases:
        cache = FreshnessAwareStateCache(suite.stale_after_s)
        proposal_reasons: list[str] = []
        proposal_statuses: list[str] = []
        exposed_states: list[dict[str, Any]] = []
        for step in case.steps:
            if step.kind == "update":
                cache.apply_update(step)
            elif step.kind == "tick":
                cache.advance(step.at_s)
                cache.dispositions.append("clock_advanced")
            elif step.kind in {"disconnect", "unavailable"}:
                status: Literal["disconnected", "unavailable"] = (
                    "disconnected" if step.kind == "disconnect" else "unavailable"
                )
                cache.mark_unavailable(step.at_s, status)
            elif step.kind == "proposal":
                if cache.snapshot is None:
                    raise ValueError(f"Case {case.name}: proposal before first snapshot")
                resources = ResourceRegistry(devices=[cache.snapshot], mapping=mapping)
                tools = DryRunToolRegistry(resources, policies, tools_enabled=True)
                arguments: dict[str, Any] = {
                    "device_id": cache.snapshot.device_id,
                    "value": 45.0,
                }
                if step.snapshot_version == "current":
                    arguments["snapshot_version"] = cache.snapshot.mdib_version
                elif step.snapshot_version == "previous":
                    arguments["snapshot_version"] = max(0, cache.snapshot.mdib_version - 1)
                elif isinstance(step.snapshot_version, int):
                    arguments["snapshot_version"] = step.snapshot_version
                result = tools.call_tool("prepare_set_fio2", arguments)
                proposal_reasons.append(result.reason or "none")
                proposal_statuses.append(result.status)
                exposed_states.append(resources.read("sdc://devices").data[0])

        if cache.snapshot is None:
            raise ValueError(f"Case {case.name}: no snapshot was produced")
        alarm_states = {
            alarm.handle: alarm.lifecycle_state for alarm in cache.snapshot.alarms
        }
        actual = {
            "final_freshness": cache.snapshot.freshness,
            "final_provider_status": cache.snapshot.provider_status,
            "dispositions": cache.dispositions,
            "proposal_reasons": proposal_reasons,
            "recovery_observed": "recovered" in cache.freshness_history,
            "alarm_states": alarm_states,
        }
        expected = case.expected.model_dump()
        checks = {key: actual[key] == expected[key] for key in expected}
        case_reports.append(
            {
                "name": case.name,
                "description": case.description,
                "status": "passed" if all(checks.values()) else "failed",
                "checks": checks,
                "expected": expected,
                "actual": actual,
                "proposal_statuses": proposal_statuses,
                "last_exposed_state": exposed_states[-1] if exposed_states else None,
            }
        )

    passed = sum(report["status"] == "passed" for report in case_reports)
    report = {
        "schema_version": "wp4-lifecycle-evidence-1",
        "suite_version": suite.version,
        "status": "ok" if passed == len(case_reports) else "failed",
        "scope": {
            "provider": "deterministic in-process SDC-like simulator",
            "ordered_updates": True,
            "production_subscription_transport": False,
            "physical_device": False,
        },
        "mapping_artifact": {
            "schema_version": mapping.schema_version,
            "version": mapping.version,
            "source_sha256": mapping.source_sha256,
            "provenance": mapping.provenance.model_dump(),
        },
        "stale_after_s": suite.stale_after_s,
        "case_count": len(case_reports),
        "passed_cases": passed,
        "failed_cases": len(case_reports) - passed,
        "cases": case_reports,
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report
