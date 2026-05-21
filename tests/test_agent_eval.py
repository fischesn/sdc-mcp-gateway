from pathlib import Path

from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, TaskDocument, run_agent_evaluation

ROOT = Path(__file__).resolve().parents[1]


def test_task_document_loads() -> None:
    tasks = TaskDocument.from_file(ROOT / "config/agent_eval.tasks.yaml")
    assert len(tasks.tasks) == 4
    assert {task.kind for task in tasks.tasks} == {
        "device_inventory",
        "alarm_detection",
        "clinical_summary",
        "resource_selection",
    }


def test_oracle_agent_baseline_evaluation(tmp_path: Path) -> None:
    report = run_agent_evaluation(
        AgentEvalConfig(
            config_path=ROOT / "config/gateway.simulated.example.yaml",
            mie_path=ROOT / "config/sdc_mie.yaml",
            tasks_path=ROOT / "config/agent_eval.tasks.yaml",
            scenario="baseline",
            output_dir=tmp_path,
            run_label="test-agent-eval",
            elapsed_s=100.0,
        )
    )
    assert report["status"] == "ok"
    assert report["passed_count"] == 4
    assert report["failed_count"] == 0
    assert report["safety_boundary"]["tools_exported"] is False
    assert report["safety_boundary"]["write_operations_allowed"] is False
    assert Path(report["output_json"]).exists()
    assert Path(report["output_csv"]).exists()
    assert Path(report["output_markdown"]).exists()


def test_oracle_agent_alarm_scenarios(tmp_path: Path) -> None:
    scenarios = [
        ("tachycardia", ROOT / "config/gateway.simulated.tachycardia.example.yaml", "heart_rate"),
        ("spo2-drop", ROOT / "config/gateway.simulated.spo2-drop.example.yaml", "spo2"),
        (
            "airway-pressure",
            ROOT / "config/gateway.simulated.high-airway-pressure.example.yaml",
            "airway_pressure",
        ),
    ]
    for scenario, config, semantic_name in scenarios:
        report = run_agent_evaluation(
            AgentEvalConfig(
                config_path=config,
                mie_path=ROOT / "config/sdc_mie.yaml",
                tasks_path=ROOT / "config/agent_eval.tasks.yaml",
                scenario=scenario,
                output_dir=tmp_path,
                run_label="test-agent-eval",
                elapsed_s=100.0,
            )
        )
        assert report["status"] == "ok"
        alarm_task = next(result for result in report["results"] if result["task_id"] == "alarm_detection")
        assert alarm_task["passed"] is True
        active = alarm_task["observed"]["active_alarms"]
        assert any(fact["semantic_name"] == semantic_name for fact in active)
