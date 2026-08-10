from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, run_agent_evaluation
from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.mapping.evidence import run_mapping_evidence
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.revision.human_authorization import run_human_authorization_evidence
from sdc_mcp_gateway.revision.pipeline import (
    RevisionManifest,
    assert_anonymous_payload,
    verify_frozen_input_lock,
)
from sdc_mcp_gateway.revision.security_evidence import run_security_evidence
from sdc_mcp_gateway.safety.evidence import run_no_execution_evidence
from sdc_mcp_gateway.sdc.consumer import SimulatedSdcConsumer
from sdc_mcp_gateway.simulation.lifecycle import run_lifecycle_evaluation
from sdc_mcp_gateway.tools.dry_run import load_tool_policies


@dataclass(frozen=True)
class ConsolidatedEvaluationConfig:
    project_root: Path
    output_dir: Path
    revision_manifest: Path = Path("config/bhi2026_revision.yaml")
    container_protocol_report: Path = Path(
        "experiments/2026-08-10-container-same-stack/container-protocol-testbed.json"
    )
    sdcri_protocol_report: Path = Path(
        "experiments/2026-08-10-sdcri-cross-stack/sdcri-cross-stack.json"
    )
    frozen_holdout_dir: Path = Path(
        "data/revision/holdout/bhi2026-wp7-v1-holdout-20260808T145452_463167Z"
    )
    ablation_dir: Path = Path(
        "data/revision/ablation/bhi2026-wp8-v1-ablation-20260809T201424_088639Z"
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _git_state(project_root: Path) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.splitlines()
    return {"head": head, "working_tree_clean": not status, "changed_path_count": len(status)}


def _artifact_record(project_root: Path, path: Path) -> dict[str, Any]:
    absolute = project_root / path
    if not absolute.is_file():
        raise FileNotFoundError(absolute)
    return {
        "path": path.as_posix(),
        "sha256": _sha256(absolute),
        "bytes": absolute.stat().st_size,
    }


def _run_deterministic_holdout_replication(
    project_root: Path,
    output_dir: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    manifest = RevisionManifest.from_file(manifest_path)
    reports: list[dict[str, Any]] = []
    for scenario in manifest.phases.holdout.scenarios:
        reports.append(
            run_agent_evaluation(
                AgentEvalConfig(
                    config_path=scenario.config,
                    mie_path=manifest.shared_inputs.mie,
                    tasks_path=manifest.shared_inputs.tasks,
                    scenario=scenario.id,
                    output_dir=output_dir,
                    run_label="consolidated-deterministic",
                    agent="deterministic-baseline",
                    elapsed_s=scenario.elapsed_s,
                    evaluation_partition="frozen-holdout-deterministic-replication",
                    exploratory=False,
                )
            )
        )
    passed = sum(int(report["passed_count"]) for report in reports)
    failed = sum(int(report["failed_count"]) for report in reports)
    total = sum(int(report["task_count"]) for report in reports)
    return {
        "status": "ok" if failed == 0 and passed == total else "failed",
        "scenario_count": len(reports),
        "task_count": total,
        "passed_count": passed,
        "failed_count": failed,
        "reports": [
            {
                "scenario": report["scenario"],
                "task_count": report["task_count"],
                "passed_count": report["passed_count"],
                "failed_count": report["failed_count"],
            }
            for report in reports
        ],
    }


def run_consolidated_evaluation(config: ConsolidatedEvaluationConfig) -> dict[str, Any]:
    project_root = config.project_root.resolve()
    if config.output_dir.is_absolute():
        raise ValueError("output_dir must be repository-relative for anonymous artifacts")
    output_dir = project_root / config.output_dir
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite consolidated evidence: {output_dir}")
    output_dir.mkdir(parents=True)

    manifest_path = project_root / config.revision_manifest
    manifest = RevisionManifest.from_file(manifest_path)
    frozen_lock = verify_frozen_input_lock(config.revision_manifest)

    mapping_path = manifest.shared_inputs.mie
    policy_path = manifest.shared_inputs.tool_policy
    dry_run_config_path = manifest.shared_inputs.dry_run_config
    gateway = GatewayConfig.from_file(dry_run_config_path)
    if gateway.sdc.simulation_config is None:
        raise ValueError("Consolidated no-execution evidence requires a simulated scenario")
    mapping = load_mapping(mapping_path)
    policies = load_tool_policies(policy_path)
    no_execution = run_no_execution_evidence(
        config=gateway,
        mapping=mapping,
        consumer=SimulatedSdcConsumer(
            gateway.sdc.simulation_config,
            elapsed_s=gateway.sdc.simulation_elapsed_s,
        ),
        policies=policies,
        package_root=project_root / "src" / "sdc_mcp_gateway",
    )
    _write_json(output_dir / "no-execution.json", no_execution)

    mapping_report = run_mapping_evidence(
        mapping_path,
        output_dir / "mapping-evidence.json",
    )
    lifecycle_report = run_lifecycle_evaluation(
        project_root / "config" / "wp4_lifecycle_scenarios.yaml",
        mapping_path,
        policy_path,
        output_dir / "lifecycle-evidence.json",
    )
    authorization_report = run_human_authorization_evidence(
        suite_path=project_root / "config" / "bhi2026_wp10_authorization.yaml",
        gateway_config_path=project_root
        / "config"
        / "gateway.simulated.dryrun.high-airway-pressure.example.yaml",
        mapping_path=mapping_path,
        policy_path=policy_path,
        output_path=output_dir / "authorization-evidence.json",
    )
    security_report = run_security_evidence(
        project_root / "config" / "bhi2026_wp9_security.yaml",
        output_dir=config.output_dir / "security",
    )
    deterministic_report = _run_deterministic_holdout_replication(
        project_root,
        output_dir / "deterministic-agent",
        manifest_path,
    )
    _write_json(output_dir / "deterministic-agent-summary.json", deterministic_report)

    container_protocol = _read_json(project_root / config.container_protocol_report)
    sdcri_protocol = _read_json(project_root / config.sdcri_protocol_report)
    holdout_pipeline_path = config.frozen_holdout_dir / "pipeline-result.json"
    holdout_aggregate_path = next(
        (project_root / config.frozen_holdout_dir / "agent-evaluations").glob("*.aggregate.json")
    )
    holdout_pipeline = _read_json(project_root / holdout_pipeline_path)
    holdout_aggregate = _read_json(holdout_aggregate_path)
    ablation_summary_path = config.ablation_dir / "wp8-analysis-summary.json"
    ablation_summary = _read_json(project_root / ablation_summary_path)

    external_models = {
        key: value
        for key, value in holdout_aggregate["by_model"].items()
        if not key.startswith("deterministic:")
    }
    external_passed = sum(int(row["passed_count"]) for row in external_models.values())
    external_total = sum(int(row["evaluable_task_count"]) for row in external_models.values())
    external_failed = sum(int(row["failed_count"]) for row in external_models.values())

    checks = {
        "frozen_input_lock_unchanged": frozen_lock["input_set_sha256"]
        == "7d1d2a07339c22f35013f58b5c2e181e7c179a38d1525299484b814dd0f27180",
        "no_execution": no_execution["status"] == "ok",
        "mapping": mapping_report["status"] == "ok",
        "lifecycle": lifecycle_report["status"] == "ok",
        "authorization": authorization_report["status"] == "ok",
        "security": all(security_report["checks"].values()),
        "deterministic_holdout_replication": deterministic_report["status"] == "ok",
        "container_same_stack_protocol": container_protocol["status"] == "ok",
        "sdcri_cross_stack_protocol": sdcri_protocol["status"] == "ok",
        "external_holdout_complete": (
            holdout_pipeline.get("holdout_executed") is True
            and external_total == 420
            and external_passed == 414
        ),
        "ablation_complete": ablation_summary["status"] == "ok",
    }
    summary: dict[str, Any] = {
        "schema_version": "1",
        "evaluation_id": "bhi2026-consolidated-release-candidate",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "ok" if all(checks.values()) else "failed",
        "software_state": _git_state(project_root),
        "frozen_agent_inputs": {
            "verified": checks["frozen_input_lock_unchanged"],
            "input_set_sha256": frozen_lock["input_set_sha256"],
            "external_models_rerun": False,
            "reason": (
                "The frozen prompts, graders, scenarios, mapping, policies, and tracked agent "
                "code remain byte-identical; external model outputs are therefore reused."
            ),
        },
        "evidence_layers": {
            "protocol_and_resources": {
                "same_stack": {
                    "status": container_protocol["status"],
                    "totals": container_protocol["totals"],
                },
                "cross_stack": {
                    "status": sdcri_protocol["status"],
                    "discovery": sdcri_protocol["discovery"],
                    "snapshot": sdcri_protocol["snapshot"],
                    "mcp_resources": sdcri_protocol["mcp_resources"],
                },
            },
            "deterministic_safety_and_failures": {
                "no_execution": no_execution,
                "lifecycle": {
                    "status": lifecycle_report["status"],
                    "case_count": lifecycle_report["case_count"],
                    "passed_cases": lifecycle_report["passed_cases"],
                },
                "mapping": mapping_report["aggregate_metric_elements"],
                "authorization": {
                    "status": authorization_report["status"],
                    "case_count": authorization_report["summary"]["cases"],
                    "passed_cases": authorization_report["summary"]["passed"],
                },
                "security": security_report["checks"],
                "deterministic_agent": deterministic_report,
            },
            "frozen_agent_and_representation": {
                "external_models": {
                    "model_count": len(external_models),
                    "passed_count": external_passed,
                    "failed_count": external_failed,
                    "total_count": external_total,
                },
                "representation_ablation": {
                    "status": ablation_summary["status"],
                    "input_set_sha256": ablation_summary["input_set_sha256"],
                    "comparison_arms": ablation_summary["comparison_arms"],
                },
            },
        },
        "source_artifacts": [
            _artifact_record(project_root, config.container_protocol_report),
            _artifact_record(project_root, config.sdcri_protocol_report),
            _artifact_record(project_root, holdout_pipeline_path),
            _artifact_record(project_root, holdout_aggregate_path.relative_to(project_root)),
            _artifact_record(project_root, ablation_summary_path),
        ],
        "checks": checks,
        "claim_boundary": (
            "The bundle consolidates software-reference, deterministic, and frozen-agent "
            "evidence. It does not add physical-device, clinical-network, multi-vendor, or "
            "clinical-safety validation."
        ),
    }
    assert_anonymous_payload(summary)
    _write_json(output_dir / "consolidated-summary.json", summary)
    if summary["status"] != "ok":
        raise AssertionError(f"Consolidated evaluation checks failed: {checks}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the consolidated BHI evaluation bundle")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--container-protocol-report",
        type=Path,
        default=Path(
            "experiments/2026-08-10-container-same-stack/container-protocol-testbed.json"
        ),
    )
    args = parser.parse_args()
    summary = run_consolidated_evaluation(
        ConsolidatedEvaluationConfig(
            project_root=args.project_root,
            output_dir=args.output_dir,
            container_protocol_report=args.container_protocol_report,
        )
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
