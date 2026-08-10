from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer


@dataclass(frozen=True)
class SDCriTestbedConfig:
    """Configuration for an independent Java-provider/Python-consumer experiment."""

    java_path: Path
    classpath_path: Path
    mapping_path: Path
    output_path: Path
    local_ip: str
    sdcri_version: str = "7.0.0"
    sdcri_commit: str = "cc46b3b8e113c80ef4977920160b858ac72f1343"
    repetitions: int = 5
    discovery_timeout_s: float = 2.0
    startup_timeout_s: float = 90.0
    provider_epr: str = "urn:uuid:5dc11073-0000-4000-8000-000000000700"


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


def _write_certificate(
    *,
    directory: Path,
    common_name: str,
    local_ip: str,
    ca_key: Any,
    ca_certificate: Any,
    encrypted_key_password: bytes | None,
    server: bool,
) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    directory.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
        .issuer_name(ca_certificate.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(local_ip))]),
            critical=False,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH]
                if server
                else [ExtendedKeyUsageOID.CLIENT_AUTH]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    encryption = (
        serialization.BestAvailableEncryption(encrypted_key_password)
        if encrypted_key_password
        else serialization.NoEncryption()
    )
    key_bytes = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    )
    (directory / "userkey.pem").write_bytes(key_bytes)
    (directory / "usercert.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    (directory / "cacert.pem").write_bytes(
        ca_certificate.public_bytes(serialization.Encoding.PEM)
    )


def _write_mutual_tls_material(root: Path, local_ip: str, password: bytes) -> tuple[Path, Path]:
    """Create separate provider and consumer identities signed by one ephemeral test CA."""

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    ca_subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "SDCri cross-stack test CA")])
    ca_certificate = (
        x509.CertificateBuilder()
        .subject_name(ca_subject)
        .issuer_name(ca_subject)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    provider_dir = root / "provider"
    consumer_dir = root / "consumer"
    _write_certificate(
        directory=provider_dir,
        common_name="sdcri-provider",
        local_ip=local_ip,
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        encrypted_key_password=password,
        server=True,
    )
    _write_certificate(
        directory=consumer_dir,
        common_name="sdc-mcp-gateway-consumer",
        local_ip=local_ip,
        ca_key=ca_key,
        ca_certificate=ca_certificate,
        encrypted_key_password=None,
        server=False,
    )
    return provider_dir, consumer_dir


def _start_provider(
    config: SDCriTestbedConfig,
    provider_tls_dir: Path,
    password: str,
    log_path: Path,
) -> tuple[subprocess.Popen[str], Any]:
    classpath = config.classpath_path.read_text(encoding="utf-8").strip()
    command = [
        str(config.java_path),
        "-cp",
        classpath,
        "com.example.provider1.Provider",
        "--address",
        config.local_ip,
        "--epr",
        config.provider_epr,
        "--userkey",
        str(provider_tls_dir / "userkey.pem"),
        "--usercert",
        str(provider_tls_dir / "usercert.pem"),
        "--cacert",
        str(provider_tls_dir / "cacert.pem"),
        "--userkey_password",
        password,
        "--report_interval",
        "60000",
        "--waveform_interval",
        "60000",
    ]
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=creation_flags,
    )
    return process, log_handle


def _stop_provider(process: subprocess.Popen[str], log_handle: Any) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    log_handle.close()


def run_sdcri_testbed(config: SDCriTestbedConfig) -> dict[str, Any]:
    """Run a TLS-protected cross-stack SDCri-to-gateway read-path experiment."""

    if config.repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    if not config.java_path.is_file():
        raise FileNotFoundError(f"Java executable not found: {config.java_path}")
    if not config.classpath_path.is_file():
        raise FileNotFoundError(f"SDCri runtime classpath not found: {config.classpath_path}")

    mapping = load_mapping(config.mapping_path)
    password = "sdcri-cross-stack"
    from sdc11073.certloader import mk_ssl_contexts_from_folder
    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.wsdiscovery import Service, WSDiscovery

    with tempfile.TemporaryDirectory(prefix="sdc-sdcri-cross-stack-") as tmp_dir:
        temp_root = Path(tmp_dir)
        provider_tls_dir, consumer_tls_dir = _write_mutual_tls_material(
            temp_root / "tls", config.local_ip, password.encode("utf-8")
        )
        provider_log = temp_root / "sdcri-provider.log"
        audit_path = temp_root / "gateway-consumer-audit.jsonl"
        provider_process: subprocess.Popen[str] | None = None
        provider_log_handle: Any | None = None
        services: list[Any] = []
        discovery_attempts = 0
        discovery_latencies: list[float] = []
        ws_discovery_succeeded = False
        directed_service_fallback = False

        try:
            with WSDiscovery(config.local_ip) as discovery:
                provider_process, provider_log_handle = _start_provider(
                    config, provider_tls_dir, password, provider_log
                )
                startup_deadline = time.monotonic() + config.startup_timeout_s
                provider_ready = False
                provider_log_text = ""
                while time.monotonic() < startup_deadline and not services and not provider_ready:
                    if provider_process.poll() is not None:
                        raise RuntimeError(
                            "SDCri provider exited during startup: "
                            + provider_log.read_text(encoding="utf-8", errors="replace")
                        )
                    discovery_attempts += 1
                    start = time.monotonic()
                    found = discovery.search_services(
                        types=SdcV1Definitions.MedicalDeviceTypesFilter,
                        timeout=config.discovery_timeout_s,
                    )
                    discovery_latencies.append((time.monotonic() - start) * 1000.0)
                    services = [service for service in found if service.epr == config.provider_epr]
                    ws_discovery_succeeded = bool(services)
                    provider_log_text = provider_log.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    provider_ready = (
                        f"Device {config.provider_epr} (Provider Example Unit) is running"
                        in provider_log_text
                    )

                if not services:
                    if not provider_ready:
                        raise TimeoutError(
                            "SDCri provider did not become ready within the startup window. "
                            "Provider log: "
                            + provider_log_text
                        )
                    ports = re.findall(
                        rf"\{{{re.escape(config.local_ip)}:(\d+)\}}", provider_log_text
                    )
                    if not ports:
                        raise RuntimeError(
                            "SDCri became ready, but its HTTPS port could not be read from the log. "
                            "Provider log: "
                            + provider_log_text
                        )
                    provider_path = config.provider_epr.removeprefix("urn:uuid:")
                    directed_xaddr = f"https://{config.local_ip}:{ports[-1]}/{provider_path}"
                    services = [
                        Service(
                            types=list(SdcV1Definitions.MedicalDeviceTypesFilter),
                            scopes=None,
                            x_addrs=[directed_xaddr],
                            epr=config.provider_epr,
                            instance_id="1",
                        )
                    ]
                    directed_service_fallback = True

                ssl_contexts = mk_ssl_contexts_from_folder(consumer_tls_dir)
                consumer = Sdc11073Consumer(
                    discovery_timeout_s=config.discovery_timeout_s,
                    provider_whitelist=[config.provider_epr],
                    local_ip=config.local_ip,
                    max_devices=1,
                    recorder=JsonlRecorder(audit_path),
                    ssl_context_container=ssl_contexts,
                )
                snapshot_latencies: list[float] = []
                snapshot_successes = 0
                resource_reads_attempted = 0
                resource_reads_succeeded = 0
                representative_snapshot: Any | None = None
                representative_registry: ResourceRegistry | None = None

                for _ in range(config.repetitions):
                    start = time.monotonic()
                    snapshots = consumer.get_snapshots_from_services(services[:1])
                    snapshot_latencies.append((time.monotonic() - start) * 1000.0)
                    if not snapshots:
                        continue
                    snapshot_successes += 1
                    representative_snapshot = snapshots[0]
                    registry = ResourceRegistry(devices=snapshots, mapping=mapping)
                    representative_registry = registry
                    for uri in registry.list_resource_uris():
                        resource_reads_attempted += 1
                        registry.read(uri)
                        resource_reads_succeeded += 1

                if representative_snapshot is None or representative_registry is None:
                    audit = audit_path.read_text(encoding="utf-8", errors="replace")
                    raise RuntimeError(f"No MDIB snapshot could be read from SDCri. Audit: {audit}")

                _, untrusted_consumer_tls_dir = _write_mutual_tls_material(
                    temp_root / "untrusted-tls",
                    config.local_ip,
                    password.encode("utf-8"),
                )
                untrusted_consumer = Sdc11073Consumer(
                    provider_whitelist=[config.provider_epr],
                    local_ip=config.local_ip,
                    max_devices=1,
                    ssl_context_container=mk_ssl_contexts_from_folder(
                        untrusted_consumer_tls_dir
                    ),
                )
                untrusted_client_rejected = not untrusted_consumer.get_snapshots_from_services(
                    services[:1]
                )

                mapped_metrics = representative_registry.mapper.map_device_metrics(
                    representative_snapshot
                )
                raw_summary = representative_snapshot.raw_mdib
                service = services[0]
                report = {
                    "status": "ok",
                    "scope": "local-host software cross-stack experiment; no physical medical device",
                    "provider": {
                        "stack": "SDCri",
                        "language": "Java",
                        "version": config.sdcri_version,
                        "git_commit": config.sdcri_commit,
                        "epr": config.provider_epr,
                    },
                    "gateway_consumer": {
                        "stack": "sdc11073",
                        "language": "Python",
                        "version": _sdc11073_version(),
                    },
                    "transport_security": {
                        "tls": True,
                        "mutual_authentication": True,
                        "separate_provider_and_consumer_identities": True,
                        "ephemeral_test_ca": True,
                        "untrusted_client_negative_control_rejected": untrusted_client_rejected,
                    },
                    "discovery": {
                        "success": ws_discovery_succeeded,
                        "attempts": discovery_attempts,
                        "directed_service_fallback": directed_service_fallback,
                        "epr_matched_exactly": service.epr == config.provider_epr,
                        "advertised_xaddrs": list(service.x_addrs),
                        "note": (
                            "WS-Discovery was attempted while the independent provider started. "
                            "If same-host multicast was not delivered, the provider's logged HTTPS "
                            "XAddr was used and the discovery miss remains visible."
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
                        "context_state_count": len(
                            representative_snapshot.context.raw["context_states"]
                        ),
                        "latency": _summarize_latency(snapshot_latencies),
                    },
                    "mcp_resources": {
                        "advertised_count": len(representative_registry.list_resource_uris()),
                        "reads_succeeded": resource_reads_succeeded,
                        "reads_attempted": resource_reads_attempted,
                        "success_rate": resource_reads_succeeded / resource_reads_attempted,
                    },
                    "mapping": {
                        "mapped_metrics": sum(metric.mapped for metric in mapped_metrics),
                        "total_metrics": len(mapped_metrics),
                        "source_sha256": mapping.source_sha256,
                    },
                    "unsupported": {
                        "descriptor_types": raw_summary["unsupported_descriptor_types"],
                        "state_types": raw_summary["unsupported_state_types"],
                    },
                    "protocol_elements": {
                        "independent_provider_and_consumer_implementations": True,
                        "ws_discovery_attempted": True,
                        "ws_discovery_succeeded": ws_discovery_succeeded,
                        "directed_xaddr_fallback": directed_service_fallback,
                        "https_soap_getmdib": True,
                        "consumer_mdib_initialization": True,
                        "read_only_sdc_to_mcp_resource_path": True,
                        "subscriptions_and_periodic_reports": False,
                        "physical_device_or_clinical_network": False,
                        "setservice_or_activateoperation_invocation": False,
                    },
                    "claim_boundary": (
                        "This validates local software interoperability across independent Java and "
                        "Python SDC stacks. It does not validate a physical device, clinical network, "
                        "continuous report handling, or regulatory safety."
                    ),
                }
        finally:
            if provider_process is not None and provider_log_handle is not None:
                _stop_provider(provider_process, provider_log_handle)

    config.output_path.parent.mkdir(parents=True, exist_ok=True)
    config.output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _sdc11073_version() -> str:
    import sdc11073

    return str(getattr(sdc11073, "__version__", "unknown"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the gateway consumer against an independent Java SDCri provider."
    )
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--classpath", type=Path, required=True)
    parser.add_argument("--local-ip", required=True)
    parser.add_argument("--mie", type=Path, default=Path("config/sdc_mie.yaml"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/revision/development/sdcri-cross-stack.json"),
    )
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--discovery-timeout-s", type=float, default=2.0)
    args = parser.parse_args()
    report = run_sdcri_testbed(
        SDCriTestbedConfig(
            java_path=args.java,
            classpath_path=args.classpath,
            mapping_path=args.mie,
            output_path=args.output,
            local_ip=args.local_ip,
            repetitions=args.repetitions,
            discovery_timeout_s=args.discovery_timeout_s,
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":  # pragma: no cover - integration entry point
    main()
