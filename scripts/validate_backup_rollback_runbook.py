#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "ops" / "BACKUP_ROLLBACK_VERIFICATION_V1.md"
RENDER = ROOT / "docs" / "ops" / "RENDER_POSTGRES_BACKUP_RUNBOOK.md"
CHECKLIST = ROOT / "docs" / "ops" / "BACKUP_ROLLBACK_CHECKLIST.csv"
REHEARSAL = ROOT / "docs" / "ops" / "ROLLBACK_REHEARSAL_TEMPLATE.csv"
DECISION = ROOT / "docs" / "ops" / "BACKUP_ROLLBACK_DECISION_MATRIX.csv"
POLICY = ROOT / "docs" / "ops" / "BACKUP_ROLLBACK_POLICY.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require(path: Path, needles: tuple[str, ...], label: str) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    checks = [
        (
            RUNBOOK,
            (
                "Backup / Rollback Verification V1",
                "rollback_snapshot_id",
                "schema_ok=true",
                "database_revision == alembic_head",
                "ENABLE_EMR_REAL_IMPORT",
                "Hard No-Go",
                "Do not",
            ),
            "backup rollback runbook",
        ),
        (
            RENDER,
            (
                "Render PostgreSQL Backup Runbook",
                "pet-med-ai-db",
                "pet-med-ai-backend",
                "/api/system/version",
                "/api/system/feature-flags",
                "BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh",
                "Do not run",
            ),
            "render backup runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner,command_or_action",
                "rollback_snapshot_id",
                "Confirm Render DB backup exists",
                "Confirm online smoke",
            ),
            "backup rollback checklist",
        ),
        (
            REHEARSAL,
            (
                "rehearsal_id",
                "rollback_snapshot_id",
                "restore_path_verified",
                "smoke_after_passed",
                "clinical_check_passed",
            ),
            "rollback rehearsal template",
        ),
        (
            DECISION,
            (
                "condition,severity,decision",
                "schema_ok=false",
                "no rollback snapshot",
                "rollback-evaluate",
            ),
            "backup rollback decision matrix",
        ),
        (
            POLICY,
            (
                "operation,backup_required",
                "database-migration",
                "emr-create-only-pilot",
                "ENABLE_EMR_REAL_IMPORT",
            ),
            "backup rollback policy",
        ),
        (
            SMOKE,
            (
                "validate_backup_rollback_runbook.py",
                "backup rollback verification validation",
            ),
            "smoke script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK backup/rollback verification: runbooks, checklists and smoke validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
