# Artifact and Reproducibility Notes

This repository is a research artifact for evaluating an SDC-to-MCP gateway.

## Included

The artifact includes:

- simulated SDC-like providers;
- read-only MCP resource exposure;
- scenario-based simulation configurations;
- benchmark and aggregation utilities;
- deterministic oracle-agent evaluation;
- optional LLM-backed agent evaluation;
- dry-run MCP tools with policy validation and audit logging.

## Not included

The artifact does not include:

- clinical validation;
- real medical-device operation;
- real SDC write operations;
- production security hardening;
- vendor-specific credentials or VPN configuration.

## Reproducing the main checks

```powershell
pytest -q

sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway benchmark --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --iterations 200 --warmup 20 --output-dir data/experiment_runs --label baseline-v1

sdc-mcp-gateway tool-smoke-test --config config/gateway.simulated.dryrun.example.yaml
```
## Dry-run tool evaluation

```powershell
sdc-mcp-gateway evaluate-dry-run-tools --config config/gateway.simulated.dryrun.example.yaml --ack-config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml --mie config/sdc_mie.yaml --tool-policy config/tool_policies.yaml --output-dir data/tool_eval --label dryrun-tools-v0106
```

The evaluation writes JSON, CSV, and Markdown outputs under `data/tool_eval/`. Generated files are ignored by Git.
