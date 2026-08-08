# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r3-holdout-unavailable-20260808T151904_269431Z`
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
| `alarm_detection` | `alarm_detection` | True | No active alarms detected. |
| `clinical_summary` | `clinical_summary` | True | No active alarms detected. Gateway health is OK. No devices currently connected.<br>Gateway health status: OK.<br>No active alarms present.<br>No devices connected to the gateway.<br>Resource catalogue and mapping documents are available for reference.<br>System is operating in read‑only mode with no write operations allowed. |
| `metrics_resource_selection` | `resource_selection` | True | Target device not found; no metrics resource available. |
| `provider_availability` | `availability_detection` | True | No devices currently available. |
