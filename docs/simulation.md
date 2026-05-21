# Simulated SDC-like Device Scenarios

The v0.3.0 simulator is intentionally an **in-process SDC-like state generator**, not a real networked IEEE 11073 SDC Provider. It allows gateway, mapping, MCP-resource, and logging development while no real SDC network is available.

## Available scenarios

- `config/sim.patient-monitor.yaml`
- `config/sim.ventilator.yaml`
- `config/sim.combined.yaml`

## Direct snapshot command

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.combined.yaml --elapsed-s 10 --mie config/sdc_mie.yaml
```

This command bypasses SDC networking and prints the same MCP resource payloads that the gateway would expose.

## Gateway adapter command

```bash
sdc-mcp-gateway snapshot --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

This exercises the normal gateway path through the `simulated` adapter.

## Creating a new scenario

Copy one of the YAML files and change:

- `device_id`
- `display_name`
- metric `handle`, `code`, `unit`, `baseline`, and variation parameters
- alarm thresholds

Metric values are generated deterministically from baseline, amplitude, period, and noise. Use the same `random_seed` for reproducible runs.

## Limitations

The simulator does not test:

- WS-Discovery,
- TLS,
- real BICEPS/MDIB parsing,
- real provider connection handling,
- real SDC operation invocation.

Those remain part of the real `sdc11073` adapter and the future laboratory testbed.
