# SDC-MCP Gateway: Software and Evaluation Artifacts

Bennet Gerlach and Stefan Fischer, University of Lübeck.

Archival version: **2.0.0-rc1**. Archive prepared: 25 September 2026.
Software tag: **v2.0.0-rc1**, created 10 August 2026.
Source commit: **4cf508eee7c70b8fa7873f6ce457e6407e99f0e7**.
Repository: https://github.com/fischesn/sdc-mcp-gateway

This archive accompanies *A Safety-Bounded SDC-to-MCP Gateway for Medical AI
Agents*. It does not assert acceptance or publication of that manuscript.
It contains no manuscript, confidential peer reviews, or rebuttals.

## Start here

- `source/`: unchanged Git-tracked files at the source commit, including code,
  tests, configuration, schemas, recorded responses, and evaluation results.
- `CITATION.cff`: corrected citation metadata. Please cite this top-level file,
  not the historical citation file inside `source/`.
- `zenodo-metadata.json`: record metadata prepared for the deposit.
- `manifest.json`: SHA-256 of every payload file, source Git blob identifiers,
  source commit, and explicit provenance for the added archival documents.
- `check-zenodo-archive.py`: offline integrity and key evidence checks; requires
  Python 3.11 or later, standard library only.
- `LICENSE`: existing repository MIT license, copied unchanged. Dependencies
  obtained separately retain their own licenses.

After extracting the ZIP, run from its top-level directory:

```text
python check-zenodo-archive.py
```

This checks every payload file and key scientific inputs and results. It makes
no network calls, performs no model requests, does not regrade recorded answers,
and does not execute device operations. The archive contains no Git history;
source blob identities and the pinned commit are recorded in `manifest.json`.

## Version and provenance distinctions

The release tag and the internal Python package version serve different roles:
the archival release is `v2.0.0-rc1`, while `source/pyproject.toml` records the
evaluated package as `0.13.0`. The historical `source/CITATION.cff` still names
only Stefan Fischer and version `0.10.7`; the corrected top-level citation names
Bennet Gerlach followed by Stefan Fischer and references the actual release.
This preserves the historical source tree without moving or rewriting the tag.

The consolidated deterministic checks ran on clean code commit
`7b269c0e4598d93d231a83d685a7bbd23efcf692`; the archived commit subsequently added
that evidence bundle. The May functional measurements, August model evaluations,
representation comparison, and protocol tests are distinct experiments, not one
new run. No external-model experiment was repeated for this archive.

Git exports text using its stored line endings. Some historical provenance
digests were calculated on Windows CRLF working-tree files. The checker first
tries the archived bytes, then explicitly reports any LF/CRLF-only match.
Manifest hashes always refer to the exact bytes in this archive.

## Evidence index (paths relative to source/)

| Evidence | Location |
|---|---|
| Consolidated checks and provenance | `experiments/2026-08-10-consolidated-evaluation/` |
| Python/Python protocol tests | `experiments/2026-08-10-container-same-stack/` |
| Independent Java SDCri/Python protocol tests | `experiments/2026-08-10-sdcri-cross-stack/` |
| Five-model hold-out and raw responses | `data/revision/holdout/bhi2026-wp7-v1-holdout-20260808T145452_463167Z/` |
| Representation comparison and raw responses | `data/revision/ablation/bhi2026-wp8-v1-ablation-20260809T201424_088639Z/` |
| Audit-chain evidence | `data/revision/security/bhi2026-wp9-security-v1/` |
| Earlier functional measurements | `experiments/2026-05-21-v07-simulated-scenarios/` |
| Scenarios, tasks, policies, input lock | `config/`, especially `bhi2026_wp7_freeze.json` |

The five-model evaluation contains 420 cases (five models, 28 tasks, three
repetitions), with 414 originally graded passes. Repetitions are not independent
new tasks. The representation comparison contains 168 new raw/generic cases,
reuses 84 enriched cases, and includes a 28-task deterministic baseline.

Use `wp8-analysis-summary.json` for the corrected representation analysis, not
the earlier `wp8-summary.json`. Original grades and responses remain unchanged.
The six generic-to-enriched improvements concern canonical metric-identifier
conformance, not demonstrated improvement in clinical alarm recognition. The
archive preserves earlier statistical summaries for provenance; they do not
establish independent-sample population generalization.

The May benchmark JSON files specify 200 measured iterations and 20 warm-up
iterations per run; these supersede inconsistent older README shorthand. The
SDCri report records successful discovery with `directed_service_fallback=false`;
its generic conditional fallback note does not mean a fallback was used.

## Reproduction beyond inspecting recorded evidence

For installation and tests, see `source/README.md` and `source/INSTALLATION.md`.
For deterministic reruns, see `source/docs/consolidated-evaluation.md`. Run those
commands from `source/` and choose a fresh output directory. Version-control
provenance is available by checking out the pinned commit from the repository;
the ZIP itself does not include `.git`.

The Python/Python protocol experiment requires Docker. The cross-stack experiment
requires Java and the separately obtained SDCri revision documented in its
experiment README. Third-party runtimes, dependencies, JAR files, ephemeral TLS
private keys, and provider credentials are not bundled. API credentials and
network access would be needed for new model calls, which are neither necessary
for the offline checks nor expected to reproduce nondeterministic responses
byte-for-byte.

## Scope and safety

All observations concern synthetic scenarios or software-reference devices.
There is no physical-device or clinical validation. Read-only resources and
non-executing tools do not establish safety for a clinical deployment. This
research software is not for patient care, autonomous therapy, or real device
control.
