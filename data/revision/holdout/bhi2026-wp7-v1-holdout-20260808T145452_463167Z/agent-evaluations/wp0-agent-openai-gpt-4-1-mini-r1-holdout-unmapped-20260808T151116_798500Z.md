# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-openai-gpt-4-1-mini-r1-holdout-unmapped-20260808T151116_798500Z`
- Agent: `llm-openai-compatible`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device with the device ID 'holdout-monitor-unmapped'. This device is a Research Prototype patient monitor named 'Reference Monitor with Vendor Metric', model 'Simulated-SDC-Device'. It is connected and its data is fresh and valid. |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms detected on any device. |
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is currently connected and providing fresh, valid data. The heart rate metric is mapped and shows a value of 76 beats per minute, which is within a typical range. There are no active alarms reported by the device. An additional unmapped vendor-specific perfusion index metric is present but not currently mapped to a standard semantic name.<br>Device is connected and reporting fresh, valid data.<br>Heart rate is 76 beats per minute, with a mapped and valid metric.<br>No active alarms are present on the device.<br>An unmapped vendor-specific perfusion index metric is also reported.<br>Device health status is reported as OK with no non-current devices. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified patient monitor device, matching the required resource kind and device ID. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric codes are unmapped: vendor.perfusion.index.x7 |
