# SDC-MCP Gateway

Research prototype for exposing IEEE 11073 SDC-like medical-device state through the
Model Context Protocol (MCP).

The gateway supports two interaction layers:

1. **Read-only MCP Resources** for exposing device inventories, metrics, alarms,
   context information, semantic mapping metadata, and normalized MDIB-like snapshots.
2. **Dry-run MCP Tools** for validating controlled action proposals without executing
   SDC write operations.

This repository is a research prototype. It is **not** a medical device, is **not**
intended for clinical use, and must not be used for patient care. The simulated
providers are SDC-like test fixtures, not clinically validated devices.

## Scope

The current prototype provides:

- simulated SDC-like patient monitor and ventilator providers;
- scenario-based simulations for baseline, tachycardia, SpO2 drop, and high airway pressure;
- a normalized snapshot abstraction for device state;
- an SDC-MIE semantic mapping layer;
- read-only MCP resource exposure;
- MCP client smoke tests;
- benchmark and aggregation utilities;
- deterministic resource-only baseline evaluation;
- optional LLM-backed agent evaluation, including Gemini and OpenAI-compatible endpoints;
- free-question agent mode for exploratory resource-based questions;
- dry-run MCP tools with policy validation and audit logging.

The prototype intentionally does **not** provide:

- real clinical validation;
- production security hardening;
- real SDC write operations;
- real SDC SetService or ActivateOperation execution;
- medical decision support;
- autonomous therapy or device-control functionality.

## Safety boundary

The evaluated prototype uses the following safety boundary:

- MCP Resources are read-only.
- MCP Tools are available only in dry-run mode.
- Write operations are disabled.
- Dry-run tools validate arguments and local policies.
- Dry-run tools write audit records.
- Dry-run tools always return `executed=false`.
- No SDC SetService or ActivateOperation call is executed.
- Configurations with `allow_write_operations=true` fail validation at startup.
- Non-dry-run tool policies and execution-capable tool results cannot be constructed.
- An instrumented SDC adapter independently counts attempted SetService and
  ActivateOperation calls during boundary tests.
- An AST-based architecture check rejects device-write APIs in agent-facing code.

In earlier read-only evaluations, no MCP tools were exported. Since v0.10, dry-run tools can
be exported deliberately through the dry-run configuration, but they still do not execute
device operations.

## Repository layout

```text
config/
  Example gateway configurations, simulation scenarios, SDC-MIE mappings,
  tool-policy files, and example dry-run tool arguments.

docs/
  User guide, design notes, version specifications, dry-run tool documentation,
  MCP server documentation, scenario documentation, and artifact notes.

examples/
  Small example scripts.

scripts/
  PowerShell helper scripts for running evaluations and aggregations.

src/sdc_mcp_gateway/
  Python package implementation.

tests/
  Pytest-based test suite.

data/
  Runtime outputs. Generated files under data/ are ignored by Git except .gitkeep files.
```

## Installation

Recommended development installation:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[all]"
```

For details, see [INSTALLATION.md](INSTALLATION.md).

## Quick sanity checks

Run the test suite:

```powershell
pytest -q
```

Check the read-only MCP resource path:

```powershell
sdc-mcp-gateway mcp-smoke-test `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml

sdc-mcp-gateway mcp-client-smoke-test `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Check the dry-run tool path:

```powershell
sdc-mcp-gateway tool-smoke-test `
  --config config/gateway.simulated.dryrun.example.yaml

sdc-mcp-gateway verify-no-execution `
  --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

The final command combines the independent write spy, device-state digests,
agent-facing static analysis, and exhaustive exploration of the finite abstract
proposal workflow. See [docs/no-execution-boundary.md](docs/no-execution-boundary.md).

## Simulated providers and resources

Discover the simulated providers:

```powershell
sdc-mcp-gateway discover `
  --config config/gateway.simulated.example.yaml
```

List exposed MCP resources:

```powershell
sdc-mcp-gateway list-resources `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Read the gateway health resource:

```powershell
sdc-mcp-gateway read-resource sdc://health `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Read patient-monitor metrics:

```powershell
sdc-mcp-gateway read-resource sdc://devices/sim-monitor-1/metrics `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

Read ventilator metrics:

```powershell
sdc-mcp-gateway read-resource sdc://devices/sim-ventilator-1/metrics `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

## Scenario-based simulation

Available example scenarios include:

```text
config/sim.combined.yaml
config/sim.tachycardia.yaml
config/sim.spo2-drop.yaml
config/sim.high-airway-pressure.yaml
```

Example:

```powershell
sdc-mcp-gateway simulate-snapshot `
  --scenario config/sim.high-airway-pressure.yaml `
  --elapsed-s 100 `
  --mie config/sdc_mie.yaml
```

Scenario-specific gateway configurations are available under:

```text
config/gateway.simulated.tachycardia.example.yaml
config/gateway.simulated.spo2-drop.example.yaml
config/gateway.simulated.high-airway-pressure.example.yaml
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

Generated benchmark outputs are written below `data/experiment_runs/` and are ignored by Git.

## Agent-facing evaluation

The agent-evaluation harness runs natural-language tasks against the exposed resource context
and grades the responses against scenario-specific ground truth.

Run all default tasks for one development scenario using the deterministic resource baseline:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --agent deterministic-baseline `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

Run a single task:

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario airway-pressure `
  --task-id clinical_summary `
  --agent deterministic-baseline `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

Run the same evaluation with Gemini:

```powershell
$env:GEMINI_API_KEY = "your-key"

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

Aggregate agent-evaluation JSON files:

```powershell
sdc-mcp-gateway summarize-agent-evaluations `
  --input-dir data/agent_eval/gemini-v093-final `
  --label gemini-v093-final-summary `
  --pattern "agent-eval-*.json"
```

Generated agent-evaluation outputs are written below `data/agent_eval/` and are ignored by Git.

## BHI 2026 revision pipeline

The revision workflow separates the original development cases from a disabled,
not-yet-defined hold-out phase. Run the complete current development pipeline with:

```powershell
sdc-mcp-gateway run-revision-pipeline `
  --manifest config/bhi2026_revision.yaml `
  --phase development
```

The command writes an anonymous manifest lock and paper-ready JSON, CSV, and
Markdown summaries below `data/revision/development/`. Hold-out execution is
blocked until its inputs are populated, frozen, and explicitly authorized. See
[docs/revision-evaluation.md](docs/revision-evaluation.md).

## Free-question mode

For exploratory, ungraded natural-language questions, use `ask-agent`:

```powershell
sdc-mcp-gateway ask-agent `
  --config config/gateway.simulated.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --agent llm-gemini `
  --llm-model gemini-2.5-flash `
  --question "Is there an active alarm and which device is affected?" `
  --elapsed-s 100
```

`ask-agent` is useful for manual exploration, but it is not a substitute for graded,
reproducible evaluation runs.

## Dry-run MCP tools

Use the dry-run configuration to expose policy-checked action-proposal tools:

```powershell
sdc-mcp-gateway list-tools `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call a valid dry-run tool proposal using an argument file:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_45.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

Call an intentionally invalid proposal:

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_150_invalid.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

The valid call should return `accepted_dry_run` with `executed=false`. The invalid call
should be rejected, for example with `reason=value_out_of_range`.

Run the systematic dry-run tool evaluation:

```powershell
sdc-mcp-gateway evaluate-dry-run-tools `
  --config config/gateway.simulated.dryrun.example.yaml `
  --ack-config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output-dir data/tool_eval `
  --label dryrun-tools-v0106
```

This evaluates accepted and rejected dry-run tool proposals and verifies that all
results preserve `executed=false` and `write_operations_allowed=false`.

Available dry-run tools:

```text
prepare_set_fio2
prepare_set_peep
prepare_acknowledge_alarm
```

Dry-run tools are governed by:

```text
config/tool_policies.yaml
```

Example tool arguments are stored under:

```text
config/tool_args/
```

### Non-executing human authorization

Evaluate the state- and policy-bound proposal lifecycle on seven synthetic cases:

```powershell
python -m sdc_mcp_gateway.revision.human_authorization
```

The workflow records `proposed -> policy_validated -> pending_approval`, followed by
`approved`, `denied`, or `expired`. Approval repeats policy, freshness, version, and snapshot
checks and still returns `executed=false`; it never dispatches an SDC operation. The evidence
suite covers approval, denial, expiry, duplicate approval, stale and changed state, and missing
authorization context. See
[docs/wp10-human-authorization.md](docs/wp10-human-authorization.md).


## Example MCP clients

The repository includes small Python examples that show how custom clients and agent
programs can use the gateway through the MCP Python SDK over stdio:

```powershell
python examples\mcp_client_read_resources.py
python examples\mcp_client_call_dryrun_tool.py
python examples\agent_mcp_client_demo.py --question "Is there an active alarm?"
```

See [docs/MCP_CLIENT_EXAMPLES.md](docs/MCP_CLIENT_EXAMPLES.md). Network MCP server
transport is intentionally out of scope for v0.10.x and planned for a future v2 line.

## MCP server mode

Start the MCP server:

```powershell
sdc-mcp-gateway serve `
  --config config/gateway.simulated.example.yaml `
  --mie config/sdc_mie.yaml
```

For stdio-based MCP servers, no terminal output after startup is normal. The server waits
for MCP client messages on standard input/output.

For dry-run tool exposure, use the dry-run configuration:

```powershell
sdc-mcp-gateway serve `
  --config config/gateway.simulated.dryrun.example.yaml `
  --mie config/sdc_mie.yaml
```

## Real SDC networks

For the hardware-free software-provider testbed used in the BHI revision, run:

```powershell
sdc-mcp-gateway evaluate-sdc-protocol `
  --local-ip <active-local-ipv4> `
  --repetitions 5
```

This starts monitor, ventilator, and heterogeneous `sdc11073` providers in
separate processes and exercises ephemeral mutual TLS, HTTPS/SOAP `GetMdib`,
XML/MDIB processing, mapping, and MCP resource reads. Same-host WS-Discovery
delivery is measured separately and any directed-XAddr fallback is explicit in
the JSON report. See [docs/wp3-sdc-protocol-evidence.md](docs/wp3-sdc-protocol-evidence.md).

For a step-by-step first validation in a real SDC/VPN/lab network, see
[docs/REAL_SDC_TESTING.md](docs/REAL_SDC_TESTING.md). The current MCP server mode is
stdio-based; network-facing MCP transport is planned for a later major version.

## Failure and lifecycle evaluation

Run the deterministic WP4 failure, freshness, recovery, ordering, and alarm
lifecycle suite with:

```powershell
sdc-mcp-gateway evaluate-lifecycle `
  --suite config/wp4_lifecycle_scenarios.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

The 14 scenarios expose source and reception timestamps, age of information,
provider status, sequence/MDIB versions, and explicit `fresh`, `stale`,
`invalid`, `unavailable`, or `recovered` classifications. Dry-run proposals
fail closed for non-current state and for an obsolete snapshot binding.
Duplicate and reordered updates do not replace the latest accepted snapshot.
This is an ordered-event simulator harness, not a production SDC subscription
or clinical alarm implementation. See
[docs/wp4-lifecycle-evidence.md](docs/wp4-lifecycle-evidence.md).

## Formalized SDC-MIE mapping

Validate the versioned mapping and generate coverage for all software SDC
profiles with:

```powershell
sdc-mcp-gateway evaluate-mapping `
  --mie config/sdc_mie.yaml `
  --output data/revision/development/wp5-mapping-evidence.json
```

SDC-MIE 1.0 uses a checked-in JSON Schema plus cross-entry semantic checks for
unique codes/handles, unit consistency, numeric bounds, access and safety
classification, provenance, and human-approval metadata. Loaded mappings carry
the SHA-256 of the exact source file. Observed elements are explicitly
`mapped`, `unmapped`, `unsupported`, or `conflicting`; ambiguous mappings fail
closed. See [docs/sdc-mie.md](docs/sdc-mie.md) and
[docs/wp5-mapping-evidence.md](docs/wp5-mapping-evidence.md).

A real SDC network can be configured through a local, untracked configuration file such as:

```text
config/gateway.local.yaml
```

This file must not be committed. It may include local VPN interface addresses, provider
selection, and future TLS settings.

Example template:

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

If WS-Discovery does not work through a VPN, a future direct-connect configuration may be
needed. Vendor-specific credentials, certificates, and VPN configuration must never be
committed.

## Development workflow

Run tests:

```powershell
pytest -q
```

Run selected tests:

```powershell
pytest tests/test_dry_run_tools.py -q
```

Run linting if `ruff` is installed:

```powershell
ruff check .
```

Generated outputs under `data/` should not be committed.

## Citation

If you use this software, cite the associated paper or the software artifact. A
`CITATION.cff` file is provided for citation metadata.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Disclaimer

This project is a research prototype. It is not approved or validated for clinical use.
It does not provide medical advice, clinical decision support, autonomous therapy, or
real medical-device control.
