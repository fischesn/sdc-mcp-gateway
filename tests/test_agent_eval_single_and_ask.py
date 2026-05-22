from pathlib import Path

from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, AskAgentConfig, run_agent_evaluation, run_agent_question

ROOT = Path(__file__).resolve().parents[1]


def test_evaluate_agent_tasks_can_filter_single_task(tmp_path: Path) -> None:
    report = run_agent_evaluation(
        AgentEvalConfig(
            config_path=ROOT / "config/gateway.simulated.high-airway-pressure.example.yaml",
            mie_path=ROOT / "config/sdc_mie.yaml",
            tasks_path=ROOT / "config/agent_eval.tasks.yaml",
            scenario="airway-pressure",
            output_dir=tmp_path,
            run_label="single-task",
            agent="llm-mock",
            elapsed_s=100.0,
            task_ids=["clinical_summary"],
        )
    )
    assert report["status"] == "ok"
    assert report["task_count"] == 1
    assert report["passed_count"] == 1
    assert report["results"][0]["task_id"] == "clinical_summary"


def test_evaluate_agent_tasks_unknown_task_id_fails(tmp_path: Path) -> None:
    try:
        run_agent_evaluation(
            AgentEvalConfig(
                config_path=ROOT / "config/gateway.simulated.example.yaml",
                mie_path=ROOT / "config/sdc_mie.yaml",
                tasks_path=ROOT / "config/agent_eval.tasks.yaml",
                scenario="baseline",
                output_dir=tmp_path,
                task_ids=["does_not_exist"],
            )
        )
    except ValueError as exc:
        assert "Unknown task id" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected unknown task id to raise ValueError")


def test_ask_agent_mock_returns_read_only_answer(tmp_path: Path) -> None:
    report = run_agent_question(
        AskAgentConfig(
            config_path=ROOT / "config/gateway.simulated.high-airway-pressure.example.yaml",
            mie_path=ROOT / "config/sdc_mie.yaml",
            question="Is there an active alarm and which device is affected?",
            agent="llm-mock",
            elapsed_s=100.0,
            output_dir=tmp_path,
        )
    )
    assert report["status"] == "ok"
    assert "sim-ventilator-1" in report["answer"]
    assert "airway_pressure" in report["answer"]
    assert report["safety_boundary"]["write_operations_allowed"] is False
    assert Path(report["output_json"]).exists()
