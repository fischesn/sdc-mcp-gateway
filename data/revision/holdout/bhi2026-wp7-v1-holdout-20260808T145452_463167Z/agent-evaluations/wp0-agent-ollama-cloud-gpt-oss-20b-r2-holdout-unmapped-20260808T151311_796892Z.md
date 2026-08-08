# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r2-holdout-unmapped-20260808T151311_796892Z`
- Agent: `llm-ollama`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device: holdout-monitor-unmapped. |
| `alarm_detection` | `alarm_detection` | True | No active alarms detected. |
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is currently connected and reporting a heart rate of 76 beats per minute. No alarms are active. One vendor‑specific perfusion metric is present but unmapped. The device is in read‑only mode and all data is fresh.<br>Device is connected and in read‑only mode.<br>Heart rate is 76 beats/min and is fresh.<br>No active alarms are present.<br>A vendor‑specific perfusion metric is reported but not mapped to a semantic name.<br>All reported values are valid and current. |
| `metrics_resource_selection` | `resource_selection` | True | The URI corresponds to the metrics resource for the specified device. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | vendor.perfusion.index.x7 |
