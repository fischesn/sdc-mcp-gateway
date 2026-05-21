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

## v0.5-end-to-end-mcp-client - completed

- [x] Add end-to-end MCP client smoke test using stdio transport.
- [x] Verify list_resources, read_resource, and no exported tools through a real MCP ClientSession.

## v0.6-repeatable-benchmarking - completed

- [x] Add repeatable benchmark CLI command.
- [x] Export per-iteration JSONL records.
- [x] Export CSV table for spreadsheet/plot workflows.
- [x] Export compact summary JSON with latency statistics.
- [x] Verify read-only safety boundary in benchmark summaries.

## v0.7-event-streaming

- [ ] Subscribe to real metric and alarm events through `sdc11073`.
- [ ] Add a continuously updated local state cache.
- [ ] Add event-to-resource latency measurements.
- [ ] Add time-series simulation mode for repeated snapshots.

## v0.8-dry-run-tools

- [ ] Extract SCO descriptors from the MDIB.
- [ ] Generate MCP tool definitions and JSON schemas.
- [ ] Validate tool arguments without executing SDC operations.
- [ ] Add dry-run audit records.

## v0.9-policy-hitl

- [ ] Implement policy whitelist.
- [ ] Add role and approval metadata.
- [ ] Add CLI or web-based human-in-the-loop approval.
- [ ] Add negative tests for unsafe tool calls.

## v1.0-controlled-lab-execution

- [ ] Enable explicitly whitelisted write operations in isolated lab mode only.
- [ ] Add hard kill switch for all write operations.
- [ ] Run experiments with real SDC-capable devices.


## v0.7.1 completed

- Added `summarize-benchmarks` for aggregating multiple benchmark summary files.
- Added aggregate JSON and CSV output for paper-oriented evaluation tables.

## After v0.7.1

- Add scenario comparison utilities for alarm activation timelines.
- Add agent-facing prompts for interpreting scenario resources.
- Add plotting support for benchmark and scenario CSV files.
- Compare scenario-based simulation results with real SDC devices once the lab VPN is available.


### v0.7.1 alarm-observation update

Version v0.7.1 corrects the high-airway-pressure scenario so that the simulated airway-pressure alarm remains active at the end of standard benchmark runs. Benchmark summaries also include `active_alarm_count_max` and `active_alarm_seen_any`, which are useful when evaluating transient or pulse-like alarm scenarios.


## v0.8 Agent-facing evaluation

Version v0.8.0 adds deterministic oracle-agent task evaluation. It validates whether the MCP resource surface supports device inventory, alarm detection, safe clinical-state summarization, and resource selection tasks.

Run one scenario:

```powershell
sdc-mcp-gateway evaluate-agent-tasks --config config/gateway.simulated.tachycardia.example.yaml --mie config/sdc_mie.yaml --tasks config/agent_eval.tasks.yaml --scenario tachycardia --agent oracle --output-dir data/agent_eval --elapsed-s 100
```

Run all default scenarios:

```powershell
.\scripts\run_agent_evaluation.ps1
```

The outputs are written as JSON, CSV, and Markdown files under `data/agent_eval/`.

## v0.9 completed

- Added optional LLM-backed agent evaluation.
- Added mock, Ollama, and OpenAI-compatible backends.
- Reused v0.8 tasks, ground truth, and graders.
- Preserved read-only safety boundary.

## Next

- Run real LLM evaluations and compare pass rates/error modes against the oracle baseline.
- Add repeated-run aggregation for non-deterministic LLM outputs.
- Consider a with/without SDC-MIE ablation study.

## v0.9.4 Agent-evaluation aggregation

Use `summarize-agent-evaluations` to aggregate multiple oracle or LLM-backed agent-evaluation JSON reports:

```powershell
sdc-mcp-gateway summarize-agent-evaluations --input-dir data/agent_eval --label gemini-v093-summary --pattern "agent-eval-*.json"
```

The command writes an `.aggregate.json` and `.aggregate.csv` file with task-pass counts, wrong URI counts, false alarm counts, unsafe-summary counts, and read-only safety-boundary status.
