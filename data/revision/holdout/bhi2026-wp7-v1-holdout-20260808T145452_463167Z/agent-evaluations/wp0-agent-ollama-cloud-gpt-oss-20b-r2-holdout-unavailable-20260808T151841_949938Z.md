# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r2-holdout-unavailable-20260808T151841_949938Z`
- Agent: `llm-ollama`
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
| `device_inventory` | `device_inventory` | True | No devices are currently exposed by the gateway. |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms detected in the current system state. |
| `clinical_summary` | `clinical_summary` | True | No active alarms or devices are present; gateway health is OK.<br>Gateway health status is OK with no active alarms.<br>No medical devices are currently connected or exposed.<br>Resource catalogue lists four global resources: Gateway health, Resource catalogue, Device list, SDC-MIE mapping.<br>Mapping schema version 1.0.0 and SHA256 provided.<br>System is in read-only mode; no write operations allowed. |
| `metrics_resource_selection` | `resource_selection` | True | No metrics resource available for the target device. |
| `provider_availability` | `availability_detection` | True | No devices currently available. |
