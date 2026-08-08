# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-deterministic-resource-baseline-r1-holdout-unmapped-20260808T151106_482127Z`
- Agent: `deterministic-baseline`
- Status: `ok`
- Passed tasks: 5/5
- Resource count: 8

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | Exposed devices: holdout-monitor-unmapped |
| `alarm_detection` | `alarm_detection` | True | No active alarm is present. |
| `clinical_summary` | `clinical_summary` | True | - holdout-monitor-unmapped: heart_rate: 76.0 beats/min, None: 4.2 arb<br>- No active alarm is currently present. |
| `metrics_resource_selection` | `resource_selection` | True | I would read sdc://devices/holdout-monitor-unmapped/metrics. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | Unmapped codes: vendor.perfusion.index.x7 |
