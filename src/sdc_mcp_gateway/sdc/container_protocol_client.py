from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from typing import Any

from sdc_mcp_gateway.experiments.recorder import JsonlRecorder
from sdc_mcp_gateway.mapping.mie_loader import load_mapping
from sdc_mcp_gateway.mcp.resources import ResourceRegistry
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer
from sdc_mcp_gateway.sdc.protocol_testbed import _summarize_latency


def evaluate_container_provider(
    *,
    local_ip: str,
    ready_file: Path,
    tls_dir: Path,
    mapping_path: Path,
    output_path: Path,
    repetitions: int,
    discovery_timeout_s: float,
) -> dict[str, Any]:
    """Discover and read one provider from an isolated consumer container."""

    if repetitions < 1:
        raise ValueError("repetitions must be at least 1")
    provider = json.loads(ready_file.read_text(encoding="utf-8"))
    mapping = load_mapping(mapping_path)

    from sdc11073.certloader import mk_ssl_contexts_from_folder
    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.wsdiscovery import WSDiscovery

    audit_path = output_path.with_suffix(".audit.jsonl")
    consumer = Sdc11073Consumer(
        discovery_timeout_s=discovery_timeout_s,
        provider_whitelist=[provider["epr"]],
        local_ip=local_ip,
        max_devices=1,
        recorder=JsonlRecorder(audit_path),
        ssl_context_container=mk_ssl_contexts_from_folder(tls_dir),
    )
    discovery_latencies: list[float] = []
    snapshot_latencies: list[float] = []
    discovery_successes = 0
    snapshot_successes = 0
    resource_reads_attempted = 0
    resource_reads_succeeded = 0
    representative_snapshot: Any | None = None
    representative_registry: ResourceRegistry | None = None

    with WSDiscovery(local_ip) as discovery:
        for _ in range(repetitions):
            discovery_start = time.monotonic()
            services = list(
                discovery.search_services(
                    types=SdcV1Definitions.MedicalDeviceTypesFilter,
                    timeout=discovery_timeout_s,
                )
            )
            discovery_latencies.append((time.monotonic() - discovery_start) * 1000.0)
            accepted = [service for service in services if service.epr == provider["epr"]]
            if not accepted:
                continue
            discovery_successes += 1

            snapshot_start = time.monotonic()
            snapshots = consumer.get_snapshots_from_services(accepted[:1])
            snapshot_latencies.append((time.monotonic() - snapshot_start) * 1000.0)
            if not snapshots:
                continue
            snapshot_successes += 1
            representative_snapshot = snapshots[0]
            representative_registry = ResourceRegistry(devices=snapshots, mapping=mapping)
            for uri in representative_registry.list_resource_uris():
                resource_reads_attempted += 1
                representative_registry.read(uri)
                resource_reads_succeeded += 1

    mapped_metrics = (
        representative_registry.mapper.map_device_metrics(representative_snapshot)
        if representative_registry is not None and representative_snapshot is not None
        else []
    )
    raw_mdib = representative_snapshot.raw_mdib if representative_snapshot is not None else {}
    status = "ok" if (
        discovery_successes == repetitions
        and snapshot_successes == repetitions
        and resource_reads_attempted > 0
        and resource_reads_succeeded == resource_reads_attempted
    ) else "failed"
    report: dict[str, Any] = {
        "status": status,
        "profile": provider["profile"],
        "provider": {
            "epr": provider["epr"],
            "mdib": provider["mdib"],
            "stack": "sdc11073",
            "language": "Python",
            "container_ip": provider["local_ip"],
        },
        "consumer": {
            "stack": "sdc11073",
            "language": "Python",
            "container_ip": local_ip,
        },
        "discovery": {
            "successes": discovery_successes,
            "attempts": repetitions,
            "success_rate": discovery_successes / repetitions,
            "directed_xaddr_fallbacks": 0,
            "latency": _summarize_latency(discovery_latencies),
        },
        "snapshot": {
            "successes": snapshot_successes,
            "attempts": repetitions,
            "success_rate": snapshot_successes / repetitions,
            "latency": _summarize_latency(snapshot_latencies) if snapshot_latencies else None,
            "descriptor_count": raw_mdib.get("descriptor_count"),
            "state_count": raw_mdib.get("state_count"),
            "metric_count": len(representative_snapshot.metrics)
            if representative_snapshot is not None
            else 0,
            "alarm_state_count": len(representative_snapshot.alarms)
            if representative_snapshot is not None
            else 0,
        },
        "mcp_resources": {
            "advertised_count": len(representative_registry.list_resource_uris())
            if representative_registry is not None
            else 0,
            "reads_succeeded": resource_reads_succeeded,
            "reads_attempted": resource_reads_attempted,
            "success_rate": (
                resource_reads_succeeded / resource_reads_attempted
                if resource_reads_attempted
                else 0.0
            ),
        },
        "mapping": {
            "mapped_metrics": sum(metric.mapped for metric in mapped_metrics),
            "total_metrics": len(mapped_metrics),
            "source_sha256": mapping.source_sha256,
        },
        "unsupported": {
            "descriptor_types": raw_mdib.get("unsupported_descriptor_types", {}),
            "state_types": raw_mdib.get("unsupported_state_types", {}),
        },
        "claim_boundary": (
            "This is a container-network software-reference test without a physical device "
            "or clinical network. No directed XAddr fallback is permitted."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Container-isolated SDC protocol consumer")
    parser.add_argument("--local-ip", required=True)
    parser.add_argument("--ready-file", type=Path, required=True)
    parser.add_argument("--tls-dir", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    parser.add_argument("--discovery-timeout-s", type=float, default=2.0)
    parser.add_argument("--log-level", choices=("DEBUG", "INFO", "WARNING"), default="WARNING")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    report = evaluate_container_provider(
        local_ip=args.local_ip,
        ready_file=args.ready_file,
        tls_dir=args.tls_dir,
        mapping_path=args.mapping,
        output_path=args.output,
        repetitions=args.repetitions,
        discovery_timeout_s=args.discovery_timeout_s,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
