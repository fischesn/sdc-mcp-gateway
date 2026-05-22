# Agent evaluation: airway-pressure

- Run ID: `agent-eval-airway-pressure-20260521T211759_656580Z`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing one SDC device: Simulated Ventilator - High Airway Pressure (sim-ventilator-1). |
| `alarm_detection` | `alarm_detection` | True | An active high priority airway pressure alarm is detected on device sim-ventilator-1. |
| `clinical_summary` | `clinical_summary` | True | A high airway pressure alarm is active on the Simulated Ventilator - High Airway Pressure, with a current value of 46.0 cmH2O.<br>A high priority physiological alarm for high airway pressure is currently active.<br>The alarm is reported by the 'Simulated Ventilator - High Airway Pressure' (ID: sim-ventilator-1).<br>The current airway pressure reading is 46.0 cmH2O.<br>The high threshold for the airway pressure alarm is 40.0 cmH2O.<br>Other monitored metrics from the ventilator include FiO2 at 33.793% and PEEP at 8.318 cmH2O. |
| `metrics_resource_selection` | `resource_selection` | True | The URI for metrics was selected by matching the required resource kind and the target device identifier and type. |
