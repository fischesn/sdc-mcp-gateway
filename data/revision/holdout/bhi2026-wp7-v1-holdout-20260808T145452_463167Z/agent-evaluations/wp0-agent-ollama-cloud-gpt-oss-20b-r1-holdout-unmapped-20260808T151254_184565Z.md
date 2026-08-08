# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r1-holdout-unmapped-20260808T151254_184565Z`
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
| `clinical_summary` | `clinical_summary` | True | The Reference Monitor with Vendor Metric is currently connected and reporting a heart rate of 76 beats per minute. No active alarms are present. An additional vendor-specific perfusion index metric is available but not mapped to a standard semantic name. The device operates in read‑only mode.<br>Device is connected and reporting heart rate of 76 beats/min<br>No active alarms are triggered<br>Vendor perfusion index metric is present but unmapped<br>Device operates in read‑only mode |
| `metrics_resource_selection` | `resource_selection` | True | The URI matches the device's metrics resource. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | vendor.perfusion.index.x7 |
