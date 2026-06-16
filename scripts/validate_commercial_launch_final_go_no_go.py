#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FINAL_DOC = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_GO_NO_GO_V1.md"
CHECKLIST = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_GO_NO_GO_CHECKLIST.csv"
DECISION = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_DECISION_RECORD.csv"
BLOCKERS = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_BLOCKER_REGISTER.csv"
EVIDENCE = ROOT / "docs" / "ops" / "COMMERCIAL_LAUNCH_FINAL_EVIDENCE_TEMPLATE.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

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

def first_row(path: Path, label: str) -> dict[str, str] | None:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as exc:
        print(f"FAIL {label} invalid CSV: {exc}", file=sys.stderr)
        return None
    if not rows:
        print(f"FAIL {label} has no rows", file=sys.stderr)
        return None
    return rows[0]

def truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"true", "yes", "1", "y", "go", "pass", "complete"}

def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        FINAL_DOC,
        (
            "GO_PRODUCTION_COMMERCIAL_LAUNCH",
            "BRD2_REAL_RESTORE_EVIDENCE_PENDING -> CLOSED",
            "BACKUP_RESTORE_DRILL_V2_REAL_RESTORE_EVIDENCE_COMPLETE",
            "LEGAL_CONSENT_PACK_REAL_REVIEW_SIGNOFF_COMPLETE",
            "database_revision == 0008_auto_delivery",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "EMR real import",
        ),
        "final go/no-go doc",
    )
    if rc:
        return rc

    decision = first_row(DECISION, "final decision record")
    if decision is None:
        return 1
    required = {
        "decision": "GO_PRODUCTION_COMMERCIAL_LAUNCH",
        "production_commercial_launch": "GO",
        "primary_blocker": "none",
        "backup_restore_real_evidence": "complete",
        "legal_real_signoff": "complete",
        "ci_static": "PASS",
        "online_smoke": "PASS",
        "schema_ok": "true",
        "database_revision": "0008_auto_delivery",
        "alembic_head": "0008_auto_delivery",
        "dangerous_flags_disabled": "true",
        "no_open_p0": "true",
        "no_secret_leak": "true",
    }
    for key, expected in required.items():
        if str(decision.get(key) or "").strip() != expected:
            return fail(f"final decision record {key} must be {expected}")

    blocker = first_row(BLOCKERS, "final blocker register")
    if blocker is None:
        return 1
    if blocker.get("blocker_id") != "NO_OPEN_FINAL_BLOCKERS" or blocker.get("status") != "closed":
        return fail("final blocker register must show NO_OPEN_FINAL_BLOCKERS closed")

    evidence = first_row(EVIDENCE, "final evidence")
    if evidence is None:
        return 1
    if evidence.get("decision") != "GO_PRODUCTION_COMMERCIAL_LAUNCH":
        return fail("final evidence decision must be GO_PRODUCTION_COMMERCIAL_LAUNCH")
    required_true = (
        "ci_static_pass","online_smoke_pass","healthz_ok","frontend_live","schema_ok",
        "dangerous_flags_disabled","emr_real_import_disabled","emr_case_update_disabled",
        "automated_live_delivery_disabled","feature_scope_lock_complete","ops_runbook_complete",
        "access_review_complete","monitoring_plan_complete","backup_restore_docs_complete",
        "backup_restore_real_evidence_complete","legal_docs_complete","legal_real_signoff_complete",
        "no_open_p0","no_open_p1_launch_blocker","no_secret_leak","no_phi_in_evidence",
    )
    missing = [name for name in required_true if not truthy(evidence.get(name))]
    if missing:
        return fail("final evidence requires true fields: " + ", ".join(missing))
    if evidence.get("database_revision") != "0008_auto_delivery" or evidence.get("alembic_head") != "0008_auto_delivery":
        return fail("final evidence database_revision and alembic_head must be 0008_auto_delivery")

    checklist_text = CHECKLIST.read_text(encoding="utf-8")
    for needle in ("FINAL-019", "Backup Restore Drill V2 real restore evidence", "GO_PRODUCTION_COMMERCIAL_LAUNCH"):
        if needle not in checklist_text:
            return fail(f"final checklist missing expected content: {needle}")

    rc = require_text(SMOKE, ("validate_commercial_launch_final_go_no_go.py", "commercial launch final go no-go validation"), "smoke script")
    if rc:
        return rc
    rc = require_text(CI_STATIC, ("validate_commercial_launch_final_go_no_go.py",), "ci static script")
    if rc:
        return rc

    print("OK commercial launch final go/no-go: production commercial launch decision is GO and all final evidence gates are recorded")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
