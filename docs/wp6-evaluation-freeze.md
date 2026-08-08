# WP6 deterministic baseline and evaluation freeze

WP6 replaces the legacy ground-truth-assisted oracle with a deterministic
resource processor. The processor and every LLM agent receive the same
`resource_context`, assembled only from advertised MCP resources. Scenario
ground truth is passed only to the downstream grader.

## Development evidence

Run: `bhi2026-wp6-v1-development-20260808T135832_205242Z`

- Partition: development, exploratory, excluded from final aggregates
- Scenarios: 4 original development scenarios
- Repetitions: 1 deterministic baseline run per scenario
- Cases: 16/16 passed
- Accuracy: 1.0; 95% Wilson interval 0.806392--1.0
- Critical errors: 0
- Resource read errors: 0
- Dry-run policy cases: 7/7; executed=true: 0
- Hold-out executions: 0

The regression suite changes an alarm fact in the resource context after the
baseline is constructed. The baseline result changes from active to inactive
and fails against the unchanged grader truth. This demonstrates that ground
truth cannot mask a changed or missing MCP fact.

## Frozen hold-out design

The original 16 cases remain development material. Four new hold-out scenarios
cover:

1. an active alarm in a mixed monitor/ventilator catalogue;
2. exact resource selection between two same-type devices;
3. coexistence of mapped and vendor-specific unmapped metrics; and
4. an unavailable provider returning no device snapshot.

The common task file adds hold-out-only checks for abstention on unmapped data
and explicit availability detection. The hold-out phase is enabled and frozen
but has `execution_allowed: false`; WP6 therefore does not consume it.

`config/bhi2026_wp6_freeze.json` hashes prompts, task definitions, graders,
SDC-MIE, policies, and every scenario/configuration input. Its input-set digest
is `314ced71e3ed9c7a59083dd932ba5b797ce3a26de0b8fabc3ce61ed205a7043b`.
The WP7 execution path must verify this lock before producing hold-out output.

## Reporting contract

Aggregates report run and repetition counts, total case denominators, pass
rates, 95% Wilson confidence intervals, and critical-error counts. Development
reports carry `exploratory=true` and `included_in_final_aggregate=false`, so
they cannot enter the final hold-out aggregate silently.
