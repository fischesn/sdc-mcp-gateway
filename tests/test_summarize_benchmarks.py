from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.experiments.summarize import BenchmarkSummaryConfig, summarize_benchmarks
from sdc_mcp_gateway.main import app


def _summary(run_id: str, median_total: float, p95_total: float) -> dict:
    return {
        "status": "ok",
        "run_id": run_id,
        "adapter": "simulated",
        "mapping_version": "0.6-example",
        "iterations": 100,
        "warmup": 10,
        "device_count": 2,
        "resource_count": 12,
        "metrics_count": 6,
        "alarms_count": 3,
        "active_alarm_count_last": 0,
        "active_alarm_count_max": 1,
        "active_alarm_seen_any": True,
        "read_error_count_total": 0,
        "latency": {
            "snapshot_build": {"min_ms": 1.0, "median_ms": 2.0, "mean_ms": 2.5, "p95_ms": 4.0, "max_ms": 5.0},
            "list_resources": {"min_ms": 0.01, "median_ms": 0.02, "mean_ms": 0.03, "p95_ms": 0.04, "max_ms": 0.05},
            "read_resources": {"min_ms": 3.0, "median_ms": 4.0, "mean_ms": 4.5, "p95_ms": 6.0, "max_ms": 7.0},
            "read_health": {"min_ms": 0.1, "median_ms": 0.2, "mean_ms": 0.3, "p95_ms": 0.4, "max_ms": 0.5},
            "total": {"min_ms": 10.0, "median_ms": median_total, "mean_ms": median_total + 1.0, "p95_ms": p95_total, "max_ms": p95_total + 5.0},
        },
        "safety_boundary": {
            "all_read_only": True,
            "tools_exported_any": False,
            "write_operations_allowed_any": False,
        },
    }


def test_summarize_benchmarks_writes_aggregate_outputs(tmp_path: Path) -> None:
    input_dir = tmp_path / "runs"
    input_dir.mkdir()
    (input_dir / "run1.summary.json").write_text(json.dumps(_summary("run1", 20.0, 30.0)), encoding="utf-8")
    (input_dir / "run2.summary.json").write_text(json.dumps(_summary("run2", 30.0, 40.0)), encoding="utf-8")

    report = summarize_benchmarks(BenchmarkSummaryConfig(input_dir=input_dir, label="test-summary"))

    assert report["status"] == "ok"
    assert report["run_count"] == 2
    assert report["read_error_count_total"] == 0
    assert report["safety_boundary_ok"] is True
    assert report["latency_aggregate"]["total"]["median_ms"]["mean"] == 25.0
    assert report["active_alarm_count_max_values"] == [1]
    assert report["active_alarm_seen_any"] is True
    assert Path(report["output_json"]).exists()
    assert Path(report["output_csv"]).exists()


def test_summarize_benchmarks_cli(tmp_path: Path) -> None:
    input_dir = tmp_path / "runs"
    input_dir.mkdir()
    (input_dir / "run1.summary.json").write_text(json.dumps(_summary("run1", 20.0, 30.0)), encoding="utf-8")

    result = CliRunner().invoke(app, ["summarize-benchmarks", "--input-dir", str(input_dir), "--label", "cli-summary"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["run_count"] == 1
