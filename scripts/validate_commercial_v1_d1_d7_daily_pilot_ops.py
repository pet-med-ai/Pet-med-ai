#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "docs" / "ops"

REQUIRED_FILES = [
    OPS / "COMMERCIAL_V1_D1_D7_DAILY_PILOT_OPERATIONS_EVIDENCE_V1.md",
    OPS / "COMMERCIAL_V1_D1_D7_DAILY_PILOT_CHECKLIST.csv",
    OPS / "COMMERCIAL_V1_D1_D7_DAILY_OPERATIONS_LOG_TEMPLATE.csv",
    OPS / "COMMERCIAL_V1_D1_D7_DAILY_INCIDENT_LOG.csv",
    OPS / "COMMERCIAL_V1_D1_D7_DAILY_SIGNOFF.csv",
]

CHECKLIST_COLUMNS = [
    "day", "date", "check_id", "area", "item", "required_state", "actual_state",
    "evidence", "owner", "go_no_go", "status", "notes",
]

DAILY_LOG_COLUMNS = [
    "day", "date", "pilot_clinic", "pilot_users", "base_url", "frontend_url",
    "git_commit", "healthz_ok", "ci_static_pass", "online_smoke_pass",
    "schema_ok", "database_revision", "alembic_head", "dangerous_flags_disabled",
    "ai_consult_ok", "dynamic_consult_ok", "case_save_ok", "case_detail_ok",
    "case_edit_ok", "word_export_ok", "preventive_reminder_ok", "manual_queue_ok",
    "opt_out_ok", "open_p0_count", "open_p1_count", "decision", "release_owner",
    "security_owner", "clinical_ops_owner", "notes",
]

INCIDENT_COLUMNS = [
    "incident_id", "day", "date", "severity", "area", "summary",
    "status", "owner", "decision", "notes",
]

SIGNOFF_COLUMNS = [
    "day", "date", "release_owner", "security_owner", "clinical_ops_owner",
    "daily_decision", "signoff_status", "notes",
]

DAYS = {f"D{i}" for i in range(1, 8)}
ALLOWED_DECISIONS = {
    "TBD",
    "",
    "GO_CONTINUE_NEXT_DAY",
    "GO_WITH_MONITORING",
    "NO_GO_PAUSE_PILOT",
    "GO_COMPLETE_D7",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require_columns(path: Path, required: list[str]) -> list[dict[str, str]]:
    rows = read_csv(path)
    if not rows:
        fail(f"{path.relative_to(ROOT)} has no data rows")
    missing = [col for col in required if col not in rows[0]]
    if missing:
        fail(f"{path.relative_to(ROOT)} missing columns: {missing}")
    return rows


def require_all_days(rows: list[dict[str, str]], label: str) -> None:
    found = {str(row.get("day", "")).strip() for row in rows}
    missing = sorted(DAYS - found)
    if missing:
        fail(f"{label} missing day rows: {missing}")


def main() -> int:
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing required file: {path.relative_to(ROOT)}")
        if path.stat().st_size <= 0:
            fail(f"empty required file: {path.relative_to(ROOT)}")

    md = REQUIRED_FILES[0].read_text(encoding="utf-8")
    for phrase in (
        "Commercial V1 D1-D7 Daily Pilot Operations Evidence",
        "GO_CONTINUE_D1",
        "0008_auto_delivery",
        "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
        "GO_COMPLETE_D7",
        "DiagnosticReport / Observation / ImagingStudy",
    ):
        if phrase not in md:
            fail(f"master evidence doc missing phrase: {phrase}")

    checklist = require_columns(
        OPS / "COMMERCIAL_V1_D1_D7_DAILY_PILOT_CHECKLIST.csv",
        CHECKLIST_COLUMNS,
    )
    daily_log = require_columns(
        OPS / "COMMERCIAL_V1_D1_D7_DAILY_OPERATIONS_LOG_TEMPLATE.csv",
        DAILY_LOG_COLUMNS,
    )
    incidents = require_columns(
        OPS / "COMMERCIAL_V1_D1_D7_DAILY_INCIDENT_LOG.csv",
        INCIDENT_COLUMNS,
    )
    signoffs = require_columns(
        OPS / "COMMERCIAL_V1_D1_D7_DAILY_SIGNOFF.csv",
        SIGNOFF_COLUMNS,
    )

    require_all_days(checklist, "checklist")
    require_all_days(daily_log, "daily log")
    require_all_days(incidents, "incident log")
    require_all_days(signoffs, "signoff")

    for row in daily_log:
        decision = str(row.get("decision", "")).strip()
        if decision not in ALLOWED_DECISIONS:
            fail(f"invalid daily log decision for {row.get('day')}: {decision}")
        if decision in {"GO_CONTINUE_NEXT_DAY", "GO_COMPLETE_D7"}:
            if str(row.get("open_p0_count", "")).strip() not in {"0", "0.0"}:
                fail(f"{row.get('day')} go decision requires open_p0_count=0")
            if str(row.get("open_p1_count", "")).strip() not in {"0", "0.0"}:
                fail(f"{row.get('day')} go decision requires open_p1_count=0")

    for row in signoffs:
        decision = str(row.get("daily_decision", "")).strip()
        if decision not in ALLOWED_DECISIONS:
            fail(f"invalid signoff decision for {row.get('day')}: {decision}")

    print("PASS: Commercial V1 D1-D7 Daily Pilot Operations Evidence files are present and structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
