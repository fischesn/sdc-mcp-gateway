# Consolidated release-candidate evaluation

The consolidated workflow presents the evidence as three layers rather than as
a sequence of internal work packages:

1. protocol and resource projection;
2. deterministic safety, failure, mapping, authorization, and security checks;
3. frozen agent and representation results.

The external model calls are not repeated when their frozen input lock remains
byte-identical. The consolidation runner verifies the original input-set SHA-256
before reusing those outputs and records that decision explicitly.

## Container-isolated same-stack protocol test

On Windows, two local `sdc11073` processes compete for multicast delivery on the
same interface and UDP port 3702. The container test places the Python provider
and Python consumer in separate Linux network namespaces with distinct IPv4
addresses. It permits no directed-XAddr fallback.

Start Docker Desktop and wait for the engine to report that it is running. Then
execute:

```powershell
python -m sdc_mcp_gateway.sdc.container_protocol_testbed `
  --repetitions 5 `
  --discovery-timeout-s 2.0 `
  --output data/revision/development/container-protocol-testbed.json
```

The runner builds `docker/sdc-testbed.Dockerfile`, creates a short-lived bridge
network, assigns distinct provider and consumer addresses, executes all three
versioned MDIB profiles, and removes the containers and network afterward.
Ephemeral TLS material and raw per-profile files remain below ignored `tmp/` for
diagnosis; the anonymous aggregate is written to the requested output path. In
the recorded five-repetition run, WS-Discovery succeeded in 15/15 attempts,
all 15 snapshots and all 120 advertised MCP resource reads completed, and no
directed-XAddr fallback was permitted or used. Seven of eleven observed metric
codes mapped; the other four remained explicit.

## Consolidated deterministic rerun

After the container report exists, run:

```powershell
python -m sdc_mcp_gateway.revision.consolidated_evaluation `
  --output-dir data/revision/consolidated/bhi2026-release-candidate
```

This command refuses to overwrite an existing bundle. It reruns the local
no-execution, lifecycle, mapping, authorization, security, and deterministic
agent checks, incorporates the same-stack and SDCri protocol reports, verifies
the frozen agent input digest, and references the retained external-model and
representation-ablation artifacts by SHA-256.

The resulting `consolidated-summary.json` is the single source for the paper's
evaluation table. Its claim boundary remains explicit: all protocol evidence is
software-reference evidence without a physical device, clinical network, or
multi-vendor deployment.

The anonymous recorded same-stack input used by the default consolidation
command is checked in under
`experiments/2026-08-10-container-same-stack/`.
