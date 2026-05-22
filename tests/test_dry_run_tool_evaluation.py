from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.main import app, _make_tool_registry
from sdc_mcp_gateway.tools.evaluate import DryRunToolEvaluationConfig, run_dry_run_tool_evaluation

runner = CliRunner()

CONFIG = Path("config/gateway.simulated.dryrun.example.yaml")
ACK_CONFIG = Path("config/gateway.simulated.dryrun.high-airway-pressure.example.yaml")
MIE = Path("config/sdc_mie.yaml")
POLICY = Path("config/tool_policies.yaml")


def test_dry_run_tool_evaluation_report(tmp_path: Path) -> None:
    primary = _make_tool_registry(CONFIG, MIE, POLICY)
    ack = _make_tool_registry(ACK_CONFIG, MIE, POLICY)
    report = run_dry_run_tool_evaluation(
        DryRunToolEvaluationConfig(
            config_path=CONFIG,
            ack_config_path=ACK_CONFIG,
            mie_path=MIE,
            tool_policy_path=POLICY,
            output_dir=tmp_path,
            run_label="test-dryrun",
        ),
        primary_registry=primary,
        ack_registry=ack,
    )
    assert report["status"] == "ok"
    assert report["case_count"] == 7
    assert report["passed_cases"] == 7
    assert report["failed_cases"] == 0
    assert report["executed_true_count"] == 0
    assert report["write_allowed_true_count"] == 0
    assert report["safety_boundary_ok"] is True
    assert Path(report["output_json"]).exists()
    assert Path(report["output_csv"]).exists()
    assert Path(report["output_markdown"]).exists()


def test_cli_evaluate_dry_run_tools(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "evaluate-dry-run-tools",
            "--config",
            str(CONFIG),
            "--ack-config",
            str(ACK_CONFIG),
            "--mie",
            str(MIE),
            "--tool-policy",
            str(POLICY),
            "--output-dir",
            str(tmp_path),
            "--label",
            "cli-dryrun",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"passed_cases": 7' in result.output
    assert '"executed_true_count": 0' in result.output
