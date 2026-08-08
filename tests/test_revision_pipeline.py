import json
from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.main import app
from sdc_mcp_gateway.revision.pipeline import (
    RevisionManifest,
    assert_anonymous_payload,
    build_frozen_input_lock,
    build_revision_lock,
    run_revision_pipeline,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path("config/bhi2026_revision.yaml")
runner = CliRunner()


def test_revision_manifest_separates_development_and_holdout() -> None:
    manifest = RevisionManifest.from_file(MANIFEST)
    assert manifest.phases.development.enabled is True
    assert manifest.phases.development.execution_allowed is True
    assert len(manifest.phases.development.scenarios) == 4
    assert manifest.phases.holdout.enabled is True
    assert manifest.phases.holdout.frozen is True
    assert manifest.phases.holdout.execution_allowed is True
    assert len(manifest.phases.holdout.scenarios) == 5
    assert len(manifest.phases.holdout.agents) == 6
    assert manifest.phases.development.output_dir != manifest.phases.holdout.output_dir


def test_revision_lock_hashes_inputs_without_absolute_paths() -> None:
    lock = build_revision_lock(MANIFEST)
    assert lock["phase"] == "development"
    assert lock["holdout_state"]["executed_by_this_run"] is False
    assert len(lock["input_set_sha256"]) == 64
    assert all(len(item["sha256"]) == 64 for item in lock["input_files"])
    rendered = json.dumps(lock, ensure_ascii=False, sort_keys=True)
    assert str(ROOT) not in rendered
    assert "C:\\Users\\" not in rendered
    assert_anonymous_payload(lock)


def test_anonymity_check_accepts_https_without_mistaking_scheme_for_drive() -> None:
    assert_anonymous_payload({"endpoint": "https://example.invalid/v1/chat/completions"})


def test_holdout_gate_opens_only_with_frozen_manifest() -> None:
    manifest = RevisionManifest.from_file(MANIFEST)
    assert manifest.phases.holdout.execution_allowed is True
    assert manifest.phases.holdout.frozen is True
    assert manifest.shared_inputs.freeze_lock == Path("config/bhi2026_wp7_freeze.json")


def test_checked_in_wp7_freeze_matches_current_inputs() -> None:
    expected = json.loads(Path("config/bhi2026_wp7_freeze.json").read_text(encoding="utf-8"))
    assert build_frozen_input_lock(MANIFEST) == expected


def test_revision_pipeline_produces_isolated_development_summary(tmp_path: Path) -> None:
    result = run_revision_pipeline(MANIFEST, "development", output_root_override=tmp_path)
    assert result["status"] == "ok"
    assert result["phase"] == "development"
    assert result["holdout_executed"] is False
    assert result["agent_runs"] == 4
    assert result["agent_tasks"] == 16
    assert result["agent_tasks_passed"] == 16
    assert result["benchmark_runs"] == 4
    assert result["tool_cases"] == 7

    run_dirs = [path for path in tmp_path.iterdir() if path.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    summary = json.loads((run_dir / "paper-summary.json").read_text(encoding="utf-8"))
    lock = json.loads((run_dir / "manifest.lock.json").read_text(encoding="utf-8"))
    assert summary["status"] == "ok"
    assert summary["holdout_executed"] is False
    assert len(summary["rows"]) == 4
    assert lock["holdout_state"]["executed_by_this_run"] is False
    assert (run_dir / "paper-summary.csv").is_file()
    assert (run_dir / "paper-summary.md").is_file()
    assert (run_dir / "pipeline-result.json").is_file()


def test_revision_manifest_cli_help_lists_pipeline_command() -> None:
    result = runner.invoke(app, ["run-revision-pipeline", "--help"])
    assert result.exit_code == 0
