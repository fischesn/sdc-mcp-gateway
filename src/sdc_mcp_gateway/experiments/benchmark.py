from __future__ import annotations

import csv
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.models import MappingDocument, utc_now_iso
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import (
    DummySdcConsumer,
    Sdc11073Consumer,
    SdcConsumer,
    SimulatedSdcConsumer,
)


@dataclass(frozen=True)
class BenchmarkConfig:
    config_path: Path
    mie_path: Path
    output_dir: Path = Path("data/experiment_runs")
    run_label: str = "benchmark"
    iterations: int = 10
    warmup: int = 1
    elapsed_start_s: float = 0.0
    elapsed_step_s: float = 1.0
    read_all_resources: bool = True


def _make_consumer(config: GatewayConfig, recorder: JsonlRecorder | None = None) -> SdcConsumer:
    if config.sdc.adapter == "dummy":
        return DummySdcConsumer()
    if config.sdc.adapter == "simulated":
        if not config.sdc.simulation_config:
            raise ValueError("sdc.simulation_config must be set when adapter is simulated")
        return SimulatedSdcConsumer(
            scenario_path=config.sdc.simulation_config,
            elapsed_s=config.sdc.simulation_elapsed_s,
            recorder=recorder,
        )
    if config.sdc.adapter == "sdc11073":
        return Sdc11073Consumer(
            discovery_timeout_s=config.sdc.discovery_timeout_s,
            provider_whitelist=config.sdc.provider_whitelist,
            local_ip=config.sdc.local_ip,
            max_devices=config.sdc.max_devices,
            recorder=recorder,
        )
    raise ValueError(f"Unsupported SDC adapter: {config.sdc.adapter}")


def _make_registry(config: GatewayConfig, mapping: MappingDocument, recorder: JsonlRecorder | None) -> ResourceRegistry:
    consumer = _make_consumer(config, recorder=recorder)
    devices = consumer.get_snapshots()
    return ResourceRegistry(devices=devices, mapping=mapping, recorder=recorder)


def _summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "min_ms": None, "median_ms": None, "mean_ms": None, "max_ms": None}
    ordered = sorted(values)
    p95 = ordered[min(len(ordered) - 1, max(0, int(round(0.95 * (len(ordered) - 1)))))]
    return {
        "count": len(values),
        "min_ms": round(min(values), 3),
        "median_ms": round(statistics.median(values), 3),
        "mean_ms": round(statistics.mean(values), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(max(values), 3),
    }


def _now_compact() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").replace(".", "_").replace("Z", "Z")


def run_benchmark(config: BenchmarkConfig) -> dict[str, Any]:
    if config.iterations <= 0:
        raise ValueError("iterations must be > 0")
    if config.warmup < 0:
        raise ValueError("warmup must be >= 0")

    gateway_config = GatewayConfig.from_file(config.config_path)
    mapping = load_mapping(config.mie_path)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    run_id = f"{config.run_label}-{_now_compact()}"
    jsonl_path = config.output_dir / f"{run_id}.jsonl"
    csv_path = config.output_dir / f"{run_id}.csv"
    summary_path = config.output_dir / f"{run_id}.summary.json"

    rows: list[dict[str, Any]] = []
    jsonl_records: list[dict[str, Any]] = []
    total_runs = config.warmup + config.iterations

    for run_index in range(total_runs):
        is_warmup = run_index < config.warmup
        iteration = run_index - config.warmup if not is_warmup else -1 * (config.warmup - run_index)
        elapsed_s = config.elapsed_start_s + (run_index * config.elapsed_step_s)

        effective_config = gateway_config.model_copy(deep=True)
        if effective_config.sdc.adapter == "simulated":
            effective_config.sdc.simulation_elapsed_s = elapsed_s

        recorder = JsonlRecorder(effective_config.gateway.log_file)

        t0 = time.perf_counter()
        registry = _make_registry(effective_config, mapping, recorder=recorder)
        t1 = time.perf_counter()

        descriptors = registry.list_resource_descriptors()
        resource_uris = [descriptor.uri for descriptor in descriptors]
        t2 = time.perf_counter()

        read_errors: list[dict[str, str]] = []
        resources_read = 0
        metrics_count = 0
        alarms_count = 0
        active_alarms_count = 0
        mapped_metric_count = 0
        unmapped_metric_count = 0

        if config.read_all_resources:
            for uri in resource_uris:
                try:
                    payload = registry.read(uri).model_dump()
                    resources_read += 1
                    data = payload.get("data")
                    if uri.endswith("/metrics") and isinstance(data, list):
                        metrics_count += len(data)
                        mapped_metric_count += sum(1 for metric in data if metric.get("mapped") is True)
                        unmapped_metric_count += sum(1 for metric in data if metric.get("mapped") is not True)
                    if uri.endswith("/alarms") and isinstance(data, list):
                        alarms_count += len(data)
                        active_alarms_count += sum(1 for alarm in data if alarm.get("presence") is True)
                except Exception as exc:  # pragma: no cover - user-facing robustness
                    read_errors.append({"uri": uri, "error": str(exc)})
        t3 = time.perf_counter()

        health = registry.read("sdc://health").model_dump().get("data", {})
        t4 = time.perf_counter()

        row = {
            "run_id": run_id,
            "iteration": iteration,
            "warmup": is_warmup,
            "adapter": effective_config.sdc.adapter,
            "elapsed_s": elapsed_s,
            "device_count": len(registry.devices),
            "resource_count": len(resource_uris),
            "resources_read": resources_read,
            "read_error_count": len(read_errors),
            "metrics_count": metrics_count,
            "mapped_metric_count": mapped_metric_count,
            "unmapped_metric_count": unmapped_metric_count,
            "alarms_count": alarms_count,
            "active_alarms_count": active_alarms_count,
            "snapshot_build_ms": (t1 - t0) * 1000.0,
            "list_resources_ms": (t2 - t1) * 1000.0,
            "read_resources_ms": (t3 - t2) * 1000.0,
            "read_health_ms": (t4 - t3) * 1000.0,
            "total_ms": (t4 - t0) * 1000.0,
            "health_status": health.get("status"),
            "health_mode": health.get("mode"),
            "tools_exported": health.get("tools_exported"),
            "write_operations_allowed": health.get("write_operations_allowed"),
        }
        rows.append(row)
        jsonl_records.append({**row, "read_errors": read_errors, "timestamp": utc_now_iso()})

    measurement_rows = [row for row in rows if not row["warmup"]]
    failures = [row for row in measurement_rows if row["read_error_count"] != 0]
    summary = {
        "status": "ok" if not failures else "failed",
        "run_id": run_id,
        "config": str(config.config_path),
        "mie": str(config.mie_path),
        "adapter": gateway_config.sdc.adapter,
        "mapping_version": mapping.version,
        "iterations": config.iterations,
        "warmup": config.warmup,
        "elapsed_start_s": config.elapsed_start_s,
        "elapsed_step_s": config.elapsed_step_s,
        "output_jsonl": str(jsonl_path),
        "output_csv": str(csv_path),
        "output_summary": str(summary_path),
        "device_count": measurement_rows[-1]["device_count"] if measurement_rows else None,
        "resource_count": measurement_rows[-1]["resource_count"] if measurement_rows else None,
        "metrics_count": measurement_rows[-1]["metrics_count"] if measurement_rows else None,
        "alarms_count": measurement_rows[-1]["alarms_count"] if measurement_rows else None,
        "active_alarm_count_last": measurement_rows[-1]["active_alarms_count"] if measurement_rows else None,
        "read_error_count_total": sum(int(row["read_error_count"]) for row in measurement_rows),
        "latency": {
            "snapshot_build": _summary([float(row["snapshot_build_ms"]) for row in measurement_rows]),
            "list_resources": _summary([float(row["list_resources_ms"]) for row in measurement_rows]),
            "read_resources": _summary([float(row["read_resources_ms"]) for row in measurement_rows]),
            "read_health": _summary([float(row["read_health_ms"]) for row in measurement_rows]),
            "total": _summary([float(row["total_ms"]) for row in measurement_rows]),
        },
        "safety_boundary": {
            "all_read_only": all(row["health_mode"] == "read-only" for row in measurement_rows),
            "tools_exported_any": any(row["tools_exported"] is True for row in measurement_rows),
            "write_operations_allowed_any": any(
                row["write_operations_allowed"] is True for row in measurement_rows
            ),
        },
    }

    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in jsonl_records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    if rows:
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)

    return summary
