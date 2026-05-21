# SDC-to-MCP Gateway

Research prototype for exposing IEEE 11073 SDC device state as Model Context Protocol (MCP) resources.

This repository currently contains **v0.4.1-simulated-sdc-provider-testbed**. It remains deliberately limited to read-only access:

- A deterministic dummy SDC consumer is included for local development and tests.
- A reproducible in-process simulated SDC-like provider testbed is included for patient monitor and ventilator scenarios.
- A real `sdc11073` adapter can discover providers and capture one-shot MDIB snapshots.
- MCP resources expose devices, metrics, alarms, context, raw MDIB summaries, and the SDC-MIE mapping.
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
config/gateway.simulated.example.yaml  # template for in-process simulated device scenarios
config/sim.patient-monitor.yaml        # simulated patient monitor scenario
config/sim.ventilator.yaml             # simulated ventilator scenario
config/sim.combined.yaml               # combined multi-device simulation scenario
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

The v0.4.1 simulator does **not** open a real IEEE 11073 SDC network endpoint. It generates normalized SDC-like device snapshots in-process so that mapping, MCP resources, and logging can be developed without real devices.

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

Expected result for v0.4.1:

```text
17 passed
```

## Recommended Git workflow

For a clean version history:

```bash
git init
git branch -M main
git add .
git commit -m "Add simulated SDC-like provider testbed v0.4.1"
git tag -a v0.4.1 -m "v0.4.1 simulated SDC-like provider testbed"
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
