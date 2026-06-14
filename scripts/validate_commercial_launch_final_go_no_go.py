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

PREVIOUS_VALIDATORS = (
    "validate_commercial_launch_readiness.py",
    "validate_commercial_launch_feature_scope_lock.py",
    "validate_commercial_launch_ops_runbook.py",
    "validate_commercial_launch_access_review.py",
    "validate_commercial_launch_monitoring_alerting_plan.py",
    "validate_commercial_launch_backup_restore_drill_v2.py",
    "validate_commercial_launch_legal_consent_pack.py",
)


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


def require_csv(path: Path, required_columns: tuple[str, ...], needles: tuple[str, ...], label: str, min_rows: int = 1) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")

    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")

    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return fail(f"{label} has no header")
            missing = [col for col in required_columns if col not in reader.fieldnames]
            if missing:
                return fail(f"{label} missing columns: {', '.join(missing)}")
            rows = list(reader)
    except Exception as exc:
        return fail(f"{label} is not valid CSV: {exc}")

    if len(rows) < min_rows:
        return fail(f"{label} should contain at least {min_rows} rows")
    return 0


def validate_decision_record() -> int:
    try:
        with DECISION.open("r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    except Exception as exc:
        return fail(f"final decision record invalid CSV: {exc}")
    if not rows:
        return fail("final decision record has no rows")
    row = rows[0]
    if row.get("decision") != "NO-GO_PRODUCTION_COMMERCIAL_LAUNCH":
        return fail("current final decision must remain NO-GO_PRODUCTION_COMMERCIAL_LAUNCH while restore evidence is pending")
    if row.get("continued_prelaunch_preparation") != "GO":
        return fail("continued pre-launch preparation should be GO")
    if row.get("primary_blocker") != "BRD2_REAL_RESTORE_EVIDENCE_PENDING":
        return fail("primary blocker must be BRD2_REAL_RESTORE_EVIDENCE_PENDING")
    if row.get("legal_real_signoff") != "complete":
        return fail("legal_real_signoff must be recorded complete for this stage")
    if row.get("backup_restore_real_evidence") != "pending":
        return fail("backup_restore_real_evidence must remain pending until real restore evidence exists")
    return 0


def main() -> int:
    py_compile.compile(str(Path(__file__)), doraise=True)

    rc = require_text(
        FINAL_DOC,
        (
            "Commercial Launch Final Go / No-Go V1",
            "NO-GO_PRODUCTION_COMMERCIAL_LAUNCH",
            "GO_CONTINUED_INTERNAL_PRE_LAUNCH_PREPARATION",
            "BRD2_REAL_RESTORE_EVIDENCE_PENDING",
            "LEGAL_CONSENT_PACK_REAL_REVIEW_SIGNOFF_COMPLETE",
            "BACKUP_RESTORE_DRILL_V2_REAL_RESTORE_EVIDENCE_PENDING",
            "database_revision == alembic_head",
            "database_revision == 0008_auto_delivery",
            "all_dangerous_features_disabled=true",
            "ENABLE_PREVENTIVE_AUTO_DELIVERY=false",
            "ENABLE_EMR_REAL_IMPORT=false",
            "Legal / Consent Pack V1 real review + signoff complete",
            "Backup / Restore Drill V2 real restore evidence missing",
        ),
        "final go/no-go doc",
    )
    if rc:
        return rc

    rc = require_csv(
        CHECKLIST,
        (
            "gate_id",
            "area",
            "item",
            "required_state",
            "current_state",
            "go_no_go",
            "owner",
            "status",
            "notes",
        ),
        (
            "FINAL-001",
            "FINAL-019",
            "Backup Restore Drill V2 real restore evidence",
            "FINAL-021",
            "Legal Consent Pack V1 real review + signoff",
            "NO-GO_PRODUCTION_COMMERCIAL_LAUNCH",
        ),
        "final go/no-go checklist",
        min_rows=20,
    )
    if rc:
        return rc

    rc = require_csv(
        DECISION,
        (
            "decision_id",
            "date",
            "decision",
            "production_commercial_launch",
            "continued_prelaunch_preparation",
            "primary_blocker",
            "legal_docs_validation",
            "legal_real_signoff",
            "backup_restore_docs_validation",
            "backup_restore_real_evidence",
            "ci_static",
            "online_smoke",
            "schema_ok",
            "database_revision",
            "alembic_head",
            "dangerous_flags_disabled",
            "no_open_p0",
            "no_secret_leak",
            "release_owner",
            "security_owner",
            "clinical_ops_owner",
            "notes",
        ),
        (
            "FINAL-GNG-V1",
            "NO-GO_PRODUCTION_COMMERCIAL_LAUNCH",
            "BRD2_REAL_RESTORE_EVIDENCE_PENDING",
            "legal_real_signoff",
            "complete",
            "pending",
        ),
        "final decision record",
        min_rows=1,
    )
    if rc:
        return rc

    rc = validate_decision_record()
    if rc:
        return rc

    rc = require_csv(
        BLOCKERS,
        (
            "blocker_id",
            "severity",
            "area",
            "blocker",
            "current_status",
            "required_to_close",
            "owner",
            "go_no_go",
            "status",
            "notes",
        ),
        (
            "BRD2_REAL_RESTORE_EVIDENCE_PENDING",
            "Backup / Restore Drill V2 real restore evidence missing",
            "NO-GO",
            "open",
        ),
        "final blocker register",
        min_rows=1,
    )
    if rc:
        return rc

    rc = require_csv(
        EVIDENCE,
        (
            "evidence_id",
            "date",
            "base_url",
            "frontend_url",
            "git_commit",
            "ci_static_pass",
            "online_smoke_pass",
            "healthz_ok",
            "frontend_live",
            "schema_ok",
            "database_revision",
            "alembic_head",
            "dangerous_flags_disabled",
            "emr_real_import_disabled",
            "emr_case_update_disabled",
            "automated_live_delivery_disabled",
            "feature_scope_lock_complete",
            "ops_runbook_complete",
            "access_review_complete",
            "monitoring_plan_complete",
            "backup_restore_docs_complete",
            "backup_restore_real_evidence_complete",
            "legal_docs_complete",
            "legal_real_signoff_complete",
            "no_open_p0",
            "no_open_p1_launch_blocker",
            "no_secret_leak",
            "no_phi_in_evidence",
            "release_owner_signoff",
            "security_owner_signoff",
            "clinical_ops_owner_signoff",
            "decision",
            "notes",
        ),
        (
            "FINAL-EVIDENCE-V1",
            "backup_restore_real_evidence_complete",
            "legal_real_signoff_complete",
            "NO-GO_PRODUCTION_COMMERCIAL_LAUNCH",
        ),
        "final evidence template",
        min_rows=1,
    )
    if rc:
        return rc

    for script in PREVIOUS_VALIDATORS:
        if not (ROOT / "scripts" / script).exists():
            return fail(f"missing previous launch validator: scripts/{script}")

    rc = require_text(
        SMOKE,
        (
            "validate_commercial_launch_final_go_no_go.py",
            "commercial launch final go no-go validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_commercial_launch_final_go_no_go.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK commercial launch final go/no-go: decision package is present and current production launch decision remains NO-GO due to pending restore evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
