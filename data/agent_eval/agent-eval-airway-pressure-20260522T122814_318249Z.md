# Agent evaluation: airway-pressure

- Run ID: `agent-eval-airway-pressure-20260522T122814_318249Z`
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
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing one SDC device: 'Simulated Ventilator - High Airway Pressure' (sim-ventilator-1). |
| `alarm_detection` | `alarm_detection` | True | An active high-priority alarm for 'airway_pressure' is present on device 'sim-ventilator-1'. |
| `clinical_summary` | `clinical_summary` | True | A high priority alarm for Airway pressure is active on the Simulated Ventilator - High Airway Pressure. The current airway pressure is 46.0 cmH2O, which is above the high threshold of 40.0 cmH2O.<br>A high priority alarm for Airway pressure is active on the Simulated Ventilator - High Airway Pressure.<br>The current Airway pressure reading is 46.0 cmH2O.<br>This value exceeds the high threshold of 40.0 cmH2O for airway pressure.<br>Other monitored metrics on this device include Fraction of inspired oxygen at 33.793% and Positive end-expiratory pressure (PEEP) at 8.318 cmH2O. |
| `metrics_resource_selection` | `resource_selection` | True | The selected URI corresponds to the metrics resource for the specified ventilator device, aligning with the required resource kind and target device ID. |
