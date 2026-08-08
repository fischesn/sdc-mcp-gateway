# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-gemini-2-5-flash-r1-holdout-invalid-stale-20260808T152445_514523Z`
- Agent: `llm-gemini`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing the following SDC device: Reference Data-Quality Monitor (holdout-monitor-quality). |
| `alarm_detection` | `alarm_detection` | True | No active alarms were detected. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor is connected and operational. The Peripheral oxygen saturation (SpO2) is reported as 98% but is marked as invalid. The Heart rate is 74 beats/min, which is valid but stale.<br>The Reference Data-Quality Monitor is connected and reporting.<br>Peripheral oxygen saturation (SpO2) is 98%, but the validity of this measurement is currently invalid.<br>Heart rate is 74 beats/min, however, this reading is stale.<br>There are no active alarms reported by the device. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the target device ID and type. |
| `stale_metric_detection` | `freshness_detection` | True | The following metrics are explicitly marked as stale: Heart rate (metric.hr.stale). |
| `invalid_sensor_detection` | `invalid_state_detection` | True | The following metrics have a validity status that is not 'valid': metric.spo2.invalid. |
