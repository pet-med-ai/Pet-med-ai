#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / "backend" / "ai_lab_abnormal_summary.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "AI_LAB_ABNORMAL_SUMMARY_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "AI_LAB_ABNORMAL_SUMMARY_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "AI_LAB_ABNORMAL_SUMMARY_GO_NO_GO_V1.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL {message}", file=sys.stderr)
    return 1


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def require(path: Path, needles: tuple[str, ...], label: str) -> int:
    try:
        text = read(path)
    except Exception as exc:
        return fail(f"{label} missing or invalid: {exc}")
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected marker: {needle}")
    return 0


def main() -> int:
    rc = require(
        MODULE,
        (
            "AI_LAB_ABNORMAL_SUMMARY_MODE",
            "build_ai_lab_abnormal_summary",
            "ai_lab_abnormal_summary_safety_flags",
            '"writes_database": False',
            '"creates_diagnostic_report": False',
            '"creates_observation": False',
            '"executes_real_lab_ingest": False',
            '"calls_external_ai": False',
            '"treatment_recommendation": False',
            '"drug_dose_recommendation": False',
            '"requires_human_review": True',
            "not_a_diagnosis",
            "not_a_treatment_plan",
            "not_a_drug_dose_recommendation",
        ),
        "backend/ai_lab_abnormal_summary.py",
    )
    if rc:
        return rc

    module_text = MODULE.read_text(encoding="utf-8")
    forbidden = (
        "openai",
        "anthropic",
        "requests.post(",
        "httpx.post(",
        "db.add(",
        "db.commit(",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "ENABLE_EMR_REAL_IMPORT=true",
    )
    for needle in forbidden:
        if needle in module_text:
            return fail(f"AI lab abnormal summary must be pure dry-run/no external writes: {needle}")

    rc = require(
        API,
        (
            "AI_LAB_ABNORMAL_SUMMARY_MODE",
            "build_ai_lab_abnormal_summary",
            "ai_lab_abnormal_summary_safety_flags",
            '@router.post("/dry-run/lab-results/abnormal-summary"',
            "ai_lab_abnormal_summary_dry_run",
            "_owned_case_or_404(db, int(case_id), user)",
            "parse_lab_result_fixture",
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require(
        DOC,
        (
            "AI Lab Abnormal Summary V1",
            "POST /api/diagnostic-data/dry-run/lab-results/abnormal-summary",
            "writes_database=false",
            "executes_real_lab_ingest=false",
            "calls_external_ai=false",
            "drug_dose_recommendation=false",
            "requires_human_review=true",
        ),
        "AI lab abnormal summary doc",
    )
    if rc:
        return rc

    for path in (CHECKLIST, GO_NO_GO):
        try:
            text = read(path)
        except Exception as exc:
            return fail(f"{path.relative_to(ROOT)} missing or invalid: {exc}")
        if "PENDING" not in text:
            return fail(f"{path.relative_to(ROOT)} should include PENDING evidence rows")

    rc = require(
        SMOKE,
        (
            "AI lab abnormal summary dry-run",
            "/api/diagnostic-data/dry-run/lab-results/abnormal-summary",
            "AI lab abnormal summary requires auth",
            "user B cannot summarize user A lab abnormal summary",
            "AI lab abnormal summary checks",
            "calls_external_ai",
            "drug_dose_recommendation",
        ),
        "scripts/smoke_petmed.sh",
    )
    if rc:
        return rc

    rc = require(
        CI_STATIC,
        ("validate_ai_lab_abnormal_summary.py",),
        "scripts/ci_static_checks.sh",
    )
    if rc:
        return rc

    print("PASS: AI Lab Abnormal Summary V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
