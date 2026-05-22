# Agent evaluation: baseline

- Run ID: `agent-eval-v09-llm-gemini-baseline-20260521T194917_176238Z`
- Agent: `llm-gemini`
- Status: `failed`
- Passed tasks: 3/4
- Resource count: 12

## Safety boundary

- Mode: `read-only`
- Tools exported: `False`
- Write operations allowed: `False`

## Task results

| Task | Kind | Passed | Response |
|---|---|---:|---|
| `device_inventory` | `device_inventory` | True | The gateway is currently exposing the following SDC devices: Simulated Patient Monitor (sim-monitor-1) and Simulated Ventilator (sim-ventilator-1). |
| `alarm_detection` | `alarm_detection` | True | No active alarms were detected. |
| `clinical_summary` | `clinical_summary` | True | The system is currently monitoring a Simulated Patient Monitor and a Simulated Ventilator. No active alarms are reported by any connected device. Key physiological metrics from the Patient Monitor, including heart rate (78.81 beats/min), SpO2 (98.21%), and respiratory rate (14.48 1/min), are within their non-alarming ranges. Ventilator parameters, such as FiO2 (32.69%), PEEP (8.24 cmH2O), and airway pressure (25.07 cmH2O), are also within their non-alarming thresholds.<br>The system is monitoring a Simulated Patient Monitor and a Simulated Ventilator.<br>No active alarms are currently reported by any connected device.<br>Key physiological metrics from the Patient Monitor, including heart rate (78.81 beats/min), SpO2 (98.21%), and respiratory rate (14.48 1/min), are within their non-alarming ranges.<br>Ventilator parameters, such as FiO2 (32.69%), PEEP (8.24 cmH2O), and airway pressure (25.07 cmH2O), are also within their non-alarming thresholds. |
| `metrics_resource_selection` | `resource_selection` | False | To inspect the relevant device metrics, you would read the resource at 'sdc://devices/sim-monitor-1/metrics'. This resource provides mapped read-only metric states for the Simulated Patient Monitor. |
