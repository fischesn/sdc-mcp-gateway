# Configuration files

This directory contains version-controlled default and example configuration files. Local laboratory configuration files must be kept out of Git.

## Files committed to Git

```text
gateway.yaml                    Default dummy/read-only configuration
gateway.sdc11073.example.yaml   Template for real SDC lab or VPN tests
gateway.simulated.example.yaml  Template for in-process simulated device scenarios
sim.patient-monitor.yaml        Simulated patient monitor scenario
sim.ventilator.yaml             Simulated ventilator scenario
sim.combined.yaml               Combined simulated monitor + ventilator scenario
sdc_mie.yaml                    Example semantic mapping
policies.yaml                   Read-only example policy
```

## File not committed to Git

```text
gateway.local.yaml
```

Create it from a template when needed:

```bash
cp config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

or, for local simulation experiments:

```bash
cp config/gateway.simulated.example.yaml config/gateway.local.yaml
```

Then edit `gateway.local.yaml`. Do not commit it because it may contain VPN interface IP addresses, provider identifiers, device filters, or other lab-specific details.

## Simulation note

The simulation scenarios are not real IEEE 11073 SDC providers. They generate normalized SDC-like snapshots in-process. Use them for gateway and mapping development before real devices are available.

## Scenario-based simulation files

Version 0.7.1 includes three event-based scenario files:

```text
sim.tachycardia.yaml
sim.spo2-drop.yaml
sim.high-airway-pressure.yaml
```

Each file defines simulated devices, metrics, events, and alarm thresholds. Use the matching `gateway.simulated.*.example.yaml` template when running the scenario through the normal gateway, MCP, or benchmark path.

To create your own scenario, copy one of these files, change metric baselines/events/alarms, and update or create a matching gateway template. See `docs/scenarios.md` for details.


## v0.8 Agent-facing evaluation

Version v0.8.0 adds deterministic oracle-agent task evaluation. It validates whether the MCP resource surface supports device inventory, alarm detection, safe clinical-state summarization, and resource selection tasks.

Run one scenario:

```powershell
sdc-mcp-gateway evaluate-agent-tasks --config config/gateway.simulated.tachycardia.example.yaml --mie config/sdc_mie.yaml --tasks config/agent_eval.tasks.yaml --scenario tachycardia --agent oracle --output-dir data/agent_eval --elapsed-s 100
```

Run all default scenarios:

```powershell
.\scripts\run_agent_evaluation.ps1
```

The outputs are written as JSON, CSV, and Markdown files under `data/agent_eval/`.

## v0.9 LLM agent options

LLM agent evaluation is configured primarily through CLI options. No API keys should be written into YAML files. Use environment variables for external services.

Supported agent values: `oracle`, `llm-mock`, `llm-ollama`, and `llm-openai-compatible`.
