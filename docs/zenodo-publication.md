# Zenodo publication

Status: **published on 25 September 2026**, following explicit author approval.
Public record: https://zenodo.org/records/22960634 (HTTP 200 without login).
Version DOI: `10.5281/zenodo.22960634`; all-versions concept DOI:
`10.5281/zenodo.22960633`. Cite the version DOI for the evaluated artifact.
The publication page shows the checked creators, version, MIT license, and ZIP
with MD5 `9a4f560f57cf559114d4d681f223482e`, matching the local archive.
The DOI resolver returned HTTP 404 on the publication-day checks; activation
has not yet been verified. The direct record link already provides public access.
Verification state is recorded separately in `zenodo-deposit-status.json`.

The authors confirmed **Bennet Gerlach, then Stefan Fischer**, both University
of Lübeck. One combined software-and-evidence deposit was chosen for the initial
archive because the frozen results already belong to the versioned repository.
The existing MIT license is retained; no new license is imposed on dependencies.

## Stable source, corrected metadata

- Preserve tag `v2.0.0-rc1` at
  `4cf508eee7c70b8fa7873f6ce457e6407e99f0e7`.
- Correct the current `CITATION.cff` and Zenodo creator list. Preserve the entire
  `pyproject.toml`, including internal package version `0.13.0` and historical
  packaging credits, because that file belongs to the 32 frozen experiment
  inputs. Correct archival authorship does not require rewriting those inputs.
- Build an archive with an unchanged `source/` export of the tag plus a clearly
  separate top-level citation, metadata, README, license, manifest, and checker.
- The source still contains its historical citation metadata. This is deliberate
  provenance preservation, not the metadata to use for the new deposit.
- The citation's release date is 10 August 2026; the Zenodo publication
  date is 25 September 2026.
- Do not create a new GitHub release, move a tag, activate automatic Zenodo
  publication, or describe this release candidate as stable `2.0.0`.

## Prepare and check

From the repository root:

```powershell
python scripts/build-zenodo-archive.py --output-dir dist/zenodo-v2.0.0-rc1
```

The builder refuses to overwrite an existing output directory, excludes
untracked/ignored files by exporting the pinned Git tree, verifies all source
Git blob identities, and writes one upload ZIP and an external checksum file.
Extract the ZIP and run its `check-zenodo-archive.py` for payload hashes and key
scientific evidence checks. Scan the extracted final package for credentials
before uploading; do not include credentials or a secret-scanner executable.

`docs/zenodo-archive-readme.md` becomes the archive README. `.zenodo.json` is the
preserved deposit metadata used in the published ZIP. The builder uses the
pre-publication citation snapshot in `docs/zenodo-v2.0.0-rc1/CITATION.cff` so that
the live citation can gain the actual DOI without changing the published ZIP.
The manifest retains the original preparation-time filenames. Do not modify
these archival inputs when updating current citation or publication notes.

## Zenodo workflow

1. Sign in to the existing Zenodo account; do not share login credentials.
2. Create a draft of resource type **Software** with the prepared metadata and
   one ZIP. Use the confirmed creator order and MIT license.
3. Preview the files, version, license, and description. Reserve a DOI if useful,
   but distinguish reservation from actual publication.
4. Obtain final publication approval and publish. Then verify public access,
   file checksums, creator order, version DOI, and concept DOI.
5. Add the actual version DOI to the paper and current citation metadata;
   rebuild and review both paper layouts and the minimal arXiv package.

Official instructions:

- https://help.zenodo.org/docs/deposit/create-new-upload/
- https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/
- https://help.zenodo.org/docs/github/archive-software/manual-upload/

The paper itself goes to arXiv; it is not duplicated in this software deposit.

## Checked archive

- Upload file: `dist/zenodo-v2.0.0-rc1/sdc-mcp-gateway-v2.0.0-rc1-zenodo.zip`.
- Size: 1,227,527 bytes; 659 files, including all 653 pinned source files.
- SHA-256: `4313f55d053846b616319a3fa3d3aa21778b2bf4e12a14a5a45d902be746b5f6`.
- The extracted ZIP passed 2,679 offline integrity and key evidence assertions.
- All 653 source files match their original Git blob identities. The 32
  scientific input files match their stored digests directly. Five historical
  provenance digests require explicitly disclosed LF-to-CRLF reconstruction;
  the payload itself is not changed.
- Gitleaks 8.30.1 reported no leaks in the extracted final package.
- Both archive scripts pass Ruff. The CFF and JSON metadata were parsed and
  checked for the confirmed author order; the frozen TOML remains unchanged.
- An independent repeat build produced a byte-identical ZIP.
- A post-publication rebuild using Python 3.11.7 / zlib 1.3 again produced the
  published ZIP byte-for-byte. Python 3.14.4 / zlib-ng produced different
  compressed bytes but identical contents for all 659 files, including the
  manifest; ZIP-level identity depends on the compression implementation.
- The public ZIP was downloaded without authentication after publication; its
  SHA-256 matches the approved local archive exactly.
- The paper cites the version DOI and direct record URL. Both MiKTeX layouts
  retain 18 pages; the new minimal arXiv export is `output/arxiv-zenodo/` in the
  paper repository. The independently extracted source package produces the
  same 18-page text. arXiv itself has not yet received a submission.

The ZIP contains only versioned source and deliberately added archive metadata.
The paper's confidential review material and local credentials are not included.
No experiments, new model calls, or GitHub release creation were performed.
Publication-related metadata and paper updates are committed separately from
the unchanged evaluated source tag.
