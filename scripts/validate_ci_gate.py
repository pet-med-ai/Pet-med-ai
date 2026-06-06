#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci-gate.yml"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
DOC = ROOT / "docs" / "ops" / "GITHUB_ACTIONS_CI_GATE_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    rc = require_text(
        WORKFLOW,
        (
            "name: Pet-Med-AI CI Gate",
            "pull_request:",
            "push:",
            "workflow_dispatch:",
            "actions/checkout@v4",
            "actions/setup-python@v5",
            "python-version: \"3.11\"",
            "bash scripts/ci_static_checks.sh",
            "actions/setup-node@v4",
            "node-version: \"20\"",
            "npm install",
            "npm run build",
        ),
        ".github/workflows/ci-gate.yml",
    )
    if rc:
        return rc

    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    forbidden_workflow = (
        "DATABASE_URL:",
        "SECRET_KEY:",
        "ENABLE_EMR_REAL_IMPORT: true",
        "alembic upgrade",
        "pet-med-ai-backend.onrender.com",
        "curl -sS https://",
    )
    for needle in forbidden_workflow:
        if needle in workflow_text:
            return fail(f"CI workflow should stay static/offline; forbidden marker found: {needle}")

    rc = require_text(
        CI_STATIC,
        (
            "set -euo pipefail",
            "validate_release_readiness.py",
            "validate_release_changelog.py",
            "validate_system_version_info.py",
            "validate_feature_flags.py",
            "validate_emr_import_execute_create_only.py",
            "validate_alembic_setup.py",
            "py_compile.compile",
            "CI static checks PASS",
        ),
        "scripts/ci_static_checks.sh",
    )
    if rc:
        return rc

    ci_static_text = CI_STATIC.read_text(encoding="utf-8")
    forbidden_static = (
        "BASE_URL=https://pet-med-ai-backend.onrender.com",
        "alembic upgrade",
        "ENABLE_EMR_REAL_IMPORT=true",
        "git add .",
    )
    for needle in forbidden_static:
        if needle in ci_static_text:
            return fail(f"CI static script contains forbidden marker: {needle}")

    rc = require_text(
        DOC,
        (
            "GitHub Actions CI Gate V1",
            "ci-gate.yml",
            "ci_static_checks.sh",
            "pull_request",
            "frontend build",
            "does not run Alembic upgrade",
            "does not enable ENABLE_EMR_REAL_IMPORT",
        ),
        "docs/ops/GITHUB_ACTIONS_CI_GATE_V1.md",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_ci_gate.py",
            "GitHub Actions CI gate validation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK GitHub Actions CI gate: workflow, static checks and smoke validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
