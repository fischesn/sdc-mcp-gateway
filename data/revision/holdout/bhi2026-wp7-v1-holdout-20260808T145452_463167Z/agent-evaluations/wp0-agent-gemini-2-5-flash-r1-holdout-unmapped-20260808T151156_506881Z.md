# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-gemini-2-5-flash-r1-holdout-unmapped-20260808T151156_506881Z`
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
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is connected and providing fresh data. The current heart rate is 76 beats/min. There are no active alarms reported by the device. An additional vendor-specific perfusion index is also being reported with a value of 4.2 arb, but it is currently unmapped to a standard semantic name.<br>The 'Reference Monitor with Vendor Metric' (device ID: holdout-monitor-unmapped) is connected and providing fresh data.<br>The current heart rate is 76 beats/min.<br>There are no active alarms reported by the device.<br>An unmapped vendor-specific perfusion index is reported with a value of 4.2 arb. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified device ID and type. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric codes are not mapped: vendor.perfusion.index.x7. No clinical semantic meaning has been assigned to these codes. |
