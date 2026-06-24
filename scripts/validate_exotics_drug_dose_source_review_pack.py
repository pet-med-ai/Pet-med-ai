#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_pack.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_pack.py",
]

REQUIRED_SNIPPETS = {
    "backend/exotics_drug_dose_source_review_pack.py": [
        'EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MODE = "exotics_drug_dose_source_review_pack_v1"',
        '"writes_database": False',
        '"returns_drug_dose": False',
        '"returns_drug_route": False',
        '"returns_drug_frequency": False',
        '"dose_output_enabled": False',
        '"drug_dose_recommendation": False',
        '"creates_prescription": False',
        '"writes_prescription": False',
        '"creates_treatment_plan": False',
        '"requires_human_review": True',
        '"clinician_signoff_required": True',
        '"source_review_required": True',
        '"source_review_status": "required_not_started"',
        '"drug_dose_status": "not_reviewed_not_enabled"',
    ],
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1.md": [
        "Exotics Drug Dose Source Review Pack V1",
        "is_dose_engine=false",
        "is_prescription_engine=false",
        "drug_dose_status=not_reviewed_not_enabled",
        "source_review_status=required_not_started",
        "returns_drug_dose=false",
        "dose_output_enabled=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_V1",
    ],
}

FORBIDDEN_SNIPPETS = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "OpenAI(",
    "requests.post(",
    "httpx.post(",
    "create_prescription(",
    "write_prescription(",
    "create_treatment_plan(",
]

DOSE_PATTERN = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg/kg|mcg/kg|ug/kg|ml/kg|iu/kg|units/kg|mg|mcg|ug|ml|iu|units)\b|\bq\d{1,2}h\b",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_pack.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_drug_dose_source_review_pack", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load exotics drug dose source review pack module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_required_files_and_snippets() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if rel.endswith(".py"):
            py_compile.compile(str(path), doraise=True)

    for rel, snippets in REQUIRED_SNIPPETS.items():
        text = read(rel)
        for snippet in snippets:
            if snippet not in text:
                fail("missing snippet in %s: %s" % (rel, snippet))

    for rel in [
        "backend/exotics_drug_dose_source_review_pack.py",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1.md",
        "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MATRIX_V1.csv",
    ]:
        text = read(rel)
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                fail("forbidden snippet in %s: %s" % (rel, snippet))
        match = DOSE_PATTERN.search(text)
        if match:
            fail("numeric dose-like content found in %s: %s" % (rel, match.group(0)))


def assert_matrix() -> None:
    matrix_path = ROOT / "docs" / "clinical_data" / "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_MATRIX_V1.csv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) < 14:
        fail("source review matrix is too small")

    required_species = {
        "rabbit", "bird", "ferret", "turtle", "lizard", "snake", "amphibian", "fish",
        "guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider",
    }
    species = {row.get("species_group") for row in rows}
    missing = sorted(required_species - species)
    if missing:
        fail("matrix missing species groups: %s" % ", ".join(missing))

    for row in rows:
        if row.get("source_review_status") != "required_not_started":
            fail("matrix source_review_status must be required_not_started")
        if row.get("drug_dose_status") != "not_reviewed_not_enabled":
            fail("matrix drug_dose_status must be not_reviewed_not_enabled")
        if row.get("dose_values_present") != "false":
            fail("matrix must not contain dose values")
        if row.get("dose_output_enabled") != "false":
            fail("matrix must keep dose output disabled")


def assert_module_behavior() -> None:
    module = load_module()
    pack = module.validate_exotics_drug_dose_source_review_pack()

    if pack.get("mode") != "exotics_drug_dose_source_review_pack_v1":
        fail("mode mismatch")
    if pack.get("writes_database") is not False:
        fail("source review pack must not write database")
    if pack.get("returns_drug_dose") is not False:
        fail("drug dose output must be disabled")
    if pack.get("returns_drug_route") is not False:
        fail("drug route output must be disabled")
    if pack.get("returns_drug_frequency") is not False:
        fail("drug frequency output must be disabled")
    if pack.get("dose_output_enabled") is not False:
        fail("dose output must be disabled")
    if pack.get("creates_prescription") is not False or pack.get("writes_prescription") is not False:
        fail("prescription write must be blocked")
    if pack.get("quality_gate", {}).get("status") != "PASS":
        fail("quality gate must PASS")
    if pack.get("quality_gate", {}).get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("drug_dose_status mismatch")
    if len(pack.get("matrix") or []) < 14:
        fail("module matrix is too small")


def assert_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")

    if "Exotics Drug Dose Source Review Pack V1 static checks" not in ci:
        fail("ci_static_checks missing Exotics Drug Dose Source Review Pack V1 block")
    if "python3 scripts/validate_exotics_drug_dose_source_review_pack.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Exotics Drug Dose Source Review Pack V1 smoke" not in smoke:
        fail("smoke missing Exotics Drug Dose Source Review Pack V1 block")
    if "validate_exotics_drug_dose_source_review_pack.py" not in smoke:
        fail("smoke missing validator command")


def main() -> None:
    assert_required_files_and_snippets()
    assert_matrix()
    assert_module_behavior()
    assert_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Pack V1")


if __name__ == "__main__":
    main()
