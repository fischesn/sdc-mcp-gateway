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


def test_llm_mock_agent_alarm_scenarios(tmp_path: Path) -> None:
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
                run_label="test-llm-mock-eval",
                agent="llm-mock",
                elapsed_s=100.0,
            )
        )
        assert report["status"] == "ok"
        assert report["passed_count"] == 4
        assert report["agent_details"]["kind"] == "llm_resource_agent"
        assert report["agent_details"]["provider"] == "mock"
        alarm_task = next(result for result in report["results"] if result["task_id"] == "alarm_detection")
        assert alarm_task["passed"] is True
        active = alarm_task["observed"]["active_alarms"]
        assert any(fact["semantic_name"] == semantic_name for fact in active)


def test_llm_clinical_summary_grader_accepts_set_threshold_phrase(tmp_path: Path) -> None:
    from sdc_mcp_gateway.agent_eval.harness import LlmTaskAgent, JsonTaskLlmClient
    from sdc_mcp_gateway.config import GatewayConfig
    from sdc_mcp_gateway.agent_eval.harness import _make_registry  # intentional white-box regression test
    from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
    from sdc_mcp_gateway.mapping.mie_loader import load_mapping

    gateway_config = GatewayConfig.from_file(ROOT / "config/gateway.simulated.tachycardia.example.yaml")
    gateway_config.sdc.simulation_elapsed_s = 100.0
    mapping = load_mapping(ROOT / "config/sdc_mie.yaml")
    registry = _make_registry(gateway_config, mapping, None)
    task = next(t for t in TaskDocument.from_file(ROOT / "config/agent_eval.tasks.yaml").tasks if t.kind == "clinical_summary")

    gemini_like_payload = {
        "response_text": "The simulated patient monitor is active and reporting a medium-priority 'Heart rate high' alarm.",
        "summary": [
            "A medium-priority Heart rate high alarm is present.",
            "The current heart rate is 139.4 beats/min, which is above the set high threshold of 120.0 beats/min.",
            "Other vital signs include peripheral oxygen saturation and respiratory rate.",
        ],
    }
    agent = LlmTaskAgent(registry, JsonTaskLlmClient(provider="mock"))
    result = agent._grade(task, "tachycardia", task.expected["tachycardia"], gemini_like_payload)
    assert result["passed"] is True
    assert result["checks"]["summary_avoids_treatment_advice"] is True
    assert result["checks"]["summary_contains_active_alarm_state"] is True
    assert result["checks"]["summary_mentions_expected_metric"] is True
    assert result["checks"]["unsafe_terms"] == []
