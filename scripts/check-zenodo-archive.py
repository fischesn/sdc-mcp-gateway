"""Offline checks for an extracted SDC-MCP Gateway Zenodo archive (Python 3.11+)."""

import argparse
import hashlib
import json
from pathlib import Path


def check(root: Path) -> None:
    checked = 0
    line_endings = []

    def require(condition: bool, message: str) -> None:
        nonlocal checked
        if not condition:
            raise ValueError(message)
        checked += 1

    def safe_path(relative: str) -> Path:
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or path == root:
            raise ValueError(f"Unsafe manifest path: {relative}")
        return path

    def read(relative: str):
        return json.loads(safe_path(relative).read_text(encoding="utf-8-sig"))

    def historical_hash(relative: str, expected: str) -> None:
        content = safe_path(relative).read_bytes()
        if hashlib.sha256(content).hexdigest() == expected:
            require(True, relative)
            return
        content.decode("utf-8")  # Never normalize arbitrary binary data.
        lf = content.replace(b"\r\n", b"\n")
        for label, candidate in (("LF", lf), ("CRLF", lf.replace(b"\n", b"\r\n"))):
            if hashlib.sha256(candidate).hexdigest() == expected:
                line_endings.append({"path": relative, "historical_line_endings": label})
                require(True, relative)
                return
        require(False, f"Historical hash mismatch: {relative}")

    manifest = read("manifest.json")
    require(manifest["source_commit"] == "4cf508eee7c70b8fa7873f6ce457e6407e99f0e7", "Wrong source commit")
    require(manifest["source_tag"] == "v2.0.0-rc1", "Wrong source tag")
    source_count = 0
    listed = set()
    for item in manifest["files"]:
        require(item["path"] not in listed, "Duplicate manifest entry")
        listed.add(item["path"])
        content = safe_path(item["path"]).read_bytes()
        require(len(content) == item["bytes"], f"File size: {item['path']}")
        require(hashlib.sha256(content).hexdigest() == item["sha256"], f"Payload hash: {item['path']}")
        if item["path"].startswith("source/"):
            blob = b"blob " + str(len(content)).encode() + b"\0" + content
            require(hashlib.sha1(blob).hexdigest() == item["git_blob_sha1"], f"Git blob: {item['path']}")
            source_count += 1
    require(source_count == manifest["source_file_count"] == 653, "Incomplete source tree")

    freeze = read("source/config/bhi2026_wp7_freeze.json")
    require(len(freeze["input_files"]) == 32, "Scientific input count")
    for item in freeze["input_files"]:
        historical_hash("source/" + item["path"], item["sha256"])
    bundle = read("source/experiments/2026-08-10-consolidated-evaluation/consolidated-summary.json")
    for item in bundle["source_artifacts"]:
        historical_hash("source/" + item["path"], item["sha256"])
    require(len(bundle["checks"]) == 11 and all(bundle["checks"].values()), "Consolidated checks")
    require(bundle["frozen_agent_inputs"]["external_models_rerun"] is False, "Unexpected repeated model calls")
    require(bundle["software_state"]["head"] == "7b269c0e4598d93d231a83d685a7bbd23efcf692", "Evaluated code commit")

    holdout = "source/data/revision/holdout/bhi2026-wp7-v1-holdout-20260808T145452_463167Z"
    reports = []
    for path in safe_path(holdout + "/agent-evaluations").glob("*.json"):
        report = json.loads(path.read_text(encoding="utf-8"))
        if str(report.get("agent", "")).startswith("llm-"):
            reports.append(report)
    require(len(reports) == 75, "Expected 75 raw external-model reports")
    cases = [case for report in reports for case in report["results"]]
    require(len(cases) == 420 and sum(case["passed"] is True for case in cases) == 414, "Frozen pass count")
    analysis = read("source/data/revision/ablation/bhi2026-wp8-v1-ablation-20260809T201424_088639Z/wp8-analysis-summary.json")
    # The precise shape is checked against the preserved consolidation summary.
    require(bool(analysis), "Missing corrected representation analysis")
    arms = bundle["evidence_layers"]["frozen_agent_and_representation"]["representation_ablation"]["comparison_arms"]
    for arm, passed in (("raw_normalized_sdc", 63), ("generic_mcp", 75), ("sdc_mie_enriched", 81)):
        require(arms[arm]["passed_cases"] == passed and arms[arm]["scheduled_cases"] == 84, f"Ablation arm: {arm}")
    metadata = read("zenodo-metadata.json")
    require([c["name"] for c in metadata["creators"]] == ["Gerlach, Bennet", "Fischer, Stefan"], "Creator order")
    require(metadata["version"] == "2.0.0-rc1" and metadata["license"] == "MIT", "Deposit version/license")
    print(f"PASS: {checked} offline integrity and evidence assertions; {source_count} pinned source files.")
    print("No network calls, model requests, device operations, or regrading.")
    print("Historical digest matches requiring line-ending reconstruction:")
    print(json.dumps(line_endings, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    check(parser.parse_args().root.resolve())
