#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "backend" / "imaging_metadata_parser.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_GO_NO_GO_V1.csv"
FIXTURE = ROOT / "docs" / "clinical_data" / "fixtures" / "imaging_metadata_dry_run_fixture_v1.json"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


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
            return fail(f"{label} missing expected content: {needle}")
    return 0


def main() -> int:
    for path in (PARSER, API, DOC, CHECKLIST, GO_NO_GO, FIXTURE, SMOKE, CI_STATIC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        PARSER,
        (
            "IMAGING_METADATA_DRY_RUN_MODE",
            "parse_imaging_metadata_fixture",
            "quality_gate",
            '"creates_imaging_study": False',
            '"queries_pacs": False',
            '"executes_real_dicom_ingest": False',
            '"executes_real_device_ingest": False',
            '"writes_database": False',
        ),
        "backend/imaging_metadata_parser.py",
    )
    if rc:
        return rc

    parser_text = PARSER.read_text(encoding="utf-8")
    for forbidden in ("db.add(", "db.commit(", "SessionLocal", "pydicom.dcmread", "requests.get(", "httpx.get("):
        if forbidden in parser_text:
            return fail(f"imaging parser must not write DB, read DICOM, or download attachments: {forbidden}")

    rc = require_text(
        API,
        (
            "parse_imaging_metadata_fixture",
            "IMAGING_METADATA_DRY_RUN_MODE",
            '@router.get("/dry-run/imaging-metadata/fixtures"',
            '@router.get("/dry-run/imaging-metadata/fixtures/{fixture_id}"',
            '@router.post("/dry-run/imaging-metadata/parse"',
            "_owned_case_or_404(db, int(case_id), user)",
            '"creates_imaging_study": False',
            '"queries_pacs": False',
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if data.get("fixture_id") != "imaging_metadata_dry_run_fixture_v1":
        return fail("fixture_id mismatch")
    study = data.get("imaging_study") or {}
    for key in ("modality", "body_part", "taken_at", "study_uid"):
        if not study.get(key):
            return fail(f"fixture imaging_study missing required key: {key}")
    safety = data.get("safety") or {}
    for key in ("contains_raw_dicom", "downloads_attachments", "queries_pacs", "executes_real_dicom_ingest", "executes_real_device_ingest", "writes_database", "creates_imaging_study"):
        if safety.get(key) is not False:
            return fail(f"fixture safety must be false for {key}")

    sys.path.insert(0, str(ROOT / "backend"))
    try:
        from imaging_metadata_parser import parse_imaging_metadata_fixture
    except Exception as exc:
        return fail(f"failed to import parser: {exc}")

    parsed = parse_imaging_metadata_fixture(data, case_id=123)
    if parsed.get("message") != "imaging_metadata_dry_run_parse":
        return fail("parser message mismatch")
    if parsed.get("quality_gate", {}).get("status") != "PASS":
        return fail("parser quality gate must PASS for synthetic fixture")
    if parsed.get("study_preview", {}).get("case_id") != 123:
        return fail("parser did not preserve case_id preview")
    if parsed.get("study_preview", {}).get("modality") != "XR":
        return fail("parser modality normalization mismatch")
    if parsed.get("writes_database") is not False or parsed.get("creates_imaging_study") is not False:
        return fail("parser must be no-write")

    rc = require_text(
        DOC,
        (
            "Imaging Metadata Dry-run Fixture Parser V1",
            "POST /api/diagnostic-data/dry-run/imaging-metadata/parse",
            "creates_imaging_study=false",
            "executes_real_dicom_ingest=false",
            "GO_TO_CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_V1",
        ),
        "imaging metadata parser doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "imaging metadata dry-run fixture list",
            "imaging metadata dry-run fixture get",
            "imaging metadata dry-run fixture parse",
            "imaging metadata dry-run parser requires auth",
            "user B cannot parse user A imaging metadata fixture",
            "imaging metadata dry-run fixture parser checks",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        ("validate_imaging_metadata_dry_run_fixture_parser.py",),
        "ci static checks",
    )
    if rc:
        return rc

    print("PASS: Imaging Metadata Dry-run Fixture Parser V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
