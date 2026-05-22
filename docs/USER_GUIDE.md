# SDC-MCP Gateway User Guide

This guide summarizes the command-line workflows of the SDC-to-MCP Gateway research prototype. The prototype exposes simulated or real IEEE 11073 SDC state as MCP resources, evaluates agent-facing tasks, and supports dry-run MCP tools for policy-checked action proposals.

The current evaluated version is **v0.10.6**.

## 1. Installation and shell setup

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
pytest -q
```

For Gemini-based agent tests, set one of:

```powershell
$env:GEMINI_API_KEY = "YOUR_KEY"
# or
$env:GOOGLE_API_KEY = "YOUR_KEY"
```

## 2. Configuration files

Important repository-tracked configuration files:

| File | Purpose |
|---|---|
| `config/gateway.simulated.example.yaml` | Baseline simulated monitor + ventilator gateway. |
| `config/gateway.simulated.tachycardia.example.yaml` | Single patient-monitor tachycardia scenario. |
| `config/gateway.simulated.spo2-drop.example.yaml` | Single patient-monitor SpO2-drop scenario. |
| `config/gateway.simulated.high-airway-pressure.example.yaml` | Single ventilator high-airway-pressure scenario. |
| `config/gateway.simulated.dryrun.example.yaml` | Simulated dry-run tool gateway with MCP tools enabled in dry-run mode. |
| `config/sdc_mie.yaml` | Semantic mapping from SDC-like codes/handles to agent-readable names. |
| `config/agent_eval.tasks.yaml` | Agent-evaluation task definitions and scenario ground truth. |
| `config/tool_policies.yaml` | Dry-run tool policies, value ranges, and approval requirements. |
| `config/tool_args/*.json` | Example tool-call arguments, recommended for Windows/PowerShell. |

Local/lab-specific configuration should remain untracked:

| File | Purpose |
|---|---|
| `config/gateway.local.yaml` | Local SDC/VPN/lab configuration. Do not commit. |

## 3. SDC and simulation commands

### Discover providers

```powershell
sdc-mcp-gateway discover --config config/gateway.simulated.example.yaml
```

Expected simulated result includes `sim-monitor-1` and `sim-ventilator-1`.

### Print a complete resource snapshot

```powershell
sdc-mcp-gateway snapshot --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

### Generate a scenario snapshot at a specific simulated time

```powershell
sdc-mcp-gateway simulate-snapshot --scenario config/sim.high-airway-pressure.yaml --elapsed-s 100 --mie config/sdc_mie.yaml
```

## 4. MCP resource commands

### List resources

```powershell
sdc-mcp-gateway list-resources --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

### Read one resource

```powershell
sdc-mcp-gateway read-resource sdc://health --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway read-resource sdc://devices/sim-ventilator-1/metrics --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

### Start the MCP server

```powershell
sdc-mcp-gateway serve --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

For stdio MCP servers, no visible output after start is normal. The process waits for an MCP client.

### MCP smoke tests

```powershell
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml

sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

## 5. Benchmark commands

### Run one benchmark

```powershell
sdc-mcp-gateway benchmark --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --iterations 200 --warmup 20 --output-dir data/experiment_runs --label baseline-v07-run1
```

### Aggregate benchmark summaries

```powershell
sdc-mcp-gateway summarize-benchmarks --input-dir data/experiment_runs --label baseline-v07-summary --pattern "baseline-v07-run*.summary.json"
```

## 6. Agent task evaluation

`evaluate-agent-tasks` is a **graded batch evaluator**. It reads the tasks from `config/agent_eval.tasks.yaml`, runs them for a scenario, grades the responses against scenario-specific ground truth, and writes JSON/CSV/Markdown output.

### Run all tasks for one scenario

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

Supported agent modes:

| Agent | Purpose |
|---|---|
| `oracle` | Deterministic reference agent; no LLM call. |
| `llm-mock` | Deterministic LLM-shaped mock path; no external model. |
| `llm-gemini` | Gemini Developer API via `google-genai`. |
| `llm-ollama` | Local Ollama chat endpoint. |
| `llm-openai-compatible` | OpenAI-compatible chat completions endpoint. |

### Run only one task

v0.10.2 adds `--task-id`. It can be passed multiple times.

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --task-id clinical_summary `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

Available task ids in the default task file:

| Task id | Meaning |
|---|---|
| `device_inventory` | Identify exposed devices. |
| `alarm_detection` | Detect active alarm state and associated device/metric/priority. |
| `clinical_summary` | Summarize current device state without treatment/control advice. |
| `metrics_resource_selection` | Select the correct MCP metrics resource URI. |

### Aggregate agent evaluations

```powershell
sdc-mcp-gateway summarize-agent-evaluations --input-dir data/agent_eval/gemini-v093-final --label gemini-v093-final-summary --pattern "agent-eval-*.json"
```

Use a clean input directory for final paper results. Do not aggregate exploratory failed runs and final runs together unless that is intentional.

## 7. Free natural-language questions

v0.10.2 adds `ask-agent`. This is an **ungraded exploratory command**. It asks one natural-language question about the current read-only MCP resource state and returns a JSON answer.

```powershell
sdc-mcp-gateway ask-agent `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --question "Is there an active alarm and which device is affected?" `
  --elapsed-s 100
```

Mock example without external LLM:

```powershell
sdc-mcp-gateway ask-agent `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --agent llm-mock `
  --question "Is there an active alarm and which device is affected?" `
  --elapsed-s 100
```

Use `--output-dir data/agent_eval` to save the answer report as JSON.

Important distinction:

| Command | Purpose |
|---|---|
| `evaluate-agent-tasks` | Reproducible, graded evaluation against ground truth. |
| `ask-agent` | Free natural-language exploration; not graded. |

## 8. Dry-run MCP tools

Dry-run tools validate possible actions but never execute SDC operations.

### List tools

```powershell
sdc-mcp-gateway list-tools --config config/gateway.simulated.dryrun.example.yaml --mie config/sdc_mie.yaml --tool-policy config/tool_policies.yaml
```

### Call a dry-run tool using argument files

Recommended under Windows/PowerShell:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_45.json `
  --config config/gateway.simulated.dryrun.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

Invalid value example:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_150_invalid.json `
  --config config/gateway.simulated.dryrun.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

Expected behavior:

| Case | Expected result |
|---|---|
| FiO2 45 | `accepted_dry_run`, `executed=false`, `requires_human_approval=true`. |
| FiO2 150 | `rejected`, `reason=value_out_of_range`, `executed=false`. |

### Tool smoke test

```powershell
sdc-mcp-gateway tool-smoke-test --config config/gateway.simulated.dryrun.example.yaml --mie config/sdc_mie.yaml --tool-policy config/tool_policies.yaml
```

## 9. Safety interpretation

The prototype distinguishes two safety modes:

| Mode | Expected state |
|---|---|
| Read-only resources | `tools_exported=false`, `write_operations_allowed=false`. |
| Dry-run tools | `tools_exported=true`, `tool_mode=dry-run`, `write_operations_allowed=false`, `executed=false`. |

Even when MCP tools are enabled in v0.10+, the prototype only validates proposals and writes audit records. It does not execute SDC SetService or ActivateOperation calls.

## 10. Recommended paper workflows

### Read-only agent evaluation

1. Run `evaluate-agent-tasks` for baseline and three alarm scenarios.
2. Copy final JSONs into a clean folder.
3. Run `summarize-agent-evaluations`.
4. Report pass rate, wrong URI count, unsafe term count, and safety-boundary status.

### Dry-run tool evaluation

1. Run `list-tools`.
2. Run accepted dry-run calls, e.g. FiO2 45.
3. Run rejected dry-run calls, e.g. FiO2 150.
4. Confirm `executed=false` in all tool results.
5. Inspect audit logs in `data/logs/`.

## Systematic dry-run tool evaluation

Version v0.10.6 adds a paper-oriented dry-run tool evaluation command. It runs a small set of accepted and rejected tool cases and writes JSON, CSV, and Markdown output.

```powershell
sdc-mcp-gateway evaluate-dry-run-tools `
  --config config/gateway.simulated.dryrun.example.yaml `
  --ack-config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output-dir data/tool_eval `
  --label dryrun-tools-v0106
```

The default case set checks:

- valid FiO2 proposal accepted as `accepted_dry_run`;
- out-of-range FiO2 rejected;
- valid PEEP proposal accepted as `accepted_dry_run`;
- out-of-range PEEP rejected;
- wrong-device-type PEEP proposal rejected;
- acknowledgement of an active airway-pressure alarm accepted as dry-run;
- acknowledgement of a non-active airway-pressure alarm rejected.

All cases must report `executed=false` and `write_operations_allowed=false`.
