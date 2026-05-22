# Agent evaluation: tachycardia

- Run ID: `agent-eval-tachycardia-20260521T211516_409330Z`
- Agent: `llm-gemini`
- Status: `ok`
- Passed tasks: 4/4
- Resource count: 8

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing the following SDC device: sim-monitor-1 (Simulated Patient Monitor - Tachycardia). |
| `alarm_detection` | `alarm_detection` | True | An active alarm is present. Device 'sim-monitor-1' has a medium priority 'heart_rate' alarm, indicating a high heart rate of 139.415 beats/min. |
| `clinical_summary` | `clinical_summary` | True | A medium-priority physiological alarm for high heart rate is active on the Simulated Patient Monitor (ID: sim-monitor-1). The current heart rate is 139.415 beats/min, which is above the set high threshold of 120.0 beats/min.<br>A Simulated Patient Monitor (ID: sim-monitor-1) is currently active and reporting data.<br>A medium-priority physiological alarm for high heart rate is present.<br>The current heart rate is 139.415 beats/min, exceeding the high threshold of 120.0 beats/min.<br>Other monitored parameters include Peripheral oxygen saturation at 97.348% and Respiratory rate at 16.719 1/min. |
| `metrics_resource_selection` | `resource_selection` | True | The URI was selected based on matching the required resource kind 'metrics' and the target device ID 'sim-monitor-1' and device type 'patient_monitor'. |
