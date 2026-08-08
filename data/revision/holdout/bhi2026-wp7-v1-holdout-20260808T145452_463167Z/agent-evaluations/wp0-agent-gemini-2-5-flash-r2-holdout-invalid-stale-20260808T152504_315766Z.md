# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-gemini-2-5-flash-r2-holdout-invalid-stale-20260808T152504_315766Z`
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
| `alarm_detection` | `alarm_detection` | True | No active alarms detected. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor is connected. Peripheral oxygen saturation (SpO2) data is currently invalid. Heart rate is reported as 74 beats/min, but this data is stale. There are no active alarms.<br>The Reference Data-Quality Monitor is connected and providing data.<br>Peripheral oxygen saturation (SpO2) data is currently invalid.<br>Heart rate is reported as 74 beats/min, but the data is stale.<br>No active alarms are present on the device. |
| `metrics_resource_selection` | `resource_selection` | True | The URI for the metrics resource of the specified device was selected based on matching the device ID and resource kind. |
| `stale_metric_detection` | `freshness_detection` | True | The following metrics are explicitly marked as stale: Heart rate (metric.hr.stale). |
| `invalid_sensor_detection` | `invalid_state_detection` | True | The following metrics have an invalid validity state: Peripheral oxygen saturation (metric.spo2.invalid). |
