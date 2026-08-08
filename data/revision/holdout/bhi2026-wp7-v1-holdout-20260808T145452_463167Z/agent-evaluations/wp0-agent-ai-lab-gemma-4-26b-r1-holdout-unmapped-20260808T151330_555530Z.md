# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-ai-lab-gemma-4-26b-r1-holdout-unmapped-20260808T151330_555530Z`
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
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is currently connected and reporting data. The heart rate is 76.0 beats/min, and there is an unmapped perfusion index metric present.<br>Device 'Reference Monitor with Vendor Metric' is connected and reporting fresh data.<br>Heart rate is currently 76.0 beats/min.<br>An unmapped vendor metric (perfusion index) is reporting a value of 4.2 arb.<br>No active alarms are reported by the device. |
| `metrics_resource_selection` | `resource_selection` | True | The requested URI corresponds to the metrics resource for the specified patient monitor device. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The following metric code is unmapped: vendor.perfusion.index.x7 |
