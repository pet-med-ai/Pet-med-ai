#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import py_compile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_lab_imaging_interpretation_readiness.py",
    "docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_V1.md",
    "docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_lab_imaging_interpretation_readiness.py",
]

EXPECTED_MATRIX_KEYS = {
    "rabbit",
    "bird",
    "ferret",
    "turtle",
    "lizard",
    "snake",
    "amphibian",
    "fish",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat_mouse",
    "hedgehog",
    "sugar_glider",
    "reptile",
    "rodent",
}

FORBIDDEN_BACKEND_SNIPPETS = [
    "db.add(",
    "db.commit(",
    "db.delete(",
    "requests.post(",
    "httpx.post(",
    "OpenAI(",
    "final_diagnosis =",
    "treatment_plan =",
    "prescription =",
    "drug_dose =",
]


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def require_snippets(rel: str, snippets: list[str]) -> None:
    text = read(rel)
    for snippet in snippets:
        if snippet not in text:
            fail("missing snippet in %s: %s" % (rel, snippet))


def load_module():
    path = ROOT / "backend" / "exotics_lab_imaging_interpretation_readiness.py"
    spec = importlib.util.spec_from_file_location("exotics_lab_imaging_interpretation_readiness", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def validate_required_files() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)


def validate_backend_static() -> None:
    rel = "backend/exotics_lab_imaging_interpretation_readiness.py"
    text = read(rel)
    for snippet in FORBIDDEN_BACKEND_SNIPPETS:
        if snippet in text:
            fail("forbidden backend snippet in readiness stage: %s" % snippet)
    require_snippets(
        rel,
        [
            'EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MODE = "exotics_lab_imaging_interpretation_readiness_v1"',
            "READINESS_MATRIX",
            '"writes_database": False',
            '"generates_final_diagnosis": False',
            '"creates_treatment_plan": False',
            '"writes_prescription": False',
            '"returns_drug_dose": False',
            '"lab_reference_ranges_enabled": False',
            '"imaging_ai_interpretation_enabled": False',
            '"requires_human_review": True',
            '"clinician_signoff_required": True',
            "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1",
        ],
    )


def validate_docs_and_matrix() -> None:
    require_snippets(
        "docs/clinical_data/EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_V1.md",
        [
            "Exotics Lab / Imaging Interpretation Readiness V1",
            "is_interpretation_engine=false",
            "lab_reference_ranges_enabled=false",
            "imaging_ai_interpretation_enabled=false",
            "source_review_status=required_not_started",
            "drug_dose_status=not_reviewed_not_enabled",
            "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1",
        ],
    )

    matrix_path = ROOT / "docs" / "clinical_data" / "EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_MATRIX_V1.csv"
    with matrix_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    keys = {row.get("rule_key") for row in rows}
    missing = sorted(EXPECTED_MATRIX_KEYS - keys)
    if missing:
        fail("matrix missing expected rule keys: %s" % ", ".join(missing))
    for row in rows:
        if row.get("source_review_status") != "required_not_started":
            fail("all matrix rows must keep source_review_status=required_not_started")
        if row.get("imaging_interpretation_status") not in {"readiness_only_no_ai_interpretation", "fallback_only_no_ai_interpretation"}:
            fail("matrix imaging status must remain readiness/fallback only")


def validate_module_behavior() -> None:
    module = load_module()
    review = module.build_exotics_lab_imaging_interpretation_readiness_review(root=ROOT)
    if review.get("mode") != "exotics_lab_imaging_interpretation_readiness_v1":
        fail("mode mismatch")
    if review.get("writes_database") is not False:
        fail("readiness stage must not write database")
    if review.get("generates_final_diagnosis") is not False:
        fail("readiness stage must not generate final diagnosis")
    if review.get("creates_treatment_plan") is not False:
        fail("readiness stage must not create treatment plan")
    if review.get("writes_prescription") is not False:
        fail("readiness stage must not write prescription")
    if review.get("returns_drug_dose") is not False:
        fail("readiness stage must not return drug dose")
    if review.get("lab_reference_ranges_enabled") is not False:
        fail("lab reference ranges must remain disabled")
    if review.get("imaging_ai_interpretation_enabled") is not False:
        fail("imaging AI interpretation must remain disabled")
    qg = review.get("quality_gate") or {}
    if qg.get("status") != "PASS":
        fail("quality gate must PASS")
    if qg.get("decision") != "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_PACK_V1":
        fail("unexpected next decision")
    matrix = review.get("matrix") or []
    if len(matrix) < len(EXPECTED_MATRIX_KEYS):
        fail("matrix too small")


def validate_ci_and_smoke_hooks() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "Exotics Lab / Imaging Interpretation Readiness V1" not in ci:
        fail("ci_static_checks missing stage block")
    if "python3 scripts/validate_exotics_lab_imaging_interpretation_readiness.py" not in ci:
        fail("ci_static_checks missing validator command")
    if "Exotics Lab / Imaging Interpretation Readiness V1" not in smoke:
        fail("smoke missing stage validator block")
    if "validate_exotics_lab_imaging_interpretation_readiness.py" not in smoke:
        fail("smoke missing validator command")


def main() -> None:
    validate_required_files()
    validate_backend_static()
    validate_docs_and_matrix()
    validate_module_behavior()
    validate_ci_and_smoke_hooks()
    print("VALIDATOR=PASS Exotics Lab / Imaging Interpretation Readiness V1")


if __name__ == "__main__":
    main()
