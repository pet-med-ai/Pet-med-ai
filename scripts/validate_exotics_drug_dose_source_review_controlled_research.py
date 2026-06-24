#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "backend/exotics_drug_dose_source_review_controlled_research.py",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_V1.md",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_MATRIX_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_drug_dose_source_review_controlled_research.py",
]

EXPECTED_SPECIES = {
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
}

EXPECTED_DOMAINS = {
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
}

DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
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


def assert_required_files() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)


def assert_no_dose_like_content() -> None:
    # Scan generated stage files only. Prohibition wording is allowed; actual dose-like values are not.
    for rel in REQUIRED_FILES:
        if rel.endswith(".py") and rel == "scripts/validate_exotics_drug_dose_source_review_controlled_research.py":
            continue
        text = read(rel)
        for match in DOSE_PATTERN.finditer(text):
            token = match.group(0)
            # The backend regex constant intentionally contains dose/route/frequency tokens for rejection.
            if rel == "backend/exotics_drug_dose_source_review_controlled_research.py":
                continue
            fail("dose-like or route/frequency-like token found in %s: %s" % (rel, token))


def assert_docs() -> None:
    doc = read("docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_V1.md")
    required = [
        "Exotics Drug Dose Source Review Controlled Research V1",
        "not a dose engine",
        "no numerical drug dose",
        "no drug route",
        "no drug frequency",
        "dose_output_enabled=false",
        "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_EVIDENCE_ABSTRACTION_V1",
    ]
    for item in required:
        if item not in doc:
            fail("doc missing expected text: %s" % item)


def assert_matrix() -> None:
    path = ROOT / "docs/clinical_data/EXOTICS_DRUG_DOSE_SOURCE_REVIEW_CONTROLLED_RESEARCH_MATRIX_V1.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        fail("controlled research matrix is empty")

    species = {row.get("species_group") for row in rows}
    domains = {row.get("review_domain") for row in rows}
    if species != EXPECTED_SPECIES:
        fail("species coverage mismatch: %s" % sorted(species))
    if domains != EXPECTED_DOMAINS:
        fail("review domain coverage mismatch: %s" % sorted(domains))

    expected_count = len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS)
    if len(rows) != expected_count:
        fail("matrix row count expected %d got %d" % (expected_count, len(rows)))

    for row in rows:
        if row.get("dose_output_enabled") != "false":
            fail("dose_output_enabled must be false for every row")
        if row.get("prescription_enabled") != "false":
            fail("prescription_enabled must be false for every row")
        blocked = (row.get("blocked_content") or "").lower()
        if "no numerical dose" not in blocked:
            fail("blocked_content must explicitly prohibit numerical dose")


def load_module():
    path = ROOT / "backend" / "exotics_drug_dose_source_review_controlled_research.py"
    spec = importlib.util.spec_from_file_location("exotics_drug_dose_source_review_controlled_research", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def assert_module_behavior() -> None:
    module = load_module()
    result = module.build_exotics_drug_dose_source_review_controlled_research_pack({})
    if result.get("mode") != "exotics_drug_dose_source_review_controlled_research_v1":
        fail("mode mismatch")
    for key in (
        "writes_database",
        "creates_case",
        "writes_audit_log",
        "generates_final_diagnosis",
        "creates_treatment_plan",
        "writes_prescription",
        "returns_drug_dose",
        "returns_drug_route",
        "returns_drug_frequency",
        "dose_output_enabled",
    ):
        if result.get(key) is not False:
            fail("%s must be false" % key)
    if result.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if result.get("clinician_signoff_required") is not True:
        fail("clinician_signoff_required must be true")
    if len(result.get("matrix_preview") or []) != len(EXPECTED_SPECIES) * len(EXPECTED_DOMAINS):
        fail("matrix preview row count mismatch")

    filtered = module.build_exotics_drug_dose_source_review_controlled_research_pack({"species": "rabbit"})
    if filtered.get("species_groups") != ["rabbit"]:
        fail("species filter should return rabbit only")

    try:
        module.build_exotics_drug_dose_source_review_controlled_research_pack({"research_note": "2 mg/kg"})
        fail("payload containing actual dose-like text should fail")
    except ValueError:
        pass


def assert_ci_smoke() -> None:
    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_drug_dose_source_review_controlled_research.py" not in ci:
        fail("ci_static_checks missing controlled research validator")
    if "Exotics Drug Dose Source Review Controlled Research V1 smoke" not in smoke:
        fail("smoke missing controlled research block")
    if "validate_exotics_drug_dose_source_review_controlled_research.py" not in smoke:
        fail("smoke missing controlled research validator command")


def main() -> None:
    assert_required_files()
    assert_docs()
    assert_matrix()
    assert_no_dose_like_content()
    assert_module_behavior()
    assert_ci_smoke()
    print("VALIDATOR=PASS Exotics Drug Dose Source Review Controlled Research V1")


if __name__ == "__main__":
    main()
