# SDC-to-MCP Gateway

Research prototype for exposing IEEE 11073 SDC device state as Model Context Protocol (MCP) resources.

This repository currently contains **v0.1-read-only**. It is deliberately limited to read-only access:

- SDC device discovery is represented by an adapter interface.
- A dummy SDC consumer is included for local development and tests.
- A real `sdc11073` adapter stub is provided, but not yet completed.
- MCP resources expose devices, metrics, alarms, context, raw MDIB snapshots, and the SDC-MIE mapping.
- No SDC operation is executed.
- No MCP tool is exported in v0.1.
- No clinical use is intended or permitted.

## Repository layout

```text
sdc-mcp-gateway/
  config/                  Example gateway, mapping, and policy files
  docs/                    v0.1 specification and implementation notes
  examples/                Small local demos
  src/sdc_mcp_gateway/     Python package
  tests/                   Unit tests
  data/                    Local logs and experiment outputs, ignored by Git in a real repo
```

## Installation for local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

The real SDC adapter will later require `sdc11073`. For now, the default path uses the built-in dummy consumer.

## Run a local dummy snapshot

```bash
python -m sdc_mcp_gateway snapshot --mie config/sdc_mie.yaml
```

## Run the MCP server with dummy data

```bash
python -m sdc_mcp_gateway serve --mie config/sdc_mie.yaml
```

This requires the Python MCP SDK. If it is not installed, the package will explain the missing dependency.

## Run tests

```bash
pytest
```

## Safety status

This prototype is a research scaffold only. It is not a medical device, not a clinical decision support system, and not suitable for clinical operation. It must only be used in isolated laboratory and demonstration environments.
