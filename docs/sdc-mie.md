# SDC-MIE 1.0 Research Artifact

SDC-MIE is the gateway's versioned, machine-validatable semantic mapping from
SDC/BICEPS-facing codes and handles to agent-readable MCP metadata. Version 1.0
is a research artifact. It is neither part of IEEE 11073 nor a proposed
standard, and it is not file-format compatible with TogoMCP.

## Formal structure

Let a mapping document be `M = (S, V, P, E)`, where:

- `S` is the supported schema version;
- `V` is the artifact version;
- `P` is the document provenance;
- `E` is the finite set of mapping entries.

Each entry fixes a code, zero or more handles, a semantic name, label, unit,
access classification, safety classification, optional numeric bounds,
human-approval metadata, description, and optional entry provenance. Codes and
handles are globally unique. Repeated semantic names may not declare
conflicting units. Bounds must occur as a valid pair.

For an observed metric `x`, resolution returns exactly one state:

- `mapped`: a unique code or handle match with a compatible unit;
- `unmapped`: no entry matches;
- `unsupported`: the extractor explicitly marks the element unsupported;
- `conflicting`: code and handle resolve differently, or the observed unit
  conflicts with the selected entry.

Only `mapped` elements receive the configured semantic metadata. The other
states remain visible with a machine-readable reason; conflicts never fall
back to a plausible-looking mapping.

## Validation

The checked-in schema is
`src/sdc_mcp_gateway/mapping/schemas/sdc-mie-1.0.schema.json`. The loader first
rejects unsupported schema versions, then validates the complete YAML object
against JSON Schema Draft 2020-12, and finally performs cross-entry semantic
checks that standard JSON Schema cannot express conveniently.

Validation fails closed for, among other cases:

- unknown fields or missing required descriptions;
- duplicate codes or handles;
- conflicting units for a semantic name;
- incomplete or reversed numeric bounds;
- controlled/critical entries without human-approval metadata;
- unsupported schema versions.

The SHA-256 of the exact source bytes is attached to the loaded document,
resource payloads, audit records, and evaluation outputs. This distinguishes
the semantic artifact version from the exact file used in a run.

## Relationship to TogoMCP

TogoMCP motivates the general idea that explicit metadata can make external
knowledge more usable by LLM-facing protocols. SDC-MIE applies that high-level
idea to the narrower SDC gateway boundary: codes, handles, units, alarm
references, access classes, provenance, and dry-run policy metadata. SDC-MIE
does not reuse TogoMCP's file format, ontology, or serialization and makes no
compatibility claim.

## Standards-oriented evolution path

A possible evolution path is deliberately staged:

1. stabilize the research schema and publish versioned examples;
2. test independent mappings against heterogeneous and physical-device MDIBs;
3. align codes, units, and provenance rules with the applicable IEEE 11073 and
   UCUM artifacts;
4. obtain multi-implementation and clinical-domain review;
5. only then consider submitting a profile or implementation guide to an
   appropriate standards community.

The present work completes only the first step and part of the second with
software profiles. It does not claim consensus, standardization, conformance,
or clinical validity.
