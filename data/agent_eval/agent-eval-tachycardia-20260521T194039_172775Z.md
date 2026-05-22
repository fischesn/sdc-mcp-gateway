# Agent evaluation: tachycardia

- Run ID: `agent-eval-tachycardia-20260521T194039_172775Z`
- Agent: `llm-gemini`
- Status: `failed`
- Passed tasks: 3/4
- Resource count: 8

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing one SDC device: Simulated Patient Monitor - Tachycardia (sim-monitor-1). |
| `alarm_detection` | `alarm_detection` | True | An active alarm for heart_rate with medium priority is detected on device sim-monitor-1. |
| `clinical_summary` | `clinical_summary` | False | ['The "Simulated Patient Monitor - Tachycardia" (SimMonitor-v0.7) is currently active.', 'A medium-priority "Heart rate high" alarm is present.', 'The current heart rate is 139.4 beats/min, which is above the set high threshold of 120.0 beats/min.', 'Other vital signs include a peripheral oxygen saturation of 97.3% and a respiratory rate of 16.7 breaths/min.'] |
| `metrics_resource_selection` | `resource_selection` | True | To inspect the relevant device metrics, you would read the resource that provides mapped read-only metric states for the simulated patient monitor. |
