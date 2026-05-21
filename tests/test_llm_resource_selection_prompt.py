from __future__ import annotations

from pathlib import Path

from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, JsonTaskLlmClient, run_agent_evaluation


class CapturePromptClient(JsonTaskLlmClient):
    def __init__(self) -> None:
        super().__init__(provider="mock")
        self.last_user_prompt = ""

    def complete_json(self, *, system_prompt: str, user_prompt: str, mock_payload: dict):  # type: ignore[override]
        self.last_user_prompt = user_prompt
        return mock_payload


def test_resource_selection_prompt_contains_target_device_constraints(tmp_path: Path) -> None:
    # This test exercises the public run path with the mock backend and verifies
    # the resulting baseline selection remains the ventilator metrics URI.
    report = run_agent_evaluation(
        AgentEvalConfig(
            config_path=Path("config/gateway.simulated.example.yaml"),
            mie_path=Path("config/sdc_mie.yaml"),
            tasks_path=Path("config/agent_eval.tasks.yaml"),
            scenario="baseline",
            output_dir=tmp_path,
            agent="llm-mock",
            elapsed_s=100,
        )
    )
    resource_task = next(item for item in report["results"] if item["task_id"] == "metrics_resource_selection")
    assert resource_task["passed"] is True
    assert resource_task["observed"]["selected_uri"] == "sdc://devices/sim-ventilator-1/metrics"


def test_agent_task_file_has_explicit_resource_selection_prompt() -> None:
    text = Path("config/agent_eval.tasks.yaml").read_text(encoding="utf-8")
    assert "Return exactly one existing URI" in text
    assert "Do not provide an example" in text
