# Agent evaluation: tachycardia

- Run ID: `agent-eval-tachycardia-20260521T185730_700431Z`
- Agent: `oracle`
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
| `device_inventory` | `device_inventory` | True | Exposed devices: sim-monitor-1 |
| `alarm_detection` | `alarm_detection` | True | Active alarm(s): sim-monitor-1 reports medium alarm alarm.hr.high related to heart_rate=139.415 beats/min |
| `clinical_summary` | `clinical_summary` | True | - sim-monitor-1: heart_rate: 139.415 beats/min, spo2: 97.348 %, respiratory_rate: 16.719 1/min<br>- Active alarm: sim-monitor-1 medium heart_rate |
| `metrics_resource_selection` | `resource_selection` | True | I would read sdc://devices/sim-monitor-1/metrics. |
