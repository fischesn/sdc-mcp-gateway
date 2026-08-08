# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-ai-lab-gemma-4-26b-r2-holdout-unmapped-20260808T151336_476698Z`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing one SDC device: 'holdout-monitor-unmapped' (Reference Monitor with Vendor Metric). |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms reported for any device. |
| `clinical_summary` | `clinical_summary` | True | The device state for the Reference Monitor with Vendor Metric is currently stable with no active alarms reported.<br>Heart rate is recorded at 76.0 beats/min.<br>A vendor-specific perfusion index metric is present but currently unmapped to semantic standards.<br>The device 'Reference Monitor with Vendor Metric' is connected and providing fresh data.<br>No active alarms are present in the current device state. |
| `metrics_resource_selection` | `resource_selection` | True | The requested URI corresponds to the metrics resource for the specified patient monitor device. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric code is unmapped: vendor.perfusion.index.x7 |
