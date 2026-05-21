# Development TODO

## v0.1-read-only - completed

- [x] Create repository skeleton without paper directory.
- [x] Add v0.1 read-only specification.
- [x] Add gateway, SDC-MIE, and placeholder policy configuration files.
- [x] Add normalized internal data models.
- [x] Add deterministic dummy SDC consumer.
- [x] Add SDC-MIE loader and metric mapper.
- [x] Add MCP resource registry for devices, metrics, alarms, context, raw MDIB, mapping, and health.
- [x] Add optional FastMCP server wrapper.
- [x] Add JSONL recorder for resource-read audit events.
- [x] Add unit tests for mapping, resources, and read-only policy.

## v0.2-real-sdc-snapshot - completed

- [x] Implement provider discovery with `sdc11073`.
- [x] Extract real MDIB snapshots into `DeviceSnapshot` using a defensive extractor.
- [x] Add configuration for network interface / adapter IP.
- [x] Add provider whitelist enforcement.
- [x] Record discovery time and initial MDIB synchronization time.
- [ ] Run integration test with a real or vendor-provided lab SDC provider.

## v0.3-simulated-provider-testbed - completed

- [x] Add YAML-based simulated device scenarios.
- [x] Add simulated patient monitor scenario.
- [x] Add simulated ventilator scenario.
- [x] Add combined multi-device scenario.
- [x] Add `simulated` adapter to the normal gateway path.
- [x] Add `simulate-snapshot` CLI command.
- [x] Add tests for simulation loading, snapshot generation, and simulated consumer behavior.
- [x] Document that this is an in-process SDC-like simulator, not a real networked SDC Provider.

## v0.4-read-only-mcp-resource-server - completed

- [x] Add read-only MCP resource server wrapper.
- [x] Add `sdc://resources` machine-readable resource catalogue.
- [x] Add `list-resources` CLI command.
- [x] Add `read-resource` CLI command.
- [x] Add `mcp-smoke-test` CLI command.
- [x] Verify that all advertised resources are readable.
- [x] Verify read-only safety boundary in `sdc://health`.

## v0.5-event-streaming

- [ ] Subscribe to real metric and alarm events through `sdc11073`.
- [ ] Add a continuously updated local state cache.
- [ ] Add event-to-resource latency measurements.
- [ ] Add time-series simulation mode for repeated snapshots.
- [ ] Export experiment CSV/JSONL summaries.

## v0.6-dry-run-tools

- [ ] Extract SCO descriptors from the MDIB.
- [ ] Generate MCP tool definitions and JSON schemas.
- [ ] Validate tool arguments without executing SDC operations.
- [ ] Add dry-run audit records.

## v0.7-policy-hitl

- [ ] Implement policy whitelist.
- [ ] Add role and approval metadata.
- [ ] Add CLI or web-based human-in-the-loop approval.
- [ ] Add negative tests for unsafe tool calls.

## v0.8-controlled-lab-execution

- [ ] Enable explicitly whitelisted write operations in isolated lab mode only.
- [ ] Add hard kill switch for all write operations.
- [ ] Run experiments with real SDC-capable devices.


## After v0.4.1

- Test `serve` with a real MCP client.
- Add automated MCP client integration tests when the MCP SDK is available in CI.
- Add dynamic refresh for long-running server mode.
- Define v0.6 dry-run MCP tools, still without SDC write execution.


## v0.5.0

- [x] Add end-to-end MCP client smoke test using stdio transport.
- [x] Verify list_resources, read_resource, and no exported tools through a real MCP ClientSession.
- [ ] Next: connect an external MCP-capable agent/client and add experiment recording for client-side latencies.
