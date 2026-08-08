# Agent evaluation: holdout-unmapped

- Run ID: `wp0-agent-digital-hub-qwen-3-6-27b-r3-holdout-unmapped-20260808T151651_144609Z`
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
| `device_inventory` | `device_inventory` | True | The gateway currently exposes one SDC device: Reference Monitor with Vendor Metric (ID: holdout-monitor-unmapped). |
| `alarm_detection` | `alarm_detection` | True | No active alarms are currently reported by any connected devices. |
| `clinical_summary` | `clinical_summary` | True | The reference monitor is connected and reporting fresh, valid data. Heart rate is 76.0 beats/min. An unmapped vendor perfusion metric shows 4.2 arbitrary units. No active alarms are present, and the system remains in read-only mode.<br>The Reference Monitor with Vendor Metric is connected and transmitting fresh, valid data.<br>Heart rate is currently reported at 76.0 beats/min.<br>An unmapped vendor-specific perfusion index metric is reporting a value of 4.2 in arbitrary units.<br>No active alarms are currently triggered on the device or gateway.<br>The monitoring system is operating in read-only mode with all metrics classified as informational. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI matches the target device ID and required metrics resource kind as defined in the provided resource catalogue. |
| `unmapped_metric_abstention` | `mapping_abstention` | True | The metric code with mapping_state 'unmapped' is vendor.perfusion.index.x7. |
