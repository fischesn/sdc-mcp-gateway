from __future__ import annotations

from sdc_mcp_gateway.revision.representation_ablation_analysis import (
    _mcnemar_exact,
    _paired_comparison,
    _uri_metrics,
)


def _report(repetition: int, passed: bool, selected_uri: str = "") -> dict:
    return {
        "scenario": "scenario-a",
        "repetition": repetition,
        "valid_resource_uris": ["sdc://devices/a/metrics"],
        "results": [
            {
                "task_id": "selection",
                "kind": "resource_selection",
                "passed": passed,
                "observed": {"selected_uri": selected_uri},
                "expected": {"uri": "sdc://devices/a/metrics"},
                "checks": {},
            }
        ],
    }


def test_uri_metrics_use_scenario_catalogue() -> None:
    reports = [
        _report(1, True, "sdc://devices/a/metrics"),
        _report(2, False, "sdc://devices/b/metrics"),
    ]
    metrics = _uri_metrics(reports, {"scenario-a": {"sdc://devices/a/metrics"}})
    assert metrics == {
        "selected_resource_uri_count": 2,
        "hallucinated_resource_uri_count": 1,
        "wrong_existing_resource_uri_count": 0,
    }


def test_paired_comparison_and_exact_mcnemar() -> None:
    baseline = [_report(1, False), _report(2, False), _report(3, True)]
    candidate = [_report(1, True), _report(2, True), _report(3, True)]
    result = _paired_comparison(baseline, candidate)
    assert result["candidate_improved"] == 2
    assert result["candidate_worsened"] == 0
    assert result["both_passed"] == 1
    assert result["mcnemar_exact_two_sided_p"] == 0.5
    assert _mcnemar_exact(6, 0) == 0.03125
