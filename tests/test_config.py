from sdc_mcp_gateway.config import GatewayConfig


def test_default_sdc_config_contains_v02_network_fields() -> None:
    config = GatewayConfig()
    assert config.sdc.local_ip == "127.0.0.1"
    assert config.sdc.max_devices is None
