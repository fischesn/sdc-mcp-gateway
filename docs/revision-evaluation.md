# BHI 2026 revision evaluation workflow

The revision workflow separates exploratory development runs from final hold-out
evaluation. Its configuration is stored in `config/bhi2026_revision.yaml`.

## Phase boundary

The four original scenarios and the original 16 tasks are development material.
They may be used to improve implementation code, prompts, mappings, and graders.
They must not be presented as an untouched final hold-out set.

WP6 populates and freezes the hold-out inputs while keeping execution closed:

- `enabled: true`
- `frozen: true`
- `execution_allowed: false`

It contains four new scenarios and a deterministic baseline plan. The pipeline
refuses to run hold-out evaluation until it is explicitly authorized.
The refusal occurs before an output directory is created.

Development and hold-out artifacts use separate directory trees:

```text
data/revision/development/
data/revision/holdout/
```

Generated outputs are ignored by Git. Only the empty directory markers are
tracked.

## Validate and inspect the manifest

```powershell
sdc-mcp-gateway revision-manifest `
  --manifest config/bhi2026_revision.yaml `
  --phase development
```

This prints an anonymous content lock with:

- relative input paths;
- SHA-256 for every input file;
- a combined input-set SHA-256;
- Python and dependency versions;
- scenario, agent, model, repetition, temperature, and seed settings;
- development and hold-out gate states.

The lock excludes host names, user names, absolute paths, credentials, public
repository links, and public commit identifiers.

## Run the current reproducible development pipeline

```powershell
sdc-mcp-gateway run-revision-pipeline `
  --manifest config/bhi2026_revision.yaml `
  --phase development
```

The command creates one timestamped directory containing:

```text
manifest.lock.json
pipeline-result.json
paper-summary.json
paper-summary.csv
paper-summary.md
agent-evaluations/
benchmarks/
tool-evaluations/
logs/
```

WP6 uses deterministic processing of the exact MCP resource context supplied
to the LLMs. Scenario ground truth is available only to the downstream grader.
Development outputs are marked exploratory and excluded from final aggregates.

## Frozen hold-out phase

WP6 seals prompts, task definitions, graders, SDC-MIE, policies, and scenario
inputs in `config/bhi2026_wp6_freeze.json`. Hold-out execution may be enabled
only after all of the following have been reviewed:

1. model identifiers and decoding settings are pinned;
2. repetition counts and metrics are fixed;
3. the WP6 input freeze verifies without changes;
4. an anonymous manifest lock has been inspected;
5. `execution_allowed` is changed as an explicit WP7 decision.

After the first hold-out execution, changes to evaluation inputs require a new
manifest version and must not be merged into the original aggregate.

WP7 superseded the WP6 design lock after adding the declared stress cases and
pinning five hosted models. The completed final run and its conservative
failures are documented in `docs/wp7-evaluation-evidence.md`. The WP7 scientific
input digest is `7d1d2a07339c22f35013f58b5c2e181e7c179a38d1525299484b814dd0f27180`;
the frozen prompts, graders, scenarios, mappings, and tracked evaluation code
must not be changed or rerun under the same manifest version.
