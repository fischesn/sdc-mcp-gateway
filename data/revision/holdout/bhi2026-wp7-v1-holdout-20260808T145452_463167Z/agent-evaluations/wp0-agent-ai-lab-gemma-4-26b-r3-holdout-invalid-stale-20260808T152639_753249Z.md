# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-ai-lab-gemma-4-26b-r3-holdout-invalid-stale-20260808T152639_753249Z`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing one SDC device: Reference Data-Quality Monitor (device_id: holdout-monitor-quality). |
| `alarm_detection` | `alarm_detection` | True | No active alarms were detected in the provided resource context. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor is currently connected and reporting metrics, though data quality issues are present.<br>The heart rate is reported at 74.0 beats/min, but the data is flagged as stale.<br>The peripheral oxygen saturation (spo2) is reported at 98.0%, but the validity is marked as invalid.<br>No active alarms are currently reported by the device.<br>The device status is connected and the gateway health is reported as ok. |
| `metrics_resource_selection` | `resource_selection` | True | The requested URI is the specific metrics resource for the target device ID. |
| `stale_metric_detection` | `freshness_detection` | True | The following metric is explicitly marked as stale: Heart rate (handle: metric.hr.stale). |
| `invalid_sensor_detection` | `invalid_state_detection` | True | The metric with handle 'metric.spo2.invalid' (Peripheral oxygen saturation) has a validity status of 'invalid'. |
