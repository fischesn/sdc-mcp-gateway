# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-digital-hub-qwen-3-6-27b-r1-holdout-unavailable-20260808T152042_053073Z`
- Agent: `llm-openai-compatible`
- Status: `ok`
- Passed tasks: 5/5
- Resource count: 4

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | There are currently no SDC devices exposed by the gateway. |
| `alarm_detection` | `alarm_detection` | True | No active alarms are currently reported. The active alarms list is empty and the gateway health status indicates 'ok'. |
| `clinical_summary` | `clinical_summary` | True | The SDC-to-MCP gateway is operating in read-only mode with no connected medical devices or active alarms. All exposed resources are global system metadata, and the gateway health status reports as ok.<br>The gateway is currently operating in read-only mode with a reported health status of ok.<br>No medical devices are currently connected or registered in the system.<br>There are no active alarms or device-specific metrics available for review.<br>All four exposed resources consist of global system metadata, including gateway health, resource catalogues, device lists, and semantic mapping documents. |
| `metrics_resource_selection` | `resource_selection` | True | The target device is not present in the resource context, so no metrics URI exists. |
| `provider_availability` | `availability_detection` | True | No devices are currently available. The device list is empty and the health status reports a device count of 0. |
