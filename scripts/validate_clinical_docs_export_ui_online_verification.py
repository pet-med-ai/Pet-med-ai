#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNBOOK = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_UI_ONLINE_VERIFICATION_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_UI_ONLINE_VERIFICATION_CHECKLIST.csv"
EVIDENCE = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_UI_ONLINE_VERIFICATION_EVIDENCE.csv"
TRIAGE = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_UI_ONLINE_VERIFICATION_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "CLINICAL_DOCS_EXPORT_UI_ONLINE_VERIFICATION_RELEASE_ADDENDUM.md"
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
            RUNBOOK,
            (
                "Clinical Docs Export UI Online Verification V1",
                "https://pet-med-ai-frontend-static.onrender.com",
                "https://pet-med-ai-backend.onrender.com",
                "导出入院/住院记录 DOCX",
                "导出出院小结 DOCX",
                "POST /api/clinical-docs/render",
                "X-PMAI-Document-Hash",
                "writes_database=false",
                "creates_case=false",
            ),
            "online verification runbook",
        ),
        (
            CHECKLIST,
            (
                "phase,item,owner",
                "Admission DOCX download",
                "Discharge DOCX download",
                "Check render API status",
                "Check read-only headers",
            ),
            "online verification checklist",
        ),
        (
            EVIDENCE,
            (
                "verification_id,date,operator_id",
                "admission_downloaded",
                "discharge_downloaded",
                "document_hash_present",
                "writes_database_false",
                "creates_case_false",
            ),
            "online verification evidence",
        ),
        (
            TRIAGE,
            (
                "issue_id,date,severity",
                "CDOC-401",
                "CDOC-DOCX-CORRUPT",
                "CDOC-PLACEHOLDER",
                "CDOC-SECRET",
            ),
            "online verification triage",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Clinical Docs Export UI Online Verification",
                "Admission DOCX downloaded",
                "X-PMAI-Writes-Database=false",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_clinical_docs_export_ui_online_verification.py",
                "clinical docs export UI online verification validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_clinical_docs_export_ui_online_verification.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK clinical docs export UI online verification: runbook, checklist and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
