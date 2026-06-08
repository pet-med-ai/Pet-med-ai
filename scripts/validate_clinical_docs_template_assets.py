#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_DIR = ROOT / "templates" / "clinical_docs"
ADMISSION_DOCX = TEMPLATE_DIR / "admission_hospitalization_record_bilingual.docx"
DISCHARGE_DOCX = TEMPLATE_DIR / "discharge_summary_bilingual.docx"
MANIFEST = TEMPLATE_DIR / "CLINICAL_DOCS_TEMPLATE_ASSETS_MANIFEST.json"
SAMPLE_CONTEXT = TEMPLATE_DIR / "clinical_doc_sample_context.json"
DOC = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_TEMPLATE_ASSETS_V1.md"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"

EXPECTED_DOCX = {
    ADMISSION_DOCX: {
        "label": "admission template",
        "required_text": (
            "入院",
            "Hospitalization",
            "{{case_id}}",
            "{{pet.name}}",
            "{{species}}",
            "{{admission_reason}}",
            "{{provisional_dx}}",
            "{{treatment_plan}}",
            "{{meds}}",
            "{{clinician_id}}",
            "{{timestamp}}",
            "{{hash}}",
        ),
    },
    DISCHARGE_DOCX: {
        "label": "discharge template",
        "required_text": (
            "出院",
            "Discharge",
            "{{case_id}}",
            "{{pet.name}}",
            "{{species}}",
            "{{hospital_course}}",
            "{{final_dx}}",
            "{{discharge_instructions}}",
            "{{home_meds}}",
            "{{follow_up_plan}}",
            "{{clinician_id}}",
            "{{timestamp}}",
            "{{hash}}",
        ),
    },
}


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def require_file(path: Path) -> int:
    if not path.exists():
        return fail(f"missing file: {path.relative_to(ROOT)}")
    if path.stat().st_size <= 0:
        return fail(f"empty file: {path.relative_to(ROOT)}")
    return 0


def require_text_file(path: Path, needles: tuple[str, ...], label: str) -> int:
    rc = require_file(path)
    if rc:
        return rc
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected content: {needle}")
    return 0


def docx_text(path: Path) -> str:
    """Extract visible text from a DOCX using only the Python standard library."""
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        if "word/document.xml" not in names:
            raise ValueError("word/document.xml missing")
        chunks: list[str] = []
        for name in sorted(n for n in names if n.startswith("word/") and n.endswith(".xml")):
            try:
                root = ET.fromstring(zf.read(name))
            except ET.ParseError:
                continue
            for node in root.iter():
                if node.tag.endswith("}t") and node.text:
                    chunks.append(node.text)
    return "".join(chunks)


def normalize_docx_text(value: str) -> str:
    # Word can split braces and keys across runs. Remove whitespace between
    # placeholder tokens so validator is stable across Word/LibreOffice saves.
    compact = re.sub(r"\s+", "", value)
    compact = compact.replace("｛", "{").replace("｝", "}")
    return compact


def validate_docx(path: Path, *, label: str, required_text: tuple[str, ...]) -> int:
    rc = require_file(path)
    if rc:
        return rc
    try:
        visible_text = docx_text(path)
    except Exception as exc:
        return fail(f"{label} is not a valid DOCX: {exc}")

    compact = normalize_docx_text(visible_text)
    visible_for_labels = visible_text.lower()

    for needle in required_text:
        if needle.startswith("{{"):
            if needle not in compact:
                return fail(f"{label} missing placeholder: {needle}")
        else:
            if needle.lower() not in visible_for_labels and needle not in visible_text:
                return fail(f"{label} missing visible label/text: {needle}")

    return 0


def validate_manifest() -> int:
    rc = require_file(MANIFEST)
    if rc:
        return rc
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"manifest JSON invalid: {exc}")

    text = json.dumps(data, ensure_ascii=False)
    for needle in (
        "clinical-docs-template-assets-v1",
        "admission_hospitalization_record_bilingual.docx",
        "discharge_summary_bilingual.docx",
        "contains_real_stamp",
        "writes_database",
        "creates_case",
        "updates_case",
        "downloads_attachments",
        "executes_real_import",
    ):
        if needle not in text:
            return fail(f"manifest missing expected content: {needle}")

    safety_text = text.lower()
    for marker in (
        '"contains_real_stamp": false',
        '"writes_database": false',
        '"creates_case": false',
        '"updates_case": false',
        '"downloads_attachments": false',
        '"executes_real_import": false',
    ):
        if marker not in safety_text:
            return fail(f"manifest safety marker missing or not false: {marker}")

    return 0


def validate_sample_context() -> int:
    rc = require_file(SAMPLE_CONTEXT)
    if rc:
        return rc
    try:
        data = json.loads(SAMPLE_CONTEXT.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"sample context JSON invalid: {exc}")

    text = json.dumps(data, ensure_ascii=False)
    for needle in (
        "case_id",
        "pet",
        "owner",
        "clinician",
        "generator",
        "clinician_id",
        "timestamp",
        "hash",
    ):
        if needle not in text:
            return fail(f"sample context missing expected key: {needle}")

    return 0


def main() -> int:
    for path, meta in EXPECTED_DOCX.items():
        rc = validate_docx(path, label=meta["label"], required_text=meta["required_text"])
        if rc:
            return rc

    rc = validate_manifest()
    if rc:
        return rc

    rc = validate_sample_context()
    if rc:
        return rc

    rc = require_text_file(
        DOC,
        (
            "Clinical Docs Template Assets V1",
            "admission_hospitalization_record_bilingual.docx",
            "discharge_summary_bilingual.docx",
            "contains_real_stamp=false",
            "writes_database=false",
            "creates_case=false",
        ),
        "clinical docs template assets doc",
    )
    if rc:
        return rc

    rc = require_text_file(
        SMOKE,
        (
            "validate_clinical_docs_template_assets.py",
            "clinical docs template assets validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text_file(
        CI_STATIC,
        (
            "validate_clinical_docs_template_assets.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("OK clinical docs template assets: DOCX templates, manifest and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
