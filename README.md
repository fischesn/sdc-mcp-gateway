# SDC-to-MCP Gateway

Research prototype for exposing IEEE 11073 SDC device state as Model Context Protocol (MCP) resources.

This repository currently contains **v0.9.3-stricter-resource-selection-prompting**. It remains deliberately limited to read-only access:

- A deterministic dummy SDC consumer is included for local development and tests.
- A reproducible in-process simulated SDC-like provider testbed is included for patient monitor and ventilator scenarios.
- A real `sdc11073` adapter can discover providers and capture one-shot MDIB snapshots.
- MCP resources expose devices, metrics, alarms, context, raw MDIB summaries, and the SDC-MIE mapping.
- Repeatable benchmarks write JSONL, CSV, and summary artifacts for paper-oriented experiments.
- Agent-facing evaluations cover deterministic oracle agents and optional LLM-backed agents.
- No SDC operation is executed.
- No MCP tool is exported.
- No clinical use is intended or permitted.

## Repository layout

```text
sdc-mcp-gateway/
  config/                  Version-controlled defaults and example templates
  docs/                    Version specifications and implementation notes
  examples/                Small local demos
  src/sdc_mcp_gateway/     Python package
  tests/                   Unit tests
  data/                    Local logs and experiment outputs; generated files are ignored by Git
```

## Configuration files and Git hygiene

The repository intentionally includes configuration templates so that other users can understand and reproduce the setup.

Committed files:

```text
config/gateway.yaml                    # default dummy/read-only configuration
config/gateway.sdc11073.example.yaml   # template for real SDC lab tests
config/gateway.simulated.example.yaml  # template for in-process simulated baseline scenarios
config/gateway.simulated.tachycardia.example.yaml
config/gateway.simulated.spo2-drop.example.yaml
config/gateway.simulated.high-airway-pressure.example.yaml
config/sim.patient-monitor.yaml        # simulated patient monitor scenario
config/sim.ventilator.yaml             # simulated ventilator scenario
config/sim.combined.yaml               # combined multi-device baseline simulation scenario
config/sim.tachycardia.yaml           # event-based tachycardia scenario
config/sim.spo2-drop.yaml             # event-based oxygen desaturation scenario
config/sim.high-airway-pressure.yaml  # event-based ventilator pressure scenario
config/sdc_mie.yaml                    # example semantic mapping
config/policies.yaml                   # read-only example policy
config/README.md                       # configuration workflow explanation
```

Local file that must not be committed:

```text
config/gateway.local.yaml
```

`gateway.local.yaml` may contain your SDC VPN interface IP address, provider identifiers, device filters, or lab-specific details. It is listed in `.gitignore`.

For real SDC tests, create it from the template:

```bash
cp config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

On Windows PowerShell:

```powershell
Copy-Item config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

Then edit `config/gateway.local.yaml` and set:

```yaml
sdc:
  adapter: "sdc11073"
  local_ip: "YOUR_LOCAL_SDC_VPN_OR_LAB_INTERFACE_IPV4"
```

The `local_ip` value is the IPv4 address of the interface on which the gateway process runs. In an SDC VPN, this is normally your own VPN adapter address, not the address of a medical device.

## Installation for local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e ".[dev]"
```

For the real SDC adapter:

```bash
python -m pip install -e ".[sdc,dev]"
```

For all optional components including MCP and SDC:

```bash
python -m pip install -e ".[all]"
```

See `INSTALLATION.md` for a full Python 3.14-oriented installation guide.

## Run a local dummy snapshot

```bash
sdc-mcp-gateway snapshot --config config/gateway.yaml --mie config/sdc_mie.yaml
```


## Run a simulated SDC-like snapshot

The v0.7.1 simulator does **not** open a real IEEE 11073 SDC network endpoint. It generates normalized SDC-like device snapshots in-process so that mapping, MCP resources, and logging can be developed without real devices.

Direct scenario snapshot:

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.combined.yaml --elapsed-s 10 --mie config/sdc_mie.yaml
```

Through the regular gateway adapter path:

```bash
sdc-mcp-gateway discover --config config/gateway.simulated.example.yaml
sdc-mcp-gateway snapshot --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

## Discover real SDC providers

Create and edit the local config first:

```bash
cp config/gateway.sdc11073.example.yaml config/gateway.local.yaml
# edit config/gateway.local.yaml, especially sdc.local_ip
```

Then run:

```bash
sdc-mcp-gateway discover --config config/gateway.local.yaml
```

## Capture a real read-only MDIB snapshot

```bash
sdc-mcp-gateway snapshot --config config/gateway.local.yaml --mie config/sdc_mie.yaml
```

## Run the MCP server

```bash
sdc-mcp-gateway serve --config config/gateway.yaml --mie config/sdc_mie.yaml
```

This requires the Python MCP SDK. If it is not installed, the package will explain the missing dependency.

## Run tests

```bash
pytest -q
```

Expected result for v0.7.1:

```text
20 passed
```

## Recommended Git workflow

For a clean version history:

```bash
git init
git branch -M main
git add .
git commit -m "Add repeatable benchmark and experiment logging v0.7.1"
git tag -a v0.7.1 -m "v0.7.1 repeatable benchmark and experiment logging"
```

Before committing, check that `config/gateway.local.yaml` is not staged:

```bash
git status
```

If it appears under staged or unstaged files, remove it from Git tracking:

```bash
git rm --cached config/gateway.local.yaml
```

## Safety status

This prototype is a research scaffold only. It is not a medical device, not a clinical decision support system, and not suitable for clinical operation. It must only be used in isolated laboratory and demonstration environments.


## v0.4: Read-only MCP resource server

Version v0.4 exposes the gateway state as an MCP resource surface while keeping
the prototype strictly read-only. No MCP tools are exported and no write
operations are allowed.

Inspect the resource catalogue without an MCP client:

```bash
sdc-mcp-gateway list-resources --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Read one resource:

```bash
sdc-mcp-gateway read-resource sdc://health --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Run a local MCP smoke test before connecting an external MCP client:

```bash
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Start the MCP server after installing the optional MCP dependency:

```bash
python -m pip install -e ".[mcp]"
sdc-mcp-gateway serve --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

See `docs/v0.4-spec.md`, `docs/v0.4.1-spec.md`, and `docs/mcp-server.md` for details.


## v0.5: End-to-end MCP client smoke test

Version v0.5 adds an actual MCP client smoke test. Unlike `mcp-smoke-test`, which
checks the internal registry and FastMCP server construction, this command starts
`serve` as a stdio MCP subprocess and interacts with it through an MCP `ClientSession`.

```bash
sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Expected result: `status: ok`, 12 listed resources for the simulated two-device
scenario, readable health/devices/metrics resources, and zero exported MCP tools.


## Benchmark aggregation (v0.7.1)

After producing multiple benchmark runs, aggregate their summary files with:

```powershell
sdc-mcp-gateway summarize-benchmarks --input-dir data/experiment_runs --label simulated-v06-summary
```

This writes an `.aggregate.json` file and an `.aggregate.csv` file with one row per benchmark summary and aggregate latency statistics across runs.

## Scenario-based simulation experiments

Version 0.7.1 adds explicit clinical-style simulation scenarios. The built-in examples are:

```text
config/sim.tachycardia.yaml
config/sim.spo2-drop.yaml
config/sim.high-airway-pressure.yaml
```

Each scenario has a matching gateway template:

```text
config/gateway.simulated.tachycardia.example.yaml
config/gateway.simulated.spo2-drop.example.yaml
config/gateway.simulated.high-airway-pressure.example.yaml
```

Example snapshot:

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.tachycardia.yaml --elapsed-s 60 --mie config/sdc_mie.yaml
```

Example benchmark:

```bash
sdc-mcp-gateway benchmark --config config/gateway.simulated.tachycardia.example.yaml --mie config/sdc_mie.yaml --iterations 100 --warmup 10 --label tachycardia-v07
```

See `docs/scenarios.md` for a detailed guide to writing custom scenario YAML files.


### v0.7.1 alarm-observation update

Version v0.7.1 corrects the high-airway-pressure scenario so that the simulated airway-pressure alarm remains active at the end of standard benchmark runs. Benchmark summaries also include `active_alarm_count_max` and `active_alarm_seen_any`, which are useful when evaluating transient or pulse-like alarm scenarios.


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

## Agent-facing LLM evaluation (v0.9)

v0.9 extends the deterministic v0.8 oracle-agent evaluation with optional LLM-backed agents. The same task definitions, scenario ground truth, and graders are reused. This keeps the evaluation comparable across deterministic and non-deterministic agents.

The safest local smoke test uses the mock LLM backend, which exercises the LLM prompt/JSON/grading path without calling an external model:

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

A local Ollama model can be used with:

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

OpenAI-compatible chat-completion endpoints are supported through `--agent llm-openai-compatible`. Keep API keys in environment variables and never commit them. The gateway remains read-only in all LLM modes: no MCP tools are exported and write operations remain disabled.

Gemini is supported through `--agent llm-gemini` after installing the optional `gemini` extra and setting `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Example: `python -m pip install -e ".[gemini]"`, then run with `--llm-model gemini-2.5-flash`.

### v0.9.2 note

v0.9.2 refines LLM clinical-summary grading. It fixes a false positive where benign wording such as "set high threshold" was interpreted as an unsafe device-control recommendation. Unsafe detection now focuses on action-oriented recommendations such as setting FiO2/PEEP, changing ventilator settings, administering medication, or silencing alarms.


### v0.9.3 note

v0.9.3 refines LLM resource-selection prompting for multi-device scenarios. The LLM prompt now includes explicit target-device constraints and an agent-facing resource index with parsed `device_id`, inferred `device_type`, and `resource_kind`. This prevents models from returning example monitor metric URIs when the task asks for the ventilator metrics resource in the baseline scenario. The gateway remains read-only and exports no MCP tools.

## v0.9.4 Agent-evaluation aggregation

Use `summarize-agent-evaluations` to aggregate multiple oracle or LLM-backed agent-evaluation JSON reports:

```powershell
sdc-mcp-gateway summarize-agent-evaluations --input-dir data/agent_eval --label gemini-v093-summary --pattern "agent-eval-*.json"
```

The command writes an `.aggregate.json` and `.aggregate.csv` file with task-pass counts, wrong URI counts, false alarm counts, unsafe-summary counts, and read-only safety-boundary status.
