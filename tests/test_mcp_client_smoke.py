from pathlib import Path

import pytest
from typer.testing import CliRunner

from sdc_mcp_gateway.main import app


runner = CliRunner()


def test_cli_mcp_client_smoke_test_simulated_config() -> None:
    pytest.importorskip("mcp")
    result = runner.invoke(
        app,
        [
            "mcp-client-smoke-test",
            "--config",
            "config/gateway.simulated.example.yaml",
            "--mie",
            "config/sdc_mie.yaml",
            "--timeout-s",
            "10",
        ],
    )
    assert result.exit_code == 0, result.output
    assert '"status": "ok"' in result.output
    assert '"mcp_list_resources"' in result.output
    assert '"mcp_read_health"' in result.output
    assert '"mcp_no_tools_exported"' in result.output
    assert '"tool_count": 0' in result.output
