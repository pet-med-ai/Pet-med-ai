#!/usr/bin/env python3
"""Export a pinned source-only Mac kit; no credentials, DB files or old evidence."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GIT = ["git", "--no-replace-objects", "-C", str(ROOT)]
PATHS = [
    "requirements.txt", "backend", "frontend/src", "frontend/index.html",
    "frontend/public", "frontend/package.json", "frontend/package-lock.json",
    "frontend/vite.config.js", "scripts/treatment_acceptance.py",
    "scripts/treatment_acceptance_support.py", "scripts/treatment_acceptance_drill.py",
    "scripts/treatment_acceptance_mac.command", "docs/treatment-acceptance-mac-card.md",
]


def runtime_files(tree):
    entries = subprocess.check_output([*GIT, "ls-tree", "-r", "-z", tree, "--", *PATHS])
    for entry in entries.split(b"\0")[:-1]:
        meta, path_bytes = entry.split(b"\t", 1)
        path = path_bytes.decode()
        if path.endswith((".db", ".sqlite", ".sqlite3")) or "/.env" in path:
            continue
        mode, kind, oid = meta.split()
        if kind != b"blob" or mode not in (b"100644", b"100755"):
            raise ValueError(f"Unsupported Git entry in treatment kit: {path}")
        yield path, int(mode, 8) & 0o777, oid


def read_blob(process, oid):
    process.stdin.write(oid + b"\n")
    process.stdin.flush()
    header = process.stdout.readline().split()
    if len(header) != 3 or header[:2] != [oid, b"blob"]:
        raise RuntimeError(f"Cannot read pinned Git blob {oid.decode()}")
    size = int(header[2])
    data = process.stdout.read(size)
    if len(data) != size or process.stdout.read(1) != b"\n":
        raise RuntimeError(f"Incomplete Git blob {oid.decode()}")
    return data


def add_file(archive, name, mode, data):
    # TarInfo starts with zero uid/gid/mtime and empty owner/group names.
    entry = tarfile.TarInfo("PMAI-treatment-acceptance/" + name)
    entry.mode = mode
    entry.size = len(data)
    archive.addfile(entry, io.BytesIO(data))


def write_kit(output, commit, tree):
    files = {}
    with (
        subprocess.Popen([*GIT, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as blobs,
        output.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT, encoding="utf-8") as archive,
    ):
        for name, mode, oid in runtime_files(tree):
            data = read_blob(blobs, oid)
            files[name] = hashlib.sha256(data).hexdigest()
            add_file(archive, name, mode, data)
        manifest = {"format": "pmai-treatment-kit-v1", "commit": commit, "tree": tree, "files": files}
        add_file(archive, "acceptance-manifest.json", 0o644, json.dumps(manifest, ensure_ascii=False, indent=2).encode())
    if blobs.returncode:
        raise subprocess.CalledProcessError(blobs.returncode, blobs.args)
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if subprocess.check_output([*GIT, "status", "--porcelain"]).strip():
        raise SystemExit("Package only a clean, committed candidate")
    commit = subprocess.check_output([*GIT, "rev-parse", "HEAD"]).decode().strip()
    tree = subprocess.check_output([*GIT, "rev-parse", commit + "^{tree}"]).decode().strip()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        staged = Path(tmp) / "kit.tar.gz"
        count = write_kit(staged, commit, tree)
        size = staged.stat().st_size
        with staged.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        staged.replace(args.output)
    print(json.dumps({"commit": commit, "tree": tree, "files": count, "sha256": digest, "bytes": size}))


if __name__ == "__main__":
    main()
