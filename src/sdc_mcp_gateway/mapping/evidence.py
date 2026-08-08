from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.mapping.mapper import SdcMieMapper
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.models import MappingState
from sdc_mcp_gateway.sdc.extractor import MdibSnapshotExtractor
from sdc_mcp_gateway.sdc.reference_provider import (
    PROFILE_VALUES,
    _initialize_metric_values,
    profile_mdib_path,
)

MAPPING_STATES: tuple[MappingState, ...] = (
    "mapped",
    "unmapped",
    "unsupported",
    "conflicting",
)


def _class_state_counts(snapshot: Any, mapped_metrics: list[Any], kind: str) -> dict[str, Any]:
    raw_key = "descriptor_types" if kind == "descriptor" else "state_types"
    unsupported_key = (
        "unsupported_descriptor_types" if kind == "descriptor" else "unsupported_state_types"
    )
    totals: dict[str, int] = snapshot.raw_mdib[raw_key]
    unsupported: dict[str, int] = snapshot.raw_mdib[unsupported_key]
    counts: dict[str, Counter[str]] = defaultdict(Counter)

    metric_class_totals: Counter[str] = Counter()
    for metric, mapped in zip(snapshot.metrics, mapped_metrics, strict=True):
        class_name = metric.raw.get(f"{kind}_type")
        if class_name:
            counts[str(class_name)][mapped.mapping_state] += 1
            metric_class_totals[str(class_name)] += 1

    for class_name, total in totals.items():
        remaining = total - metric_class_totals[class_name]
        if remaining <= 0:
            continue
        state = "unsupported" if class_name in unsupported else "mapped"
        counts[class_name][state] += remaining

    return {
        class_name: {
            "total": totals[class_name],
            "states": {state: counts[class_name].get(state, 0) for state in MAPPING_STATES},
        }
        for class_name in sorted(totals)
    }


def run_mapping_evidence(
    mapping_path: str | Path,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Validate SDC-MIE and measure mapping coverage on all software profiles."""

    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.mdib import ProviderMdib

    mapping = load_mapping(mapping_path)
    mapper = SdcMieMapper(mapping)
    profiles: list[dict[str, Any]] = []
    aggregate_metric_states: Counter[MappingState] = Counter()

    for profile in sorted(PROFILE_VALUES):
        mdib = ProviderMdib.from_mdib_file(str(profile_mdib_path(profile)), SdcV1Definitions)
        _initialize_metric_values(mdib, profile)
        snapshot = MdibSnapshotExtractor().extract(
            mdib,
            provider_epr=f"urn:uuid:anonymous-{profile}",
            display_name=f"Anonymous {profile} profile",
        )
        metrics = mapper.map_device_metrics(snapshot)
        metric_states = Counter(metric.mapping_state for metric in metrics)
        aggregate_metric_states.update(metric_states)
        profiles.append(
            {
                "profile": profile,
                "metric_elements": {
                    "total": len(metrics),
                    "states": {state: metric_states.get(state, 0) for state in MAPPING_STATES},
                    "coverage": metric_states.get("mapped", 0) / len(metrics) if metrics else 0.0,
                    "unresolved": [
                        {
                            "handle": metric.handle,
                            "code": metric.code,
                            "state": metric.mapping_state,
                            "reason": metric.mapping_reason,
                        }
                        for metric in metrics
                        if metric.mapping_state != "mapped"
                    ],
                },
                "descriptor_classes": _class_state_counts(snapshot, metrics, "descriptor"),
                "state_classes": _class_state_counts(snapshot, metrics, "state"),
            }
        )

    total_metrics = sum(aggregate_metric_states.values())
    report = {
        "schema_version": "wp5-mapping-evidence-1",
        "status": "ok",
        "mapping": {
            "schema_version": mapping.schema_version,
            "schema_id": mapping.schema_id,
            "version": mapping.version,
            "source_sha256": mapping.source_sha256,
            "provenance": mapping.provenance.model_dump(),
            "entry_count": len(mapping.mappings),
            "json_schema_valid": True,
            "semantic_validation_valid": True,
        },
        "aggregate_metric_elements": {
            "total": total_metrics,
            "states": {
                state: aggregate_metric_states.get(state, 0) for state in MAPPING_STATES
            },
            "coverage": aggregate_metric_states.get("mapped", 0) / total_metrics
            if total_metrics
            else 0.0,
        },
        "profiles": profiles,
        "claim_boundary": (
            "SDC-MIE is a versioned research artifact. It is not an IEEE 11073 standard, "
            "is not file-format compatible with TogoMCP, and does not establish clinical semantics."
        ),
    }
    if output_path is not None:
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report
