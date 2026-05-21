# Scenario-based simulation

Version 0.7.1 adds scenario-based simulation for repeatable semantic and alarm-oriented experiments. The simulator remains an in-process, SDC-like generator of normalized gateway snapshots. It is not a real IEEE 11073 SDC provider and does not open network endpoints.

## Included scenarios

The repository includes the following scenario YAML files:

```text
config/sim.combined.yaml              baseline patient monitor + ventilator scenario
config/sim.tachycardia.yaml          heart-rate ramp above high threshold
config/sim.spo2-drop.yaml            SpO2 ramp below low threshold
config/sim.high-airway-pressure.yaml ventilator airway-pressure pulse above high threshold
```

Matching gateway templates are available for benchmark and MCP tests:

```text
config/gateway.simulated.example.yaml
config/gateway.simulated.tachycardia.example.yaml
config/gateway.simulated.spo2-drop.example.yaml
config/gateway.simulated.high-airway-pressure.example.yaml
```

## Running a scenario snapshot

```bash
sdc-mcp-gateway simulate-snapshot --scenario config/sim.tachycardia.yaml --elapsed-s 60 --mie config/sdc_mie.yaml
```

The `elapsed-s` argument selects the simulated scenario time. For example, in the tachycardia scenario the heart-rate ramp is active between 20 s and 60 s and should trigger the high-heart-rate alarm near the end of that interval.

## Benchmarking a scenario

```bash
sdc-mcp-gateway benchmark \
  --config config/gateway.simulated.tachycardia.example.yaml \
  --mie config/sdc_mie.yaml \
  --iterations 100 \
  --warmup 10 \
  --elapsed-start-s 0 \
  --elapsed-step-s 1 \
  --output-dir data/experiment_runs \
  --label tachycardia-v07
```

The benchmark summary includes `active_alarm_count_last` and per-iteration JSONL/CSV rows include `active_alarms_count`. This makes it possible to evaluate whether the scenario actually crosses the configured alarm threshold.

## Scenario YAML structure

A scenario file has this structure:

```yaml
version: "0.7"
description: "Short human-readable scenario description."
random_seed: 7001
devices:
  - device_id: "sim-monitor-1"
    display_name: "Simulated Patient Monitor"
    manufacturer: "Research Prototype"
    model: "SimMonitor-v0.7"
    location_ref: "simulation-bed-1"
    patient_ref: "simulated-patient-redacted"
    metrics:
      - handle: "metric.hr"
        code: "150456"
        unit: "beats/min"
        baseline: 78
        amplitude: 4
        period_s: 45
        noise: 0.8
        min_value: 35
        max_value: 190
        events:
          - kind: "ramp"
            start_s: 20
            end_s: 60
            target: 135
            description: "Heart rate gradually rises above threshold."
    alarms:
      - handle: "alarm.hr.high"
        code: "alarm.hr.high"
        metric_handle: "metric.hr"
        high_threshold: 120
        priority: "medium"
        kind: "physiological"
```

## Metric model

For each metric, the simulator computes a deterministic value as:

```text
baseline + sinusoidal_component + bounded_noise + event_modifier
```

Supported fields:

| Field | Meaning |
|---|---|
| `handle` | Internal metric handle used by alarms and payloads. |
| `code` | SDC/BICEPS-like code or placeholder mapped by `sdc_mie.yaml`. |
| `unit` | Display unit. |
| `baseline` | Baseline value. |
| `amplitude` | Sinusoidal amplitude. |
| `period_s` | Sinusoidal period in seconds. |
| `noise` | Deterministic bounded pseudo-random noise. |
| `min_value`, `max_value` | Hard clipping bounds. |
| `events` | Optional time-dependent modifiers. |

## Event types

Version 0.7 supports three event types:

### `step`

Applies a fixed target or delta after `start_s` and, if `end_s` is set, until `end_s`.

```yaml
events:
  - kind: "step"
    start_s: 30
    target: 130
```

### `ramp`

Gradually moves toward `target` or `delta` between `start_s` and `end_s`.

```yaml
events:
  - kind: "ramp"
    start_s: 20
    end_s: 60
    target: 135
```

### `pulse`

Applies a finite step between `start_s` and `end_s`. This is useful for transient ventilator events.

```yaml
events:
  - kind: "pulse"
    start_s: 30
    end_s: 90
    target: 46
```

## Alarm configuration

An alarm references a metric by handle and becomes present if the metric crosses a threshold.

```yaml
alarms:
  - handle: "alarm.spo2.low"
    code: "alarm.spo2.low"
    metric_handle: "metric.spo2"
    low_threshold: 90
    priority: "high"
    kind: "physiological"
```

Use `high_threshold` for high-value alarms and `low_threshold` for low-value alarms.

## Creating your own scenario

1. Copy one of the existing scenario files.
2. Change `device_id`, `display_name`, and `random_seed` if needed.
3. Define metrics with stable `handle` values.
4. Add events to force clinically meaningful changes.
5. Add alarms that refer to the metric handles.
6. Add or update mappings in `config/sdc_mie.yaml` if you introduce new metric codes.
7. Create a matching gateway template by copying one of the `gateway.simulated.*.example.yaml` files and changing `sdc.simulation_config`.
8. Test the scenario with `simulate-snapshot` at different `elapsed-s` values.
9. Run `benchmark` and inspect `active_alarms_count` in the CSV/JSONL output.

Keep scenario files free of real patient data. Use synthetic identifiers such as `simulated-patient-redacted`.


### v0.7.1 alarm-observation update

Version v0.7.1 corrects the high-airway-pressure scenario so that the simulated airway-pressure alarm remains active at the end of standard benchmark runs. Benchmark summaries also include `active_alarm_count_max` and `active_alarm_seen_any`, which are useful when evaluating transient or pulse-like alarm scenarios.
