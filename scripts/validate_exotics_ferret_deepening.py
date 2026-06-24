#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import py_compile
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]

KB = ROOT / "knowledge-base" / "exotics" / "ferret.json"
INTAKE = ROOT / "knowledge-base" / "exotics" / "intake" / "ferret.json"
HELPER = ROOT / "backend" / "exotics_ferret_deepening.py"
DOC = ROOT / "docs" / "clinical_data" / "EXOTICS_FERRET_DEEPENING_V1.md"
CHECKLIST = ROOT / "docs" / "clinical_data" / "EXOTICS_FERRET_DEEPENING_CHECKLIST_V1.csv"
GO_NO_GO = ROOT / "docs" / "clinical_data" / "EXOTICS_FERRET_DEEPENING_GO_NO_GO_V1.csv"
VALIDATOR = ROOT / "scripts" / "validate_exotics_ferret_deepening.py"
CI = ROOT / "scripts" / "ci_static_checks.sh"
SMOKE = ROOT / "scripts" / "smoke_petmed.sh"

REQUIRED_TERMS = (
    "低血糖", "胰岛素瘤", "胃肠异物", "部分梗阻", "腹泻脱水", "肾上腺",
    "排尿困难", "呼吸困难", "肿块", "外伤", "神经异常",
)
REQUIRED_FEATURES = (
    "hypoglycemia_signs", "foreign_body_risk", "urinary_issue", "hair_loss",
    "respiratory_distress", "mass_or_swelling", "neurologic_signs",
)
REQUIRED_SECTIONS = (
    "signalment",
    "weakness_hypoglycemia",
    "foreign_body_gi",
    "diarrhea_dehydration",
    "urinary_reproductive_endocrine",
    "respiratory_exposure",
    "mass_neuro_trauma",
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    if not path.exists():
        fail("missing file: %s" % path.relative_to(ROOT))
    return path.read_text(encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        fail("missing file: %s" % path.relative_to(ROOT))
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("expected JSON object: %s" % path.relative_to(ROOT))
    return data


def contains(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(contains(child, needle) for child in value.values())
    if isinstance(value, list):
        return any(contains(child, needle) for child in value)
    return needle in str(value or "")


def load_helper():
    py_compile.compile(str(HELPER), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_ferret_deepening", str(HELPER))
    if spec is None or spec.loader is None:
        fail("could not load helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def main() -> None:
    for path in (KB, INTAKE, HELPER, DOC, CHECKLIST, GO_NO_GO, CI, SMOKE):
        if not path.exists():
            fail("missing file: %s" % path.relative_to(ROOT))
    py_compile.compile(str(VALIDATOR), doraise=True)

    kb = read_json(KB)
    intake = read_json(INTAKE)
    if kb.get("key") != "ferret":
        fail("ferret KB key mismatch")
    if intake.get("key") != "ferret":
        fail("ferret intake key mismatch")

    for term in REQUIRED_TERMS:
        if not contains(kb, term):
            fail("ferret KB missing required term: %s" % term)
    for feature in REQUIRED_FEATURES:
        if not contains(kb, feature):
            fail("ferret KB missing required feature: %s" % feature)
        if feature not in (intake.get("feature_flags") or []):
            fail("ferret intake missing feature flag: %s" % feature)

    if len(kb.get("system_hints") or []) < 7:
        fail("ferret KB should have at least 7 system hints")
    if len(kb.get("red_flags") or []) < 8:
        fail("ferret KB should have at least 8 red flags")
    if len(kb.get("diseases") or []) < 9:
        fail("ferret KB should have at least 9 disease directions")
    if len(kb.get("checks") or []) < 9:
        fail("ferret KB should have at least 9 check directions")
    if len(kb.get("questions") or []) < 8:
        fail("ferret KB should have at least 8 questions")

    section_keys = [str(section.get("key")) for section in intake.get("sections") or [] if isinstance(section, dict)]
    for key in REQUIRED_SECTIONS:
        if key not in section_keys:
            fail("ferret intake missing section: %s" % key)
    if len(section_keys) < 7:
        fail("ferret intake should have at least 7 sections")

    coverage = kb.get("ferret_deepening_v1") or {}
    if coverage.get("mode") != "exotics_ferret_deepening_v1":
        fail("ferret KB missing ferret_deepening_v1 mode")
    if coverage.get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("drug dose must remain not reviewed / not enabled")
    if coverage.get("source_review_status") != "required_not_started":
        fail("source review status must remain required_not_started")

    module = load_helper()
    summary = module.summarize_ferret_deepening(kb, intake)
    if summary.get("status") != "PASS":
        fail("helper summary did not PASS: %s" % summary)
    if summary.get("writes_database") is not False:
        fail("helper must not write database")
    if summary.get("returns_drug_dose") is not False:
        fail("helper must not return drug dose")

    doc = read_text(DOC)
    for needle in ("Exotics Ferret Deepening V1", "no drug dose", "GO_TO_EXOTICS_LAB_IMAGING_INTERPRETATION_READINESS_V1"):
        if needle not in doc:
            fail("doc missing: %s" % needle)

    ci = read_text(CI)
    smoke = read_text(SMOKE)
    if "validate_exotics_ferret_deepening.py" not in ci:
        fail("ci_static_checks missing ferret validator")
    if "Exotics Ferret Deepening V1 validator" not in smoke:
        fail("smoke missing ferret validator block")

    print(json.dumps({
        "mode": summary.get("mode"),
        "status": summary.get("status"),
        "system_hints": summary.get("system_hint_count"),
        "red_flags": summary.get("red_flag_count"),
        "intake_sections": summary.get("intake_section_count"),
        "drug_dose_status": summary.get("drug_dose_status"),
    }, ensure_ascii=False))
    print("VALIDATOR=PASS Exotics Ferret Deepening V1")


if __name__ == "__main__":
    main()
