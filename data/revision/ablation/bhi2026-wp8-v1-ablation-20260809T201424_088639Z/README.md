# WP8 result-file guide

The external run completed once under input lock
`17cc5af7475d6ce753912c7aefc47aad54ec0f63e957deba9988de0f444ba4b0`.

- `reports/` contains the 30 newly executed raw-SDC and generic-MCP reports.
- `input.lock.json` is the exact pre-execution input lock.
- `pipeline-result.json` records run completion and case counts.
- `wp8-summary.*` is the sealed runner's first-pass summary.
- `wp8-analysis-summary.{json,csv,md}` is the authoritative analysis used in the paper.

The first-pass runner summary lacked `valid_resource_uris` in the reused WP7 report
format and consequently overcounted invented URIs for the reused deterministic and
SDC-MIE arms. The authoritative post-hoc analysis reconstructs each valid catalogue
from frozen scenario inputs. It changes no prompt, model response, task grade, or
pass/fail result, and no model call was repeated.
