# Agent evaluation: holdout-invalid-stale

- Run ID: `wp0-agent-openai-gpt-4-1-mini-r3-holdout-invalid-stale-20260808T152412_921682Z`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device with the device ID 'holdout-monitor-quality', named 'Reference Data-Quality Monitor'. |
| `alarm_detection` | `alarm_detection` | True | No active alarms are present. The holdout-monitor-quality device has no active alarms reported. |
| `clinical_summary` | `clinical_summary` | True | The Reference Data-Quality Monitor shows no active alarms. The heart rate metric is currently stale but valid, with a value of 74 beats per minute. The peripheral oxygen saturation metric is fresh but marked invalid, with a value of 98%. The device is connected and reporting data with good freshness for most parameters.<br>No active alarms are present on the Reference Data-Quality Monitor.<br>Heart rate measurement is valid but stale, currently at 74 beats per minute.<br>Peripheral oxygen saturation is fresh but flagged as invalid, with a value of 98%.<br>The device is connected and operating in read-only mode with current valid state.<br>Data freshness varies between metrics, indicating some parameters may not be up-to-date. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified patient monitor device, matching the required resource kind and target device ID. |
| `stale_metric_detection` | `freshness_detection` | True | The following metric is explicitly marked as stale: Heart rate. |
| `invalid_sensor_detection` | `invalid_state_detection` | True | One metric has invalid validity: metric.spo2.invalid (Peripheral oxygen saturation). The heart rate metric is valid but stale. |
