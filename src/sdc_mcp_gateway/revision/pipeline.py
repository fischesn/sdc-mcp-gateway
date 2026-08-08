from __future__ import annotations

import csv
import hashlib
import json
import os
import platform
import re
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from sdc_mcp_gateway import __version__
from sdc_mcp_gateway.agent_eval.harness import AgentEvalConfig, run_agent_evaluation
from sdc_mcp_gateway.agent_eval.summarize import (
    AgentEvalSummaryConfig,
    summarize_agent_evaluations,
)
from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.benchmark import BenchmarkConfig, run_benchmark
from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import DummySdcConsumer, SdcConsumer, SimulatedSdcConsumer
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies
from sdc_mcp_gateway.tools.evaluate import (
    DryRunToolEvaluationConfig,
    run_dry_run_tool_evaluation,
)


class RevisionScenario(BaseModel):
    id: str
    config: Path
    elapsed_s: float = 100.0


class RevisionAgent(BaseModel):
    id: str
    backend: str
    provider: str
    model_id: str | None = None
    repetitions: int = Field(default=1, ge=1)
    temperature: float = 0.0
    random_seed: int | None = None
    endpoint: str | None = None
    endpoint_env: str | None = None
    endpoint_suffix: str = ""
    api_key_env: str | None = None
    input_usd_per_million: float | None = None
    output_usd_per_million: float | None = None


class RevisionPhase(BaseModel):
    enabled: bool = False
    frozen: bool = False
    execution_allowed: bool = False
    output_dir: Path
    scenarios: list[RevisionScenario] = Field(default_factory=list)
    agents: list[RevisionAgent] = Field(default_factory=list)


class SharedInputs(BaseModel):
    mie: Path
    tasks: Path
    tool_policy: Path
    dry_run_config: Path
    dry_run_ack_config: Path
    freeze_lock: Path | None = None
    tracked_files: list[Path] = Field(default_factory=list)


class BenchmarkPlan(BaseModel):
    enabled: bool = True
    iterations: int = Field(default=5, ge=1)
    warmup: int = Field(default=1, ge=0)
    elapsed_start_s: float = 100.0
    elapsed_step_s: float = 0.0


class ToolEvaluationPlan(BaseModel):
    enabled: bool = True


class RevisionPhases(BaseModel):
    development: RevisionPhase
    holdout: RevisionPhase


class RevisionManifest(BaseModel):
    version: str
    study_id: str
    description: str
    shared_inputs: SharedInputs
    benchmark: BenchmarkPlan = Field(default_factory=BenchmarkPlan)
    tool_evaluation: ToolEvaluationPlan = Field(default_factory=ToolEvaluationPlan)
    phases: RevisionPhases

    @classmethod
    def from_file(cls, path: str | Path) -> "RevisionManifest":
        manifest_path = Path(path)
        with manifest_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Expected a YAML mapping at {manifest_path}")
        manifest = cls.model_validate(loaded)
        _validate_manifest(manifest)
        return manifest


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")


def _ensure_relative(path: Path, label: str) -> None:
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must be a repository-relative path: {path}")


def _validate_manifest(manifest: RevisionManifest) -> None:
    paths: list[tuple[str, Path]] = [
        ("shared_inputs.mie", manifest.shared_inputs.mie),
        ("shared_inputs.tasks", manifest.shared_inputs.tasks),
        ("shared_inputs.tool_policy", manifest.shared_inputs.tool_policy),
        ("shared_inputs.dry_run_config", manifest.shared_inputs.dry_run_config),
        ("shared_inputs.dry_run_ack_config", manifest.shared_inputs.dry_run_ack_config),
        *(
            [("shared_inputs.freeze_lock", manifest.shared_inputs.freeze_lock)]
            if manifest.shared_inputs.freeze_lock
            else []
        ),
        *[("shared_inputs.tracked_files", path) for path in manifest.shared_inputs.tracked_files],
    ]
    for phase_name in ("development", "holdout"):
        phase = getattr(manifest.phases, phase_name)
        paths.append((f"phases.{phase_name}.output_dir", phase.output_dir))
        paths.extend(
            (f"phases.{phase_name}.scenarios.config", row.config) for row in phase.scenarios
        )
        if phase.enabled and phase.execution_allowed and (not phase.scenarios or not phase.agents):
            raise ValueError(f"Enabled phase {phase_name!r} needs scenarios and agents")

    for label, path in paths:
        _ensure_relative(path, label)

    development_dir = manifest.phases.development.output_dir.as_posix().rstrip("/")
    holdout_dir = manifest.phases.holdout.output_dir.as_posix().rstrip("/")
    if development_dir == holdout_dir:
        raise ValueError("Development and hold-out output directories must be different")
    if not development_dir.startswith("data/revision/development"):
        raise ValueError("Development output must remain below data/revision/development")
    if not holdout_dir.startswith("data/revision/holdout"):
        raise ValueError("Hold-out output must remain below data/revision/holdout")


def _phase_for(manifest: RevisionManifest, phase_name: str) -> RevisionPhase:
    if phase_name not in {"development", "holdout"}:
        raise ValueError("phase must be 'development' or 'holdout'")
    phase = manifest.phases.development if phase_name == "development" else manifest.phases.holdout
    if not phase.enabled:
        raise ValueError(f"Phase {phase_name!r} is disabled in the revision manifest")
    if not phase.execution_allowed:
        raise ValueError(f"Phase {phase_name!r} is not authorized for execution")
    if phase_name == "holdout" and not phase.frozen:
        raise ValueError("Hold-out phase must be frozen before execution is permitted")
    if not phase.scenarios or not phase.agents:
        raise ValueError(f"Phase {phase_name!r} has no scenarios or agents")
    return phase


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _input_paths(
    manifest_path: Path,
    manifest: RevisionManifest,
    *,
    include_freeze_lock: bool = True,
) -> list[Path]:
    paths = {
        manifest_path,
        manifest.shared_inputs.mie,
        manifest.shared_inputs.tasks,
        manifest.shared_inputs.tool_policy,
        manifest.shared_inputs.dry_run_config,
        manifest.shared_inputs.dry_run_ack_config,
        *(
            [manifest.shared_inputs.freeze_lock]
            if include_freeze_lock and manifest.shared_inputs.freeze_lock
            else []
        ),
        *manifest.shared_inputs.tracked_files,
    }
    for phase_name in ("development", "holdout"):
        for scenario in getattr(manifest.phases, phase_name).scenarios:
            paths.add(scenario.config)
            gateway = GatewayConfig.from_file(scenario.config)
            if gateway.sdc.simulation_config:
                simulation_path = Path(gateway.sdc.simulation_config)
                _ensure_relative(simulation_path, "sdc.simulation_config")
                paths.add(simulation_path)
    missing = sorted(path.as_posix() for path in paths if not path.is_file())
    if missing:
        raise FileNotFoundError(f"Revision manifest inputs are missing: {', '.join(missing)}")
    return sorted(paths, key=lambda path: path.as_posix())


def build_frozen_input_lock(manifest_path: str | Path) -> dict[str, Any]:
    """Hash study inputs while excluding mutable execution gates and agent choices."""
    path = Path(manifest_path)
    _ensure_relative(path, "manifest_path")
    manifest = RevisionManifest.from_file(path)
    excluded = {path}
    if manifest.shared_inputs.freeze_lock:
        excluded.add(manifest.shared_inputs.freeze_lock)
    input_paths = [
        item
        for item in _input_paths(path, manifest, include_freeze_lock=False)
        if item not in excluded
    ]
    records = [
        {"path": item.as_posix(), "sha256": _sha256(item), "bytes": item.stat().st_size}
        for item in input_paths
    ]
    lock = {
        "schema_version": "1",
        "study_id": manifest.study_id,
        "purpose": "WP7 frozen prompts, graders, mappings, policies, and scenario inputs",
        "input_files": records,
        "input_set_sha256": hashlib.sha256(
            "\n".join(f"{row['path']}:{row['sha256']}" for row in records).encode("utf-8")
        ).hexdigest(),
    }
    assert_anonymous_payload(lock)
    return lock


def verify_frozen_input_lock(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = RevisionManifest.from_file(path)
    if manifest.shared_inputs.freeze_lock is None:
        raise ValueError("Hold-out execution requires shared_inputs.freeze_lock")
    with manifest.shared_inputs.freeze_lock.open("r", encoding="utf-8") as handle:
        expected = json.load(handle)
    current = build_frozen_input_lock(path)
    if expected != current:
        raise ValueError(
            "Frozen WP7 evaluation inputs changed; create a new declared freeze before execution"
        )
    return current


_ANONYMITY_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]"),
    re.compile(r"(?:^|[\\/])Users[\\/]", re.IGNORECASE),
    re.compile(r"(?:^|[\\/])home[\\/]", re.IGNORECASE),
    re.compile(r"file://", re.IGNORECASE),
    re.compile(r"github\.com", re.IGNORECASE),
    re.compile(r"git\.overleaf\.com", re.IGNORECASE),
]


def assert_anonymous_payload(payload: Any) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    matches = [pattern.pattern for pattern in _ANONYMITY_PATTERNS if pattern.search(rendered)]
    if matches:
        raise ValueError(
            f"Generated revision artifact contains identifying path/link patterns: {matches}"
        )


def build_revision_lock(
    manifest_path: str | Path,
    phase_name: Literal["development", "holdout"] = "development",
    *,
    require_executable_phase: bool = False,
) -> dict[str, Any]:
    path = Path(manifest_path)
    _ensure_relative(path, "manifest_path")
    manifest = RevisionManifest.from_file(path)
    phase = (
        _phase_for(manifest, phase_name)
        if require_executable_phase
        else getattr(manifest.phases, phase_name)
    )
    records = [
        {"path": item.as_posix(), "sha256": _sha256(item), "bytes": item.stat().st_size}
        for item in _input_paths(path, manifest)
    ]
    source_digest = hashlib.sha256(
        "\n".join(f"{row['path']}:{row['sha256']}" for row in records).encode("utf-8")
    ).hexdigest()
    lock: dict[str, Any] = {
        "schema_version": "1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_version": manifest.version,
        "manifest_sha256": _sha256(path),
        "study_id": manifest.study_id,
        "phase": phase_name,
        "phase_state": {
            "enabled": phase.enabled,
            "frozen": phase.frozen,
            "execution_allowed": phase.execution_allowed,
        },
        "holdout_state": {
            "enabled": manifest.phases.holdout.enabled,
            "frozen": manifest.phases.holdout.frozen,
            "execution_allowed": manifest.phases.holdout.execution_allowed,
            "executed_by_this_run": phase_name == "holdout",
        },
        "runtime": {
            "python": platform.python_version(),
            "gateway_package": __version__,
            "packages": {
                name: _package_version(name)
                for name in ("pydantic", "PyYAML", "jsonschema", "mcp", "sdc11073")
            },
        },
        "phase_inputs": {
            "output_dir": phase.output_dir.as_posix(),
            "scenarios": [scenario.model_dump(mode="json") for scenario in phase.scenarios],
            "agents": [agent.model_dump(mode="json") for agent in phase.agents],
            "benchmark": manifest.benchmark.model_dump(mode="json"),
            "tool_evaluation": manifest.tool_evaluation.model_dump(mode="json"),
        },
        "input_files": records,
        "input_set_sha256": source_digest,
    }
    assert_anonymous_payload(lock)
    return lock


def _make_tool_registry(
    config_path: Path,
    mie_path: Path,
    policy_path: Path,
    recorder_path: Path,
) -> DryRunToolRegistry:
    gateway = GatewayConfig.from_file(config_path)
    recorder = JsonlRecorder(recorder_path)
    mapping = load_mapping(mie_path)
    if gateway.sdc.adapter == "simulated":
        if not gateway.sdc.simulation_config:
            raise ValueError("Simulated dry-run config requires sdc.simulation_config")
        consumer: SdcConsumer = SimulatedSdcConsumer(
            gateway.sdc.simulation_config,
            elapsed_s=gateway.sdc.simulation_elapsed_s,
            recorder=recorder,
        )
    elif gateway.sdc.adapter == "dummy":
        consumer = DummySdcConsumer()
    else:
        raise ValueError("WP0 dry-run pipeline supports simulated or dummy adapters only")
    resources = ResourceRegistry(
        devices=consumer.get_snapshots(),
        mapping=mapping,
        recorder=recorder,
        tools_exported=gateway.gateway.allow_tools,
        tool_mode="dry-run" if gateway.gateway.allow_tools else None,
        write_operations_allowed=gateway.gateway.allow_write_operations,
        gateway_mode=gateway.gateway.mode,
    )
    return DryRunToolRegistry(
        resource_registry=resources,
        policies=load_tool_policies(policy_path),
        recorder=recorder,
        tools_enabled=gateway.gateway.allow_tools,
        write_operations_allowed=gateway.gateway.allow_write_operations,
    )


def _paper_summary(
    run_id: str,
    phase_name: str,
    agent_reports: list[dict[str, Any]],
    benchmark_reports: list[dict[str, Any]],
    tool_report: dict[str, Any] | None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for scenario in sorted({str(report["scenario"]) for report in agent_reports}):
        scenario_agents = [report for report in agent_reports if report["scenario"] == scenario]
        scenario_benchmarks = [
            report for report in benchmark_reports if report.get("revision_scenario") == scenario
        ]
        rows.append(
            {
                "scenario": scenario,
                "agent_runs": len(scenario_agents),
                "agent_tasks": sum(int(report["task_count"]) for report in scenario_agents),
                "agent_tasks_passed": sum(
                    int(report["passed_count"]) for report in scenario_agents
                ),
                "agent_tasks_failed": sum(
                    int(report["failed_count"]) for report in scenario_agents
                ),
                "resource_count": scenario_benchmarks[-1].get("resource_count")
                if scenario_benchmarks
                else None,
                "read_error_count": sum(
                    int(report.get("read_error_count_total") or 0) for report in scenario_benchmarks
                ),
            }
        )
    summary = {
        "run_id": run_id,
        "phase": phase_name,
        "status": "ok"
        if all(row["agent_tasks_failed"] == 0 and row["read_error_count"] == 0 for row in rows)
        and (tool_report is None or tool_report.get("status") == "ok")
        else "failed",
        "holdout_executed": phase_name == "holdout",
        "development_note": (
            "Development cases are exploratory and excluded from final aggregates. The WP6 "
            "deterministic baseline reads only the same MCP resource context supplied to LLMs; "
            "scenario ground truth is used only by the downstream grader."
        ),
        "rows": rows,
        "tool_evaluation": None
        if tool_report is None
        else {
            "case_count": tool_report.get("case_count"),
            "passed_cases": tool_report.get("passed_cases"),
            "failed_cases": tool_report.get("failed_cases"),
            "safety_boundary_ok": tool_report.get("safety_boundary_ok"),
            "executed_true_count": tool_report.get("executed_true_count"),
        },
    }
    assert_anonymous_payload(summary)
    return summary


def _write_paper_summary(run_dir: Path, summary: dict[str, Any]) -> dict[str, str]:
    json_path = run_dir / "paper-summary.json"
    csv_path = run_dir / "paper-summary.csv"
    markdown_path = run_dir / "paper-summary.md"
    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "scenario",
            "agent_runs",
            "agent_tasks",
            "agent_tasks_passed",
            "agent_tasks_failed",
            "resource_count",
            "read_error_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary["rows"])
    lines = [
        f"# Revision development summary: {summary['run_id']}",
        "",
        f"Status: **{summary['status']}**",
        "",
        summary["development_note"],
        "",
        "| Scenario | Agent tasks | Passed | Failed | Resources | Read errors |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary["rows"]:
        lines.append(
            f"| {row['scenario']} | {row['agent_tasks']} | {row['agent_tasks_passed']} | "
            f"{row['agent_tasks_failed']} | {row['resource_count']} | {row['read_error_count']} |"
        )
    if summary["tool_evaluation"] is not None:
        tool = summary["tool_evaluation"]
        lines.extend(
            [
                "",
                "## Dry-run tools",
                "",
                f"- Passed: {tool['passed_cases']}/{tool['case_count']}",
                f"- Safety boundary OK: {tool['safety_boundary_ok']}",
                f"- Executed=true count: {tool['executed_true_count']}",
            ]
        )
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "json": json_path.name,
        "csv": csv_path.name,
        "markdown": markdown_path.name,
    }


def run_revision_pipeline(
    manifest_path: str | Path,
    phase_name: Literal["development", "holdout"] = "development",
    *,
    output_root_override: Path | None = None,
) -> dict[str, Any]:
    path = Path(manifest_path)
    manifest = RevisionManifest.from_file(path)
    phase = _phase_for(manifest, phase_name)
    if phase_name == "holdout":
        verify_frozen_input_lock(path)
    output_root = output_root_override or phase.output_dir
    run_id = f"{manifest.version}-{phase_name}-{_utc_stamp()}"
    run_dir = output_root / run_id
    agent_dir = run_dir / "agent-evaluations"
    benchmark_dir = run_dir / "benchmarks"
    tool_dir = run_dir / "tool-evaluations"
    log_dir = run_dir / "logs"
    for directory in (agent_dir, benchmark_dir, tool_dir, log_dir):
        directory.mkdir(parents=True, exist_ok=True)

    lock = build_revision_lock(path, phase_name, require_executable_phase=True)
    lock_path = run_dir / "manifest.lock.json"
    lock_path.write_text(
        json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )

    agent_reports: list[dict[str, Any]] = []
    for scenario in phase.scenarios:
        for agent in phase.agents:
            endpoint = agent.endpoint
            if agent.endpoint_env:
                base_url = os.environ.get(agent.endpoint_env)
                if not base_url:
                    raise ValueError(f"Missing endpoint environment variable: {agent.endpoint_env}")
                endpoint = base_url.rstrip("/") + agent.endpoint_suffix
            for repetition in range(1, agent.repetitions + 1):
                report = run_agent_evaluation(
                    AgentEvalConfig(
                        config_path=scenario.config,
                        mie_path=manifest.shared_inputs.mie,
                        tasks_path=manifest.shared_inputs.tasks,
                        scenario=scenario.id,
                        output_dir=agent_dir,
                        run_label=f"wp0-agent-{agent.id}-r{repetition}",
                        agent=agent.backend,
                        elapsed_s=scenario.elapsed_s,
                        llm_provider=agent.provider,
                        llm_model=agent.model_id or "not-applicable",
                        llm_endpoint=endpoint,
                        llm_api_key_env=agent.api_key_env,
                        llm_temperature=agent.temperature,
                        llm_input_usd_per_million=agent.input_usd_per_million,
                        llm_output_usd_per_million=agent.output_usd_per_million,
                        recorder_path=log_dir
                        / f"agent-{scenario.id}-{agent.id}-r{repetition}.jsonl",
                        evaluation_partition=phase_name,
                        exploratory=phase_name == "development",
                    )
                )
                report["revision_agent_id"] = agent.id
                report["revision_repetition"] = repetition
                agent_reports.append(report)

    agent_aggregate = summarize_agent_evaluations(
        AgentEvalSummaryConfig(
            input_dir=agent_dir,
            output_dir=agent_dir,
            label="wp0-agent-aggregate",
            pattern="wp0-agent-*.json",
        )
    )

    benchmark_reports: list[dict[str, Any]] = []
    if manifest.benchmark.enabled:
        for scenario in phase.scenarios:
            report = run_benchmark(
                BenchmarkConfig(
                    config_path=scenario.config,
                    mie_path=manifest.shared_inputs.mie,
                    output_dir=benchmark_dir,
                    run_label=f"wp0-benchmark-{scenario.id}",
                    iterations=manifest.benchmark.iterations,
                    warmup=manifest.benchmark.warmup,
                    elapsed_start_s=manifest.benchmark.elapsed_start_s,
                    elapsed_step_s=manifest.benchmark.elapsed_step_s,
                    recorder_path=log_dir / f"benchmark-{scenario.id}.jsonl",
                )
            )
            report["revision_scenario"] = scenario.id
            benchmark_reports.append(report)

    tool_report: dict[str, Any] | None = None
    if manifest.tool_evaluation.enabled:
        primary = _make_tool_registry(
            manifest.shared_inputs.dry_run_config,
            manifest.shared_inputs.mie,
            manifest.shared_inputs.tool_policy,
            log_dir / "dry-run-primary.jsonl",
        )
        acknowledgement = _make_tool_registry(
            manifest.shared_inputs.dry_run_ack_config,
            manifest.shared_inputs.mie,
            manifest.shared_inputs.tool_policy,
            log_dir / "dry-run-ack.jsonl",
        )
        tool_report = run_dry_run_tool_evaluation(
            DryRunToolEvaluationConfig(
                config_path=manifest.shared_inputs.dry_run_config,
                ack_config_path=manifest.shared_inputs.dry_run_ack_config,
                mie_path=manifest.shared_inputs.mie,
                tool_policy_path=manifest.shared_inputs.tool_policy,
                output_dir=tool_dir,
                run_label="wp0-dry-run-tools",
            ),
            primary_registry=primary,
            ack_registry=acknowledgement,
        )

    paper_summary = _paper_summary(
        run_id, phase_name, agent_reports, benchmark_reports, tool_report
    )
    paper_outputs = _write_paper_summary(run_dir, paper_summary)
    result = {
        "status": paper_summary["status"],
        "run_id": run_id,
        "phase": phase_name,
        "manifest_version": manifest.version,
        "input_set_sha256": lock["input_set_sha256"],
        "holdout_executed": phase_name == "holdout",
        "agent_runs": len(agent_reports),
        "agent_tasks": sum(int(report["task_count"]) for report in agent_reports),
        "agent_tasks_passed": sum(int(report["passed_count"]) for report in agent_reports),
        "benchmark_runs": len(benchmark_reports),
        "tool_cases": tool_report.get("case_count") if tool_report else 0,
        "agent_aggregate_status": agent_aggregate.get("status"),
        "outputs": {
            "manifest_lock": lock_path.name,
            "paper_summary": paper_outputs,
        },
    }
    assert_anonymous_payload(result)
    result_path = run_dir / "pipeline-result.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result
