#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PARSER = ROOT / "backend" / "lab_result_parser.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "LAB_RESULT_DRY_RUN_FIXTURE_PARSER_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "LAB_RESULT_DRY_RUN_FIXTURE_PARSER_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "LAB_RESULT_DRY_RUN_FIXTURE_PARSER_GO_NO_GO_V1.csv"
FIXTURE = ROOT / "docs" / "clinical_data" / "fixtures" / "lab_result_dry_run_fixture_v1.json"
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
    for path in (PARSER, API, DOC, CHECKLIST, GO_NO_GO, FIXTURE, SMOKE, CI_STATIC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        PARSER,
        (
            "lab_result_dry_run_fixture_parser_v1",
            "parse_lab_result_fixture",
            "lab_parser_safety_flags",
            "writes_database",
            "False",
            "executes_real_lab_ingest",
            "creates_diagnostic_report",
            "creates_observation",
            "quality_gate",
            "abnormal_observations",
        ),
        "backend/lab_result_parser.py",
    )
    if rc:
        return rc

    parser_text = PARSER.read_text(encoding="utf-8")
    forbidden = (
        "db.add(",
        "db.commit(",
        "Session(",
        "requests.",
        "httpx.",
        "smtplib",
        "twilio",
        "pydicom",
        "pynetdicom",
        "socket.",
    )
    for needle in forbidden:
        if needle in parser_text:
            return fail(f"lab parser must remain pure dry-run and offline: {needle}")

    rc = require_text(
        API,
        (
            "parse_lab_result_fixture",
            "lab_parser_safety_flags",
            '@router.get("/dry-run/lab-results/fixtures"',
            '@router.get("/dry-run/lab-results/fixtures/{fixture_id}"',
            '@router.post("/dry-run/lab-results/parse"',
            "_owned_case_or_404(db, int(case_id), user)",
            "lab_result_dry_run_parsed",
            "executes_real_lab_ingest",
            "writes_database",
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Lab Result Dry-run Fixture Parser V1",
            "POST /api/diagnostic-data/dry-run/lab-results/parse",
            "writes_database=false",
            "executes_real_lab_ingest=false",
            "GO_TO_IMAGING_METADATA_DRY_RUN_FIXTURE_PARSER_V1",
        ),
        "lab parser doc",
    )
    if rc:
        return rc

    with FIXTURE.open("r", encoding="utf-8") as f:
        fixture = json.load(f)
    if fixture.get("fixture_id") != "lab_result_dry_run_fixture_v1":
        return fail("lab fixture fixture_id mismatch")
    results = fixture.get("results")
    if not isinstance(results, list) or len(results) < 4:
        return fail("lab fixture must include at least 4 result rows")
    codes = {str(item.get("code")) for item in results if isinstance(item, dict)}
    for code in ("WBC", "ALT", "CREA", "GLU"):
        if code not in codes:
            return fail(f"lab fixture missing code: {code}")

    # Import the parser and verify the fixture parses as expected.
    backend_dir = ROOT / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    from lab_result_parser import parse_lab_result_fixture  # type: ignore

    parsed = parse_lab_result_fixture(fixture, case_id=123)
    if parsed.get("quality_gate", {}).get("status") != "PASS":
        return fail("fixture parse quality gate must PASS")
    if parsed.get("writes_database") is not False:
        return fail("parser must report writes_database false")
    if parsed.get("executes_real_lab_ingest") is not False:
        return fail("parser must report executes_real_lab_ingest false")
    abnormal_codes = {
        item.get("code")
        for item in parsed.get("abnormal_observations", [])
        if isinstance(item, dict)
    }
    for code in ("WBC", "ALT", "GLU"):
        if code not in abnormal_codes:
            return fail(f"expected abnormal code missing from parse output: {code}")

    rc = require_text(
        SMOKE,
        (
            "lab result dry-run fixture list",
            "lab result dry-run fixture get",
            "lab result dry-run fixture parse",
            "lab result dry-run parser requires auth",
            "user B cannot parse user A lab dry-run fixture",
            "/api/diagnostic-data/dry-run/lab-results/parse",
            "executes_real_lab_ingest",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        (
            "validate_lab_result_dry_run_fixture_parser.py",
        ),
        "ci static script",
    )
    if rc:
        return rc

    print("PASS: Lab Result Dry-run Fixture Parser V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
