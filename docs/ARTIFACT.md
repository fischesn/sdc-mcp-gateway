# Artifact and Reproducibility Notes

This repository is a research artifact for evaluating an SDC-to-MCP gateway.

## Included

The artifact includes:

- simulated SDC-like providers;
- read-only MCP resource exposure;
- scenario-based simulation configurations;
- benchmark and aggregation utilities;
- deterministic resource-only baseline evaluation;
- optional LLM-backed agent evaluation;
- dry-run MCP tools with policy validation and audit logging;
- a deterministic, non-executing human-authorization lifecycle and synthetic review cases.

## Not included

The artifact does not include:

- clinical validation;
- real medical-device operation;
- real SDC write operations;
- production security hardening;
- vendor-specific credentials or VPN configuration.

## Reproducing the main checks

### Software SDC protocol path (WP3)

On a host with an active IPv4 interface:

```powershell
sdc-mcp-gateway evaluate-sdc-protocol `
  --local-ip <active-local-ipv4> `
  --repetitions 5 `
  --output data/revision/development/wp3-protocol-testbed.json
```

This is a development-phase, hardware-free protocol experiment. It does not
execute the LLM hold-out suite. Exact scope and known discovery limitations are
recorded in `docs/wp3-sdc-protocol-evidence.md`.

### Failure, freshness, recovery, and alarm lifecycle (WP4)

```powershell
sdc-mcp-gateway evaluate-lifecycle `
  --suite config/wp4_lifecycle_scenarios.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output data/revision/development/wp4-lifecycle-evidence.json
```

This deterministic simulator evaluation covers availability faults, validity,
missing and stale data, delayed/duplicate/out-of-order updates, recovery,
snapshot-version binding, and five alarm-lifecycle cases. It evaluates ordered
state transitions, not a production SDC subscription implementation. See
`docs/wp4-lifecycle-evidence.md`.

### Formalized SDC-MIE mapping (WP5)

```powershell
sdc-mcp-gateway evaluate-mapping `
  --mie config/sdc_mie.yaml `
  --output data/revision/development/wp5-mapping-evidence.json
```

This validates SDC-MIE against the checked-in JSON Schema, applies semantic
uniqueness and bounds checks, records the exact source SHA-256 and provenance,
and generates coverage by profile and descriptor/state class. See
`docs/sdc-mie.md` and `docs/wp5-mapping-evidence.md`.

```powershell
pytest -q

sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway benchmark --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --iterations 200 --warmup 20 --output-dir data/experiment_runs --label baseline-v1

sdc-mcp-gateway tool-smoke-test --config config/gateway.simulated.dryrun.example.yaml

sdc-mcp-gateway verify-no-execution --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml --mie config/sdc_mie.yaml --tool-policy config/tool_policies.yaml
```

The no-execution evidence command reports the number of public resource and
tool interactions exercised, the independent SDC operation-attempt count,
before/after device-state digests, static boundary violations, and the result
of exhaustive finite-state transition exploration. It does not claim formal
verification of the Python implementation or general clinical safety.

### Non-executing human authorization (WP10)

```powershell
python -m sdc_mcp_gateway.revision.human_authorization `
  --suite config/bhi2026_wp10_authorization.yaml `
  --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output data/revision/authorization/bhi2026-wp10-authorization-v1/workflow-evidence.json
```

This exercises approval, denial, expiry, duplicate approval, stale and changed source state,
and missing authorization context. The workflow is non-executing and the synthetic prompts are
not expert feedback or clinical validation. See `docs/wp10-human-authorization.md`.

## Dry-run tool evaluation

```powershell
sdc-mcp-gateway evaluate-dry-run-tools --config config/gateway.simulated.dryrun.example.yaml --ack-config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml --mie config/sdc_mie.yaml --tool-policy config/tool_policies.yaml --output-dir data/tool_eval --label dryrun-tools-v0106
```

The evaluation writes JSON, CSV, and Markdown outputs under `data/tool_eval/`. Generated files are ignored by Git.
