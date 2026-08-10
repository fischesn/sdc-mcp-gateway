# Agent evaluation: holdout-unavailable

- Run ID: `consolidated-deterministic-holdout-unavailable-20260810T153300_297612Z`
- Agent: `deterministic-baseline`
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
| `device_inventory` | `device_inventory` | True | No devices are exposed. |
| `alarm_detection` | `alarm_detection` | True | No active alarm is present. |
| `clinical_summary` | `clinical_summary` | True | - No active alarm is currently present. |
| `metrics_resource_selection` | `resource_selection` | True | No matching resource URI is available. |
| `provider_availability` | `availability_detection` | True | Device state is unavailable. |
