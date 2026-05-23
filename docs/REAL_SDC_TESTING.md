# Real SDC Network Testing

This document describes how to prepare the SDC-MCP Gateway for a first test in a real
IEEE 11073 SDC network, for example in a vendor-provided laboratory or VPN environment.

The current gateway is prepared for real SDC discovery and best-effort MDIB extraction
through the optional `sdc11073` adapter. However, the real-device path has not yet been
validated in the Dräger network. Treat the first run as an integration test.

## Important distinction

The command

```powershell
sdc-mcp-gateway serve
```

starts the MCP server. In the current v0.10.x artifact this is a **stdio MCP server**.
It is intended to be started by a local MCP client or agent process. It is not a
network-facing HTTP/SSE MCP server.

The intended real-SDC data path is:

```text
real SDC network
  -> sdc11073 adapter
  -> normalized gateway snapshot
  -> MCP resources
  -> local MCP stdio client / agent
```

It is not yet:

```text
remote MCP client over HTTP/TCP/SSE
  -> network-exposed MCP gateway
```

Network-facing MCP transport is planned for a later major version.

## Safety recommendation for first real-network tests

For first tests in a real SDC network, use a **read-only configuration**.

Do not enable dry-run tools for initial discovery and snapshot validation. Dry-run tools
still do not execute device operations, but separating the first real SDC resource tests
from tool exposure keeps the integration test easier to interpret.

Recommended initial mode:

```yaml
gateway:
  mode: "read-only"
  allow_tools: false
```

## Installation

Install the optional SDC adapter support, or install all extras:

```powershell
python -m pip install -e ".[sdc]"
```

or:

```powershell
python -m pip install -e ".[all]"
```

Then verify the command is available:

```powershell
sdc-mcp-gateway --help
```

## Create a local configuration

Do not edit or commit the example file directly. Create a local file:

```powershell
Copy-Item config\gateway.sdc11073.example.yaml config\gateway.local.yaml
```

`config/gateway.local.yaml` is ignored by Git and may contain local network settings.

## Configure the local SDC interface

In `config/gateway.local.yaml`, set the `local_ip` field to the IPv4 address of **your
own computer** on the SDC/VPN/lab-network interface.

This is not the IP address of the medical device.

Example:

```yaml
gateway:
  name: "sdc-mcp-gateway-local"
  mode: "read-only"
  allow_tools: false

sdc:
  adapter: "sdc11073"
  local_ip: "192.0.2.10"
  discovery_timeout_s: 5
  max_devices: 1
  provider_whitelist: []

mapping:
  version: "local"

logging:
  enabled: true
  directory: "data/logs"
```

Replace `192.0.2.10` with your actual VPN or lab-network interface address. The address
above is a documentation address.

On Windows, identify candidate IPv4 addresses with:

```powershell
ipconfig
```

Look for the adapter that belongs to the SDC VPN or the lab network.

## Step-by-step validation

### 1. Test SDC discovery

```powershell
sdc-mcp-gateway discover --config config\gateway.local.yaml
```

Expected outcome: one or more SDC provider identifiers are returned.

If no providers are found, do not continue with MCP server tests yet. First check the
network and discovery setup.

Common causes:

- wrong `local_ip`;
- VPN does not forward WS-Discovery/multicast;
- firewall blocks discovery traffic;
- provider is not in the same discovery segment;
- SDC security/TLS setup differs from the simple discovery path;
- the provider whitelist excludes all providers.

### 2. Test snapshot extraction

```powershell
sdc-mcp-gateway snapshot `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

Expected outcome: a normalized snapshot object is printed.

The real SDC path currently performs best-effort extraction from the provider's MDIB.
The exact available metrics, alarms, and context states depend on the provider and on
what the extractor can map.

### 3. List MCP resources derived from the real provider

```powershell
sdc-mcp-gateway list-resources `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

Expected outcome: static gateway resources plus provider-specific resources, for example:

```text
sdc://health
sdc://resources
sdc://devices
sdc://mapping
sdc://devices/{provider-or-device-id}/metrics
sdc://devices/{provider-or-device-id}/alarms
sdc://devices/{provider-or-device-id}/context
sdc://devices/{provider-or-device-id}/mdib/raw
```

The exact `{provider-or-device-id}` is determined from the discovered provider and the
normalized snapshot.

### 4. Read core resources

```powershell
sdc-mcp-gateway read-resource sdc://health `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

```powershell
sdc-mcp-gateway read-resource sdc://devices `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

Then read a provider-specific resource from the output of `list-resources`, for example:

```powershell
sdc-mcp-gateway read-resource sdc://devices/<device-id>/metrics `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

### 5. Start the local stdio MCP server

Only after discovery, snapshot, and resource reads work, start the MCP server:

```powershell
sdc-mcp-gateway serve `
  --config config\gateway.local.yaml `
  --mie config\sdc_mie.yaml
```

For a stdio MCP server, it is normal that no human-readable output appears after startup.
The process waits for MCP messages on standard input/output.

Use the example clients in `examples/` or your own MCP client to start and communicate
with the server.

## Using the Python MCP client examples

For local stdio MCP client tests, see:

```text
docs/MCP_CLIENT_EXAMPLES.md
examples/mcp_client_read_resources.py
examples/mcp_client_call_dryrun_tool.py
examples/agent_mcp_client_demo.py
```

For real SDC read-only testing, adapt the example command-line options to use:

```text
config/gateway.local.yaml
```

Do not use dry-run tool examples for the first real-network read-only validation.

## Troubleshooting

### Discovery returns no providers

Check:

```powershell
ipconfig
```

Then verify that `local_ip` is the IP address of your own machine on the SDC/VPN network.

Also check:

- Windows Defender Firewall or institutional firewall rules;
- VPN multicast/WS-Discovery forwarding;
- whether the device/provider is powered on and reachable;
- whether the provider requires a secured setup not represented by the current example;
- whether `provider_whitelist` is empty or contains the correct provider identifier.

### Snapshot fails after discovery succeeds

This usually means discovery works, but provider connection or MDIB initialization fails.
Possible causes:

- provider security requirements;
- unsupported provider behavior;
- incompatible `sdc11073` version;
- incomplete TLS/certificate configuration;
- assumptions in the best-effort extractor that do not match the real MDIB.

Capture the error output and the gateway version before modifying code.

### Resources exist but metrics or alarms are empty

This can happen if the provider exposes no matching states, or if the current best-effort
extractor does not yet recognize the relevant MDIB structures. In that case, preserve the
raw or normalized MDIB output for debugging, subject to any vendor confidentiality rules.

### Do not commit local outputs

Do not commit:

- `config/gateway.local.yaml`;
- VPN configuration;
- certificates or keys;
- `.env` files;
- real-device logs if they contain sensitive data;
- generated files under `data/`.

## What counts as a successful first real-SDC test?

A minimal successful integration test would show:

1. `discover` returns at least one provider;
2. `snapshot` creates a normalized snapshot;
3. `list-resources` exposes provider-specific MCP resources;
4. `read-resource sdc://devices` works;
5. at least one provider-specific metrics, alarms, context, or raw MDIB resource can be read;
6. `sdc://health` still reports a read-only mode and no write operations.

For the paper artifact, a real-SDC run should be reported explicitly as preliminary unless
it has been repeated and documented under a controlled test setup.
