#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "preventive_care_ops_api.py"
MAIN = ROOT / "backend" / "main.py"
OPS = ROOT / "frontend" / "src" / "pages" / "OpsDashboard.jsx"
DOC = ROOT / "docs" / "preventive_care" / "PREVENTIVE_CARE_OPS_DASHBOARD_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_file(path: Path) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
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
    for path in (API, MAIN, OPS, DOC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        API,
        (
            'router = APIRouter(prefix="/api/preventive-care/ops"',
            '@router.get("/summary"',
            "PreventiveCareReminder",
            "PreventiveCareNotificationQueue",
            "PreventiveCareClientPreference",
            "PreventiveCareEvent",
            '"message": "preventive_care_ops_summary"',
            '"read_only": True',
            '"writes_database": False',
            '"auto_send": False',
            '"sends_external_message": False',
            '"executes_real_import": False',
        ),
        "backend/preventive_care_ops_api.py",
    )
    if rc:
        return rc

    api_text = API.read_text(encoding="utf-8")
    for forbidden in ("db.add(", "db.commit(", "requests.post(", "httpx.post(", "smtplib", "twilio", "ENABLE_EMR_REAL_IMPORT=true"):
        if forbidden in api_text:
            return fail(f"preventive care ops API must remain read-only/no external send: {forbidden}")

    rc = require_text(
        MAIN,
        (
            "preventive_care_ops_api_router",
            "app.include_router(preventive_care_ops_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        OPS,
        (
            "Preventive Care Reminder Ops Dashboard V1",
            "/api/preventive-care/ops/summary",
            "preventiveCareOps",
            "Preventive attention",
            "Queue needs review",
            "Blocked opt-out",
            "Recent events 30d",
            "sends_external_message=false",
            "auto_send=false",
        ),
        "OpsDashboard.jsx",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Preventive Care Reminder Ops Dashboard V1",
            "GET /api/preventive-care/ops/summary",
            "read_only=true",
            "writes_database=false",
            "sends_external_message=false",
            "manual_review_required=true",
        ),
        "ops dashboard doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_preventive_care_ops_dashboard.py",
            "preventive care reminder ops dashboard validation",
            "/api/preventive-care/ops/summary",
            "preventive care ops summary",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_preventive_care_ops_dashboard.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK preventive care ops dashboard: read-only summary API and Ops UI are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
