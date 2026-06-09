#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
DOC = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_SMOKE_COVERAGE_V1.md"


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
            DOC,
            (
                "Clinical Docs Export Smoke Coverage V1",
                "POST /api/clinical-docs/render-preview",
                "POST /api/clinical-docs/render",
                "valid DOCX",
                "writes_database=false",
                "creates_case=false",
            ),
            "clinical docs smoke coverage doc",
        ),
        (
            SMOKE,
            (
                "Clinical Docs Export Smoke Coverage V1",
                "/api/clinical-docs/templates",
                "/api/clinical-docs/render-preview",
                "/api/clinical-docs/render",
                "clinical docs admission DOCX render",
                "clinical docs discharge DOCX render",
                "validate_docx_smoke_output",
                "word/document.xml",
                "unreplaced placeholders",
                "X-PMAI-Document-Hash",
                "writes_database",
                "creates_case",
            ),
            "scripts/smoke_petmed.sh",
        ),
        (
            CI_STATIC,
            (
                "validate_clinical_docs_export_smoke.py",
            ),
            "scripts/ci_static_checks.sh",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    print("OK clinical docs export smoke coverage: runtime DOCX render checks are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
