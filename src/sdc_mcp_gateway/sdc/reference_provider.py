from __future__ import annotations

import argparse
import json
import signal
import threading
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any


PROFILE_VALUES: dict[str, dict[str, Decimal]] = {
    "monitor": {
        "metric.hr": Decimal("72"),
        "metric.spo2": Decimal("98"),
        "metric.rr": Decimal("16"),
        "metric.monitor.unknown": Decimal("1"),
    },
    "ventilator": {
        "metric.fio2": Decimal("40"),
        "metric.peep": Decimal("8"),
        "metric.airway_pressure": Decimal("18"),
        "metric.ventilator.unknown": Decimal("450"),
    },
    "heterogeneous": {
        "metric.hr": Decimal("65"),
        "metric.unknown.numeric": Decimal("12.5"),
        "metric.unknown.vendor": Decimal("7"),
    },
}


def profile_mdib_path(profile: str) -> Path:
    if profile not in PROFILE_VALUES:
        raise ValueError(f"Unknown reference-provider profile: {profile}")
    return Path(__file__).resolve().parent / "mdib_profiles" / f"{profile}.xml"


def _initialize_metric_values(mdib: Any, profile: str) -> None:
    values = PROFILE_VALUES[profile]
    descriptors = [
        descriptor
        for descriptor in mdib.descriptions.objects
        if "MetricDescriptor" in type(descriptor).__name__
    ]
    with mdib.metric_state_transaction() as transaction:
        for descriptor in descriptors:
            state = transaction.get_state(descriptor.Handle)
            state.mk_metric_value()
            state.MetricValue.Value = values[descriptor.Handle]


def run_reference_provider(
    profile: str,
    *,
    local_ip: str = "127.0.0.1",
    ready_file: Path | None = None,
    tls_dir: Path | None = None,
) -> None:
    """Run a deterministic software SDC provider until it receives a stop signal."""

    from sdc11073.definitions_sdc import SdcV1Definitions
    from sdc11073.certloader import mk_ssl_contexts_from_folder
    from sdc11073.mdib import ProviderMdib
    from sdc11073.provider import SdcProvider
    from sdc11073.wsdiscovery import WSDiscovery
    from sdc11073.xml_types.dpws_types import ThisDeviceType, ThisModelType

    mdib_path = profile_mdib_path(profile)
    mdib = ProviderMdib.from_mdib_file(str(mdib_path), SdcV1Definitions)
    _initialize_metric_values(mdib, profile)
    profile_uuid = uuid.uuid5(uuid.UUID("8f303b40-0254-4bd3-a8f4-59d995e55f81"), profile)
    epr = f"urn:uuid:{profile_uuid}"
    this_model = ThisModelType(
        manufacturer="Anonymous software reference provider",
        model_name=f"WP3 {profile} profile",
        model_number="1",
    )
    this_device = ThisDeviceType(
        friendly_name=f"WP3 {profile} provider",
        firmware_version="artifact-0.11",
        serial_number=f"wp3-{profile}",
    )
    stop_event = threading.Event()
    ssl_context_container = mk_ssl_contexts_from_folder(tls_dir) if tls_dir is not None else None

    def request_stop(_signum: int, _frame: object) -> None:
        stop_event.set()

    for signal_name in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, signal_name, None)
        if signum is not None:
            signal.signal(signum, request_stop)

    with WSDiscovery(local_ip) as discovery:
        provider = SdcProvider(
            ws_discovery=discovery,
            this_model=this_model,
            this_device=this_device,
            device_mdib_container=mdib,
            epr=epr,
            ssl_context_container=ssl_context_container,
        )
        provider.start_all(start_rtsample_loop=False)
        ready = {
            "status": "ready",
            "profile": profile,
            "epr": epr,
            "local_ip": local_ip,
            "mdib": mdib_path.name,
            "pid": __import__("os").getpid(),
            "x_addrs": provider.get_xaddrs(),
        }
        if ready_file is not None:
            ready_file.write_text(json.dumps(ready, sort_keys=True), encoding="utf-8")
        print(json.dumps(ready, sort_keys=True), flush=True)
        try:
            stop_event.wait()
        finally:
            provider.stop_all()


def main() -> None:
    parser = argparse.ArgumentParser(description="WP3 software SDC reference provider")
    parser.add_argument("--profile", choices=sorted(PROFILE_VALUES), required=True)
    parser.add_argument("--local-ip", default="127.0.0.1")
    parser.add_argument("--ready-file", type=Path)
    parser.add_argument("--tls-dir", type=Path)
    args = parser.parse_args()
    run_reference_provider(
        args.profile,
        local_ip=args.local_ip,
        ready_file=args.ready_file,
        tls_dir=args.tls_dir,
    )


if __name__ == "__main__":
    main()
