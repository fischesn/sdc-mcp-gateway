# Installation Guide for the SDC-to-MCP Gateway v0.1

This document describes how to set up a local Python virtual environment and install all dependencies required for the current read-only research prototype.

Version v0.1 is intentionally limited to dummy/read-only operation. It does not yet connect to real SDC-capable medical devices. The real `sdc11073` adapter is prepared as a stub and will be implemented in v0.2.

## 1. Prerequisites

Use Python 3.11, 3.12, 3.13, or 3.14. For the planned v0.2 SDC adapter, Python 3.14 is acceptable because the current `sdc11073` package declares support for Python `>=3.10,<3.15` and lists Python 3.14 among its supported classifiers.

Recommended tools:

- Python 3.14 if this is already installed on your system; otherwise Python 3.11 or newer
- Git, optional but recommended
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
cd sdc-mcp-gateway
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

### Minimal development installation for v0.1

This is the recommended installation for the current read-only prototype:

```bash
python -m pip install -e ".[dev]"
```

This installs the gateway in editable mode and adds the development tools required for tests and linting.

### Installation with MCP support

Use this when you want to run the MCP server interface rather than only the local snapshot demo:

```bash
python -m pip install -e ".[mcp,dev]"
```

### Installation with future SDC dependencies

The real SDC adapter is scheduled for v0.2. You can already install the optional SDC dependency, but v0.1 will still not perform real device discovery:

```bash
python -m pip install -e ".[sdc,dev]"
```

This installs `sdc11073>=2.4.1,<3.0`. The upper bound is intentional for now: v0.2 will initially target the stable 2.x API, not the 3.0 alpha/pre-release line.

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

Expected result for v0.1:

```text
6 passed
```

Show the command-line help:

```bash
sdc-mcp-gateway --help
```

Print the read-only dummy resource snapshot:

```bash
sdc-mcp-gateway snapshot
```

Alternative without relying on the installed console script:

```bash
python -m sdc_mcp_gateway snapshot
```

Run the example script:

```bash
python examples/read_only_demo.py
```

Verify the optional SDC dependency if installed:

```bash
python -c "import sdc11073; print('sdc11073 import ok')"
```

## 6. Important configuration files

The default configuration files are:

```text
config/gateway.yaml
config/sdc_mie.yaml
config/policies.yaml
```

Their roles are:

- `gateway.yaml`: gateway mode, logging path, SDC adapter selection, MCP transport settings
- `sdc_mie.yaml`: semantic mappings from SDC/BICEPS/nomenclature elements to agent-readable names
- `policies.yaml`: read-only safety policy for v0.1; all write/tool operations are denied

For v0.1, the default SDC adapter should remain:

```yaml
sdc:
  adapter: dummy
```

Do not switch to `sdc11073` yet unless you are deliberately testing the not-yet-implemented v0.2 adapter stub.

## 7. Deactivation and cleanup

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

## 8. Troubleshooting

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

Then retry the installation. If the failure concerns `sdc11073`, use the v0.1 minimal installation instead:

```bash
python -m pip install -e ".[dev]"
```

### `sdc-mcp-gateway` command not found

Use the module form:

```bash
python -m sdc_mcp_gateway --help
```

If that works, the package is installed but the console-script path is not visible in your shell. Reactivate the virtual environment.

## 9. Safety note

This repository is a research prototype. v0.1 is read-only and uses a dummy SDC consumer. It must not be used for clinical operation, patient treatment, clinical decision-making, or uncontrolled access to real medical devices.
