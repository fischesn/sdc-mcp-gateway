# WP10 non-executing human-authorization evidence

## Scope

WP10 implements a deterministic proposal lifecycle above the existing dry-run tool
registry:

```text
proposed -> policy_validated -> pending_approval -> approved | denied | expired
```

`approved` is a documentation state, not permission to dispatch an SDC operation. Every
proposal and decision model requires `dry_run=true`, `executed=false`, and
`write_operations_allowed=false`.

## Bound proposal record

Each proposal records:

- proposal ID, target device, tool/operation, and exact parameters;
- policy version;
- MDIB/snapshot version, canonical snapshot SHA-256, and freshness state;
- proposer, proposal time, expiry time, and transition history; and
- for a recorded human decision, the approval identity and authorization reference.

Approval repeats the dry-run policy check against the current gateway state and compares the
policy version, snapshot version, freshness classification, and complete snapshot digest with
the bound values. Expiry or any failed revalidation moves the proposal to `expired`; human
approval cannot override those checks. A decision without identity/reference leaves the
proposal in `pending_approval`. Terminal proposals reject duplicate decisions.

The supplied identity/reference is workflow context only. WP10 does not authenticate a person,
provide a clinical UI, establish role authority, or implement device write-back.

## Reproduce the evidence

```powershell
python -m sdc_mcp_gateway.revision.human_authorization `
  --suite config/bhi2026_wp10_authorization.yaml `
  --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml `
  --output data/revision/authorization/bhi2026-wp10-authorization-v1/workflow-evidence.json
```

The seven synthetic cases cover approval, denial, expiry, duplicate approval, stale data,
changed device state, and missing authorization context. All 7/7 cases pass. The two valid
approvals, one denial, three expiries, and one still-pending proposal all retain zero SDC write
attempts and preserve the state present immediately before the decision.

The checked-in YAML also contains review prompts covering clarity, plausibility, missing
information, and workflow-safety concerns. These prompts prepare a possible later expert
assessment; they are not participant data or expert evidence.

## Expert-review boundary

No expert review was conducted in WP10 and no participant data were collected. Suitable expert
availability and applicable consent, ethics, and institutional-governance requirements must be
established before such an assessment. Consequently, the evidence supports workflow mechanics
and the no-execution boundary only. Clinical appropriateness, usability, and clinical validation
remain unevaluated.
