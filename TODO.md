# Development TODO

## v0.1-read-only - completed in this scaffold

- [x] Create repository skeleton without paper directory.
- [x] Add v0.1 read-only specification.
- [x] Add gateway, SDC-MIE, and placeholder policy configuration files.
- [x] Add normalized internal data models.
- [x] Add deterministic dummy SDC consumer.
- [x] Add `sdc11073` adapter placeholder for v0.2.
- [x] Add SDC-MIE loader and metric mapper.
- [x] Add MCP resource registry for devices, metrics, alarms, context, raw MDIB, mapping, and health.
- [x] Add optional FastMCP server wrapper.
- [x] Add JSONL recorder for resource-read audit events.
- [x] Add unit tests for mapping, resources, and read-only policy.

## v0.2-real-sdc-snapshot - completed in this scaffold

- [x] Implement provider discovery with `sdc11073`.
- [x] Extract real MDIB snapshots into `DeviceSnapshot` using a defensive extractor.
- [x] Add configuration for network interface / adapter IP.
- [x] Add provider whitelist enforcement.
- [ ] Add integration test with a simulated or lab SDC provider.
- [x] Record discovery time and initial MDIB synchronization time.

## v0.3-event-streaming

- [ ] Subscribe to metric and alarm events.
- [ ] Maintain a continuously updated local state cache.
- [ ] Add event-to-resource latency measurements.
- [ ] Export experiment CSV/JSONL summaries.

## v0.4-dry-run-tools

- [ ] Extract SCO descriptors from the MDIB.
- [ ] Generate MCP tool definitions and JSON schemas.
- [ ] Validate tool arguments without executing SDC operations.
- [ ] Add dry-run audit records.

## v0.5-policy-hitl

- [ ] Implement policy whitelist.
- [ ] Add role and approval metadata.
- [ ] Add CLI or web-based human-in-the-loop approval.
- [ ] Add negative tests for unsafe tool calls.

## v0.6-controlled-lab-execution

- [ ] Enable explicitly whitelisted write operations in isolated lab mode only.
- [ ] Add hard kill switch for all write operations.
- [ ] Run experiments with real SDC-capable devices.
