# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-openai-gpt-4-1-mini-r1-holdout-unavailable-20260808T151658_719627Z`
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
| `alarm_detection` | `alarm_detection` | True | No active alarms detected. |
| `clinical_summary` | `clinical_summary` | True | No active alarms or device metrics are currently reported by the system.<br>No active alarms are present in the system.<br>There are no connected or recognized medical devices at this time.<br>No device metrics or vital signs are currently available.<br>The system status is reported as 'ok' with no errors.<br>The gateway and resource catalogue are accessible but show no active device data. |
| `metrics_resource_selection` | `resource_selection` | True | No metrics resource URI is available for the target device as it is not present in the resource context. |
| `provider_availability` | `availability_detection` | True | No current device state is available as the device list is empty and no devices are reported. |
