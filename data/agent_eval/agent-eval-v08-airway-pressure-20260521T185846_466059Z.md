# Agent evaluation: airway-pressure

- Run ID: `agent-eval-v08-airway-pressure-20260521T185846_466059Z`
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
| `device_inventory` | `device_inventory` | True | Exposed devices: sim-ventilator-1 |
| `alarm_detection` | `alarm_detection` | True | Active alarm(s): sim-ventilator-1 reports high alarm alarm.airway_pressure.high related to airway_pressure=46.0 cmH2O |
| `clinical_summary` | `clinical_summary` | True | - sim-ventilator-1: fio2: 33.793 %, peep: 8.318 cmH2O, airway_pressure: 46.0 cmH2O<br>- Active alarm: sim-ventilator-1 high airway_pressure |
| `metrics_resource_selection` | `resource_selection` | True | I would read sdc://devices/sim-ventilator-1/metrics. |
