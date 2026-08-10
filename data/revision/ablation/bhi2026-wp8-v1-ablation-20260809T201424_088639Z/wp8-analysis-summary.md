# WP8 authoritative post-hoc analysis

- Frozen execution input lock: `17cc5af7475d6ce753912c7aefc47aad54ec0f63e957deba9988de0f444ba4b0`
- No model answer, prompt, grader, or pass/fail result was changed.

| Arm | Passed / evaluable | Rate | 95% Wilson CI | Invented URIs | Unsafe |
|---|---:|---:|---:|---:|---:|
| deterministic_same_mcp_resources | 28/28 | 1.000 | 0.879--1.000 | 0 | 0 |
| raw_normalized_sdc | 63/84 | 0.750 | 0.648--0.830 | 15 | 0 |
| generic_mcp | 75/84 | 0.893 | 0.809--0.943 | 0 | 0 |
| sdc_mie_enriched | 81/84 | 0.964 | 0.900--0.988 | 0 | 0 |

## Paired comparisons

- `generic_to_sdc_mie_enriched`: improved 6, worsened 0, exact McNemar p=0.031250.
- `raw_to_generic_mcp`: improved 12, worsened 0, exact McNemar p=0.000488.
