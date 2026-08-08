# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-ollama-cloud-gpt-oss-20b-r3-holdout-unmapped-20260808T151324_873834Z`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes 1 device: holdout-monitor-unmapped. |
| `alarm_detection` | `alarm_detection` | True | There are no active alarms at this time. |
| `clinical_summary` | `clinical_summary` | True | The patient monitor is currently connected and reporting a heart rate of 76 beats per minute. No active alarms are present. The device is in a fresh, valid state with all metrics mapped. The vendor-specific perfusion index metric is present but unmapped and not used for clinical decision-making. Overall system health is OK with no current device issues.<br>Heart rate reported at 76 beats/min and is valid.<br>No active alarms detected.<br>Device is connected and data is fresh.<br>Vendor perfusion index metric is present but unmapped.<br>System health status is OK. |
| `metrics_resource_selection` | `resource_selection` | True | The URI matches the device's metrics resource. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | vendor.perfusion.index.x7 |
