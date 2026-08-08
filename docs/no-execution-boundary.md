# Mechanically Checked No-Execution Boundary

## Scope of the claim

For every MCP interaction exposed by the evaluated configuration, the gateway
must dispatch no SDC Set Service or ActivateOperation call and must leave the
observed device snapshot unchanged. This is a bounded software property under
the assumptions documented in the paper; it is not a claim of general,
clinical, deployment, or closed-loop safety.

## Independent checks

WP2 implements complementary checks instead of relying only on response flags.

1. **Fail-closed configuration.** `GatewayConfig` rejects
   `allow_write_operations=true`, unsupported modes, and mismatches between
   `mode` and `allow_tools` while loading the configuration.
2. **Fail-closed tool policy.** Tool-policy loading rejects duplicate names and
   every policy for which `dry_run_only` is not true.
3. **Unrepresentable executed result.** `ToolCallResult` validation requires
   `dry_run=true`, `executed=false`, and `write_operations_allowed=false`.
4. **Observation-only device contract.** `SdcConsumer` exposes only `discover`
   and `get_snapshots`. Device-operation methods are absent.
5. **Independent operation spy.** `WriteSpySdcConsumer` delegates observation
   calls but separately counts and blocks modeled Set Service and
   ActivateOperation attempts. Normal resource and tool tests require the count
   to remain zero.
6. **State integrity.** Tests hash the complete normalized device snapshots
   before and after all advertised resource reads and dry-run tool calls.
7. **Static architecture check.** An AST scan covers the MCP, tool, agent,
   policy, and application entry-point code and rejects direct `sdc11073`
   imports or known device-write call symbols in those paths.
8. **Generated malformed inputs.** Hypothesis generates arbitrary JSON tool
   arguments, arbitrary resource URIs, and arbitrary abstract workflow event
   sequences. Every outcome must preserve the spy count and snapshot digest.

## Abstract transition system

The finite model contains the states `idle`, `read_returned`, `proposed`,
`validated`, `pending_approval`, `approved`, `rejected`, `expired`, and
`returned`. Its events are read, propose, validate, require approval, approve,
reject, expire, and return. All states are reachable from `idle`, every edge is
explicitly marked as having no device effect, and neither an execution state
nor an execution event exists.

The artifact exhaustively traverses this finite transition relation. This is a
mechanical check of the abstract workflow, not model checking of the Python
implementation and not formal verification of the overall gateway. The Python
implementation is covered separately by validation, static analysis, example
tests, MCP smoke tests, and property-based tests.

## Reproduction

```powershell
pytest -q

sdc-mcp-gateway verify-no-execution `
  --config config/gateway.simulated.dryrun.high-airway-pressure.example.yaml `
  --mie config/sdc_mie.yaml `
  --tool-policy config/tool_policies.yaml
```

The JSON report deliberately contains no author-specific paths. A successful
run reports zero device writes, equal before/after device-state digests, no
static violations, no effectful transition edges, and an overall `ok` status.

## Limitations

The spy observes the two SDC operation families modeled by the test adapter; it
does not defend against a compromised interpreter, host, dependency, provider,
or configuration source. The static checker is a guardrail over named APIs, not
a proof against arbitrary obfuscation. Real protocol interoperability and
network behavior are addressed separately in WP3.
