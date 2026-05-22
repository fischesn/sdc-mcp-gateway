# Installation Guide

This document describes how to install and test the SDC-MCP Gateway research prototype.

The instructions assume Windows PowerShell because the prototype has been developed and
tested primarily in that environment. Linux/macOS users can use the same Python commands
with the corresponding shell activation command for virtual environments.

## Requirements

Recommended:

- Python 3.11, 3.12, 3.13, or 3.14
- Git
- PowerShell
- Optional: Ollama for local LLM experiments
- Optional: Gemini API key for Gemini-backed LLM experiments

The package metadata currently declares:

```text
requires-python = >=3.11,<3.15
```

## Clone the repository

```powershell
git clone https://github.com/fischesn/sdc-mcp-gateway.git
cd sdc-mcp-gateway
```

If your repository URL is different, adjust the command accordingly.

## Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If PowerShell blocks script execution, use a process-local execution policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Install the package

### Full development installation

For most development and paper-artifact reproduction work, install all optional dependencies:

```powershell
python -m pip install -e ".[all]"
```

This installs:

- core package dependencies;
- MCP SDK support;
- `sdc11073` support;
- Gemini support;
- development/test tools.

### Minimal installation

```powershell
python -m pip install -e .
```

This is sufficient for basic non-MCP, non-LLM functionality.

### MCP support only

```powershell
python -m pip install -e ".[mcp]"
```

### SDC support only

```powershell
python -m pip install -e ".[sdc]"
```

### Gemini support only

```powershell
python -m pip install -e ".[gemini]"
```

### Development tools only

```powershell
python -m pip install -e ".[dev]"
```

## Verify installation

Run:

```powershell
sdc-mcp-gateway --help
```

Then run the test suite:

```powershell
pytest -q
```

A clean release candidate should have no failing tests. One skipped test can be acceptable
if it depends on an optional external service or optional SDK behavior.

## Quick read-only resource checks

Run the internal MCP/resource smoke test:

```powershell
sdc-mcp-gateway mcp-smoke-test `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Run the MCP client smoke test:

```powershell
sdc-mcp-gateway mcp-client-smoke-test `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

List resources:

```powershell
sdc-mcp-gateway list-resources `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Read gateway health:

```powershell
sdc-mcp-gateway read-resource sdc://health `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Read simulated ventilator metrics:

```powershell
sdc-mcp-gateway read-resource sdc://devices/sim-ventilator-1/metrics `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

## Run scenario simulations

Baseline combined scenario:

```powershell
sdc-mcp-gateway simulate-snapshot `
  --scenario config/sim.combined.yaml `
  --elapsed-s 100 `
  --mie config/sdc_mie.yaml
```

Tachycardia:

```powershell
sdc-mcp-gateway simulate-snapshot `
  --scenario config/sim.tachycardia.yaml `
  --elapsed-s 100 `
  --mie config/sdc_mie.yaml
```

SpO2 drop:

```powershell
sdc-mcp-gateway simulate-snapshot `
  --scenario config/sim.spo2-drop.yaml `
  --elapsed-s 100 `
  --mie config/sdc_mie.yaml
```

High airway pressure:

```powershell
sdc-mcp-gateway simulate-snapshot `
  --scenario config/sim.high-airway-pressure.yaml `
  --elapsed-s 100 `
  --mie config/sdc_mie.yaml
```

## Benchmarking

Run a benchmark:

```powershell
sdc-mcp-gateway benchmark `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml `
  --iterations 200 `
  --warmup 20 `
  --output-dir data/experiment_runs `
  --label baseline-v1
```

Aggregate benchmark summaries:

```powershell
sdc-mcp-gateway summarize-benchmarks `
  --input-dir data/experiment_runs `
  --label baseline-summary `
  --pattern "baseline-v1*.summary.json"
```

Generated benchmark files are written to `data/experiment_runs/` and should not be committed.

## Agent evaluation

### Deterministic oracle agent

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --agent oracle `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

### Single-task evaluation

Use `--task-id` to run one task instead of the complete task file:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --task-id clinical_summary `
  --agent oracle `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

You can pass `--task-id` multiple times if needed.

### Gemini-backed evaluation

Install Gemini support if you did not install `.[all]`:

```powershell
python -m pip install -e ".[gemini]"
```

Set your API key:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

Alternatively, the code can use `GOOGLE_API_KEY` if supported by your environment.

Run an evaluation:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.tachycardia.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario tachycardia `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

### LLM mock agent

For deterministic local tests without an external LLM:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.tachycardia.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario tachycardia `
  --agent llm-mock `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

### Ollama-backed evaluation

Make sure Ollama is running and the model is available.

Example:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.tachycardia.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario tachycardia `
  --agent llm-ollama `
  --llm-model llama3.1 `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

### OpenAI-compatible evaluation

For OpenAI-compatible chat completion endpoints:

```powershell
$env:OPENAI_API_KEY = "your-key"
```

Then run, adapting endpoint/model arguments according to the current CLI help:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.tachycardia.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario tachycardia `
  --agent llm-openai-compatible `
  --llm-model your-model `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

Use:

```powershell
sdc-mcp-gateway evaluate-agent-tasks --help
```

to inspect the exact options supported by the installed version.

## Free-question mode

`ask-agent` asks a free natural-language question against the current resource context. It is
exploratory and ungraded.

Example with Gemini:

```powershell
sdc-mcp-gateway ask-agent `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --question "Is there an active alarm and which device is affected?" `
  --elapsed-s 100
```

Example with mock agent:

```powershell
sdc-mcp-gateway ask-agent `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --agent llm-mock `
  --question "Is there an active alarm and which device is affected?" `
  --elapsed-s 100
```

For paper-quality, reproducible evaluation results, use `evaluate-agent-tasks`, not
`ask-agent`.

## Summarize agent evaluations

Aggregate selected agent-evaluation JSON files:

```powershell
sdc-mcp-gateway summarize-agent-evaluations `
  --input-dir data/agent_eval/gemini-v093-final `
  --label gemini-v093-final-summary `
  --pattern "agent-eval-*.json"
```

Important: use a clean input directory or a restrictive pattern. Otherwise old exploratory
runs, failed preliminary runs, oracle runs, and LLM runs may be aggregated together.

Generated aggregation files should not be committed.

## Dry-run MCP tools

Dry-run tools are enabled through:

```text
config/gateway.simulated.dryrun.example.yaml
```

List tools:

```powershell
sdc-mcp-gateway list-tools `
  --config config/gateway.simulated.dryrun.example.yaml
```

Run dry-run smoke tests:

```powershell
sdc-mcp-gateway tool-smoke-test `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call a valid dry-run FiO2 proposal:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_45.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call an invalid FiO2 proposal:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_150_invalid.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call a PEEP dry-run proposal:

```powershell
sdc-mcp-gateway call-tool prepare_set_peep `
  --args-file config/tool_args/set_peep_10.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call a dry-run alarm acknowledgment proposal:

```powershell
sdc-mcp-gateway call-tool prepare_acknowledge_alarm `
  --args-file config/tool_args/ack_airway_pressure_alarm.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

Prefer `--args-file` on Windows. Passing raw JSON via `--args-json` is fragile in PowerShell
because of quoting rules.

Dry-run tool results must always report:

```json
{
  "executed": false,
  "write_operations_allowed": false
}
```

Valid proposals should be accepted as dry-runs. Invalid proposals should be rejected by
the policy layer.

## Systematic dry-run tool evaluation

Run the paper-oriented dry-run tool evaluation:

```powershell
sdc-mcp-gateway evaluate-dry-run-tools `
  --config config/gateway.simulated.dryrun.example.yaml `
  --ack-config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output-dir data/tool_eval `
  --label dryrun-tools-v0106
```

The command writes JSON, CSV, and Markdown outputs under `data/tool_eval/`.
These files are ignored by Git.

## MCP server mode

Read-only resource server:

```powershell
sdc-mcp-gateway serve `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Dry-run resource/tool server:

```powershell
sdc-mcp-gateway serve `
  --config config/gateway.simulated.dryrun.example.yaml `
  --mie config/sdc_mie.yaml
```

If the server starts and prints no further output, that can be normal for a stdio-based
MCP server. It is waiting for an MCP client.

## Real SDC network configuration

Create a local file such as:

```text
config/gateway.local.yaml
```

Do not commit this file.

Example:

```yaml
gateway:
  name: "sdc-mcp-gateway-local"
  mode: "read-only"

sdc:
  adapter: "sdc11073"
  local_ip: "192.0.2.10"
  max_devices: 2
  provider_whitelist: []

mapping:
  version: "local"

logging:
  enabled: true
  directory: "data/logs"
```

The address above uses a documentation address range. Replace it locally with the real
VPN or interface address when testing in a real SDC network.

Do not commit:

- VPN configuration;
- certificates;
- private keys;
- device credentials;
- real network addresses if they are sensitive;
- `config/gateway.local.yaml`;
- `.env`;
- `secrets/`.

## Generated files and Git hygiene

The following folders are for runtime outputs and should normally contain only `.gitkeep`
files in Git:

```text
data/agent_eval/
data/experiment_runs/
data/logs/
```

If generated files are accidentally tracked, remove them from the Git index while keeping
them locally:

```powershell
git rm -r --cached data\agent_eval
git rm -r --cached data\experiment_runs
git rm -r --cached data\logs
git add data\agent_eval\.gitkeep
git add data\experiment_runs\.gitkeep
git add data\logs\.gitkeep
```

## Troubleshooting

### PowerShell blocks virtual-environment activation

Use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### JSON command-line arguments fail under PowerShell

Use `--args-file` instead of `--args-json`:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_45.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

### Gemini evaluation fails because no API key is configured

Set:

```powershell
$env:GEMINI_API_KEY = "your-key"
```

Then rerun the command.

### MCP server appears to hang

For a stdio MCP server, this can be normal. Use the smoke tests to validate the server path:

```powershell
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

### Tests fail after cleaning data directories

Make sure `.gitkeep` files still exist:

```powershell
New-Item -ItemType Directory -Force data\agent_eval | Out-Null
New-Item -ItemType Directory -Force data\experiment_runs | Out-Null
New-Item -ItemType Directory -Force data\logs | Out-Null

New-Item -ItemType File -Force data\agent_eval\.gitkeep | Out-Null
New-Item -ItemType File -Force data\experiment_runs\.gitkeep | Out-Null
New-Item -ItemType File -Force data\logs\.gitkeep | Out-Null
```

## Recommended pre-release checklist

Before tagging a release candidate:

```powershell
pytest -q

sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway tool-smoke-test --config config/gateway.simulated.dryrun.example.yaml

git status
git ls-files data
```

`git ls-files data` should normally show only `.gitkeep` files.

## Next steps for paper artifacts

For a paper artifact release, keep code/configuration/scripts in the repository and place
large or generated experiment outputs in a GitHub Release artifact or archival repository.
If final experiment summaries are included in the repository, document them explicitly
under `experiments/` and keep only the final, curated data.
