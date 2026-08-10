# WP8 representation ablation evidence

## Objective

WP8 isolates the contribution of the agent-facing representation while keeping the
underlying synthetic source facts, task definitions, grader, model, decoding settings,
and repetition count fixed. It does not compare clinical systems or claim that a higher
task score establishes clinical correctness.

The four comparison arms are:

1. a deterministic processor over the same enriched MCP resources;
2. raw normalized SDC snapshots, without an MCP resource catalogue or SDC-MIE fields;
3. generic read-only MCP resources with the same URIs and raw normalized facts, but without
   SDC-MIE semantic names, labels, mapping states, or mapping provenance; and
4. the proposed SDC-MIE-enriched MCP context.

The raw, generic, and enriched contexts contain identical device/metric source tuples
(`device_id`, handle, code, value, and unit). Their structure and enrichment differ by
design. URI-specific tasks remain in the matched suite because an agent-facing addressing
scheme is one of the capabilities under comparison.

## Freeze and execution discipline

- Experiment version: `bhi2026-wp8-v1`
- Frozen input lock: `17cc5af7475d6ce753912c7aefc47aad54ec0f63e957deba9988de0f444ba4b0`
- Model: `gpt-4.1-mini-2025-04-14`
- Temperature: `0.0`
- Scenarios: five frozen WP7 hold-out scenarios
- Matched tasks: 28 task--scenario pairs
- Repetitions: three
- Newly executed cases: 168 (raw and generic arms)
- Reused cases: 84 SDC-MIE cases and 28 deterministic cases from frozen WP7 reports
- Endpoint errors: zero

The transformation code, scenarios, tasks, mapping, model identifier, repetitions, and
the exact referenced WP7 reports were hashed before the new model calls. The WP7 proposed
arm was not re-executed. Neither the transforms nor prompts, graders, tasks, or mappings
were changed after the WP8 execution.

## Results

| Arm | Passed / evaluable | Pass rate | Wilson 95% CI | Invented resource URIs | Unsafe recommendations |
|---|---:|---:|---:|---:|---:|
| Deterministic, same enriched MCP resources | 28/28 | 100.0% | 87.9--100.0% | 0 | 0 |
| Raw normalized SDC | 63/84 | 75.0% | 64.8--83.0% | 15 | 0 |
| Generic MCP, no SDC-MIE | 75/84 | 89.3% | 80.9--94.3% | 0 | 0 |
| SDC-MIE-enriched MCP | 81/84 | 96.4% | 90.0--98.8% | 0 | 0 |

Because the same model repetition solves the same task and scenario in every LLM arm,
the primary comparisons are paired:

- Generic MCP to SDC-MIE: six cases improved, zero worsened, 75 passed in both, and three
  failed in both; exact two-sided McNemar p = 0.03125.
- Raw SDC to generic MCP: twelve cases improved, zero worsened, 63 passed in both, and nine
  failed in both; exact two-sided McNemar p = 0.000488.

All six generic-to-SDC-MIE improvements concern alarm semantics: three ordinary alarm
detection cases and three simultaneous-alarm-set cases. Generic MCP retained correct device,
metric, freshness, validity, availability, abstention, and resource-URI behavior. The three
failures shared by all LLM arms are the already retained conservative prompt-injection flag
failures from WP7; they returned the correct existing URI and no unsafe advice.

Raw normalized SDC lacked an agent-visible MCP catalogue. It therefore invented a resource
URI in 15 cases: twelve non-empty metric-resource selection cases and three prompt-injection
selection cases. The three unavailable-provider resource-selection cases correctly returned
no URI. This result measures the capability difference created by the interface; it is not
evidence that a direct deterministic SDC consumer would hallucinate URIs.

## Representation size and complexity

| Representation | Mean serialized context | Mean scalar fields | Maximum depth |
|---|---:|---:|---:|
| Raw normalized SDC | 1,592.4 bytes | 115.4 | 6 |
| Generic MCP | 3,241.2 bytes | 224.0 | 5 |
| SDC-MIE-enriched MCP | 4,706.4 bytes | 277.2 | 5 |

SDC-MIE increased the mean serialized context by 45.2% relative to generic MCP. The measured
accuracy improvement is therefore not a compression effect; it trades a larger explicit
semantic representation for fewer alarm-interpretation errors in this controlled suite.

## Post-hoc analysis correction

The sealed runner summary initially overcounted invented URIs for the two reused WP7 arms,
because the earlier report format did not store each scenario's complete valid URI catalogue.
The raw answers and all pass/fail grades were correct. A separate versioned analysis step
reconstructed the catalogues deterministically from the frozen scenarios and produced
`wp8-analysis-summary.{json,csv,md}`, which is the authoritative WP8 summary. No model call,
answer, prompt, grader, or pass/fail result was changed, and no model call was repeated.

## Conceptual positioning

| Integration | Intended use and temporal semantics | Agent-facing interface | Write authority and implementation boundary |
|---|---|---|---|
| Direct SDC consumer | Current device capabilities and MDIB state | Application-specific; normally deterministic, not an LLM interface | Defined by the SDC application and service roles |
| Generic MCP | Application-defined resources and tools | Standard MCP primitives without inherent medical-device semantics | Depends on server implementation; not device-specific |
| FHIR/EHR-style integration | Longitudinal clinical record and workflow exchange | Patient-data APIs and clinical information resources | Separated from point-of-care device operations |
| Proposed SDC-MCP gateway | Current normalized SDC-derived state plus explicit semantic/provenance fields | Read-only resources and non-executing proposal tools | Evaluated gateway enforces a no-execution boundary |

This table is an architectural comparison, not a measured performance ranking. A complete
FHIR/EHR implementation was deliberately not built or assigned incomparable latency values.

## Reproduction

```powershell
python -m sdc_mcp_gateway.revision.representation_ablation plan `
  --config config/bhi2026_wp8_ablation.yaml

python -m sdc_mcp_gateway.revision.representation_ablation verify `
  --config config/bhi2026_wp8_ablation.yaml

python -m sdc_mcp_gateway.revision.representation_ablation_analysis `
  --config config/bhi2026_wp8_ablation.yaml `
  --run-dir data/revision/ablation/bhi2026-wp8-v1-ablation-20260809T201424_088639Z
```

The external `run` command requires `OPENAI_API_KEY`; verification and post-hoc analysis do
not. Credentials and authorization headers are never written to reports.

## Limitations

- One pinned model is used for the controlled representation comparison.
- The task suite and source states are synthetic and inherited from WP7.
- Raw SDC is represented by the prototype's normalized snapshot, not a complete live BICEPS
  MDIB or a production subscription stream.
- The paired p-values describe this fixed task suite and do not establish general model or
  clinical superiority.
- SDC-MIE semantic correctness still depends on curated mapping content; schema validity and
  improved task performance do not establish standardization or clinical validation.
