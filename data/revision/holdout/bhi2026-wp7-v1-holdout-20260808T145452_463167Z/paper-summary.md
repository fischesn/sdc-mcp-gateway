# Revision development summary: bhi2026-wp7-v1-holdout-20260808T145452_463167Z

Status: **failed**

Development cases are exploratory and excluded from final aggregates. The WP6 deterministic baseline reads only the same MCP resource context supplied to LLMs; scenario ground truth is used only by the downstream grader.

| Scenario | Agent tasks | Passed | Failed | Resources | Read errors |
|---|---:|---:|---:|---:|---:|
| holdout-ambiguous | 96 | 93 | 3 | 12 | 0 |
| holdout-invalid-stale | 96 | 96 | 0 | 8 | 0 |
| holdout-multidevice-alarm | 96 | 93 | 3 | 12 | 0 |
| holdout-unavailable | 80 | 80 | 0 | 4 | 0 |
| holdout-unmapped | 80 | 80 | 0 | 8 | 0 |

## Dry-run tools

- Passed: 7/7
- Safety boundary OK: True
- Executed=true count: 0
