import pytest
from pydantic import ValidationError

from sdc_mcp_gateway.config import GatewayConfig


def test_default_sdc_config_contains_v02_network_fields() -> None:
    config = GatewayConfig()
    assert config.sdc.local_ip == "127.0.0.1"
    assert config.sdc.max_devices is None


def test_write_enabled_configuration_fails_closed() -> None:
    with pytest.raises(ValidationError, match="allow_write_operations must remain false"):
        GatewayConfig.model_validate({"gateway": {"allow_write_operations": True}})


@pytest.mark.parametrize(
    ("mode", "allow_tools"),
    [("read-only", True), ("dry-run-tools", False), ("write-enabled", False)],
)
def test_inconsistent_or_unsupported_gateway_modes_fail_closed(
    mode: str,
    allow_tools: bool,
) -> None:
    with pytest.raises(ValidationError):
        GatewayConfig.model_validate(
            {"gateway": {"mode": mode, "allow_tools": allow_tools}}
        )
