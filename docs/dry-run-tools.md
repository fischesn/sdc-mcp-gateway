# Dry-run MCP tools

Dry-run tools are the first active MCP affordances in the SDC-to-MCP gateway prototype. They are designed to let an agent propose and validate actions without granting authority to change a medical device state.

## Why dry-run tools?

MCP resources are passive. They expose context such as devices, metrics, alarms, mapping information, and gateway health. MCP tools are active functions. In a medical-device setting, exposing write-capable tools directly to an LLM would be unsafe. Therefore v0.10 exposes only dry-run tools.

A dry-run tool validates the request, records the result, and returns a structured response. It never sends SDC operations to a device.

## Configuration

Use:

```text
config/gateway.simulated.dryrun.example.yaml
config/tool_policies.yaml
```

The gateway configuration must explicitly enable tools while keeping writes disabled:

```yaml
gateway:
  mode: "dry-run-tools"
  allow_tools: true
  allow_write_operations: false
```

The policy file defines the available tools, target device type, semantic metric, allowed value range, units, and whether human approval is required.

## Example accepted dry-run

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_45.json `
  --config config/gateway.simulated.dryrun.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

The older `--args-json` form remains available, but `--args-file` is preferred on Windows/PowerShell and for reproducible experiments.

The response should contain:

```json
{
  "status": "accepted_dry_run",
  "operation": "set_fio2",
  "requested_value": 45.0,
  "allowed_range": [21.0, 100.0],
  "requires_human_approval": true,
  "executed": false
}
```

## Example rejected dry-run

```powershell
sdc-mcp-gateway call-tool prepare_set_fio2 `
  --args-file config/tool_args/set_fio2_150_invalid.json `
  --config config/gateway.simulated.dryrun.example.yaml
```

The response should contain:

```json
{
  "status": "rejected",
  "reason": "value_out_of_range",
  "executed": false
}
```

## Audit log

Dry-run tool calls are recorded as `tool_dry_run` events in the configured JSONL log file. The audit record includes the tool name, arguments, validation status, reason, policy version, and explicit `executed: false` field.

## Limitations

v0.10 does not implement real SDC SetService, ActivateOperation, alarm acknowledgement, user authentication, or human-approval UI. Those are future work and require a controlled real SDC testbed.
