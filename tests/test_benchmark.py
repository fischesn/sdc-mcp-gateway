from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.experiments.benchmark import BenchmarkConfig, run_benchmark
from sdc_mcp_gateway.main import app


def test_run_benchmark_writes_outputs(tmp_path: Path) -> None:
    report = run_benchmark(
        BenchmarkConfig(
            config_path=Path("config/gateway.simulated.example.yaml"),
            mie_path=Path("config/sdc_mie.yaml"),
            output_dir=tmp_path,
            run_label="pytest",
            iterations=2,
            warmup=1,
            elapsed_start_s=0.0,
            elapsed_step_s=1.0,
        )
    )

    assert report["status"] == "ok"
    assert report["iterations"] == 2
    assert report["warmup"] == 1
    assert report["resource_count"] == 12
    assert report["safety_boundary"]["all_read_only"] is True
    assert report["safety_boundary"]["tools_exported_any"] is False
    assert Path(str(report["output_jsonl"])).exists()
    assert Path(str(report["output_csv"])).exists()
    assert Path(str(report["output_summary"])).exists()


def test_benchmark_cli(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "benchmark",
            "--config",
            "config/gateway.simulated.example.yaml",
            "--mie",
            "config/sdc_mie.yaml",
            "--iterations",
            "1",
            "--warmup",
            "0",
            "--output-dir",
            str(tmp_path),
            "--label",
            "cli-pytest",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"resource_count": 12' in result.output
