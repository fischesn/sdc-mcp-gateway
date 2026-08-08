# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r1-holdout-unavailable-20260808T151825_624709Z`
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
| `alarm_detection` | `alarm_detection` | True | There are no active alarms at this time. |
| `clinical_summary` | `clinical_summary` | True | The gateway is operating in read‑only mode with no active alarms and no devices currently exposed. The health status reports OK, and the mapping document is at version 1.0.0.<br>Gateway health status is OK.<br>No active alarms are present.<br>No devices are currently listed.<br>Mapping schema version is 1.0.0.<br>System is in read‑only mode with write operations disabled. |
| `metrics_resource_selection` | `resource_selection` | True | No metrics resource exists for the target device. |
| `provider_availability` | `availability_detection` | True | No devices currently available. |
