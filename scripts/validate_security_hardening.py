#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "security": ROOT / "SECURITY.md",
    "runbook": ROOT / "docs" / "ops" / "RENDER_GITHUB_SECURITY_HARDENING_V1.md",
    "checklist": ROOT / "docs" / "ops" / "SECURITY_CHECKLIST.csv",
    "rotation": ROOT / "docs" / "ops" / "SECRET_ROTATION_RUNBOOK.md",
    "render_logs": ROOT / "docs" / "ops" / "RENDER_ENV_LOG_REDACTION_RUNBOOK.md",
    "db_drill": ROOT / "docs" / "ops" / "DB_BACKUP_RESTORE_DRILL_RUNBOOK.md",
    "db_log": ROOT / "docs" / "ops" / "DB_RESTORE_DRILL_LOG.csv",
    "security_check": ROOT / "scripts" / "security_check.sh",
}
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


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
            FILES["security"],
            (
                "Security Policy",
                "No hardcoded production secrets",
                "Weekly security check",
                "ENABLE_EMR_REAL_IMPORT=false",
            ),
            "SECURITY.md",
        ),
        (
            FILES["runbook"],
            (
                "Render / GitHub Security Hardening V1",
                "GitHub token / PAT review",
                "Render environment and log review",
                "Database backup and restore drill",
                "security_check.sh",
                "Hard No-Go before pilot_0 real execution",
            ),
            "security hardening runbook",
        ),
        (
            FILES["checklist"],
            (
                "phase,item,owner",
                "Review classic PATs",
                "Review backend env vars",
                "Confirm DB backup",
            ),
            "security checklist",
        ),
        (
            FILES["rotation"],
            (
                "Secret Rotation Runbook",
                "GitHub PAT rotation",
                "Render secret rotation",
                "Webhook secret rotation",
            ),
            "secret rotation runbook",
        ),
        (
            FILES["render_logs"],
            (
                "Render Environment / Log Redaction Runbook",
                "SECRET_KEY",
                "DATABASE_URL",
                "PMAI_WEBHOOK_SECRET",
                "bash scripts/security_check.sh",
            ),
            "render env log runbook",
        ),
        (
            FILES["db_drill"],
            (
                "Database Backup / Restore Drill Runbook",
                "pet-med-ai-db",
                "DB_RESTORE_DRILL_LOG.csv",
                "No-Go",
            ),
            "db restore drill runbook",
        ),
        (
            FILES["db_log"],
            (
                "drill_id,date,environment",
                "rollback_snapshot_id",
                "smoke_after_restore",
            ),
            "db restore drill log",
        ),
        (
            FILES["security_check"],
            (
                "Pet-Med-AI security check V1",
                "Secret echo / print scan",
                "Common hardcoded credential patterns",
                "render.yaml secret marker scan",
                "tracked sensitive filename scan",
            ),
            "security_check.sh",
        ),
        (
            SMOKE,
            (
                "validate_security_hardening.py",
                "render github security hardening validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_security_hardening.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK Render/GitHub security hardening: runbooks, security scan and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
