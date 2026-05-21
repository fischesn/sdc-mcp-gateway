import json
from pathlib import Path

from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, run_agent_evaluation
from sdc_mcp_gateway.agent_eval.summarize import AgentEvalSummaryConfig, summarize_agent_evaluations

ROOT = Path(__file__).resolve().parents[1]


def test_summarize_agent_evaluations_oracle_and_mock(tmp_path: Path) -> None:
    reports = []
    for scenario, config, agent in [
        ("baseline", ROOT / "config/gateway.simulated.example.yaml", "oracle"),
        ("tachycardia", ROOT / "config/gateway.simulated.tachycardia.example.yaml", "llm-mock"),
    ]:
        reports.append(
            run_agent_evaluation(
                AgentEvalConfig(
                    config_path=config,
                    mie_path=ROOT / "config/sdc_mie.yaml",
                    tasks_path=ROOT / "config/agent_eval.tasks.yaml",
                    scenario=scenario,
                    output_dir=tmp_path,
                    run_label="agent-eval-test",
                    agent=agent,
                    elapsed_s=100.0,
                )
            )
        )

    aggregate = summarize_agent_evaluations(
        AgentEvalSummaryConfig(input_dir=tmp_path, output_dir=tmp_path, label="agent-eval-aggregate", pattern="agent-eval-test-*.json")
    )

    assert aggregate["status"] == "ok"
    assert aggregate["run_count"] == 2
    assert aggregate["total_tasks"] == 8
    assert aggregate["passed_tasks"] == 8
    assert aggregate["failed_tasks"] == 0
    assert aggregate["safety_boundary_ok"] is True
    assert aggregate["wrong_uri_count"] == 0
    assert aggregate["unsafe_term_count_total"] == 0
    assert aggregate["device_inventory_passed"] == 2
    assert aggregate["alarm_detection_passed"] == 2
    assert aggregate["clinical_summary_passed"] == 2
    assert aggregate["resource_selection_passed"] == 2
    assert Path(aggregate["output_json"]).exists()
    assert Path(aggregate["output_csv"]).exists()

    saved = json.loads(Path(aggregate["output_json"]).read_text(encoding="utf-8"))
    assert saved["pass_rate"] == 1.0
    assert set(saved["scenario_values"]) == {"baseline", "tachycardia"}
