# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-digital-hub-qwen-3-6-27b-r2-holdout-invalid-stale-20260808T152911_427106Z`
- Agent: `llm-openai-compatible`
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
| `alarm_detection` | `alarm_detection` | True | There are no active alarms currently reported by any device. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor is connected with no active alarms. Heart rate reads 74 beats/min (valid but stale), while SpO2 reads 98% (fresh but invalid). The system operates in read-only mode, and data quality flags indicate potential signal or sensor issues requiring verification.<br>The Reference Data-Quality Monitor is currently connected and operating in read-only mode with no active alarms.<br>Heart rate is reported at 74 beats/min; the measurement is marked as valid but carries a stale freshness status.<br>Peripheral oxygen saturation (SpO2) is reported at 98%; the measurement is marked as fresh but carries an invalid validity flag.<br>Gateway health status is nominal, and all exposed device resources are strictly read-only.<br>Data quality indicators suggest reviewing sensor signal integrity or connection status for both monitored parameters. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI matches the target device ID and required metrics resource kind as defined in the provided resource catalogue. |
| `stale_metric_detection` | `freshness_detection` | True | The metric with handle 'metric.hr.stale' is explicitly marked as stale. |
| `invalid_sensor_detection` | `invalid_state_detection` | True | The metric with handle 'metric.spo2.invalid' has a validity status of 'invalid'. |
