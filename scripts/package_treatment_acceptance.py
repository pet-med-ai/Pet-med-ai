#!/usr/bin/env python3
"""Export a pinned source-only Mac kit; no credentials, DB files or old evidence."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    def git(*items):
        return subprocess.check_output(["git", "-C", str(ROOT), *items])
    if git("status", "--porcelain").strip():
        raise SystemExit("Package only a clean, committed candidate")
    paths = ["requirements.txt", "backend", "frontend/src", "frontend/index.html", "frontend/public", "frontend/package.json", "frontend/package-lock.json", "frontend/vite.config.js", "scripts/treatment_acceptance.py", "scripts/treatment_acceptance_support.py", "scripts/treatment_acceptance_drill.py", "scripts/treatment_acceptance_mac.command", "docs/treatment-acceptance-mac-card.md"]
    names = git("ls-files", "-z", "--", *paths).decode().split("\0")
    names = [n for n in names if n and not n.endswith((".db", ".sqlite", ".sqlite3")) and "/.env" not in n]
    info = {"format": "pmai-treatment-kit-v1", "commit": git("rev-parse", "HEAD").decode().strip(), "tree": git("rev-parse", "HEAD^{tree}").decode().strip(), "files": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.output, "w:gz") as archive:
        for name in names:
            archive.add(ROOT / name, arcname="PMAI-treatment-acceptance/" + name, recursive=False)
        data = json.dumps(info, ensure_ascii=False, indent=2).encode()
        entry = tarfile.TarInfo("PMAI-treatment-acceptance/acceptance-manifest.json")
        entry.size, entry.mode = len(data), 0o644
        archive.addfile(entry, io.BytesIO(data))
    print(json.dumps({"commit": info["commit"], "tree": info["tree"], "files": len(names), "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(), "bytes": args.output.stat().st_size}))


if __name__ == "__main__":
    main()
