#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MODULE = ROOT / "backend" / "drug_dose_knowledge_base.py"
API = ROOT / "backend" / "diagnostic_data_api.py"
KB = ROOT / "docs" / "clinical_data" / "drug_dose_knowledge_base" / "drug_dose_kb_v1.json"
DOC = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_KNOWLEDGE_BASE_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_KNOWLEDGE_BASE_CHECKLIST_V1.csv"
GONOGO = ROOT / "docs" / "clinical_data" / "DRUG_DOSE_KNOWLEDGE_BASE_GO_NO_GO_V1.csv"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"
CI = ROOT / "scripts" / "ci_static_checks.sh"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def require_file(path: Path) -> str:
    if not path.exists():
        fail(f"missing file: {path.relative_to(ROOT)}")
    if path.suffix == ".py":
        py_compile.compile(str(path), doraise=True)
    return path.read_text(encoding="utf-8")


def require_markers(text: str, markers: list[str], label: str) -> None:
    for marker in markers:
        if marker not in text:
            fail(f"{label} missing expected marker: {marker}")


def main() -> int:
    module_text = require_file(MODULE)
    api_text = require_file(API)
    kb_text = require_file(KB)
    doc_text = require_file(DOC)
    require_file(CHECKLIST)
    require_file(GONOGO)
    smoke_text = require_file(SMOKE)
    ci_text = require_file(CI)

    require_markers(
        module_text,
        [
            "DRUG_DOSE_KNOWLEDGE_BASE_MODE",
            "drug_dose_knowledge_base_flags",
            "list_drug_dose_monographs",
            "get_drug_dose_monograph",
            "review_drug_dose_knowledge_base",
            '"numeric_dose_values_redacted": True',
            '"dose_calculation_enabled": False',
            '"dose_lookup_enabled": False',
            '"returns_numeric_dose": False',
            '"returns_route_frequency": False',
            '"writes_prescription": False',
            '"drug_dose_recommendation": False',
            '"calls_external_ai": False',
            '"requires_human_review": True',
        ],
        "drug dose knowledge base module",
    )

    forbidden_module = (
        "requests.post(",
        "httpx.post(",
        "openai",
        "anthropic",
        "client.chat.completions",
        "db.commit(",
        "session.add(",
        "DiagnosticReport(",
        "Observation(",
        "Prescription(",
    )
    for item in forbidden_module:
        if item in module_text:
            fail(f"drug dose knowledge base module must not call providers or write data: {item}")

    require_markers(
        api_text,
        [
            "DRUG_DOSE_KNOWLEDGE_BASE_MODE",
            "drug_dose_knowledge_base_flags",
            "list_drug_dose_monographs",
            "get_drug_dose_monograph",
            "review_drug_dose_knowledge_base",
            '@router.get("/dry-run/drug-dose-kb/monographs"',
            '@router.get("/dry-run/drug-dose-kb/monographs/{drug_key}"',
            '@router.post("/dry-run/drug-dose-kb/review"',
            '"message": "drug_dose_knowledge_base_monographs"',
            '"message": "drug_dose_knowledge_base_monograph"',
            '"message": "drug_dose_knowledge_base_reviewed"',
        ],
        "diagnostic data API",
    )

    data = json.loads(kb_text)
    monographs = data.get("monographs")
    if not isinstance(monographs, list) or not monographs:
        fail("drug dose KB JSON must contain non-empty monographs list")
    drug_keys = {str(row.get("drug_key", "")).lower() for row in monographs if isinstance(row, dict)}
    for required in ("maropitant", "ondansetron", "gabapentin"):
        if required not in drug_keys:
            fail(f"drug dose KB JSON missing monograph: {required}")

    if re.search(r"\b\d+(\.\d+)?\s*(mg/kg|mcg/kg|ug/kg|ml/kg|iu/kg|units/kg|mg|mcg|ug|ml|iu|units)\b", kb_text, re.I):
        fail("drug dose KB JSON must not expose numeric dose values")

    require_markers(
        kb_text,
        [
            '"numeric_dose_values_redacted": true',
            '"dose_calculation_enabled": false',
            '"dose_lookup_enabled": false',
            '"returns_numeric_dose": false',
            '"returns_route_frequency": false',
            '"requires_clinician_source_review": true',
        ],
        "drug dose KB JSON",
    )

    require_markers(
        doc_text,
        [
            "Drug Dose Knowledge Base V1",
            "numeric dose values redacted",
            "does not calculate dose",
            "does not recommend medication",
            "writes_prescription=false",
            "returns_numeric_dose=false",
        ],
        "drug dose knowledge base doc",
    )

    require_markers(
        smoke_text,
        [
            "Drug dose knowledge base list",
            "Drug dose knowledge base monograph get",
            "Drug dose knowledge base review",
            "Drug dose knowledge base requires auth",
            "user B cannot review user A drug dose knowledge base",
            "Drug dose knowledge base checks",
        ],
        "smoke script",
    )

    require_markers(
        ci_text,
        [
            "validate_drug_dose_knowledge_base.py",
        ],
        "CI static checks",
    )

    print("PASS: Drug Dose Knowledge Base V1 files and gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
