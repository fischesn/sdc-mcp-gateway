# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-openai-gpt-4-1-mini-r2-holdout-unmapped-20260808T151127_623217Z`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device with the device ID 'holdout-monitor-unmapped'. This device is a Research Prototype patient monitor named 'Reference Monitor with Vendor Metric', model 'Simulated-SDC-Device'. |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms reported by the holdout-monitor-unmapped device or any other device. |
| `clinical_summary` | `clinical_summary` | True | The patient monitor is currently reporting a heart rate of 76 beats per minute with no active alarms.<br>One patient monitor device is connected and reporting data.<br>The heart rate metric is fresh, valid, and mapped correctly with a value of 76 beats per minute.<br>No active alarms are present on the device or in the system.<br>There is an additional unmapped vendor-specific metric present but it is informational and not currently mapped to a known semantic name.<br>The system status is healthy and operating in read-only mode. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified patient monitor device, matching the required resource kind and device ID. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric codes are unmapped: vendor.perfusion.index.x7 |
