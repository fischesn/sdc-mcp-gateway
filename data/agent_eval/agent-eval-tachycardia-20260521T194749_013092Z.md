# Agent evaluation: tachycardia

- Run ID: `agent-eval-tachycardia-20260521T194749_013092Z`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing the following SDC devices: Simulated Patient Monitor - Tachycardia (ID: sim-monitor-1). |
| `alarm_detection` | `alarm_detection` | True | An active alarm for high heart rate (tachycardia) is present on device sim-monitor-1 with medium priority. |
| `clinical_summary` | `clinical_summary` | True | A high heart rate alarm is active on the Simulated Patient Monitor - Tachycardia. The current heart rate is 139.4 beats/min, which is above the high threshold of 120 beats/min.<br>A high heart rate alarm (alarm.hr.high) is currently active.<br>The heart rate is measured at 139.4 beats/min.<br>The high heart rate threshold for this alarm is 120 beats/min.<br>The alarm is originating from 'Simulated Patient Monitor - Tachycardia'. |
| `metrics_resource_selection` | `resource_selection` | True | To inspect the relevant device metrics, you would read the resource that provides mapped read-only metric states for the simulated patient monitor. |
