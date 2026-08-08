# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-deterministic-resource-baseline-r1-holdout-invalid-stale-20260808T152332_595461Z`
- Agent: `deterministic-baseline`
- Status: `ok`
- Passed tasks: 6/6
- Resource count: 8

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | Exposed devices: holdout-monitor-quality |
| `alarm_detection` | `alarm_detection` | True | No active alarm is present. |
| `clinical_summary` | `clinical_summary` | True | - holdout-monitor-quality: heart_rate: 74.0 beats/min, spo2: 98.0 %<br>- No active alarm is currently present. |
| `metrics_resource_selection` | `resource_selection` | True | I would read sdc://devices/holdout-monitor-quality/metrics. |
| `stale_metric_detection` | `freshness_detection` | True | Stale metrics: metric.hr.stale |
| `invalid_sensor_detection` | `invalid_state_detection` | True | Invalid metrics: metric.spo2.invalid |
