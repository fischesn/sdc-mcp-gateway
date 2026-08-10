# WP9 threat model, provenance, and audit evidence

## Evaluated boundary

WP9 evaluates the local gateway over MCP stdio. The MCP host launches the gateway as a
same-host subprocess; the experiment opens no MCP network listener. The device state is a
deterministic simulator snapshot. The controls below are meaningful for that boundary but
are not a production authentication, authorization, or clinical-network security claim.

The bounded no-execution claim assumes that the evaluated Python code, configuration, host,
and process boundary are not compromised. Exact allowlisting, hashes, and a local audit chain
improve detection and traceability under that assumption; they do not make a malicious host
trustworthy.

## Assets, trust boundaries, and attacker model

Assets are (1) SDC device-state integrity and provenance, (2) the no-execution boundary,
(3) mapping and policy integrity, (4) audit completeness and integrity, (5) model/API
credentials, and (6) provider, client, and human identities.

The relevant trust boundaries are:

1. SDC provider to the observation-only consumer;
2. checked-in or operator-supplied configuration to the gateway process;
3. local MCP host/client to the stdio gateway subprocess;
4. gateway resource context to any separately configured hosted model; and
5. gateway process to local audit storage.

The in-scope attacker can send malformed or malicious MCP requests, embed prompt-like text in
resource content, advertise a provider identifier chosen to resemble an allowlisted identity,
modify configuration before a run, expose credential-shaped fields to the recorder, or edit,
insert, delete, or reorder locally stored audit records after creation. A compromised gateway
host, stolen operating-system credentials, malicious replacement code, physical device
attacks, production PKI failure, denial of service, and effective SDC write-back are out of
scope for the evaluated prototype.

## Threats, current controls, and future requirements

| Threat | Current evaluated control/evidence | Residual risk or production requirement |
|---|---|---|
| Malformed or malicious MCP client | Closed tool schemas, unexpected-field rejection, resource-URI checks, dry-run-only result model, and property tests | Authenticate clients, authorize each resource/tool, rate-limit, limit request size, and isolate processes |
| Prompt injection in provider/resource content | Resource data is untrusted context; the adapter exposes no write method and every tool remains non-executing. WP7 retained three conservative injection-flag failures | Content-origin labelling, stronger context separation, model isolation, monitoring, and a separate safety case remain necessary |
| Look-alike or forged provider EPR | Allowlisting now uses exact endpoint-reference equality; one exact and three look-alike cases pass | String equality is not authentication; require authenticated SDC identity, certificate policy, and lifecycle management |
| Mapping, policy, task, prompt, or snapshot tampering | Every WP9 record carries SHA-256 identifiers for provider snapshot, mapping, policy, task, and prompt plus model ID and timestamp | Verify hashes against signed/approved manifests in an immutable deployment |
| Audit modification, insertion, deletion, or reordering | Optional SHA-256 chaining binds each record to its predecessor; changed content is detected and appending to an invalid chain fails closed | Local administrators can truncate the tail or replace the full file; remotely anchor chain heads and use access-controlled/WORM retention |
| Credential or authorization-header disclosure | Recorder recursively replaces authorization, API-key, token, password, cookie, and secret fields with `[REDACTED]`; a credential probe is absent from the output | Audit all surrounding libraries and infrastructure; use a dedicated secret store and prevent payload/body logging |
| Compromised gateway host or code | Explicitly outside the bounded claim | Hardened host, measured/signed artifacts, least privilege, monitoring, patching, and incident response |
| Future network-facing MCP transport | No listener exists in the evaluated stdio experiment | Mutual endpoint authentication, scoped authorization, TLS/certificate lifecycle, replay protection, rate limits, and externally anchored audits |

## Provenance and audit-chain design

`AuditProvenance` binds every protected record to:

- exact provider identity;
- canonical SHA-256 of the resource snapshot;
- SHA-256 of the SDC-MIE mapping and dry-run policy files;
- canonical SHA-256 of the task and prompt;
- model or deterministic processor identifier; and
- the timestamp and explicit decision reason already present in each audit event.

Before hashing, the recorder recursively redacts credential-bearing fields. Each record then
stores a zero-based chain index, the previous record hash, and a SHA-256 over its canonical
JSON representation. Verification recomputes every record and link. This detects modification,
insertion, reordering, and non-tail deletion within the available file. It cannot prove that
the final records were not truncated unless the chain head is anchored outside the host; the
evidence reports this limitation explicitly.

## Responsibility and accountability

| Actor/component | Responsible for | Not authorized or not established here |
|---|---|---|
| AI agent | Interpret supplied context and produce a bounded structured response/proposal | Clinical decision authority or device execution |
| MCP host/client | Start the local subprocess, constrain context, protect model credentials, and present outputs | Bypass gateway policy or claim provider authenticity |
| SDC-MCP gateway | Exact allowlist comparison, mapping, freshness/policy checks, redaction, provenance, audit records, and no-execution enforcement | Decide clinical appropriateness or authenticate future network clients |
| SDC provider | Supply correct device identity and state | Trust is not established merely by an EPR string |
| Clinician | Retain clinical judgment and any future approval responsibility | No approval workflow is evaluated in WP9 |
| System operator | Approve configurations, protect hosts/keys/logs, review alerts, and anchor/retain audits | Transfer accountability to the model |

## Reproduction and measured outcome

Run from the repository root:

```powershell
.venv\Scripts\python.exe -m sdc_mcp_gateway.revision.security_evidence `
  --config config/bhi2026_wp9_security.yaml
```

The checked-in evidence is under
`data/revision/security/bhi2026-wp9-security-v1/`. It contains four chained records: one
resource read, one accepted non-executing proposal, one out-of-range rejection, and one
malformed request carrying a synthetic authorization-header probe. All seven declared checks
pass. The chain verifies, a modified first record is detected, the exact provider identity is
accepted while three look-alikes are rejected, and the probe secret is absent. No network or
model call is made.
