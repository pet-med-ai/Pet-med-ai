#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "clinical_docs_api.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_API_V1.md"
TEMPLATE_DIR = ROOT / "templates" / "clinical_docs"
ADMISSION = TEMPLATE_DIR / "admission_hospitalization_record_bilingual.docx"
DISCHARGE = TEMPLATE_DIR / "discharge_summary_bilingual.docx"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
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
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (API, MAIN, DOC, ADMISSION, DISCHARGE):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        API,
        (
            'router = APIRouter(prefix="/api/clinical-docs"',
            '@router.get("/templates"',
            '@router.post("/render-preview"',
            '@router.post("/render"',
            "ClinicalDocRenderIn",
            "StreamingResponse",
            "DOCX_MEDIA_TYPE",
            "_render_docx",
            "_replace_placeholders_in_xml",
            "_case_or_404",
            "owner_id",
            "document_hash",
            "Content-Disposition",
            "X-PMAI-Writes-Database",
            '"writes_database": False',
            '"creates_case": False',
            '"updates_case": False',
            '"downloads_attachments": False',
            '"executes_real_import": False',
            "admission_hospitalization_record_bilingual",
            "discharge_summary_bilingual",
        ),
        "backend/clinical_docs_api.py",
    )
    if rc:
        return rc

    api_text = API.read_text(encoding="utf-8")
    forbidden = (
        "db.add(",
        "db.commit(",
        "AuditLog(",
        "Case(",
        "requests.get(",
        "urllib",
        "download(",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    for needle in forbidden:
        if needle in api_text:
            return fail(f"Clinical Docs Export API V1 must stay read-only; forbidden marker found: {needle}")

    rc = require_text(
        MAIN,
        (
            "clinical_docs_api_router",
            "app.include_router(clinical_docs_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Clinical Docs Export API V1",
            "GET /api/clinical-docs/templates",
            "POST /api/clinical-docs/render-preview",
            "POST /api/clinical-docs/render",
            "writes_database=false",
            "creates_case=false",
        ),
        "clinical docs export API doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_clinical_docs_export_api.py",
            "clinical docs export API validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_clinical_docs_export_api.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK clinical docs export API: DOCX render endpoints and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
