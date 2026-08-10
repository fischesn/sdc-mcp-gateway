# Container-isolated same-stack SDC experiment

This hardware-free experiment evaluates the Python `sdc11073` 2.4.1 provider
and gateway consumer in separate Linux containers, network namespaces, and
IPv4 addresses on a short-lived Docker bridge. The runner permits no directed
XAddr fallback.

## Recorded configuration

- Docker Desktop 29.6.2 with Linux containers
- Python 3.12 container image
- `sdc11073` 2.4.1
- monitor, ventilator, and heterogeneous versioned MDIB profiles
- five repetitions per profile
- ephemeral mutual TLS
- WS-Discovery timeout: 1.2 s per attempt

## Recorded result

- WS-Discovery: 15/15
- MDIB snapshots: 15/15
- MCP resource reads: 120/120
- directed XAddr fallbacks: 0
- mapped metrics: 7/11

The result JSON SHA-256 is
`62c7ddae9e5605222c322cb172ca07a3fe5d64831a122d2cddec74230a4490ea`.
This is software-reference evidence, not physical-device, clinical-network,
multi-vendor, or clinical-safety validation.

## Reproduction

Start Docker Desktop, then run from the repository root:

```powershell
python -m sdc_mcp_gateway.sdc.container_protocol_testbed `
  --repetitions 5 `
  --discovery-timeout-s 1.2 `
  --output data/revision/development/container-protocol-testbed.json
```

The ignored development output can be compared byte-for-byte at the semantic
field level; timing values and the allocated private subnet will vary.
