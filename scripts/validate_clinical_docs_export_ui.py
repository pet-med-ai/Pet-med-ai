#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASE_DETAIL = ROOT / "frontend" / "src" / "pages" / "CaseDetail.jsx"
DOC = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_UI_V1.md"
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
            CASE_DETAIL,
            (
                "Clinical Docs Export UI V1",
                "exportClinicalDoc",
                "/api/clinical-docs/render",
                'responseType: "blob"',
                "Content-Disposition",
                "X-PMAI-Document-Hash",
                "admission_hospitalization_record_bilingual",
                "discharge_summary_bilingual",
                "导出入院/住院记录 DOCX",
                "导出出院小结 DOCX",
                "clinical-doc-export-status",
            ),
            "frontend/src/pages/CaseDetail.jsx",
        ),
        (
            DOC,
            (
                "Clinical Docs Export UI V1",
                "POST /api/clinical-docs/render",
                "导出入院/住院记录 DOCX",
                "导出出院小结 DOCX",
                "writes_database=false",
                "creates_case=false",
                "responseType=blob",
            ),
            "clinical docs export UI doc",
        ),
        (
            SMOKE,
            (
                "validate_clinical_docs_export_ui.py",
                "clinical docs export UI validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_clinical_docs_export_ui.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK clinical docs export UI: Case detail DOCX export buttons and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
