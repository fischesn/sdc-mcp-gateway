"""Package the pinned Git tree plus separate archival metadata; no network calls."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

COMMIT = "4cf508eee7c70b8fa7873f6ce457e6407e99f0e7"
TAG = "v2.0.0-rc1"


def build(output_dir: Path) -> None:
    repo = Path(__file__).resolve().parents[1]

    def git(*args: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(repo), *args])

    if git("rev-parse", f"{TAG}^{{commit}}").decode().strip() != COMMIT:
        raise ValueError("Pinned release tag no longer resolves to the expected commit")
    tree = {}
    for row in git("ls-tree", "-rz", COMMIT).split(b"\0"):
        if not row:
            continue
        header, filename = row.split(b"\t", 1)
        mode, kind, oid = header.decode().split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"Unsupported Git tree entry: {filename!r}")
        tree[filename.decode("utf-8")] = oid
    archive = zipfile.ZipFile(io.BytesIO(git(
        "-c", "core.autocrlf=false", "-c", "core.eol=lf",
        "archive", "--format=zip", COMMIT,
    )))
    source = {i.filename: archive.read(i) for i in archive.infolist() if not i.is_dir()}
    if source.keys() != tree.keys():
        raise ValueError("Git archive did not contain the entire pinned tree")
    for filename, content in source.items():
        blob = b"blob " + str(len(content)).encode() + b"\0" + content
        if hashlib.sha1(blob).hexdigest() != tree[filename]:
            raise ValueError(f"Source bytes differ from Git blob: {filename}")

    payload = {"source/" + name: content for name, content in source.items()}
    extras = {
        "README.md": "docs/zenodo-archive-readme.md",
        "CITATION.cff": "CITATION.cff",
        "zenodo-metadata.json": ".zenodo.json",
        "check-zenodo-archive.py": "scripts/check-zenodo-archive.py",
    }
    for name, relative in extras.items():
        # Preserve the published ZIP after adding its DOI to the live citation.
        # Manifest origins name the files as they were prepared before upload.
        snapshot = "docs/zenodo-v2.0.0-rc1/CITATION.cff" if name == "CITATION.cff" else relative
        payload[name] = (repo / snapshot).read_bytes().replace(b"\r\n", b"\n")
    payload["LICENSE"] = source["LICENSE"]
    metadata = json.loads(payload["zenodo-metadata.json"])
    if [c["name"] for c in metadata["creators"]] != ["Gerlach, Bennet", "Fischer, Stefan"]:
        raise ValueError("Unexpected creator order")
    if metadata["version"] != "2.0.0-rc1" or metadata["license"] != "MIT":
        raise ValueError("Unexpected archival version or license")
    manifest = {
        "schema_version": 1,
        "repository": "https://github.com/fischesn/sdc-mcp-gateway",
        "source_commit": COMMIT,
        "source_tag": TAG,
        "source_file_count": len(source),
        "archive_prepared_date": "2026-09-25",
        "metadata_policy": "source/ is unchanged; top-level files correct citation metadata and add verification instructions",
        "files": [],
    }
    for name, content in sorted(payload.items()):
        item = {"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        if name.startswith("source/"):
            item["git_blob_sha1"] = tree[name.removeprefix("source/")]
        else:
            item["origin"] = extras.get(name, "pinned source LICENSE")
        manifest["files"].append(item)
    payload["manifest.json"] = (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode()

    output_dir.mkdir(parents=True, exist_ok=False)
    zip_path = output_dir / "sdc-mcp-gateway-v2.0.0-rc1-zenodo.zip"
    with zipfile.ZipFile(zip_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as result:
        for name, content in sorted(payload.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            result.writestr(info, content)
    with zipfile.ZipFile(zip_path) as result:
        if result.testzip() is not None:
            raise ValueError("ZIP integrity test failed")
        for name, content in payload.items():
            if result.read(name) != content:
                raise ValueError(f"ZIP verification failed: {name}")
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (output_dir / "SHA256SUMS.txt").write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    print(json.dumps({"archive": str(zip_path.resolve()), "bytes": zip_path.stat().st_size,
                      "sha256": digest, "source_files": len(source),
                      "archive_files": len(payload)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    build(parser.parse_args().output_dir.resolve())
