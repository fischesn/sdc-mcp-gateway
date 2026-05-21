from __future__ import annotations

import csv
import json
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.models import utc_now_iso


LATENCY_KEYS = ["snapshot_build", "list_resources", "read_resources", "read_health", "total"]
LATENCY_FIELDS = ["min_ms", "median_ms", "mean_ms", "p95_ms", "max_ms"]


@dataclass(frozen=True)
class BenchmarkSummaryConfig:
    input_dir: Path = Path("data/experiment_runs")
    output_dir: Path | None = None
    label: str = "benchmark-summary"
    pattern: str = "*.summary.json"


def _now_compact() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_").replace("Z", "Z")


def _load_summary(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Summary file does not contain a JSON object: {path}")
    return data


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 3)


def _mean(values: list[float]) -> float | None:
    return _round(statistics.mean(values)) if values else None


def _median(values: list[float]) -> float | None:
    return _round(statistics.median(values)) if values else None


def _min(values: list[float]) -> float | None:
    return _round(min(values)) if values else None


def _max(values: list[float]) -> float | None:
    return _round(max(values)) if values else None


def _extract_latency(summary: dict[str, Any], key: str, field: str) -> float | None:
    latency = summary.get("latency", {})
    if not isinstance(latency, dict):
        return None
    block = latency.get(key, {})
    if not isinstance(block, dict):
        return None
    value = block.get(field)
    if isinstance(value, int | float):
        return float(value)
    return None


def _row_for_summary(path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    safety = summary.get("safety_boundary", {}) if isinstance(summary.get("safety_boundary"), dict) else {}
    row: dict[str, Any] = {
        "file": path.name,
        "run_id": summary.get("run_id"),
        "status": summary.get("status"),
        "adapter": summary.get("adapter"),
        "mapping_version": summary.get("mapping_version"),
        "iterations": summary.get("iterations"),
        "warmup": summary.get("warmup"),
        "device_count": summary.get("device_count"),
        "resource_count": summary.get("resource_count"),
        "metrics_count": summary.get("metrics_count"),
        "alarms_count": summary.get("alarms_count"),
        "active_alarm_count_last": summary.get("active_alarm_count_last"),
        "read_error_count_total": summary.get("read_error_count_total"),
        "all_read_only": safety.get("all_read_only"),
        "tools_exported_any": safety.get("tools_exported_any"),
        "write_operations_allowed_any": safety.get("write_operations_allowed_any"),
    }
    for key in LATENCY_KEYS:
        for field in LATENCY_FIELDS:
            row[f"{key}_{field}"] = _extract_latency(summary, key, field)
    return row


def summarize_benchmarks(config: BenchmarkSummaryConfig) -> dict[str, Any]:
    input_dir = config.input_dir
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    paths = sorted(input_dir.glob(config.pattern))
    if not paths:
        raise FileNotFoundError(f"No benchmark summary files found in {input_dir} matching {config.pattern}")

    loaded: list[tuple[Path, dict[str, Any]]] = [(path, _load_summary(path)) for path in paths]
    rows = [_row_for_summary(path, summary) for path, summary in loaded]
    summaries = [summary for _, summary in loaded]

    statuses = [str(summary.get("status")) for summary in summaries]
    failed_runs = [str(summary.get("run_id") or path.name) for path, summary in loaded if summary.get("status") != "ok"]
    read_error_count_total = sum(int(summary.get("read_error_count_total") or 0) for summary in summaries)

    safety_ok = all(
        isinstance(summary.get("safety_boundary"), dict)
        and summary["safety_boundary"].get("all_read_only") is True
        and summary["safety_boundary"].get("tools_exported_any") is False
        and summary["safety_boundary"].get("write_operations_allowed_any") is False
        for summary in summaries
    )

    latency_aggregate: dict[str, dict[str, Any]] = {}
    for key in LATENCY_KEYS:
        latency_aggregate[key] = {}
        for field in LATENCY_FIELDS:
            values = [value for summary in summaries if (value := _extract_latency(summary, key, field)) is not None]
            latency_aggregate[key][field] = {
                "runs": len(values),
                "min": _min(values),
                "median": _median(values),
                "mean": _mean(values),
                "max": _max(values),
                "values": [_round(value) for value in values],
            }

    run_count = len(summaries)
    output_dir = config.output_dir or input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    aggregate_id = f"{config.label}-{_now_compact()}"
    json_path = output_dir / f"{aggregate_id}.aggregate.json"
    csv_path = output_dir / f"{aggregate_id}.aggregate.csv"

    aggregate = {
        "status": "ok" if not failed_runs and read_error_count_total == 0 and safety_ok else "warning",
        "aggregate_id": aggregate_id,
        "input_dir": str(input_dir),
        "pattern": config.pattern,
        "run_count": run_count,
        "runs": [str(summary.get("run_id") or path.name) for path, summary in loaded],
        "statuses": statuses,
        "failed_runs": failed_runs,
        "adapter_values": sorted({str(summary.get("adapter")) for summary in summaries}),
        "mapping_versions": sorted({str(summary.get("mapping_version")) for summary in summaries}),
        "iterations_values": sorted({int(summary.get("iterations") or 0) for summary in summaries}),
        "warmup_values": sorted({int(summary.get("warmup") or 0) for summary in summaries}),
        "device_count_values": sorted({int(summary.get("device_count") or 0) for summary in summaries}),
        "resource_count_values": sorted({int(summary.get("resource_count") or 0) for summary in summaries}),
        "metrics_count_values": sorted({int(summary.get("metrics_count") or 0) for summary in summaries}),
        "alarms_count_values": sorted({int(summary.get("alarms_count") or 0) for summary in summaries}),
        "read_error_count_total": read_error_count_total,
        "safety_boundary_ok": safety_ok,
        "latency_aggregate": latency_aggregate,
        "rows": rows,
        "output_json": str(json_path),
        "output_csv": str(csv_path),
    }

    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(aggregate, handle, ensure_ascii=False, indent=2, sort_keys=True)

    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    return aggregate
