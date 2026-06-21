#!/usr/bin/env python3
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE_DETAIL = ROOT / "frontend" / "src" / "pages" / "CaseDetail.jsx"
DOC = ROOT / "docs" / "clinical_data" / "CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "CASE_DETAIL_DIAGNOSTIC_DATA_DISPLAY_GO_NO_GO_V1.csv"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"


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
            return fail(f"{label} missing expected marker: {needle}")
    return 0


def main() -> int:
    for path in (CASE_DETAIL, DOC, CHECKLIST, GO_NO_GO, CI_STATIC, SMOKE):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        CASE_DETAIL,
        (
            "Case Detail Diagnostic Data Display V1",
            "DiagnosticDataPanel",
            "diagnosticDataSummary",
            "setDiagnosticDataSummary",
            "/api/diagnostic-data/cases/${data.id}/summary",
            "诊断数据 / Diagnostic Data",
            "Diagnostic Reports",
            "Observations",
            "Imaging Studies",
            "read_only=true",
            "writes_database=false",
            "creates_case=false",
            "executes_real_lab_ingest=false",
            "executes_real_dicom_ingest=false",
            "executes_real_device_ingest=false",
        ),
        "frontend CaseDetail diagnostic display",
    )
    if rc:
        return rc

    case_text = CASE_DETAIL.read_text(encoding="utf-8")
    forbidden = (
        "api.post(`/api/diagnostic-data",
        "api.post(\"/api/diagnostic-data",
        "api.put(`/api/diagnostic-data",
        "api.put(\"/api/diagnostic-data",
        "api.delete(`/api/diagnostic-data",
        "api.delete(\"/api/diagnostic-data",
        "executes_real_lab_ingest=true",
        "executes_real_dicom_ingest=true",
        "executes_real_device_ingest=true",
        "sends_external_message=true",
    )
    for needle in forbidden:
        if needle in case_text:
            return fail(f"case detail diagnostic display must be read-only and safe; forbidden marker found: {needle}")

    rc = require_text(
        DOC,
        (
            "Case Detail Diagnostic Data Display V1",
            "GET /api/diagnostic-data/cases/{case_id}/summary",
            "display-only",
            "real lab equipment ingest",
            "real DICOM / PACS ingest",
            "writes_database=false",
            "GO_TO_AI_LAB_ABNORMAL_SUMMARY_V1",
        ),
        "case detail diagnostic data display doc",
    )
    if rc:
        return rc

    rc = require_text(
        CHECKLIST,
        (
            "case_detail_panel_present",
            "read_only_endpoint_used",
            "safety_markers_visible",
            "owner_scope_preserved",
        ),
        "case detail diagnostic data display checklist",
    )
    if rc:
        return rc

    rc = require_text(
        GO_NO_GO,
        (
            "validator_pass",
            "ci_static_checks_pass",
            "online_smoke_all_pass",
            "final_decision",
        ),
        "case detail diagnostic data display go no-go",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        ("validate_case_detail_diagnostic_data_display.py",),
        "ci static checks",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "validate_case_detail_diagnostic_data_display.py",
            "case detail diagnostic data display validation",
        ),
        "smoke script",
    )
    if rc:
        return rc

    print("PASS: Case Detail Diagnostic Data Display V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
