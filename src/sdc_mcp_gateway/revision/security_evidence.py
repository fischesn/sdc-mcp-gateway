from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from sdc_mcp_gateway.config import GatewayConfig
from sdc_mcp_gateway.experiments.recorder import (
    REDACTED,
    AuditProvenance,
    JsonlRecorder,
    sha256_canonical,
    sha256_file,
    verify_hash_chain,
)
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer, SimulatedSdcConsumer
from sdc_mcp_gateway.tools.dry_run import DryRunToolRegistry, load_tool_policies


class SecurityEvidenceConfig(BaseModel):
    schema_version: str
    study_id: str
    provider_identity: str
    gateway_config: Path
    mapping: Path
    policy: Path
    task: str
    prompt: str
    model_id: str
    output_dir: Path

    @classmethod
    def from_file(cls, path: str | Path) -> "SecurityEvidenceConfig":
        with Path(path).open("r", encoding="utf-8") as handle:
            value = yaml.safe_load(handle) or {}
        return cls.model_validate(value)


def run_security_evidence(
    config_path: str | Path,
    *,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Exercise the WP9 controls without a network transport or model call."""

    config_path = Path(config_path)
    config = SecurityEvidenceConfig.from_file(config_path)
    destination = Path(output_dir) if output_dir is not None else config.output_dir
    destination.mkdir(parents=True, exist_ok=True)
    audit_path = destination / "audit-chain.jsonl"
    summary_path = destination / "security-evidence.json"
    if audit_path.exists() or summary_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing WP9 evidence in {destination}")

    gateway = GatewayConfig.from_file(config.gateway_config)
    if gateway.mcp.transport != "stdio":
        raise ValueError("WP9 evaluates the local stdio boundary only")
    if not gateway.sdc.simulation_config:
        raise ValueError("WP9 evidence requires a simulated snapshot configuration")

    snapshots = SimulatedSdcConsumer(
        gateway.sdc.simulation_config,
        elapsed_s=gateway.sdc.simulation_elapsed_s,
    ).get_snapshots()
    matching = [snapshot for snapshot in snapshots if snapshot.device_id == config.provider_identity]
    if len(matching) != 1:
        raise ValueError("Configured provider identity must select exactly one snapshot")
    snapshot = matching[0]
    mapping = load_mapping(config.mapping)
    policies = load_tool_policies(config.policy)
    provenance = AuditProvenance(
        provider_identity=config.provider_identity,
        resource_snapshot_sha256=sha256_canonical(snapshot.model_dump(mode="json")),
        mapping_sha256=sha256_file(config.mapping),
        policy_sha256=sha256_file(config.policy),
        task_sha256=sha256_canonical(config.task),
        prompt_sha256=sha256_canonical(config.prompt),
        model_id=config.model_id,
    )
    recorder = JsonlRecorder(audit_path, provenance=provenance, hash_chain=True)
    registry = ResourceRegistry(
        [snapshot],
        mapping,
        recorder=recorder,
        tools_exported=True,
        tool_mode="dry-run",
        write_operations_allowed=False,
        gateway_mode="dry-run-tools",
    )
    tools = DryRunToolRegistry(
        registry,
        policies,
        recorder=recorder,
        tools_enabled=True,
        write_operations_allowed=False,
    )

    resource_uri = f"sdc://devices/{config.provider_identity}/metrics"
    registry.read(resource_uri)
    accepted = tools.call_tool(
        "prepare_set_fio2",
        {"device_id": config.provider_identity, "value": 45.0},
    )
    rejected = tools.call_tool(
        "prepare_set_fio2",
        {"device_id": config.provider_identity, "value": 150.0},
    )
    secret_probe = "Bearer wp9-secret-probe-must-not-appear"
    malformed = tools.call_tool(
        "prepare_set_fio2",
        {
            "device_id": config.provider_identity,
            "value": 45.0,
            "Authorization": secret_probe,
        },
    )

    verification = verify_hash_chain(audit_path)
    audit_text = audit_path.read_text(encoding="utf-8")
    redaction_ok = secret_probe not in audit_text and REDACTED in audit_text

    tampered_path = destination / "audit-chain-tampered.jsonl"
    shutil.copyfile(audit_path, tampered_path)
    tampered_text = tampered_path.read_text(encoding="utf-8")
    tampered_path.write_text(tampered_text.replace('"status":"ok"', '"status":"changed"', 1), encoding="utf-8")
    tampered = verify_hash_chain(tampered_path)
    tampered_path.unlink()

    allowlist_probe = Sdc11073Consumer(provider_whitelist=[config.provider_identity])
    identities = [
        config.provider_identity,
        f"{config.provider_identity}.attacker",
        f"attacker.{config.provider_identity}",
        config.provider_identity.removeprefix("sim-"),
    ]
    allowlist_results = {
        identity: allowlist_probe._provider_allowed(identity) for identity in identities
    }
    exact_allowlist_ok = allowlist_results == {
        config.provider_identity: True,
        f"{config.provider_identity}.attacker": False,
        f"attacker.{config.provider_identity}": False,
        config.provider_identity.removeprefix("sim-"): False,
    }

    summary: dict[str, Any] = {
        "schema_version": "1",
        "study_id": config.study_id,
        "transport": {
            "evaluated": "stdio",
            "network_listener": False,
            "future_http_requirements": [
                "mutual endpoint authentication",
                "least-privilege resource and tool authorization",
                "TLS with managed certificate lifecycle",
                "request size and rate limits",
                "replay protection and externally anchored audit retention",
            ],
        },
        "provenance": provenance.model_dump(),
        "configuration_sha256": sha256_file(config_path),
        "audit": {
            "path": audit_path.as_posix(),
            "record_count": verification.record_count,
            "chain_valid": verification.valid,
            "head_sha256": verification.head_sha256,
            "tamper_detected": not tampered.valid,
            "tamper_detection_reason": tampered.reason,
            "tamper_detection_line": tampered.error_line,
            "secret_redaction_passed": redaction_ok,
            "tail_truncation_requires_external_anchor": True,
        },
        "provider_allowlist": {
            "comparison": "exact endpoint-reference string equality",
            "cases": allowlist_results,
            "passed": exact_allowlist_ok,
        },
        "decisions": [
            accepted.model_dump(mode="json"),
            rejected.model_dump(mode="json"),
            malformed.model_dump(mode="json"),
        ],
        "checks": {
            "accepted_dry_run": accepted.status == "accepted_dry_run" and not accepted.executed,
            "out_of_range_rejected": rejected.reason == "value_out_of_range" and not rejected.executed,
            "malformed_client_rejected": malformed.reason == "unexpected_arguments",
            "provider_exact_match": exact_allowlist_ok,
            "audit_chain_verified": verification.valid,
            "audit_tampering_detected": not tampered.valid,
            "secrets_absent_from_log": redaction_ok,
        },
    }
    if not all(summary["checks"].values()):
        raise AssertionError(f"WP9 evidence check failed: {summary['checks']}")
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate local WP9 security evidence")
    parser.add_argument(
        "--config",
        default="config/bhi2026_wp9_security.yaml",
        help="WP9 evidence configuration",
    )
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    args = parser.parse_args()
    summary = run_security_evidence(args.config, output_dir=args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
