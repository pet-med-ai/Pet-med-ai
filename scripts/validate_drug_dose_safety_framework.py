#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import py_compile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "backend" / "drug_dose_safety_framework.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
DOC = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_SAFETY_FRAMEWORK_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_SAFETY_FRAMEWORK_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_SAFETY_FRAMEWORK_GO_NO_GO_V1.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI_STATIC = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> int:
    print(f"FAIL: {message}", file=sys.stderr)
    return 1


def read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8")


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
    text = read(path)
    for needle in needles:
        if needle not in text:
            return fail(f"{label} missing expected marker: {needle}")
    return 0


def main() -> int:
    for path in (MODULE, API, DOC, CHECKLIST, GO_NO_GO, SMOKE, CI_STATIC):
        rc = require_file(path)
        if rc:
            return rc

    rc = require_text(
        MODULE,
        (
            "DRUG_DOSE_SAFETY_FRAMEWORK_MODE",
            "drug_dose_safety_framework_flags",
            "build_drug_dose_safety_framework",
            '"dose_calculation_enabled": False',
            '"drug_dose_recommendation": False',
            '"returns_numeric_dose": False',
            '"creates_prescription": False',
            '"writes_prescription": False',
            '"requires_human_review": True',
            "blocked_dose_calculation_disabled",
        ),
        "backend/drug_dose_safety_framework.py",
    )
    if rc:
        return rc

    module_text = read(MODULE)
    forbidden = (
        "db.add(",
        "db.commit(",
        "requests.",
        "httpx.",
        "openai",
        "anthropic",
        "send_sms",
        "send_wechat",
        "send_email",
    )
    for needle in forbidden:
        if needle in module_text:
            return fail(f"drug dose framework must be pure dry-run and offline: {needle}")

    try:
        sys.path.insert(0, str(ROOT / "backend"))
        from drug_dose_safety_framework import build_drug_dose_safety_framework  # type: ignore

        result = build_drug_dose_safety_framework({
            "species": "dog",
            "weight_kg": 5.2,
            "drug_name": "maropitant",
            "dose_expression": "mg/kg PO q24h",
        })
    except Exception as exc:
        return fail(f"drug dose framework import/self-test failed: {exc}")

    if result.get("framework", {}).get("decision") != "blocked_dose_calculation_disabled":
        return fail("drug dose framework must block dose calculation by default")
    for key in (
        "writes_database",
        "creates_prescription",
        "writes_prescription",
        "dose_calculation",
        "dose_calculation_enabled",
        "drug_dose_recommendation",
        "returns_numeric_dose",
    ):
        if result.get(key) is not False:
            return fail(f"drug dose framework safety flag must be false: {key}")
    if result.get("requires_human_review") is not True:
        return fail("drug dose framework must require human review")

    rc = require_text(
        API,
        (
            "DRUG_DOSE_SAFETY_FRAMEWORK_MODE",
            "build_drug_dose_safety_framework",
            "drug_dose_safety_framework_flags",
            '@router.post("/dry-run/drug-dose-safety/check"',
            '"message": "drug_dose_safety_framework_checked"',
            '"mode": DRUG_DOSE_SAFETY_FRAMEWORK_MODE',
        ),
        "backend/diagnostic_data_api.py",
    )
    if rc:
        return rc

    rc = require_text(
        DOC,
        (
            "Drug Dose Safety Framework V1",
            "dose_calculation_enabled=false",
            "drug_dose_recommendation=false",
            "returns_numeric_dose=false",
            "requires_human_review=true",
            "POST /api/diagnostic-data/dry-run/drug-dose-safety/check",
        ),
        "drug dose safety framework doc",
    )
    if rc:
        return rc

    rc = require_text(
        SMOKE,
        (
            "Drug dose safety framework dry-run",
            "Drug dose safety framework blocks dose",
            "Drug dose safety framework requires auth",
            "user B cannot check user A drug dose safety",
            "Drug dose safety framework checks",
        ),
        "smoke script",
    )
    if rc:
        return rc

    rc = require_text(
        CI_STATIC,
        ("validate_drug_dose_safety_framework.py",),
        "ci static script",
    )
    if rc:
        return rc

    print("PASS: Drug Dose Safety Framework V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
