# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r3-holdout-invalid-stale-20260808T152619_175072Z`
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
| `alarm_detection` | `alarm_detection` | True | No active alarms detected. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor reports a heart rate of 74 beats/min that is considered stale, indicating the value may not reflect the current patient state. Peripheral oxygen saturation (SpO₂) is reported as 98% but is marked invalid, suggesting the measurement may be unreliable. No active alarms are currently triggered by the device. The device is connected and its data is considered valid for the heart rate metric, though the freshness status is stale. Overall, the device is functioning but the key vital signs may not be up-to-date or reliable.<br>Heart rate 74 beats/min is stale, meaning it may not reflect the current patient state.<br>SpO₂ 98 % is invalid, indicating the measurement may be unreliable.<br>No active alarms are present on the device.<br>The device is connected and its data is considered valid for the heart rate metric, but freshness is stale.<br>The device is operating in read‑only mode with no write operations allowed. |
| `metrics_resource_selection` | `resource_selection` | True | The URI corresponds to the metrics resource for the specified device. |
| `stale_metric_detection` | `freshness_detection` | True | The following metric is marked stale: metric.hr.stale |
| `invalid_sensor_detection` | `invalid_state_detection` | True | The metric with handle "metric.spo2.invalid" has a validity status of "invalid" and should be flagged as unreliable. |
