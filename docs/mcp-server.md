# Using the MCP Resource Server

The gateway can now be used in two modes:

1. **CLI inspection mode**, which prints JSON to the terminal.
2. **MCP server mode**, which exposes the same resources to an MCP client.

The implementation is read-only. It exports MCP resources only; it does not export
MCP tools.

## Verify the resource surface first

Before starting an MCP client, check the resource catalogue:

```bash
sdc-mcp-gateway list-resources --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Read a single resource:

```bash
sdc-mcp-gateway read-resource sdc://devices/sim-monitor-1/metrics --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

If these commands work, the adapter, mapping, and resource registry are functioning.

## Start the server

Install the optional MCP dependency:

```bash
python -m pip install -e ".[mcp]"
```

Start the server:

```bash
sdc-mcp-gateway serve --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

The default transport is stdio. Keep the terminal open while the MCP client is
connected.

## Resource catalogue

The `sdc://resources` resource returns a machine-readable list of currently
available resources, including per-device resource URIs. This is useful because
real SDC networks may expose different device identifiers than the simulated
provider.

## Real SDC networks

The same command can be used with a local real-SDC configuration:

```bash
sdc-mcp-gateway serve --config config/gateway.local.yaml --mie config/sdc_mie.yaml
```

`gateway.local.yaml` must remain local and must not be committed. The current
prototype should still be run in read-only mode when connected to real devices.

## MCP smoke test

Version v0.4.1 adds a smoke-test command that exercises the same read-only
resource surface used by the MCP server without opening a long-running stdio
session:

```bash
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

The command checks that:

- the registry can be built from the selected adapter,
- all advertised resources can be read,
- `sdc://health` reports read-only mode,
- the health resource count matches the catalogue,
- the resource catalogue is readable,
- a FastMCP server can be constructed when the optional MCP SDK is installed.

If the MCP SDK is not installed, the command still succeeds by default but reports
`mcp_sdk_available: false`. To make the MCP SDK mandatory, use:

```bash
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --require-mcp-sdk
```
