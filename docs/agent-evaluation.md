# Agent Evaluation Guide

This guide describes how to run the deterministic oracle-agent evaluation introduced in v0.8.0.

## Why an oracle agent?

The oracle agent is deterministic and reads the same MCP resource payloads that an LLM-based agent would see. It does not use natural-language reasoning. Its role is to validate task definitions, ground truth, safety checks, and graders before non-deterministic LLM agents are added.

## Run one scenario

```powershell
sdc-mcp-gateway evaluate-agent-tasks `
  --config config/gateway.simulated.spo2-drop.example.yaml `
  --mie config/sdc_mie.yaml `
  --tasks config/agent_eval.tasks.yaml `
  --scenario spo2-drop `
  --agent oracle `
  --output-dir data/agent_eval `
  --elapsed-s 100
```

For the three alarm scenarios, `--elapsed-s 100` places the simulation after the alarm-inducing event. For the baseline scenario, no alarm should be active.

## Run all default scenarios

```powershell
.\scripts\run_agent_evaluation.ps1
```

The script evaluates:

- `baseline`
- `tachycardia`
- `spo2-drop`
- `airway-pressure`

## Output files

Each evaluation produces:

- `.json`: full machine-readable report
- `.csv`: one row per evaluated task
- `.md`: human-readable summary

## Task file format

Tasks are defined in `config/agent_eval.tasks.yaml`.

Each task has:

```yaml
tasks:
  - id: alarm_detection
    kind: alarm_detection
    prompt: "Is there any active alarm?"
    expected:
      tachycardia:
        active_alarm: true
        device_id: "sim-monitor-1"
        semantic_name: "heart_rate"
        priority: "medium"
```

The `expected` block contains scenario-specific ground truth. This makes the same task reusable across multiple scenarios.

## Extending the task set

To add a new task, add a new entry in `config/agent_eval.tasks.yaml` and implement a matching task kind in `OracleAgent` if needed. Recommended task kinds for future versions include:

- active-alarm prioritization
- multi-device state comparison
- resource-description robustness testing
- safe refusal testing for treatment requests

## Current limitation

v0.8 does not evaluate a real LLM. That is deliberate. The next logical step is a v0.9 LLM-agent evaluation that reuses the same task file and graders.
