from __future__ import annotations

import json
from pathlib import Path

import pytest

from sdc_mcp_gateway.experiments.recorder import (
    REDACTED,
    AuditProvenance,
    JsonlRecorder,
    redact_secrets,
    sha256_canonical,
    verify_hash_chain,
)
from sdc_mcp_gateway.models import AuditRecord
from sdc_mcp_gateway.revision.security_evidence import run_security_evidence
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer


def provenance() -> AuditProvenance:
    digest = "a" * 64
    return AuditProvenance(
        provider_identity="urn:uuid:trusted-provider",
        resource_snapshot_sha256=digest,
        mapping_sha256=digest,
        policy_sha256=digest,
        task_sha256=digest,
        prompt_sha256=digest,
        model_id="deterministic-test",
    )


def test_provider_allowlist_uses_exact_identity_matching() -> None:
    trusted = "urn:uuid:trusted-provider"
    consumer = Sdc11073Consumer(provider_whitelist=[trusted])
    assert consumer._provider_allowed(trusted)
    assert not consumer._provider_allowed(f"{trusted}.attacker")
    assert not consumer._provider_allowed(f"attacker.{trusted}")
    assert not consumer._provider_allowed("trusted-provider")


def test_recursive_redaction_handles_headers_and_nested_secrets() -> None:
    value = {
        "headers": {"Authorization": "Bearer secret", "X-Trace": "safe"},
        "nested": [
            {"api-key": "secret-2"},
            {"token": "secret-3"},
            {"openai_api_key": "secret-4"},
        ],
    }
    redacted = redact_secrets(value)
    assert redacted["headers"]["Authorization"] == REDACTED
    assert redacted["headers"]["X-Trace"] == "safe"
    assert redacted["nested"][0]["api-key"] == REDACTED
    assert redacted["nested"][1]["token"] == REDACTED
    assert redacted["nested"][2]["openai_api_key"] == REDACTED


def test_hash_chain_detects_record_changes_and_refuses_append(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    recorder = JsonlRecorder(path, provenance=provenance(), hash_chain=True)
    recorder.write(AuditRecord(event_type="test", status="ok", details={"reason": "first"}))
    recorder.write(AuditRecord(event_type="test", status="rejected", details={"reason": "second"}))
    valid = verify_hash_chain(path)
    assert valid.valid
    assert valid.record_count == 2

    text = path.read_text(encoding="utf-8").replace('"status":"ok"', '"status":"changed"', 1)
    path.write_text(text, encoding="utf-8")
    invalid = verify_hash_chain(path)
    assert not invalid.valid
    assert invalid.error_line == 1
    assert invalid.reason == "record_hash_mismatch"
    with pytest.raises(ValueError, match="invalid audit chain"):
        JsonlRecorder(path, provenance=provenance(), hash_chain=True)


def test_canonical_hash_changes_when_configuration_changes() -> None:
    first = sha256_canonical({"allow": ["provider-a"], "limit": 1})
    second = sha256_canonical({"allow": ["provider-a"], "limit": 2})
    assert first != second


def test_wp9_evidence_contains_complete_provenance_and_no_secret(tmp_path: Path) -> None:
    output = tmp_path / "evidence"
    summary = run_security_evidence("config/bhi2026_wp9_security.yaml", output_dir=output)
    assert all(summary["checks"].values())
    assert summary["audit"]["record_count"] == 4
    records = [json.loads(line) for line in (output / "audit-chain.jsonl").read_text().splitlines()]
    required = {
        "provider_identity",
        "resource_snapshot_sha256",
        "mapping_sha256",
        "policy_sha256",
        "task_sha256",
        "prompt_sha256",
        "model_id",
    }
    assert all(required <= set(record["provenance"]) for record in records)
    assert records[1]["decision_reason"] == "policy_validated_no_execution"
    assert records[2]["decision_reason"] == "value_out_of_range"
    assert records[3]["details"]["arguments"]["Authorization"] == REDACTED
    assert "wp9-secret-probe-must-not-appear" not in (output / "audit-chain.jsonl").read_text()
