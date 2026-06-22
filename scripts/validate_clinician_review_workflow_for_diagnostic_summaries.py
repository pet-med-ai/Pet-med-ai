#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / "backend" / "clinician_review_workflow.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "CLINICIAN_REVIEW_WORKFLOW_FOR_DIAGNOSTIC_SUMMARIES_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "CLINICIAN_REVIEW_WORKFLOW_FOR_DIAGNOSTIC_SUMMARIES_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "CLINICIAN_REVIEW_WORKFLOW_FOR_DIAGNOSTIC_SUMMARIES_GO_NO_GO_V1.csv"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
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
            return fail(f"{label} missing expected marker: {needle}")
    return 0


def forbid_text(path: Path, needles: tuple[str, ...], label: str) -> int:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle in text:
            return fail(f"{label} contains forbidden marker: {needle}")
    return 0


def main() -> int:
    for path in (MODULE, API, DOC, CHECKLIST, GO_NO_GO, CI, SMOKE):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODULE,
        (
            "CLINICIAN_REVIEW_WORKFLOW_MODE",
            "clinician_review_workflow_for_diagnostic_summaries_v1",
            "def clinician_review_workflow_safety_flags",
            '"writes_database": False',
            '"writes_ai_summary": False',
            '"creates_audit_log": False',
            '"writes_audit_log": False',
            '"signs_report": False',
            '"persists_review_status": False',
            '"releases_to_client": False',
            '"writes_prescription": False',
            '"drug_dose_recommendation": False',
            '"requires_human_review": True',
            '"clinician_signoff_required": True',
            "blocked_actions",
            "allowed_actions",
            "build_clinician_review_workflow",
        ),
        "backend/clinician_review_workflow.py",
    )
    if rc:
        return rc

    rc = forbid_text(
        MODULE,
        (
            "db.commit(",
            "db.add(",
            "requests.post(",
            "httpx.post(",
            '"writes_database": True',
            '"writes_ai_summary": True',
            '"creates_audit_log": True',
            '"signs_report": True',
            '"releases_to_client": True',
            '"writes_prescription": True',
            '"drug_dose_recommendation": True',
            '"calls_external_ai": True',
        ),
        "backend/clinician_review_workflow.py",
    )
    if rc:
        return rc

    rc = require_text(
        API,
        (
            "/dry-run/clinician-review/diagnostic-summaries/check",
            "clinician_review_workflow_checked",
            "build_clinician_review_workflow",
            "clinician_review_workflow_safety_flags",
            "_owned_case_or_404",
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Clinician Review Workflow for Diagnostic Summaries V1",
            "POST /api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check",
            "writes_database=false",
            "writes_ai_summary=false",
            "creates_audit_log=false",
            "signs_report=false",
            "releases_to_client=false",
            "requires_human_review=true",
            "clinician_signoff_required=true",
        ),
        "clinical data doc",
    )
    if rc:
        return rc

    rc = require_text(
        CI,
        (
            "validate_clinician_review_workflow_for_diagnostic_summaries.py",
        ),
        "ci static checks",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "Clinician review diagnostic summaries dry-run",
            "Clinician review workflow requires auth",
            "user B cannot check user A clinician review workflow",
            "Clinician review diagnostic summaries checks",
            "/api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check",
        ),
        "smoke script",
    )
    if rc:
        return rc

    print("PASS: Clinician Review Workflow for Diagnostic Summaries V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
