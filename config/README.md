# Configuration files

This directory intentionally contains **version-controlled templates and defaults**. They document the expected configuration structure and make the repository usable for other developers.

## Files that should be committed

| File | Purpose |
|---|---|
| `gateway.yaml` | Default read-only dummy configuration for local development and unit tests. |
| `gateway.sdc11073.example.yaml` | Template for real SDC lab tests with the optional `sdc11073` adapter. Copy this file before editing lab-specific values. |
| `sdc_mie.yaml` | Example SDC-MIE semantic mapping file. It maps SDC/BICEPS/nomenclature elements to stable, agent-readable names. |
| `policies.yaml` | Example read-only safety policy. In v0.2, all write/tool operations remain denied. |

## File that should not be committed

| File | Purpose |
|---|---|
| `gateway.local.yaml` | Your local lab configuration. It may contain VPN interface IP addresses, provider identifiers, device-specific filters, or other institution-specific testbed details. It is ignored by Git. |

## Recommended workflow for real SDC tests

Create a local configuration from the example template:

```bash
cp config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

On Windows PowerShell, the equivalent command is:

```powershell
Copy-Item config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

Then edit only `config/gateway.local.yaml`:

```yaml
sdc:
  adapter: "sdc11073"
  local_ip: "YOUR_LOCAL_SDC_VPN_OR_LAB_INTERFACE_IPV4"
  max_devices: 1
  provider_whitelist: []
```

`local_ip` is the IPv4 address of the network interface on which the gateway process runs. In a Dräger-provided SDC VPN, this is normally your own VPN adapter address, not the address of a medical device.

Run discovery with the local file:

```bash
sdc-mcp-gateway discover --config config/gateway.local.yaml
```

Capture a read-only snapshot:

```bash
sdc-mcp-gateway snapshot --config config/gateway.local.yaml --mie config/sdc_mie.yaml
```

Do not put real device addresses, VPN details, or lab-specific identifiers into the committed example files.
