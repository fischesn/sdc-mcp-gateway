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
sdc_mie.yaml                    Schema-validated SDC-MIE 1.0 semantic mapping
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

The WP6 evaluation uses a deterministic resource processor that receives the same MCP resource context as the LLM agents. Scenario ground truth is available only to the downstream grader.

Run one scenario:

```powershell
sdc-mcp-gateway evaluate-agent-tasks --config config/gateway.simulated.tachycardia.example.yaml --mie config/sdc_mie.yaml --tasks config/agent_eval.tasks.yaml --scenario tachycardia --agent deterministic-baseline --output-dir data/agent_eval --elapsed-s 100
```

Run all default scenarios:

```powershell
.\scripts\run_agent_evaluation.ps1
```

The outputs are written as JSON, CSV, and Markdown files under `data/agent_eval/`.

## v0.9 LLM agent options

LLM agent evaluation is configured primarily through CLI options. No API keys should be written into YAML files. Use environment variables for external services.

Supported agent values include `deterministic-baseline`, `llm-mock`, `llm-ollama`, `llm-openai-compatible`, and `llm-gemini`. `oracle` remains only as a backward-compatible alias.

## Dry-run tool configuration

v0.10 adds:

```text
config/gateway.simulated.dryrun.example.yaml
config/tool_policies.yaml
```

The dry-run gateway configuration enables MCP tools while keeping device writes disabled. The policy file defines the allowed dry-run proposals, value ranges, target device types, and human-approval requirements.

Do not put real credentials, real device endpoints, or local lab secrets into these files. Use local ignored configuration files for testbed-specific settings.

## Tool argument examples

`config/tool_args/` contains JSON files used with the dry-run `call-tool --args-file` command. This is the recommended way to pass tool arguments on Windows/PowerShell and for reproducible experiments.

Examples:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 --args-file config\tool_args\set_fio2_45.json --config config\gateway.simulated.dryrun.example.yaml
sdc-mcp-gateway call-tool prepare_set_fio2 --args-file config\tool_args\set_fio2_150_invalid.json --config config\gateway.simulated.dryrun.example.yaml
```

## Dry-run tool evaluation configuration

v0.10.6 adds:

```text
gateway.simulated.dryrun.high-airway-pressure.example.yaml
```

This configuration enables dry-run tools for the high-airway-pressure scenario and is used by `evaluate-dry-run-tools` to validate acknowledgement of an active airway-pressure alarm.


## Real SDC local configuration

For first tests in a real SDC/VPN/lab network, copy `gateway.sdc11073.example.yaml` to `gateway.local.yaml`, set `sdc.local_ip` to your own interface address on the SDC network, and follow `docs/REAL_SDC_TESTING.md`. Do not commit `gateway.local.yaml`.
