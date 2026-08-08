# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r2-holdout-invalid-stale-20260808T152557_963190Z`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device: Reference Data-Quality Monitor (device ID: holdout-monitor-quality). |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms at this time. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor reports a peripheral oxygen saturation (SpO₂) value of 98 % that is marked as invalid, and a heart rate of 74 beats/min that is considered stale. No active alarms are present. The device is connected and its data are currently considered fresh for the SpO₂ metric but stale for the heart rate metric. Overall system health is reported as OK.<br>Peripheral oxygen saturation (SpO₂) value of 98 % is flagged as invalid.<br>Heart rate value of 74 beats/min is flagged as stale.<br>No active alarms are currently present.<br>Device is connected and reporting data.<br>System health status is OK. |
| `metrics_resource_selection` | `resource_selection` | True | Selected metrics resource for device holdout-monitor-quality. |
| `stale_metric_detection` | `freshness_detection` | True | The following metric is marked stale: metric.hr.stale |
| `invalid_sensor_detection` | `invalid_state_detection` | True | Metric with handle 'metric.spo2.invalid' has validity 'invalid' and should be treated as unreliable. |
