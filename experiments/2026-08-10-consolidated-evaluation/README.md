# Consolidated BHI 2026 evaluation

This directory records the final consolidated evaluation generated from a
clean software tree at commit
`7b269c0e4598d93d231a83d685a7bbd23efcf692`. All 11 release checks in
`consolidated-summary.json` passed.

The bundle combines deterministic safety, authorization, lifecycle, mapping,
and no-execution checks with the container-isolated same-stack SDC experiment,
the SDCri cross-stack experiment, and the previously frozen multi-model agent
evaluation. The manifest records a clean working tree and verifies the frozen
input digest; external model calls were not repeated.

Key protocol results are 15/15 successful same-stack WS-Discovery runs without
directed-XAddr fallback, 15/15 MDIB snapshots, 120/120 MCP resource reads, and
5/5 successful cross-stack SDCri snapshots with 40/40 resource reads. The
frozen multi-model evaluation retained 414/420 passing task-model cases.

This is software-reference, deterministic, and frozen-agent evidence. It is
not physical-device, clinical-network, multi-vendor, or clinical-safety
validation.

## Reproduction

With the recorded protocol inputs available, run from the repository root:

```powershell
python -m sdc_mcp_gateway.revision.consolidated_evaluation `
  --output-dir data\revision\consolidated\bhi2026-release-candidate-final
```

The ignored output directory can then be compared with this checked-in bundle.
Runtime timestamps and generated report filenames may differ.
