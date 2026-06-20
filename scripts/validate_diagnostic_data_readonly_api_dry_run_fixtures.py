#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

API = ROOT / "backend" / "diagnostic_data_api.py"
MAIN = ROOT / "backend" / "main.py"
DOC = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_FIXTURES_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_FIXTURES_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "DIAGNOSTIC_DATA_READONLY_API_DRY_RUN_FIXTURES_GO_NO_GO_V1.csv"
FIXTURE = ROOT / "docs" / "clinical_data" / "fixtures" / "diagnostic_data_dry_run_fixture_v1.json"
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
    for path in (API, MAIN, DOC, CHECKLIST, GO_NO_GO, FIXTURE, SMOKE, CI_STATIC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        API,
        (
            'router = APIRouter(prefix="/api/diagnostic-data"',
            '@router.get("/cases/{case_id}/summary"',
            '@router.get("/cases/{case_id}/reports"',
            '@router.get("/reports/{report_id}"',
            '@router.get("/cases/{case_id}/observations"',
            '@router.get("/cases/{case_id}/imaging-studies"',
            '@router.get("/dry-run/fixtures"',
            '@router.get("/dry-run/fixtures/{fixture_id}"',
            "get_current_user",
            "DiagnosticReport",
            "Observation",
            "ImagingStudy",
            "Case",
            "Case.owner_id",
            '"diagnostic_data_case_summary"',
            '"diagnostic_data_dry_run_fixture"',
            '"writes_database": False',
            '"creates_case": False',
            '"updates_case": False',
            '"downloads_attachments": False',
            '"sends_external_message": False',
            '"executes_real_import": False',
            '"executes_real_lab_ingest": False',
            '"executes_real_dicom_ingest": False',
            '"executes_real_device_ingest": False',
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    api_text = API.read_text(encoding="utf-8")
    forbidden = (
        "db.add(",
        "db.commit(",
        "db.delete(",
        "requests.post(",
        "httpx.post(",
        "smtplib",
        "pydicom",
        "pynetdicom",
        "dicomweb",
        "hl7",
        "ENABLE_EMR_REAL_IMPORT=true",
        "ENABLE_DEVICE_REAL_INGEST=true",
    )
    for needle in forbidden:
        if needle in api_text:
            return fail(f"diagnostic data read-only API must not write DB or enable real integrations: {needle}")

    rc = require_text(
        MAIN,
        (
            "diagnostic_data_api_router",
            "app.include_router(diagnostic_data_api_router)",
        ),
        "backend/main.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Diagnostic Data Read-only API / Dry-run Fixtures V1",
            "GET /api/diagnostic-data/cases/{case_id}/summary",
            "GET /api/diagnostic-data/dry-run/fixtures/{fixture_id}",
            "writes_database=false",
            "real lab equipment ingest",
            "real DICOM / PACS ingest",
            "real device gateway ingest",
            "automatic SMS / WeChat / email delivery",
        ),
        "diagnostic data read-only API doc",
    )
    if rc:
        return rc

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if fixture.get("fixture_id") != "diagnostic_data_dry_run_fixture_v1":
        return fail("diagnostic fixture id mismatch")
    if fixture.get("dry_run") is not True or fixture.get("synthetic") is not True:
        return fail("diagnostic fixture must be synthetic dry-run data")
    for key in ("diagnostic_reports", "observations", "imaging_studies"):
        if not isinstance(fixture.get(key), list) or not fixture[key]:
            return fail(f"diagnostic fixture missing non-empty list: {key}")
    safety = fixture.get("safety") or {}
    for key in (
        "writes_database",
        "creates_case",
        "updates_case",
        "downloads_attachments",
        "sends_external_message",
        "executes_real_import",
        "executes_real_lab_ingest",
        "executes_real_dicom_ingest",
        "executes_real_device_ingest",
    ):
        if safety.get(key) is not False:
            return fail(f"diagnostic fixture safety flag must be false: {key}")

    rc = require_text(
        SMOKE,
        (
            "/api/diagnostic-data/cases/${case_id}/summary",
            "/api/diagnostic-data/cases/${case_id}/reports",
            "/api/diagnostic-data/cases/${case_id}/observations",
            "/api/diagnostic-data/cases/${case_id}/imaging-studies",
            "/api/diagnostic-data/dry-run/fixtures",
            "/api/diagnostic-data/dry-run/fixtures/diagnostic_data_dry_run_fixture_v1",
            "diagnostic data fixture requires auth",
            "user B cannot read user A diagnostic data",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_diagnostic_data_readonly_api_dry_run_fixtures.py",
        ),
        "scripts/ci_static_checks.sh",
    )
    if rc:
        return rc

    print("PASS: Diagnostic data read-only API / dry-run fixtures V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
