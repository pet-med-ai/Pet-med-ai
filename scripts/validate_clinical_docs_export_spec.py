#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SPEC = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_WORD_TEMPLATE_SPEC_V1.md"
MAPPING = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_FIELD_MAPPING.csv"
KEYS = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_TEMPLATE_KEYS_V1.json"
RUNBOOK = ROOT / "docs" / "clinical_docs" / "CLINICAL_DOCS_EXPORT_RUNBOOK_V1.md"
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


def validate_mapping() -> int:
    if not MAPPING.exists():
        return fail(f"missing file: {MAPPING.relative_to(ROOT)}")
    rows = list(csv.DictReader(MAPPING.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return fail("clinical docs field mapping is empty")

    required_placeholders = {
        "case_id",
        "pet.name",
        "species",
        "clinician.name",
        "generator",
        "clinician_id",
        "timestamp",
        "hash",
    }
    actual = {row.get("placeholder", "") for row in rows}
    missing = sorted(required_placeholders - actual)
    if missing:
        return fail("clinical docs field mapping missing placeholders: " + ", ".join(missing))

    templates = {row.get("template", "") for row in rows}
    if not {"admission", "discharge"}.issubset(templates):
        return fail(f"field mapping must include admission and discharge templates; actual={sorted(templates)}")

    return 0


def validate_keys_json() -> int:
    if not KEYS.exists():
        return fail(f"missing file: {KEYS.relative_to(ROOT)}")
    try:
        data = json.loads(KEYS.read_text(encoding="utf-8"))
    except Exception as exc:
        return fail(f"invalid template keys JSON: {exc}")

    if data.get("version") != "clinical-docs-export-word-template-spec-v1":
        return fail("template keys JSON has unexpected version")

    templates = data.get("templates") or {}
    for name in ("admission_hospitalization_record_bilingual", "discharge_summary_bilingual"):
        if name not in templates:
            return fail(f"template keys JSON missing template: {name}")
        required = set((templates.get(name) or {}).get("required_keys") or [])
        for key in ("case_id", "pet.name", "species", "clinician.name", "generator", "clinician_id", "timestamp", "hash"):
            if key not in required:
                return fail(f"template {name} missing required key: {key}")

    safety = data.get("safety") or {}
    for key in ("writes_database", "creates_case", "updates_case", "downloads_attachments", "executes_real_import"):
        if safety.get(key) is not False:
            return fail(f"template keys safety marker must be false: {key}")

    return 0


def main() -> int:
    checks = [
        (
            SPEC,
            (
                "Clinical Docs Export / Word Template Spec V1",
                "Admission / Hospitalization Record",
                "Discharge Summary",
                "120 x 120 px",
                "{{case_id}}",
                "{{clinician_id}}",
                "{{hash}}",
                "writes_database=false",
            ),
            "clinical docs spec",
        ),
        (
            RUNBOOK,
            (
                "Clinical Docs Export Runbook V1",
                "docxtpl",
                "document_hash",
                "writes_database",
                "Do not embed real clinic seal",
            ),
            "clinical docs runbook",
        ),
        (
            SMOKE,
            (
                "validate_clinical_docs_export_spec.py",
                "clinical docs export spec validation",
            ),
            "smoke script",
        ),
        (
            CI_STATIC,
            (
                "validate_clinical_docs_export_spec.py",
            ),
            "ci static script",
        ),
    ]

    for path, needles, label in checks:
        rc = require(path, needles, label)
        if rc:
            return rc

    rc = validate_mapping()
    if rc:
        return rc

    rc = validate_keys_json()
    if rc:
        return rc

    print("OK clinical docs export spec: Word template spec, mappings and validation are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
