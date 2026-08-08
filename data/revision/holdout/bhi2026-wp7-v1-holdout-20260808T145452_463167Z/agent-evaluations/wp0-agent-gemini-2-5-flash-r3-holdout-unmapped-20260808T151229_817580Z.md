# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-gemini-2-5-flash-r3-holdout-unmapped-20260808T151229_817580Z`
- Agent: `llm-gemini`
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
| `device_inventory` | `device_inventory` | True | The gateway is exposing the following SDC devices: holdout-monitor-unmapped. |
| `alarm_detection` | `alarm_detection` | True | No active alarms were detected. |
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is connected and reporting a heart rate of 76 beats/min. An unmapped vendor-specific perfusion index metric is also present with a value of 4.2 arb. There are no active alarms.<br>The 'Reference Monitor with Vendor Metric' device is connected and operational.<br>The device is reporting a heart rate of 76 beats/min.<br>An additional vendor-specific metric, 'vendor.perfusion.index.x7', is present with a value of 4.2 arb, but it is currently unmapped to a standard semantic name.<br>All reported metrics are fresh and valid.<br>There are no active alarms from this device. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified device ID and type. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric codes are not mapped: vendor.perfusion.index.x7. |
