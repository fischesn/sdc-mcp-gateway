# WP2 No-Execution Evidence Report

## Status

- Completed: 2026-08-08
- Full prototype suite: 70 tests passed
- Focused WP2 suite: 18 tests passed
- Static/type QA of changed WP2 files: passed
- Hold-out LLM evaluation: not executed

## Implemented controls

- Central fail-closed validation rejects write-enabled configurations,
  unsupported gateway modes, and mode/tool inconsistencies.
- Tool-policy validation rejects non-dry-run entries and duplicate names.
- Tool-result validation makes `dry_run=false`, `executed=true`, and
  `write_operations_allowed=true` invalid model states.
- The `SdcConsumer` interface exposes only `discover` and `get_snapshots`.
- `WriteSpySdcConsumer` independently counts and blocks modeled Set Service and
  ActivateOperation attempts.
- Numeric tool arguments reject booleans, strings, NaN, infinity, and unexpected
  fields without changing device state.
- An AST checker scans agent-facing application, MCP, tool, agent, and policy
  code for direct SDC imports and named device-write APIs.
- A finite abstract transition system contains proposal, validation, approval,
  rejection, expiry, read-return, and return behavior but no execution edge.
- Hypothesis properties cover arbitrary JSON tool inputs, arbitrary resource
  URIs, and arbitrary event sequences. The three properties are configured for
  up to 650 generated examples in a complete run, including mixed sequences of
  MCP resource and tool interactions.

## Reproducible evidence command

The command

```powershell
sdc-mcp-gateway verify-no-execution `
  --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

reported:

- 8 advertised resources exercised;
- 7 representative valid, invalid, or unknown tool interactions exercised;
- `device_write_count = 0`;
- equal pre/post snapshot SHA-256 digests within the run;
- 11 agent-facing source files scanned with 0 violations; and
- 9 reachable states and 14 transitions with 0 device-effect edges and no
  execution-named state or event.

The digest value itself is run-specific because the simulated snapshot contains
an observation timestamp. The asserted evidence is equality before and after
the exercised interactions, not equality between separate runs.

## Interpretation

The evidence supports the bounded claim under the documented assumptions. It
combines independent configuration, type/model, interface, dynamic-spy,
state-integrity, static, generated-input, and abstract-transition checks.

The transition graph is exhaustively traversed, but the Python implementation
is not formally verified. The result does not cover compromised hosts or
dependencies, forged providers, malicious configuration sources, production
authentication, clinical appropriateness, real-device interoperability, or
safe effective device control.
