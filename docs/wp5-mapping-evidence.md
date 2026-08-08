# WP5 Formalized SDC-MIE Evidence

## Status and scope

- Completed: 2026-08-08
- SDC-MIE schema version: 1.0
- Mapping artifact version: 1.0.0
- Checked-in entries: 6
- Software SDC profiles: 3
- Observed metric elements: 11
- Mapped metric elements: 7/11 (63.6%)
- Schema and semantic validation: passed
- Hold-out LLM evaluation: not executed

The evaluation validates the exact mapping source, records its SHA-256, and
generates metric-, descriptor-class-, state-class-, and provider-profile
coverage. It does not establish the clinical validity of a mapping or claim
standardization.

## Reproduction

```powershell
sdc-mcp-gateway evaluate-mapping `
  --mie config/sdc_mie.yaml `
  --output data/revision/development/wp5-mapping-evidence.json
```

## Results

| Profile | Mapped | Unmapped | Conflicting | Metric coverage |
|---|---:|---:|---:|---:|
| Monitor | 3 | 1 | 0 | 75.0% |
| Ventilator | 3 | 1 | 0 | 75.0% |
| Heterogeneous | 1 | 2 | 0 | 33.3% |
| **Total** | **7** | **4** | **0** | **63.6%** |

Unmapped vendor codes remain explicit. The heterogeneous profile additionally
reports Clock, SCO, and ActivateOperation descriptor/state classes as
unsupported. Structural state classes that are retained in the raw MDIB
summary but not projected into dedicated MCP objects are likewise reported as
unsupported rather than counted as mapped semantics.

The generated report contains a four-way state count for every observed metric
and every descriptor/state class. No conflict occurs in the checked-in
profiles. Separate automated negative tests demonstrate that a unit mismatch
or divergent code/handle resolution becomes `conflicting` and is not mapped.

## Validation evidence

Automated tests cover:

- duplicate codes;
- duplicate handles;
- conflicting units;
- reversed numeric bounds;
- missing descriptions;
- unknown fields;
- unsupported schema versions;
- explicit mapped, unmapped, unsupported, and conflicting runtime states.

The mapping resource and experiment records include schema version, artifact
version, provenance, and the source-file SHA-256. The JSON report is anonymous
and omits local paths and user information.

## Claim boundary

SDC-MIE is inspired by the value of explicit metadata illustrated by TogoMCP,
but uses an SDC-specific schema and is not file-format compatible. It is not an
IEEE 11073 standard and does not claim current standardization. A documented
evolution path would require physical-device coverage, independent
implementations, terminology/unit alignment, and community review.
