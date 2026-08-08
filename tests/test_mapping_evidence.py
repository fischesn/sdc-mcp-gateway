from pathlib import Path

from typer.testing import CliRunner

from sdc_mcp_gateway.main import app
from sdc_mcp_gateway.mapping.evidence import run_mapping_evidence


def test_mapping_evidence_covers_all_profiles_and_classes(tmp_path: Path) -> None:
    output = tmp_path / "mapping-evidence.json"
    report = run_mapping_evidence("config/sdc_mie.yaml", output)
    assert report["status"] == "ok"
    assert report["mapping"]["json_schema_valid"] is True
    assert len(report["mapping"]["source_sha256"]) == 64
    assert report["aggregate_metric_elements"]["total"] == 11
    assert report["aggregate_metric_elements"]["states"] == {
        "mapped": 7,
        "unmapped": 4,
        "unsupported": 0,
        "conflicting": 0,
    }
    assert report["aggregate_metric_elements"]["coverage"] == 7 / 11
    assert {profile["profile"] for profile in report["profiles"]} == {
        "monitor",
        "ventilator",
        "heterogeneous",
    }
    heterogeneous = next(
        profile for profile in report["profiles"] if profile["profile"] == "heterogeneous"
    )
    assert (
        heterogeneous["descriptor_classes"]["ActivateOperationDescriptorContainer"]
        ["states"]["unsupported"]
        == 1
    )
    assert output.exists()


def test_cli_evaluate_mapping(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["evaluate-mapping", "--output", str(tmp_path / "mapping.json")],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"mapped": 7' in result.output
