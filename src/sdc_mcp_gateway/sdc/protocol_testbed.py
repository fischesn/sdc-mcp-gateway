from __future__ import annotations

import ipaddress
import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer
from sdc_mcp_gateway.sdc.reference_provider import PROFILE_VALUES


@dataclass(frozen=True)
class ProtocolTestbedConfig:
    mapping_path: Path
    output_path: Path
    local_ip: str = "127.0.0.1"
    profiles: tuple[str, ...] = tuple(PROFILE_VALUES)
    repetitions: int = 5
    discovery_timeout_s: float = 0.6
    startup_timeout_s: float = 20.0


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[position]


def _summarize_latency(values: list[float]) -> dict[str, float]:
    return {
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(_percentile(values, 0.95), 3),
        "min_ms": round(min(values), 3),
        "max_ms": round(max(values), 3),
    }


def _wait_until_ready(process: subprocess.Popen[str], ready_file: Path, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if ready_file.exists():
            return cast(dict[str, Any], json.loads(ready_file.read_text(encoding="utf-8")))
        if process.poll() is not None:
            stdout, stderr = process.communicate(timeout=2)
            raise RuntimeError(
                f"Reference provider exited with {process.returncode}: stdout={stdout!r}, stderr={stderr!r}"
            )
        time.sleep(0.05)
    raise TimeoutError(f"Reference provider did not become ready within {timeout_s} seconds")


def _stop_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _write_ephemeral_tls_material(directory: Path, local_ip: str) -> None:
    """Create an experiment-only self-signed identity trusted by both local peers."""

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    directory.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "wp3-sdc-reference")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(local_ip))]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    certificate_bytes = certificate.public_bytes(serialization.Encoding.PEM)
    (directory / "userkey.pem").write_bytes(key_bytes)
    (directory / "usercert.pem").write_bytes(certificate_bytes)
    (directory / "cacert.pem").write_bytes(certificate_bytes)


def _run_profile(config: ProtocolTestbedConfig, profile: str) -> dict[str, Any]:
    mapping = load_mapping(config.mapping_path)
    with tempfile.TemporaryDirectory(prefix=f"sdc-wp3-{profile}-") as tmp_dir:
        ready_file = Path(tmp_dir) / "ready.json"
        tls_dir = Path(tmp_dir) / "tls"
        _write_ephemeral_tls_material(tls_dir, config.local_ip)
        command = [
            sys.executable,
            "-m",
            "sdc_mcp_gateway.sdc.reference_provider",
            "--profile",
            profile,
            "--local-ip",
            config.local_ip,
            "--ready-file",
            str(ready_file),
            "--tls-dir",
            str(tls_dir),
        ]
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        from sdc11073.definitions_sdc import SdcV1Definitions
        from sdc11073.certloader import mk_ssl_contexts_from_folder
        from sdc11073.wsdiscovery import Service, WSDiscovery

        with WSDiscovery(config.local_ip) as discovery:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )
            try:
                provider = _wait_until_ready(process, ready_file, config.startup_timeout_s)
                time.sleep(0.25)
                audit_path = Path(tmp_dir) / "consumer-audit.jsonl"
                consumer = Sdc11073Consumer(
                    discovery_timeout_s=config.discovery_timeout_s,
                    provider_whitelist=[provider["epr"]],
                    local_ip=config.local_ip,
                    max_devices=1,
                    recorder=JsonlRecorder(audit_path),
                    ssl_context_container=mk_ssl_contexts_from_folder(tls_dir),
                )
                discovery_latencies: list[float] = []
                end_to_end_latencies: list[float] = []
                discovery_successes = 0
                snapshot_successes = 0
                directed_service_fallbacks = 0
                resource_reads_attempted = 0
                resource_reads_succeeded = 0
                representative_snapshot: Any | None = None
                representative_registry: ResourceRegistry | None = None

                for _ in range(config.repetitions):
                    discovery_start = time.monotonic()
                    services = list(
                        discovery.search_services(
                            types=SdcV1Definitions.MedicalDeviceTypesFilter,
                            timeout=config.discovery_timeout_s,
                        )
                    )
                    accepted_services = [service for service in services if service.epr == provider["epr"]]
                    discovery_latencies.append((time.monotonic() - discovery_start) * 1000.0)
                    if accepted_services:
                        discovery_successes += 1

                    connection_services = accepted_services
                    if not connection_services:
                        directed_service_fallbacks += 1
                        connection_services = [
                            Service(
                                types=list(SdcV1Definitions.MedicalDeviceTypesFilter),
                                scopes=None,
                                x_addrs=provider["x_addrs"],
                                epr=provider["epr"],
                                instance_id="1",
                            )
                        ]

                    e2e_start = time.monotonic()
                    snapshots = consumer.get_snapshots_from_services(connection_services[:1])
                    if snapshots:
                        snapshot_successes += 1
                        representative_snapshot = snapshots[0]
                        registry = ResourceRegistry(devices=snapshots, mapping=mapping)
                        representative_registry = registry
                        for uri in registry.list_resource_uris():
                            resource_reads_attempted += 1
                            registry.read(uri)
                            resource_reads_succeeded += 1
                    end_to_end_latencies.append((time.monotonic() - e2e_start) * 1000.0)

                if representative_snapshot is None or representative_registry is None:
                    audit_text = audit_path.read_text(encoding="utf-8") if audit_path.exists() else ""
                    raise RuntimeError(
                        f"No snapshot was extracted for profile {profile}; consumer audit={audit_text}"
                    )
                mapped_metrics = representative_registry.mapper.map_device_metrics(representative_snapshot)
                mapped_count = sum(metric.mapped for metric in mapped_metrics)
                raw_summary = representative_snapshot.raw_mdib
                public_provider = {
                    "profile": provider["profile"],
                    "epr": provider["epr"],
                    "mdib": provider["mdib"],
                    "separate_process": True,
                    "transport": "HTTPS",
                }
                return {
                    "profile": profile,
                    "provider": public_provider,
                    "discovery": {
                        "successes": discovery_successes,
                        "attempts": config.repetitions,
                        "success_rate": discovery_successes / config.repetitions,
                        "directed_service_fallbacks": directed_service_fallbacks,
                        "note": (
                            "The persistent listener records Probe/Hello discovery when the host OS "
                            "delivers same-host multicast. Otherwise the provider-advertised XAddr is "
                            "used for the SOAP/MDIB path and the discovery miss remains visible."
                        ),
                        "latency": _summarize_latency(discovery_latencies),
                    },
                    "snapshot": {
                        "successes": snapshot_successes,
                        "attempts": config.repetitions,
                        "success_rate": snapshot_successes / config.repetitions,
                        "descriptor_count": raw_summary["descriptor_count"],
                        "state_count": raw_summary["state_count"],
                        "metric_count": len(representative_snapshot.metrics),
                        "alarm_state_count": len(representative_snapshot.alarms),
                        "context_state_count": len(representative_snapshot.context.raw["context_states"]),
                    },
                    "mcp_resources": {
                        "advertised_count": len(representative_registry.list_resource_uris()),
                        "reads_succeeded": resource_reads_succeeded,
                        "reads_attempted": resource_reads_attempted,
                        "success_rate": resource_reads_succeeded / resource_reads_attempted,
                    },
                    "mapping": {
                        "mapped_metrics": mapped_count,
                        "total_metrics": len(mapped_metrics),
                        "coverage": mapped_count / len(mapped_metrics) if mapped_metrics else 0.0,
                        "states": {
                            state: sum(metric.mapping_state == state for metric in mapped_metrics)
                            for state in ("mapped", "unmapped", "unsupported", "conflicting")
                        },
                        "unmapped_codes": sorted(
                            {
                                metric.code or "<missing>"
                                for metric in mapped_metrics
                                if metric.mapping_state == "unmapped"
                            }
                        ),
                        "source_sha256": mapping.source_sha256,
                    },
                    "unsupported": {
                        "descriptor_types": raw_summary["unsupported_descriptor_types"],
                        "state_types": raw_summary["unsupported_state_types"],
                    },
                    "local_host_snapshot_to_all_resources": _summarize_latency(end_to_end_latencies),
                }
            finally:
                _stop_process(process)


def run_protocol_testbed(config: ProtocolTestbedConfig) -> dict[str, Any]:
    if config.repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    unknown = sorted(set(config.profiles) - set(PROFILE_VALUES))
    if unknown:
        raise ValueError(f"Unknown profiles: {unknown}")

    mapping = load_mapping(config.mapping_path)
    profile_reports = [_run_profile(config, profile) for profile in config.profiles]
    report = {
        "status": "ok",
        "scope": "software-reference provider on the local host; no physical medical device",
        "library": {"name": "sdc11073", "version": _sdc11073_version()},
        "mapping_artifact": {
            "schema_version": mapping.schema_version,
            "version": mapping.version,
            "source_sha256": mapping.source_sha256,
            "provenance": mapping.provenance.model_dump(),
        },
        "profiles": profile_reports,
        "protocol_elements": {
            "ws_discovery_attempted": True,
            "ws_discovery_succeeded_for_all_profiles": all(
                profile["discovery"]["success_rate"] == 1.0 for profile in profile_reports
            ),
            "http_soap_getmdib": True,
            "xml_schema_validation": True,
            "consumer_mdib_initialization": True,
            "read_only_sdc_to_mcp_resource_path": True,
            "tls": True,
            "subscriptions_and_periodic_reports": False,
            "physical_device_or_clinical_network": False,
            "setservice_or_activateoperation_invocation": False,
        },
        "claim_boundary": (
            "Latencies are local-host software-reference engineering measurements and do not "
            "characterize a clinical network or physical device."
        ),
    }
    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _sdc11073_version() -> str:
    import sdc11073

    return str(getattr(sdc11073, "__version__", "unknown"))
