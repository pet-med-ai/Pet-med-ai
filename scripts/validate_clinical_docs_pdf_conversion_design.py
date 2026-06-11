#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DESIGN = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_PDF_CONVERSION_DESIGN_V1.md"
MATRIX = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_PDF_CONVERSION_ENGINE_MATRIX.csv"
RENDER = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_PDF_CONVERSION_RENDER_RUNBOOK.md"
TESTS = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_PDF_CONVERSION_TEST_MATRIX.csv"
TRIAGE = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_PDF_CONVERSION_TRIAGE.csv"
ADDENDUM = ROOT / "docs" / "ops" / "CLINICAL_DOCS_PDF_CONVERSION_DESIGN_RELEASE_ADDENDUM.md"
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
            DESIGN,
            (
                "Clinical Docs PDF Conversion Design V1",
                "DOCX render -> LibreOffice headless -> PDF",
                "writes_database=false",
                "creates_case=false",
                "updates_case=false",
                "downloads_attachments=false",
                "executes_real_import=false",
                "Content-Type: application/pdf",
                "clinical_doc_pdf_conversion_failed",
            ),
            "PDF conversion design",
        ),
        (
            MATRIX,
            (
                "engine,where,output_quality",
                "LibreOffice headless",
                "LibreOffice worker",
                "Browser print to PDF",
            ),
            "PDF engine matrix",
        ),
        (
            RENDER,
            (
                "Clinical Docs PDF Conversion Render / LibreOffice Runbook V1",
                "soffice --headless --convert-to pdf",
                "Noto Sans CJK",
                "no shell=True",
                "timeout=30",
            ),
            "Render LibreOffice runbook",
        ),
        (
            TESTS,
            (
                "test_id,category,input",
                "PDF-001",
                "no unreplaced {{placeholder}}",
                "X-PMAI-Writes-Database=false",
            ),
            "PDF test matrix",
        ),
        (
            TRIAGE,
            (
                "issue_id,severity,area",
                "PDF-NO-SOFFICE",
                "PDF-CJK-MISSING",
                "PDF-SECRET",
            ),
            "PDF triage matrix",
        ),
        (
            ADDENDUM,
            (
                "Release record addendum",
                "Clinical Docs PDF Conversion Design",
                "writes_database=false",
                "LibreOffice availability checked",
            ),
            "release addendum",
        ),
        (
            SMOKE,
            (
                "validate_clinical_docs_pdf_conversion_design.py",
                "clinical docs PDF conversion design validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_clinical_docs_pdf_conversion_design.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK clinical docs PDF conversion design: design docs, matrices and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
