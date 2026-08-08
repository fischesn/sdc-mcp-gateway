# Agent evaluation: holdout-unavailable

- Run ID: `wp0-agent-gemini-2-5-flash-r2-holdout-unavailable-20260808T151755_060780Z`
- Agent: `llm-gemini`
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
| `device_inventory` | `device_inventory` | True | No SDC devices are currently exposed by the gateway. |
| `alarm_detection` | `alarm_detection` | True | No active alarms were detected in the provided resource context. |
| `clinical_summary` | `clinical_summary` | True | The system health is reported as 'ok'. No medical devices are currently connected or reporting data through the gateway. There are no active alarms detected by the system. The system is operating in a read-only mode, providing access to global resources like gateway health and resource listings.<br>System health is reported as "ok".<br>No medical devices are currently connected or reporting data through the gateway.<br>There are no active alarms detected by the system.<br>The system is operating in a read-only mode, providing access to global resources like gateway health and resource listings. |
| `metrics_resource_selection` | `resource_selection` | True | The target device or its metrics resource is not available in the provided resource context. |
| `provider_availability` | `availability_detection` | True | No device state is currently available. The device list is empty, and the system reports 0 connected devices. |
