# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r1-holdout-invalid-stale-20260808T152539_539568Z`
- Agent: `llm-ollama`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device: holdout-monitor-quality. |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms in the current state. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor reports a heart rate of 74 beats/min that is marked as stale, indicating the value may not reflect the current patient state. Peripheral oxygen saturation is reported as 98 % but is flagged as invalid, suggesting the measurement may be unreliable. No active alarms are present on the device. The device is connected and its data are considered fresh overall, but the specific metrics have quality issues. The gateway health status is OK and the device is in read‑only mode.<br>Heart rate 74 beats/min is stale, may not be current.<br>SpO₂ 98 % is invalid, measurement unreliable.<br>No active alarms on the device.<br>Device is connected and data overall fresh.<br>Gateway health status is OK. |
| `metrics_resource_selection` | `resource_selection` | True | The URI corresponds to the metrics resource for the specified device. |
| `stale_metric_detection` | `freshness_detection` | True | Stale metrics identified: metric.hr.stale |
| `invalid_sensor_detection` | `invalid_state_detection` | True | One metric has invalid validity: metric.spo2.invalid. |
