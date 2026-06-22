#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / "backend" / "treatment_recommendation_boundary.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "TREATMENT_RECOMMENDATION_BOUNDARY_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "TREATMENT_RECOMMENDATION_BOUNDARY_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "TREATMENT_RECOMMENDATION_BOUNDARY_GO_NO_GO_V1.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI = ROOT / "scripts" / "ci_static_checks.sh"


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
    for path in (MODULE, API, DOC, CHECKLIST, GO_NO_GO, SMOKE, CI):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODULE,
        (
            "TREATMENT_RECOMMENDATION_BOUNDARY_MODE",
            "treatment_recommendation_boundary_v1",
            "treatment_boundary_safety_flags",
            "build_treatment_recommendation_boundary",
            "blocked_drug_or_dose",
            '"writes_database": False',
            '"creates_treatment_plan": False',
            '"treatment_recommendation": False',
            '"drug_dose_recommendation": False',
            '"calls_external_ai": False',
            '"requires_human_review": True',
            "Drug Dose Safety Framework V1",
        ),
        "backend/treatment_recommendation_boundary.py",
    )
    if rc:
        return rc

    module_text = MODULE.read_text(encoding="utf-8")
    forbidden = (
        "requests.post(",
        "httpx.post(",
        "openai.",
        "client.chat.completions",
        "db.add(",
        "db.commit(",
        "db.delete(",
        "create_engine(",
    )
    for needle in forbidden:
        if needle in module_text:
            return fail(f"treatment boundary module must be pure dry-run only: {needle}")

    rc = require_text(
        API,
        (
            "TREATMENT_RECOMMENDATION_BOUNDARY_MODE",
            "treatment_boundary_safety_flags",
            "build_treatment_recommendation_boundary",
            '@router.post("/dry-run/treatment-boundary/check"',
            "treatment_recommendation_boundary_checked",
            "case = _owned_case_or_404(db, int(case_id), user)",
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Treatment Recommendation Boundary V1",
            "POST /api/diagnostic-data/dry-run/treatment-boundary/check",
            "drug_dose_recommendation=false",
            "calls_external_ai=false",
            "decision=GO_TO_DRUG_DOSE_SAFETY_FRAMEWORK_V1",
        ),
        "treatment boundary doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "Treatment recommendation boundary dry-run",
            "Treatment recommendation boundary blocks dose",
            "Treatment recommendation boundary requires auth",
            "user B cannot check user A treatment boundary",
            "Treatment recommendation boundary checks",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI,
        (
            "validate_treatment_recommendation_boundary.py",
        ),
        "ci static checks",
    )
    if rc:
        return rc

    print("PASS: Treatment Recommendation Boundary V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
