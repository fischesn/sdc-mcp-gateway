from __future__ import annotations

import argparse
import json
import random
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.sdc.protocol_testbed import _sdc11073_version, _write_ephemeral_tls_material
from sdc_mcp_gateway.sdc.reference_provider import PROFILE_VALUES


@dataclass(frozen=True)
class ContainerProtocolTestbedConfig:
    project_root: Path
    mapping_path: Path
    output_path: Path
    profiles: tuple[str, ...] = tuple(PROFILE_VALUES)
    repetitions: int = 5
    discovery_timeout_s: float = 2.0
    startup_timeout_s: float = 30.0
    image: str = "sdc-mcp-gateway-protocol-testbed:local"
    build_image: bool = True
    log_level: str = "WARNING"


def _run(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and completed.returncode != 0:
        rendered = " ".join(command)
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {rendered}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def _wait_for_file(path: Path, timeout_s: float, provider_name: str, cwd: Path) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.is_file():
            return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
        status = _run(["docker", "inspect", "-f", "{{.State.Running}}", provider_name], cwd=cwd, check=False)
        if status.returncode != 0 or status.stdout.strip().lower() != "true":
            logs = _run(["docker", "logs", provider_name], cwd=cwd, check=False)
            raise RuntimeError(
                f"Provider container exited before readiness: {logs.stdout}{logs.stderr}"
            )
        time.sleep(0.1)
    logs = _run(["docker", "logs", provider_name], cwd=cwd, check=False)
    raise TimeoutError(
        f"Provider container did not become ready within {timeout_s} seconds: "
        f"{logs.stdout}{logs.stderr}"
    )


def _create_network(cwd: Path, network_name: str) -> tuple[str, str, str, str]:
    last_error = ""
    for _ in range(12):
        octet = random.randint(32, 223)
        subnet = f"172.28.{octet}.0/24"
        provider_ip = f"172.28.{octet}.10"
        consumer_ip = f"172.28.{octet}.20"
        result = _run(
            ["docker", "network", "create", "--driver", "bridge", "--subnet", subnet, network_name],
            cwd=cwd,
            check=False,
        )
        if result.returncode == 0:
            return network_name, subnet, provider_ip, consumer_ip
        last_error = result.stderr or result.stdout
    raise RuntimeError(f"Could not allocate an isolated Docker subnet: {last_error}")


def _container_volume(path: Path) -> str:
    return f"{path.resolve()}:/evidence"


def run_container_protocol_testbed(config: ContainerProtocolTestbedConfig) -> dict[str, Any]:
    if config.repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    unknown = sorted(set(config.profiles) - set(PROFILE_VALUES))
    if unknown:
        raise ValueError(f"Unknown profiles: {unknown}")
    project_root = config.project_root.resolve()
    dockerfile = project_root / "docker" / "sdc-testbed.Dockerfile"
    if config.build_image:
        _run(
            [
                "docker",
                "build",
                "--file",
                str(dockerfile),
                "--tag",
                config.image,
                str(project_root),
            ],
            cwd=project_root,
        )

    run_token = uuid.uuid4().hex[:10]
    network_name = f"sdc-mcp-eval-{run_token}"
    run_root = project_root / "tmp" / f"container-protocol-{run_token}"
    run_root.mkdir(parents=True, exist_ok=False)
    network_created = False
    profile_reports: list[dict[str, Any]] = []
    try:
        _, subnet, provider_ip, consumer_ip = _create_network(project_root, network_name)
        network_created = True
        for profile in config.profiles:
            profile_root = run_root / profile
            profile_root.mkdir(parents=True)
            ready_file = profile_root / "ready.json"
            tls_dir = profile_root / "tls"
            _write_ephemeral_tls_material(tls_dir, provider_ip)
            provider_name = f"sdc-provider-{profile}-{run_token}"
            provider_command = [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                provider_name,
                "--network",
                network_name,
                "--ip",
                provider_ip,
                "--volume",
                _container_volume(profile_root),
                config.image,
                "sdc_mcp_gateway.sdc.reference_provider",
                "--profile",
                profile,
                "--local-ip",
                provider_ip,
                "--ready-file",
                "/evidence/ready.json",
                "--tls-dir",
                "/evidence/tls",
                "--log-level",
                config.log_level,
            ]
            _run(provider_command, cwd=project_root)
            try:
                _wait_for_file(ready_file, config.startup_timeout_s, provider_name, project_root)
                consumer_output = profile_root / "result.json"
                consumer_name = f"sdc-consumer-{profile}-{run_token}"
                consumer_command = [
                    "docker",
                    "run",
                    "--rm",
                    "--name",
                    consumer_name,
                    "--network",
                    network_name,
                    "--ip",
                    consumer_ip,
                    "--volume",
                    _container_volume(profile_root),
                    config.image,
                    "sdc_mcp_gateway.sdc.container_protocol_client",
                    "--local-ip",
                    consumer_ip,
                    "--ready-file",
                    "/evidence/ready.json",
                    "--tls-dir",
                    "/evidence/tls",
                    "--mapping",
                    f"/workspace/{config.mapping_path.as_posix()}",
                    "--output",
                    "/evidence/result.json",
                    "--repetitions",
                    str(config.repetitions),
                    "--discovery-timeout-s",
                    str(config.discovery_timeout_s),
                    "--log-level",
                    config.log_level,
                ]
                consumer_run = _run(consumer_command, cwd=project_root, check=False)
                (profile_root / "consumer.log").write_text(
                    consumer_run.stdout + consumer_run.stderr,
                    encoding="utf-8",
                )
                if not consumer_output.is_file():
                    raise RuntimeError(
                        f"Consumer container produced no report for {profile}: "
                        f"stdout={consumer_run.stdout} stderr={consumer_run.stderr}"
                    )
                profile_report = json.loads(consumer_output.read_text(encoding="utf-8"))
                if consumer_run.returncode != 0 or profile_report.get("status") != "ok":
                    raise RuntimeError(
                        f"Container protocol evaluation failed for {profile}: "
                        f"{json.dumps(profile_report, sort_keys=True)}"
                    )
                profile_reports.append(profile_report)
            finally:
                provider_logs = _run(
                    ["docker", "logs", provider_name], cwd=project_root, check=False
                )
                (profile_root / "provider.log").write_text(
                    provider_logs.stdout + provider_logs.stderr,
                    encoding="utf-8",
                )
                _run(["docker", "stop", "--time", "5", provider_name], cwd=project_root, check=False)

        mapping = load_mapping(config.mapping_path)
        report = {
            "status": "ok",
            "scope": (
                "software-reference provider and consumer in separate Linux containers on an "
                "isolated bridge network; no physical medical device"
            ),
            "network_topology": {
                "runtime": "Docker",
                "driver": "bridge",
                "subnet": subnet,
                "separate_network_namespaces": True,
                "provider_consumer_distinct_ipv4": True,
            },
            "library": {"name": "sdc11073", "version": _sdc11073_version()},
            "mapping_artifact": {
                "schema_version": mapping.schema_version,
                "version": mapping.version,
                "source_sha256": mapping.source_sha256,
            },
            "profiles": profile_reports,
            "totals": {
                "discovery_successes": sum(row["discovery"]["successes"] for row in profile_reports),
                "discovery_attempts": sum(row["discovery"]["attempts"] for row in profile_reports),
                "directed_xaddr_fallbacks": 0,
                "snapshot_successes": sum(row["snapshot"]["successes"] for row in profile_reports),
                "snapshot_attempts": sum(row["snapshot"]["attempts"] for row in profile_reports),
                "mcp_reads_succeeded": sum(row["mcp_resources"]["reads_succeeded"] for row in profile_reports),
                "mcp_reads_attempted": sum(row["mcp_resources"]["reads_attempted"] for row in profile_reports),
                "mapped_metrics": sum(row["mapping"]["mapped_metrics"] for row in profile_reports),
                "total_metrics": sum(row["mapping"]["total_metrics"] for row in profile_reports),
            },
            "protocol_elements": {
                "ws_discovery": True,
                "directed_xaddr_fallback": False,
                "mutual_tls": True,
                "https_soap_getmdib": True,
                "xml_mdib_processing": True,
                "read_only_sdc_to_mcp_resource_path": True,
                "setservice_or_activateoperation_invocation": False,
                "physical_device_or_clinical_network": False,
            },
            "claim_boundary": (
                "This validates the same-stack read path and multicast discovery across isolated "
                "software network endpoints. It is not physical-device, clinical-network, or "
                "multi-vendor evidence."
            ),
        }
        config.output_path.parent.mkdir(parents=True, exist_ok=True)
        config.output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        return report
    finally:
        if network_created:
            _run(["docker", "network", "rm", network_name], cwd=project_root, check=False)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate same-stack SDC discovery across isolated Linux containers."
    )
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--mapping", type=Path, default=Path("config/sdc_mie.yaml"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/revision/development/container-protocol-testbed.json"),
    )
    parser.add_argument("--profile", action="append", choices=sorted(PROFILE_VALUES))
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--discovery-timeout-s", type=float, default=2.0)
    parser.add_argument("--image", default="sdc-mcp-gateway-protocol-testbed:local")
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING"), default="WARNING")
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    report = run_container_protocol_testbed(
        ContainerProtocolTestbedConfig(
            project_root=args.project_root,
            mapping_path=args.mapping,
            output_path=args.output,
            profiles=tuple(args.profile) if args.profile else tuple(PROFILE_VALUES),
            repetitions=args.repetitions,
            discovery_timeout_s=args.discovery_timeout_s,
            image=args.image,
            build_image=not args.no_build,
            log_level=args.log_level,
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
