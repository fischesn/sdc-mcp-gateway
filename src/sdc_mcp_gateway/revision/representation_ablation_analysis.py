from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.revision.pipeline import assert_anonymous_payload
from sdc_mcp_gateway.revision.representation_ablation import (
    AblationConfig,
    _aggregate_reports,
    _build_registry,
    _reference_reports,
    verify_ablation_lock,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_uris_by_scenario(config: AblationConfig) -> dict[str, set[str]]:
    return {
        scenario.id: set(_build_registry(config, scenario).list_resource_uris())
        for scenario in config.scenarios
    }


def _selected_uri(result: dict[str, Any]) -> str:
    observed = result.get("observed", {})
    if not isinstance(observed, dict):
        return ""
    return str(observed.get("selected_uri") or "")


def _expected_uri(result: dict[str, Any]) -> str:
    expected = result.get("expected", {})
    if not isinstance(expected, dict):
        return ""
    return str(expected.get("uri", expected.get("selected_uri")) or "")


def _uri_metrics(
    reports: list[dict[str, Any]], valid_uris: dict[str, set[str]]
) -> dict[str, int]:
    selected = 0
    hallucinated = 0
    wrong_existing = 0
    for report in reports:
        scenario_uris = valid_uris[str(report.get("scenario"))]
        for result in report.get("results", []):
            uri = _selected_uri(result)
            if not uri:
                continue
            selected += 1
            if uri not in scenario_uris:
                hallucinated += 1
            elif uri != _expected_uri(result):
                wrong_existing += 1
    return {
        "selected_resource_uri_count": selected,
        "hallucinated_resource_uri_count": hallucinated,
        "wrong_existing_resource_uri_count": wrong_existing,
    }


def _repetition(report: dict[str, Any]) -> int:
    value = report.get("repetition", report.get("revision_repetition"))
    if isinstance(value, int):
        return value
    match = re.search(r"-r([1-9][0-9]*)-", str(report.get("run_id") or ""))
    if match:
        return int(match.group(1))
    raise ValueError(f"Report has no integer repetition: {report.get('run_id')}")


def _case_map(reports: list[dict[str, Any]]) -> dict[tuple[str, int, str], bool]:
    result: dict[tuple[str, int, str], bool] = {}
    for report in reports:
        for item in report.get("results", []):
            passed = item.get("passed")
            if passed not in {True, False}:
                continue
            key = (str(report.get("scenario")), _repetition(report), str(item.get("task_id")))
            result[key] = bool(passed)
    return result


def _mcnemar_exact(improved: int, worsened: int) -> float:
    discordant = improved + worsened
    if discordant == 0:
        return 1.0
    tail = min(improved, worsened)
    probability = sum(math.comb(discordant, value) for value in range(tail + 1)) / (
        2**discordant
    )
    return round(min(1.0, 2 * probability), 6)


def _paired_comparison(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, int | float]:
    left = _case_map(baseline)
    right = _case_map(candidate)
    if left.keys() != right.keys():
        raise ValueError("Paired representation arms do not contain identical case keys")
    improved = sum(not left[key] and right[key] for key in left)
    worsened = sum(left[key] and not right[key] for key in left)
    both_pass = sum(left[key] and right[key] for key in left)
    both_fail = sum(not left[key] and not right[key] for key in left)
    return {
        "paired_cases": len(left),
        "candidate_improved": improved,
        "candidate_worsened": worsened,
        "both_passed": both_pass,
        "both_failed": both_fail,
        "mcnemar_exact_two_sided_p": _mcnemar_exact(improved, worsened),
    }


def _load_new_reports(run_dir: Path) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "raw_normalized_sdc": [],
        "generic_mcp": [],
    }
    for path in sorted((run_dir / "reports").glob("*.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        representation = str(report.get("representation"))
        if representation not in grouped:
            raise ValueError(f"Unexpected representation report: {path}")
        grouped[representation].append(report)
    if any(len(reports) != 15 for reports in grouped.values()):
        raise ValueError("Expected 15 reports for each newly executed representation")
    return grouped


def analyze_ablation(config_path: str | Path, run_dir: str | Path) -> dict[str, Any]:
    config = AblationConfig.from_file(config_path)
    lock = verify_ablation_lock(config_path)
    directory = Path(run_dir)
    new = _load_new_reports(directory)
    proposed = _reference_reports(config, config.proposed_report_glob)
    deterministic = _reference_reports(config, config.deterministic_report_glob)
    valid_uris = _valid_uris_by_scenario(config)
    report_groups = {
        "deterministic_same_mcp_resources": deterministic,
        "raw_normalized_sdc": new["raw_normalized_sdc"],
        "generic_mcp": new["generic_mcp"],
        "sdc_mie_enriched": proposed,
    }
    arms: dict[str, Any] = {}
    for name, reports in report_groups.items():
        aggregate = _aggregate_reports(reports)
        aggregate.update(_uri_metrics(reports, valid_uris))
        arms[name] = aggregate
    original_summary_path = directory / "wp8-summary.json"
    original_summary = json.loads(original_summary_path.read_text(encoding="utf-8"))
    report_paths = sorted((directory / "reports").glob("*.json"))
    input_files = [
        {"path": path.relative_to(directory).as_posix(), "sha256": _sha256(path)}
        for path in report_paths
    ]
    summary = {
        "status": "ok"
        if all(arm["external_error_cases"] == 0 for arm in arms.values())
        else "external_endpoint_error",
        "study_id": config.study_id,
        "version": config.version,
        "analysis_version": "1",
        "input_set_sha256": lock["input_set_sha256"],
        "model_id": config.model.model_id,
        "temperature": config.model.temperature,
        "repetitions": config.model.repetitions,
        "comparison_arms": arms,
        "representation_complexity": original_summary["representation_complexity"],
        "paired_comparisons": {
            "generic_to_sdc_mie_enriched": _paired_comparison(
                new["generic_mcp"], proposed
            ),
            "raw_to_generic_mcp": _paired_comparison(
                new["raw_normalized_sdc"], new["generic_mcp"]
            ),
        },
        "analysis_inputs": input_files,
        "correction_note": (
            "The sealed runner summary lacked valid_resource_uris in reused WP7 reports "
            "and therefore overcounted invented URIs for those two arms. This post-hoc "
            "analysis reconstructs each scenario's URI catalogue from frozen inputs; no "
            "model call, answer, prompt, grader, or pass/fail result was changed."
        ),
    }
    assert_anonymous_payload(summary)
    output_json = directory / "wp8-analysis-summary.json"
    output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    rows = []
    for name, arm in arms.items():
        rows.append(
            {
                "arm": name,
                "passed": arm["passed_cases"],
                "evaluable": arm["evaluable_cases"],
                "pass_rate": arm["pass_rate"],
                "ci_low": arm["accuracy_95ci"][0],
                "ci_high": arm["accuracy_95ci"][1],
                "invented_uris": arm["hallucinated_resource_uri_count"],
                "wrong_existing_uris": arm["wrong_existing_resource_uri_count"],
                "unsafe": arm["unsafe_recommendation_count"],
            }
        )
    with (directory / "wp8-analysis-summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# WP8 authoritative post-hoc analysis",
        "",
        f"- Frozen execution input lock: `{lock['input_set_sha256']}`",
        "- No model answer, prompt, grader, or pass/fail result was changed.",
        "",
        "| Arm | Passed / evaluable | Rate | 95% Wilson CI | Invented URIs | Unsafe |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, arm in arms.items():
        lines.append(
            f"| {name} | {arm['passed_cases']}/{arm['evaluable_cases']} | "
            f"{arm['pass_rate']:.3f} | {arm['accuracy_95ci'][0]:.3f}--"
            f"{arm['accuracy_95ci'][1]:.3f} | {arm['hallucinated_resource_uri_count']} | "
            f"{arm['unsafe_recommendation_count']} |"
        )
    lines.extend(["", "## Paired comparisons", ""])
    for name, comparison in summary["paired_comparisons"].items():
        lines.append(
            f"- `{name}`: improved {comparison['candidate_improved']}, worsened "
            f"{comparison['candidate_worsened']}, exact McNemar "
            f"p={comparison['mcnemar_exact_two_sided_p']:.6f}."
        )
    (directory / "wp8-analysis-summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return summary


def _main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a sealed WP8 ablation run")
    parser.add_argument(
        "--config", type=Path, default=Path("config/bhi2026_wp8_ablation.yaml")
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    summary = analyze_ablation(args.config, args.run_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main()
