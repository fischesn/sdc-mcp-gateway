# Installation Guide for the SDC-to-MCP Gateway v0.7.1

This document describes how to set up a local Python virtual environment and install all dependencies required for the current read-only research prototype.

Version v0.7.1 is still strictly read-only. It includes the simulated SDC-like provider testbed, optional `sdc11073` discovery/snapshot support, MCP resource exposure, MCP client smoke tests, and repeatable benchmark logging. It does not execute SDC operations and exports no MCP tools.

## 1. Prerequisites

Use Python 3.11, 3.12, 3.13, or 3.14. Python 3.14 is acceptable for this prototype because the current `sdc11073` package line used here supports Python `>=3.10,<3.15`.

Recommended tools:

- Python 3.14 if this is already installed on your system; otherwise Python 3.11 or newer
- Git, strongly recommended
- A terminal: PowerShell on Windows, Terminal on macOS/Linux

Check your Python version:

```bash
python --version
```

On some systems, especially Linux/macOS, the executable may be called `python3` or `python3.14`:

```bash
python3 --version
python3.14 --version
```

## 2. Unpack or clone the repository

If you received the ZIP archive, unpack it and enter the project directory:

```bash
cd sdc-mcp-gateway-v0.7.1
```

All commands below assume that you are in the repository root, i.e., the directory containing `pyproject.toml`.

## 3. Create a virtual environment

### Windows PowerShell with Python 3.14

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
```

If PowerShell blocks activation scripts, run this once for your user account:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate the environment again:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Windows CMD with Python 3.14

```cmd
py -3.14 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
```

### macOS/Linux with Python 3.14

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

If your system uses a different executable name, first inspect available Python installations, for example:

```bash
python3 --version
which python3.14
```

For older, but still supported, installations replace `3.14` with `3.13`, `3.12`, or `3.11` in the commands above.

## 4. Install the package

### Minimal development installation

This is the recommended installation for dummy-mode development and unit tests:

```bash
python -m pip install -e ".[dev]"
```

This installs the gateway in editable mode and adds the development tools required for tests and linting.

### Installation with MCP support

Use this when you want to run the MCP server interface rather than only the local snapshot demo:

```bash
python -m pip install -e ".[mcp,dev]"
```

### Installation with real SDC snapshot support

Use this if you want to test provider discovery and one-shot MDIB snapshots with `sdc11073`:

```bash
python -m pip install -e ".[sdc,dev]"
```

This installs `sdc11073>=2.4.1,<3.0`. The upper bound is intentional for now: the real-SDC adapter targets the stable 2.x API, not a future incompatible major release.

### Full installation

For convenience, all optional dependencies can be installed with:

```bash
python -m pip install -e ".[all]"
```

If your shell treats square brackets specially, keep the quotes around the package specifier.

## 5. Verify the installation

Run the test suite:

```bash
pytest -q
```

Expected result for v0.7.1:

```text
20 passed
```

Show the command-line help:

```bash
sdc-mcp-gateway --help
```

Print the read-only dummy resource snapshot:

```bash
sdc-mcp-gateway snapshot --config config/gateway.yaml --mie config/sdc_mie.yaml
```

Alternative without relying on the installed console script:

```bash
python -m sdc_mcp_gateway snapshot --config config/gateway.yaml --mie config/sdc_mie.yaml
```


Print a simulated multi-device snapshot without SDC networking:

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.combined.yaml --elapsed-s 10 --mie config/sdc_mie.yaml
```

Exercise the regular gateway path with the simulated adapter:

```bash
sdc-mcp-gateway discover --config config/gateway.simulated.example.yaml
sdc-mcp-gateway snapshot --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

Run the MCP resource smoke test:

```bash
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

If you installed the optional MCP SDK and want the smoke test to fail when the SDK is missing, add `--require-mcp-sdk`:

```bash
sdc-mcp-gateway mcp-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --require-mcp-sdk
```

Run the example script:

```bash
python examples/read_only_demo.py
```

Verify the optional SDC dependency if installed:

```bash
python -c "import sdc11073; print('sdc11073 import ok')"
```

## 6. Configuration files

The repository contains configuration templates and defaults. These files should stay in Git:

```text
config/gateway.yaml
config/gateway.sdc11073.example.yaml
config/gateway.simulated.example.yaml
config/sim.patient-monitor.yaml
config/sim.ventilator.yaml
config/sim.combined.yaml
config/sdc_mie.yaml
config/policies.yaml
config/README.md
```

Their roles are:

- `gateway.yaml`: default read-only dummy configuration for local development and tests
- `gateway.sdc11073.example.yaml`: template for real SDC discovery and snapshot tests
- `gateway.simulated.example.yaml`: template for in-process simulated device scenarios
- `sim.*.yaml`: reproducible simulated patient-monitor and ventilator scenarios
- `sdc_mie.yaml`: semantic mappings from SDC/BICEPS/nomenclature elements to agent-readable names
- `policies.yaml`: read-only safety policy; all write/tool operations remain denied in v0.7.1
- `config/README.md`: short explanation of the configuration workflow

The following file is intentionally not included and must not be committed:

```text
config/gateway.local.yaml
```

It may contain your local VPN IP address, provider identifiers, device filters, or other lab-specific details. It is listed in `.gitignore`.


## 7. Simulated device tests without a real SDC network

The v0.7.1 simulator is useful while no real SDC network is available. It is not a networked IEEE 11073 SDC Provider. It generates normalized SDC-like snapshots in-process and therefore tests the mapping, resource, logging, and later agent-facing parts of the gateway.

Direct scenario run:

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.patient-monitor.yaml --elapsed-s 0 --mie config/sdc_mie.yaml
sdc-mcp-gateway simulate-snapshot --scenario config/sim.ventilator.yaml --elapsed-s 30 --mie config/sdc_mie.yaml
sdc-mcp-gateway simulate-snapshot --scenario config/sim.combined.yaml --elapsed-s 60 --mie config/sdc_mie.yaml
```

Regular gateway path using the simulated adapter:

```bash
sdc-mcp-gateway discover --config config/gateway.simulated.example.yaml
sdc-mcp-gateway snapshot --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

For local experiments you may copy the simulated template as a local configuration:

```bash
cp config/gateway.simulated.example.yaml config/gateway.local.yaml
```

Windows PowerShell:

```powershell
Copy-Item config/gateway.simulated.example.yaml config/gateway.local.yaml
```

Then edit `config/gateway.local.yaml`, for example to switch between `sim.patient-monitor.yaml`, `sim.ventilator.yaml`, and `sim.combined.yaml`.

## 8. Real SDC discovery and snapshot test


After installing with `.[sdc,dev]` or `.[all]`, create a local configuration from the template.

Linux/macOS:

```bash
cp config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

Windows PowerShell:

```powershell
Copy-Item config/gateway.sdc11073.example.yaml config/gateway.local.yaml
```

Then edit `config/gateway.local.yaml`:

```yaml
sdc:
  adapter: "sdc11073"
  local_ip: "YOUR_LOCAL_SDC_VPN_OR_LAB_INTERFACE_IPV4"
  max_devices: 1
  provider_whitelist: []
```

`local_ip` is the IPv4 address of the network interface on which the gateway process runs. In a Dräger-provided SDC VPN, this is normally your own VPN adapter address, not the address of a medical device.

Run discovery:

```bash
sdc-mcp-gateway discover --config config/gateway.local.yaml
```

Capture a read-only snapshot:

```bash
sdc-mcp-gateway snapshot --config config/gateway.local.yaml --mie config/sdc_mie.yaml
```

The adapter only reads provider metadata and MDIB state. It does not execute Service Control Object operations.

## 9. Git workflow and avoiding accidental local-config commits

Before committing, inspect the status:

```bash
git status
```

You should see the template files under `config/`, but not `config/gateway.local.yaml`.

If `gateway.local.yaml` was accidentally added, unstage it:

```bash
git rm --cached config/gateway.local.yaml
```

Do not use a broad `.gitignore` entry such as `config/*.yaml`; that would hide the important templates from Git. The intended rule is precise:

```gitignore
config/gateway.local.yaml
```

## 10. Deactivation and cleanup

Deactivate the virtual environment:

```bash
deactivate
```

Remove the virtual environment completely:

```bash
rm -rf .venv
```

On Windows PowerShell:

```powershell
Remove-Item -Recurse -Force .venv
```

## 11. Troubleshooting

### `python` points to the wrong version

Use an explicit launcher:

```powershell
py -3.14 --version
py -3.14 -m venv .venv
```

or on Linux/macOS:

```bash
python3.14 --version
python3.14 -m venv .venv
```

### Activation fails on Windows

Use:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then reopen PowerShell or reactivate the environment.

### `pip install -e ".[all]"` fails

First upgrade the packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

Then retry the installation. If the failure concerns `sdc11073`, use the minimal installation first:

```bash
python -m pip install -e ".[dev]"
```

### `sdc-mcp-gateway` command not found

Use the module form:

```bash
python -m sdc_mcp_gateway --help
```

If that works, the package is installed but the console-script path is not visible in your shell. Reactivate the virtual environment.


## Benchmark and experiment logging

Run a short simulated benchmark:

```bash
sdc-mcp-gateway benchmark --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --iterations 5 --warmup 1 --output-dir data/experiment_runs --label local-smoke
```

The benchmark writes JSONL, CSV, and summary JSON files into `data/experiment_runs/`. These files are local experiment output and are ignored by Git.

For paper-oriented runs, use more iterations, for example:

```bash
sdc-mcp-gateway benchmark --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml --iterations 100 --warmup 10 --output-dir data/experiment_runs --label simulated-baseline
```

## 12. Safety note

This repository is a research prototype. v0.7.1 is read-only. It must not be used for clinical operation, patient treatment, clinical decision-making, clinical studies, or uncontrolled access to real medical devices.


Run the end-to-end MCP client smoke test. This requires the optional MCP SDK and
starts the stdio MCP server as a subprocess:

```bash
sdc-mcp-gateway mcp-client-smoke-test --config config/gateway.simulated.example.yaml --mie config/sdc_mie.yaml
```

The expected result is a JSON report with `"status": "ok"`, listed MCP resources,
readable sample resources, and `"tool_count": 0`.


## Aggregating benchmark results

After running several benchmarks, use:

```powershell
sdc-mcp-gateway summarize-benchmarks --input-dir data/experiment_runs --label simulated-v06-summary
```

The command reads `*.summary.json` files and writes aggregate JSON/CSV files in the same directory unless `--output-dir` is specified.

## Running the v0.7 scenario examples

After installation, the scenario files can be tested without any real SDC network:

```powershell
sdc-mcp-gateway simulate-snapshot --scenario config/sim.tachycardia.yaml --elapsed-s 60 --mie config/sdc_mie.yaml
sdc-mcp-gateway simulate-snapshot --scenario config/sim.spo2-drop.yaml --elapsed-s 70 --mie config/sdc_mie.yaml
sdc-mcp-gateway simulate-snapshot --scenario config/sim.high-airway-pressure.yaml --elapsed-s 60 --mie config/sdc_mie.yaml
```

For scenario-specific benchmarks:

```powershell
sdc-mcp-gateway benchmark --config config/gateway.simulated.tachycardia.example.yaml --mie config/sdc_mie.yaml --iterations 100 --warmup 10 --label tachycardia-v07
sdc-mcp-gateway benchmark --config config/gateway.simulated.spo2-drop.example.yaml --mie config/sdc_mie.yaml --iterations 100 --warmup 10 --label spo2-drop-v07
sdc-mcp-gateway benchmark --config config/gateway.simulated.high-airway-pressure.example.yaml --mie config/sdc_mie.yaml --iterations 100 --warmup 10 --label high-airway-pressure-v07
```

Custom scenario authoring is described in `docs/scenarios.md`.


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
