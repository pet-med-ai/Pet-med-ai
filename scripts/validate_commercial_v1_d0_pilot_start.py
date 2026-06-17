#!/usr/bin/env python3
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "docs" / "ops"

REQUIRED_FILES = [
    OPS / "COMMERCIAL_V1_D0_PILOT_START_EVIDENCE_V1.md",
    OPS / "COMMERCIAL_V1_D0_PILOT_START_CHECKLIST.csv",
    OPS / "COMMERCIAL_V1_D0_PILOT_WORKFLOW_EVIDENCE_TEMPLATE.csv",
    OPS / "COMMERCIAL_V1_D0_PILOT_INCIDENT_SNAPSHOT.csv",
]

CHECKLIST_REQUIRED_COLUMNS = [
    "check_id",
    "area",
    "item",
    "required_state",
    "actual_state",
    "evidence",
    "owner",
    "go_no_go",
    "status",
    "notes",
]

WORKFLOW_REQUIRED_COLUMNS = [
    "evidence_id",
    "date",
    "pilot_clinic",
    "pilot_users",
    "base_url",
    "frontend_url",
    "git_commit",
    "ci_static_pass",
    "online_smoke_pass",
    "schema_ok",
    "database_revision",
    "alembic_head",
    "dangerous_flags_disabled",
    "ai_consult_ok",
    "dynamic_consult_ok",
    "case_save_ok",
    "case_detail_ok",
    "case_edit_ok",
    "word_export_ok",
    "preventive_reminder_ok",
    "manual_queue_ok",
    "opt_out_ok",
    "open_p0_count",
    "open_p1_count",
    "decision",
    "release_owner",
    "security_owner",
    "clinical_ops_owner",
    "notes",
]

INCIDENT_REQUIRED_COLUMNS = [
    "incident_id",
    "date",
    "severity",
    "area",
    "summary",
    "status",
    "owner",
    "decision",
    "notes",
]

ALLOWED_DECISIONS = {
    "GO_CONTINUE_D1",
    "NO_GO_PAUSE_PILOT",
    "GO_WITH_MONITORING",
    "TBD",
    "",
}

def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)

def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def require_columns(path: Path, required):
    rows = read_csv(path)
    if not rows:
        fail(f"{path} has no data rows")
    missing = [c for c in required if c not in rows[0].keys()]
    if missing:
        fail(f"{path} missing columns: {missing}")
    return rows

def main():
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing required file: {path}")
        if path.stat().st_size == 0:
            fail(f"empty required file: {path}")

    md_path = OPS / "COMMERCIAL_V1_D0_PILOT_START_EVIDENCE_V1.md"
    md = md_path.read_text(encoding="utf-8")
    required_phrases = [
        "Commercial V1 D0 Pilot Start Evidence",
        "0008_auto_delivery",
        "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
        "ENABLE_EMR_REAL_IMPORT=false",
        "GO_CONTINUE_D1",
    ]
    for phrase in required_phrases:
        if phrase not in md:
            fail(f"{md_path} missing phrase: {phrase}")

    checklist = require_columns(
        OPS / "COMMERCIAL_V1_D0_PILOT_START_CHECKLIST.csv",
        CHECKLIST_REQUIRED_COLUMNS,
    )
    workflow = require_columns(
        OPS / "COMMERCIAL_V1_D0_PILOT_WORKFLOW_EVIDENCE_TEMPLATE.csv",
        WORKFLOW_REQUIRED_COLUMNS,
    )
    incidents = require_columns(
        OPS / "COMMERCIAL_V1_D0_PILOT_INCIDENT_SNAPSHOT.csv",
        INCIDENT_REQUIRED_COLUMNS,
    )

    check_ids = {row["check_id"] for row in checklist}
    for required_id in ["D0-001", "D0-004", "D0-012", "D0-024", "D0-026"]:
        if required_id not in check_ids:
            fail(f"checklist missing required check_id: {required_id}")

    for row in workflow:
        decision = row.get("decision", "").strip()
        if decision not in ALLOWED_DECISIONS:
            fail(f"invalid workflow decision: {decision}")

    for row in incidents:
        if row.get("incident_id") == "D0-NO-INCIDENT":
            if row.get("severity") != "none":
                fail("D0-NO-INCIDENT must have severity=none")
            if row.get("decision") != "GO_CONTINUE_D1":
                fail("D0-NO-INCIDENT must have decision=GO_CONTINUE_D1")

    print("PASS: Commercial V1 D0 Pilot Start Evidence files are present and structurally valid")

if __name__ == "__main__":
    main()
