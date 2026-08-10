from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from sdc_mcp_gateway.sdc.sdcri_testbed import SDCriTestbedConfig, run_sdcri_testbed
from sdc_mcp_gateway.sdc.consumer import Sdc11073Consumer


def test_sdcri_testbed_rejects_missing_java(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Java executable not found"):
        run_sdcri_testbed(
            SDCriTestbedConfig(
                java_path=tmp_path / "missing-java",
                classpath_path=tmp_path / "missing-classpath",
                mapping_path=Path("config/sdc_mie.yaml"),
                output_path=tmp_path / "report.json",
                local_ip="127.0.0.1",
                repetitions=1,
            )
        )


def test_sdcri_testbed_rejects_zero_repetitions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="repetitions must be at least 1"):
        run_sdcri_testbed(
            SDCriTestbedConfig(
                java_path=tmp_path / "java",
                classpath_path=tmp_path / "classpath",
                mapping_path=Path("config/sdc_mie.yaml"),
                output_path=tmp_path / "report.json",
                local_ip="127.0.0.1",
                repetitions=0,
            )
        )


def test_real_consumer_suppresses_every_subscription_action() -> None:
    captured: dict[str, Any] = {}

    class FakeClient:
        def start_all(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    class FakeConsumerFactory:
        @staticmethod
        def from_wsd_service(service: Any, ssl_context_container: Any) -> FakeClient:
            return FakeClient()

    class FakeMdib:
        def __init__(self, client: FakeClient) -> None:
            self.client = client

        def init_mdib(self) -> None:
            captured["mdib_initialized"] = True

    consumer = Sdc11073Consumer()
    consumer._imports = lambda: {  # type: ignore[method-assign]
        "SdcConsumer": FakeConsumerFactory,
        "ConsumerMdib": FakeMdib,
        "all_actions": {"action-a", "action-b"},
    }

    consumer._connect_and_init_mdib(object())

    assert captured["not_subscribed_actions"] == {"action-a", "action-b"}
    assert captured["mdib_initialized"] is True
