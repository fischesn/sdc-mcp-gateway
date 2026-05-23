from __future__ import annotations

import py_compile
from pathlib import Path


def test_example_mcp_clients_compile() -> None:
    for path in [
        Path("examples/mcp_client_common.py"),
        Path("examples/mcp_client_read_resources.py"),
        Path("examples/mcp_client_call_dryrun_tool.py"),
        Path("examples/agent_mcp_client_demo.py"),
    ]:
        py_compile.compile(str(path), doraise=True)


def test_mcp_client_examples_documentation_exists() -> None:
    assert Path("docs/MCP_CLIENT_EXAMPLES.md").exists()
