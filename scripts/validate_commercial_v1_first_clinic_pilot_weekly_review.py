#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPS = ROOT / "docs" / "ops"

MASTER = OPS / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_WEEKLY_REVIEW_V1.md"
CHECKLIST = OPS / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_WEEKLY_REVIEW_CHECKLIST.csv"
SUMMARY = OPS / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_WEEKLY_REVIEW_SUMMARY.csv"
INCIDENTS = OPS / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_WEEKLY_REVIEW_INCIDENT_SUMMARY.csv"
DECISION = OPS / "COMMERCIAL_V1_FIRST_CLINIC_PILOT_WEEKLY_REVIEW_DECISION.csv"

REQUIRED_FILES = [MASTER, CHECKLIST, SUMMARY, INCIDENTS, DECISION]

CHECKLIST_COLUMNS = [
    "check_id", "area", "item", "required_state", "actual_state",
    "evidence", "owner", "go_no_go", "status", "notes",
]

SUMMARY_COLUMNS = [
    "review_id", "date", "pilot_clinic", "pilot_window", "d0_completed",
    "d1_completed", "d2_completed", "d3_completed", "d4_completed",
    "d5_completed", "d6_completed", "d7_completed", "d7_decision",
    "ci_static_pass", "online_smoke_final_pass", "schema_ok_final",
    "database_revision_final", "alembic_head_final",
    "dangerous_flags_disabled_final", "ai_consult_stable",
    "dynamic_consult_stable", "case_workflow_stable", "word_export_stable",
    "preventive_reminder_stable", "manual_queue_stable", "opt_out_stable",
    "total_open_p0_count", "total_open_p1_count",
    "automatic_outbound_occurred", "emr_real_write_occurred",
    "cross_user_access_incident", "phi_or_secret_in_repo_evidence",
    "weekly_decision", "next_stage", "release_owner", "security_owner",
    "clinical_ops_owner", "notes",
]

INCIDENT_COLUMNS = [
    "review_id", "date", "total_p0", "total_p1", "total_p2", "total_p3",
    "open_p0_count", "open_p1_count", "automatic_outbound_incident_count",
    "emr_real_write_incident_count", "cross_user_access_incident_count",
    "phi_or_secret_repo_incident_count", "decision", "owner", "notes",
]

DECISION_COLUMNS = [
    "decision_id", "date", "review_stage", "pilot_clinic", "decision",
    "next_stage", "release_owner", "security_owner", "clinical_ops_owner",
    "signoff_status", "notes",
]

EXPECTED_DECISION = "GO_CLOSE_D0_D7_OBSERVATION_WINDOW"
EXPECTED_NEXT = "CLINICAL_CORE_ROADMAP_REFRESH_V1"

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

def truthy(value: str) -> bool:
    return str(value).strip().lower() == "true"

def falsey(value: str) -> bool:
    return str(value).strip().lower() == "false"

def zero(value: str) -> bool:
    return str(value).strip() in {"0", "0.0"}

def main() -> int:
    for path in REQUIRED_FILES:
        if not path.exists():
            fail(f"missing required file: {path.relative_to(ROOT)}")
        if path.stat().st_size <= 0:
            fail(f"empty required file: {path.relative_to(ROOT)}")

    md = MASTER.read_text(encoding="utf-8")
    for phrase in (
        "Commercial V1 First Clinic Pilot Weekly Review V1",
        "GO_CLOSE_D0_D7_OBSERVATION_WINDOW",
        "CLINICAL_CORE_ROADMAP_REFRESH_V1",
        "DiagnosticReport / Observation / ImagingStudy",
        "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
        "ENABLE_EMR_REAL_IMPORT=false",
        "AI abnormal summary",
        "drug dose safety",
    ):
        if phrase not in md:
            fail(f"master weekly review doc missing phrase: {phrase}")

    checklist = require_columns(CHECKLIST, CHECKLIST_COLUMNS)
    summary = require_columns(SUMMARY, SUMMARY_COLUMNS)
    incidents = require_columns(INCIDENTS, INCIDENT_COLUMNS)
    decisions = require_columns(DECISION, DECISION_COLUMNS)

    required_check_ids = {f"WR-{i:03d}" for i in range(1, 21)}
    found_check_ids = {str(row.get("check_id", "")).strip() for row in checklist}
    missing_checks = sorted(required_check_ids - found_check_ids)
    if missing_checks:
        fail(f"weekly review checklist missing checks: {missing_checks}")

    for row in checklist:
        if str(row.get("go_no_go", "")).strip() == "GO_REQUIRED":
            if str(row.get("status", "")).strip().upper() != "PASS":
                fail(f"required checklist row not PASS: {row.get('check_id')}")

    row = summary[0]
    for key in (
        "d0_completed", "d1_completed", "d2_completed", "d3_completed",
        "d4_completed", "d5_completed", "d6_completed", "d7_completed",
        "ci_static_pass", "online_smoke_final_pass", "schema_ok_final",
        "dangerous_flags_disabled_final", "ai_consult_stable",
        "dynamic_consult_stable", "case_workflow_stable", "word_export_stable",
        "preventive_reminder_stable", "manual_queue_stable", "opt_out_stable",
    ):
        if not truthy(row.get(key, "")):
            fail(f"summary expected true: {key}")

    for key in (
        "automatic_outbound_occurred", "emr_real_write_occurred",
        "cross_user_access_incident", "phi_or_secret_in_repo_evidence",
    ):
        if not falsey(row.get(key, "")):
            fail(f"summary expected false: {key}")

    if row.get("d7_decision") != "GO_COMPLETE_D7":
        fail("summary d7_decision must be GO_COMPLETE_D7")
    if row.get("weekly_decision") != EXPECTED_DECISION:
        fail(f"summary weekly_decision must be {EXPECTED_DECISION}")
    if row.get("next_stage") != EXPECTED_NEXT:
        fail(f"summary next_stage must be {EXPECTED_NEXT}")
    if row.get("database_revision_final") != "0008_auto_delivery":
        fail("summary database_revision_final must be 0008_auto_delivery")
    if row.get("alembic_head_final") != "0008_auto_delivery":
        fail("summary alembic_head_final must be 0008_auto_delivery")
    if not zero(row.get("total_open_p0_count", "")):
        fail("summary total_open_p0_count must be 0")
    if not zero(row.get("total_open_p1_count", "")):
        fail("summary total_open_p1_count must be 0")

    incident = incidents[0]
    for key in (
        "total_p0", "total_p1", "open_p0_count", "open_p1_count",
        "automatic_outbound_incident_count", "emr_real_write_incident_count",
        "cross_user_access_incident_count", "phi_or_secret_repo_incident_count",
    ):
        if not zero(incident.get(key, "")):
            fail(f"incident summary expected 0: {key}")
    if incident.get("decision") != EXPECTED_DECISION:
        fail(f"incident decision must be {EXPECTED_DECISION}")

    decision = decisions[0]
    if decision.get("decision") != EXPECTED_DECISION:
        fail(f"decision row must be {EXPECTED_DECISION}")
    if decision.get("next_stage") != EXPECTED_NEXT:
        fail(f"decision next_stage must be {EXPECTED_NEXT}")
    if decision.get("signoff_status") != "signed":
        fail("decision signoff_status must be signed")

    print("PASS: Commercial V1 First Clinic Pilot Weekly Review V1 files are present and structurally valid")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
