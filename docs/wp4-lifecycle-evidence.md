# WP4 Failure, Freshness, Recovery, and Alarm-Lifecycle Evidence

## Status and scope

- Completed: 2026-08-08
- Versioned scenarios: 14
- Passed scenarios: 14/14
- Staleness threshold: 5 s
- Provider: deterministic in-process SDC-like simulator
- Ordered-update cache: implemented and evaluated
- Production SDC subscription transport: not implemented or claimed
- Physical medical devices: none available
- Hold-out LLM evaluation: not executed

WP4 evaluates deterministic gateway behavior under faults and ordered updates.
It complements the WP3 point-in-time SDC protocol experiment but does not turn
the simulator into a real SDC provider or establish production streaming,
clinical alarm performance, or physical-device interoperability.

## Reproduction

```powershell
sdc-mcp-gateway evaluate-lifecycle `
  --suite config/wp4_lifecycle_scenarios.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output data/revision/development/wp4-lifecycle-evidence.json
```

The JSON output contains no local paths, network addresses, user names, or
repository identifiers. Each case records the expected and actual resource
state, update disposition, dry-run policy decision, recovery observation, and
final alarm lifecycle state.

## Evaluated state model

Every exposed device catalogue entry now carries:

- source and gateway-reception timestamps;
- age of information;
- provider status;
- sequence identifier, MDIB version, and update sequence;
- one of `fresh`, `stale`, `invalid`, `unavailable`, or `recovered`;
- an explicit classification reason.

Metric resources preserve validity and freshness. Gateway health becomes
`degraded` when any device is unavailable or non-current. Duplicate and
out-of-order updates are explicitly recorded and do not replace the latest
accepted state.

## Scenario results

| Group | Cases | Result | Principal expected behavior |
|---|---:|---:|---|
| Availability/recovery | 3 | 3/3 | unavailable states reject; newer valid data recover |
| Validity/completeness | 2 | 2/2 | invalid or missing metrics remain visible and reject |
| Freshness/delivery | 2 | 2/2 | aged and delayed samples become stale and reject |
| Ordering/version binding | 2 | 2/2 | duplicates/older updates ignored; obsolete proposal rejected |
| Alarm lifecycle | 5 | 5/5 | ambiguity, escalation, latching, acknowledgement, suppression/reactivation explicit |
| **Total** | **14** | **14/14** | **all expected resource, policy, and recovery checks passed** |

The two recovery cases first rejected proposals in unavailable or invalid
states and then accepted only a dry-run proposal after a newer valid update was
classified as `recovered`. The stale, delayed, invalid, missing-metric, and
unavailable cases all failed closed. A proposal bound to MDIB version 1 after
version 2 had become current was rejected as `obsolete_snapshot`.

## Alarm lifecycle

Alarm states are modeled as `inactive`, `active`, `latched`, `acknowledged`, or
`suppressed`, with ordered transition counters. Two equal-priority simultaneous
alarms remain independently visible; the gateway does not invent a precedence.
Latching retains an alarm after the simulated condition clears,
acknowledgement is represented without executing a device operation, and
suppression/reactivation remain explicit transitions.

## Claim boundary

The harness evaluates point-in-time states after deterministic ordered events.
It does not implement SDC subscriptions, periodic reports, transport loss,
clinical timing guarantees, human alarm response, or an effective alarm
acknowledgement. All action-like interactions remain non-executing dry runs.
