#!/usr/bin/env python3
"""Replay the immutable PR72 governance package against its actual candidate.

Current clinic code is checked separately by the PostgreSQL/UI CI job. Never
rewrite historical expected hashes to make a different model look identical.
"""

import ast
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "58cdf136093d129fca71fb246a88d7cc896f1c91"
FROZEN = [
    "docs/clinical_data",
    "docs/ops/ALEMBIC_RELEASE_GUARDRAILS.md",
    "render.yaml",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
    ":(glob)scripts/*treatment_framework_signed_review_state_persistence*",
]


def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def main():
    run("git", "merge-base", "--is-ancestor", BASE, "HEAD")
    run("git", "diff", "--check")
    # The old governance files and runners themselves must remain byte-identical.
    run("git", "diff", "--exit-code", BASE, "--", *FROZEN)
    if list((ROOT / "backend/migrations/versions").glob("0010*.py")):
        raise RuntimeError(
            "Historical 0010 remains inactive; use the reviewed mc migration chain"
        )
    for path in (ROOT / "backend").rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    print("Current backend syntax and unchanged historical package: PASS", flush=True)
    with tempfile.TemporaryDirectory(prefix="pmai-frozen-check-") as directory:
        worktree = Path(directory) / "candidate"
        run("git", "worktree", "add", "--detach", str(worktree), BASE)
        try:
            print(f"Historical governance only: replay at {BASE}", flush=True)
            subprocess.run(
                ["bash", "scripts/ci_static_checks.sh"], cwd=worktree, check=True
            )
        finally:
            run("git", "worktree", "remove", "--force", str(worktree))


if __name__ == "__main__":
    main()
