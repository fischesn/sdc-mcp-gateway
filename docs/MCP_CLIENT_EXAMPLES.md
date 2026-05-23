# MCP Client Examples

This document explains the example MCP clients included with the SDC-MCP Gateway artifact.

The examples use the **stdio MCP transport**. This means that the Python client starts
`sdc-mcp-gateway serve` as a subprocess and communicates with it over standard
input/output. This is the local MCP integration mode supported by the current artifact.
A network server transport is intentionally out of scope for v0.10.x and planned for a
future v2 line.

## Requirements

Install the package with MCP support:

```powershell
python -m pip install -e ".[mcp]"
```

or install all optional dependencies:

```powershell
python -m pip install -e ".[all]"
```

Run examples from the repository root.

## Example 1: Read MCP resources

```powershell
python examples\mcp_client_read_resources.py
```

This starts the gateway with `config/gateway.simulated.example.yaml`, lists all exposed
MCP resources, reads `sdc://health`, reads `sdc://devices`, and reads the first available
metrics resource.

Optional arguments:

```powershell
python examples\mcp_client_read_resources.py `
  --config config\gateway.simulated.high-airway-pressure.example.yaml `
  --mie config\sdc_mie.yaml `
  --resource sdc://devices/sim-ventilator-1/metrics
```

## Example 2: Call a dry-run MCP tool

```powershell
python examples\mcp_client_call_dryrun_tool.py
```

This starts the gateway with `config/gateway.simulated.dryrun.example.yaml`, lists exposed
MCP tools, and calls:

```text
prepare_set_fio2(device_id="sim-ventilator-1", value=45.0)
```

The expected result is `accepted_dry_run` with `executed=false` and
`write_operations_allowed=false`.

To test an out-of-range proposal:

```powershell
python examples\mcp_client_call_dryrun_tool.py --fio2 150
```

The expected result is `rejected` with `reason=value_out_of_range`.

## Example 3: Deterministic agent demo

```powershell
python examples\agent_mcp_client_demo.py `
  --question "Is there an active alarm and which device is affected?"
```

This is not a generative LLM. It is a small deterministic agent program showing how a
custom Python agent can use an MCP `ClientSession` to inspect resources.

The same demo can also trigger a dry-run tool call when the question contains an FiO2
proposal:

```powershell
python examples\agent_mcp_client_demo.py `
  --config config\gateway.simulated.dryrun.example.yaml `
  --question "Prepare a dry-run proposal to set FiO2 to 45 percent."
```

The program calls `prepare_set_fio2` through MCP and prints the dry-run tool result.

## Integration pattern

The essential pattern is:

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=[
        "-m",
        "sdc_mcp_gateway.main",
        "serve",
        "--config",
        "config/gateway.simulated.example.yaml",
        "--mie",
        "config/sdc_mie.yaml",
    ],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        resources = await session.list_resources()
        health = await session.read_resource("sdc://health")
```

For dry-run tools, use the dry-run gateway configuration and call `session.list_tools()`
and `session.call_tool(...)`.

## Safety note

The examples do not execute SDC device operations. Dry-run tool calls validate proposals
and return structured results, but they must report `executed=false`.
