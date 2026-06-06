#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHANGELOG = ROOT / "CHANGELOG.md"
RUNBOOK = ROOT / "docs" / "ops" / "RELEASE_TAG_CHANGELOG_V1.md"
TEMPLATE = ROOT / "docs" / "ops" / "RELEASE_RECORD_TEMPLATE.md"
POLICY = ROOT / "docs" / "ops" / "RELEASE_POLICY.csv"
EXAMPLES = ROOT / "docs" / "ops" / "RELEASE_TAG_EXAMPLES.md"
RELEASES_DIR = ROOT / "docs" / "ops" / "releases"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

TAG_PATTERN = re.compile(r"release/[0-9]{4}\.[0-9]{2}\.[0-9]{2}(-[A-Za-z0-9_.-]+)?-[0-9]+")


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_file(path: Path) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    return 0


def require_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    rc = require_file(path)
    if rc:
        return rc
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (CHANGELOG, RUNBOOK, TEMPLATE, POLICY, EXAMPLES, SMOKE):
        rc = require_file(path)
        if rc:
            return rc

    if not RELEASES_DIR.exists():
        return fail("missing release records directory: docs/ops/releases")

    rc = require_text(
        CHANGELOG,
        (
            "# Changelog",
            "## Unreleased",
            "Release / Upgrade Framework V1",
            "Feature Flag / Safety Gate V1",
        ),
        "CHANGELOG.md",
    )
    if rc:
        return rc

    rc = require_text(
        RUNBOOK,
        (
            "Pet-Med-AI Release Tag / Changelog V1",
            "release/YYYY.MM.DD-N",
            "docs/ops/releases/",
            "git tag -a",
            "validate_release_changelog.py",
            "database_revision != alembic_head",
        ),
        "release tag/changelog runbook",
    )
    if rc:
        return rc

    rc = require_text(
        TEMPLATE,
        (
            "Release identity",
            "Database revision before",
            "Database revision after",
            "Feature flags",
            "Rollback plan",
            "Final status",
        ),
        "release record template",
    )
    if rc:
        return rc

    rc = require_text(
        POLICY,
        (
            "risk_class",
            "database-migration",
            "real-write",
            "requires_online_smoke",
            "requires_rollback_snapshot",
        ),
        "release policy CSV",
    )
    if rc:
        return rc

    rc = require_text(
        EXAMPLES,
        (
            "Release tag examples",
            "release/2026.06.06",
            "git push origin",
        ),
        "release tag examples",
    )
    if rc:
        return rc

    examples_text = EXAMPLES.read_text(encoding="utf-8")
    if not TAG_PATTERN.search(examples_text):
        return fail("release tag examples do not include a valid release/YYYY.MM.DD-* tag")

    rc = require_text(
        SMOKE,
        (
            "validate_release_changelog.py",
            "release changelog validation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    print("OK release tag/changelog: changelog, release policy, templates and smoke validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
