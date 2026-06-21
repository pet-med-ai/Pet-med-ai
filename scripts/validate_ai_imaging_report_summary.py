#!/usr/bin/env python3
from __future__ import annotations

import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / "backend" / "ai_imaging_report_summary.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "AI_IMAGING_REPORT_SUMMARY_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "AI_IMAGING_REPORT_SUMMARY_CHECKLIST_V1.csv"
GONOGO = ROOT / "docs" / "clinical_data" / "AI_IMAGING_REPORT_SUMMARY_GO_NO_GO_V1.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL: {message}")
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


def main() -> int:
    for path in (MODULE, API, DOC, CHECKLIST, GONOGO, SMOKE, CI):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODULE,
        (
            "AI_IMAGING_REPORT_SUMMARY_MODE",
            "ai_imaging_report_summary_v1",
            "build_ai_imaging_report_summary",
            "ai_imaging_report_summary_safety_flags",
            "\"writes_database\": False",
            "\"creates_imaging_study\": False",
            "\"queries_pacs\": False",
            "\"reads_raw_dicom\": False",
            "\"executes_real_dicom_ingest\": False",
            "\"calls_external_ai\": False",
            "\"treatment_recommendation\": False",
            "\"drug_dose_recommendation\": False",
            "\"requires_human_review\": True",
            "\"not_a_diagnosis\": True",
            "\"not_a_treatment_plan\": True",
            "\"not_a_radiologist_report\": True",
        ),
        "backend/ai_imaging_report_summary.py",
    )
    if rc:
        return rc

    forbidden = (
        "openai",
        "anthropic",
        "requests.post(",
        "httpx.post(",
        "db.add(",
        "db.commit(",
        "pydicom",
        "pynetdicom",
    )
    module_text = MODULE.read_text(encoding="utf-8")
    for needle in forbidden:
        if needle in module_text:
            return fail(f"AI imaging summary must not call providers, write DB or read DICOM: {needle}")

    rc = require_text(
        API,
        (
            "build_ai_imaging_report_summary",
            "ai_imaging_report_summary_safety_flags",
            '@router.post("/dry-run/imaging-metadata/report-summary"',
            "\"message\": \"ai_imaging_report_summary_dry_run\"",
            "parse_imaging_metadata_fixture",
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "AI Imaging Report Summary V1",
            "POST /api/diagnostic-data/dry-run/imaging-metadata/report-summary",
            "queries_pacs=false",
            "reads_raw_dicom=false",
            "calls_external_ai=false",
            "not_a_diagnosis=true",
        ),
        "AI imaging doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "AI imaging report summary dry-run",
            "AI imaging report summary requires auth",
            "user B cannot summarize user A imaging report",
            "AI imaging report summary checks",
            "/api/diagnostic-data/dry-run/imaging-metadata/report-summary",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI,
        (
            "validate_ai_imaging_report_summary.py",
        ),
        "ci static checks",
    )
    if rc:
        return rc

    print("PASS: AI Imaging Report Summary V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
