#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import py_compile
import re
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
MODE = "exotics_small_mammal_split_v1"
RULE_KEYS = ["guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider"]
KB_DIR = ROOT / "knowledge-base" / "exotics"
INTAKE_DIR = KB_DIR / "intake"

FORBIDDEN_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b", re.I),
    re.compile(r"\b(?:sid|bid|tid|qid|q\d{1,2}h|po|iv|im|sc|sq)\b", re.I),
]
FORBIDDEN_KEYS = {
    "final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis", "diagnostic_conclusion",
    "treatment_plan", "prescription", "drug_dose", "drug_route", "drug_frequency",
    "dose", "route", "frequency",
}

def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)

def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        fail("missing file: %s" % path.relative_to(ROOT))
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        fail("%s must be a JSON object" % path.relative_to(ROOT))
    return data

def scan_forbidden(value: Any, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_").replace(" ", "_")
            if normalized in FORBIDDEN_KEYS:
                fail("forbidden key %s in %s" % (key, path or "$"))
            scan_forbidden(child, "%s.%s" % (path, key) if path else str(key))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            scan_forbidden(child, "%s.%d" % (path, idx))
    elif isinstance(value, str):
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.search(value):
                fail("forbidden dose/route/frequency pattern in %s: %r" % (path, value[:120]))

def require_string_list(data: Dict[str, Any], key: str, label: str) -> None:
    value = data.get(key)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        fail("%s.%s must be a non-empty string list" % (label, key))

def validate_rule(key: str) -> None:
    data = read_json(KB_DIR / ("%s.json" % key))
    if data.get("key") != key:
        fail("%s key mismatch" % key)
    if not data.get("label") or not data.get("summary"):
        fail("%s missing label or summary" % key)
    system_hints = data.get("system_hints")
    if not isinstance(system_hints, list) or len(system_hints) < 4:
        fail("%s must have at least 4 system hints" % key)
    red_flags = data.get("red_flags")
    if not isinstance(red_flags, list) or len(red_flags) < 4:
        fail("%s must have at least 4 red flags" % key)
    for idx, item in enumerate(red_flags):
        if item.get("level") not in ("高", "中", "低"):
            fail("%s red_flags[%d] level invalid" % (key, idx))
        require_string_list(item, "features", "%s.red_flags[%d]" % (key, idx))
        if not isinstance(item.get("reason"), str) or not item["reason"].strip():
            fail("%s red_flags[%d] reason missing" % (key, idx))
    for field in ("diseases", "checks", "actions", "questions"):
        require_string_list(data, field, key)
    scan_forbidden(data)

def validate_intake(key: str) -> None:
    data = read_json(INTAKE_DIR / ("%s.json" % key))
    if data.get("key") != key:
        fail("%s intake key mismatch" % key)
    require_string_list(data, "species_scope", "%s.intake" % key)
    require_string_list(data, "feature_flags", "%s.intake" % key)
    sections = data.get("sections")
    if not isinstance(sections, list) or len(sections) < 3:
        fail("%s intake must have at least 3 sections" % key)
    question_count = 0
    for section in sections:
        if not isinstance(section, dict):
            fail("%s intake section invalid" % key)
        for field in ("key", "title", "priority"):
            if not isinstance(section.get(field), str) or not section[field].strip():
                fail("%s intake section missing %s" % (key, field))
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            fail("%s intake section has no questions" % key)
        question_count += len(questions)
        for question in questions:
            for field in ("key", "label", "answer_type"):
                if not isinstance(question.get(field), str) or not question[field].strip():
                    fail("%s intake question missing %s" % (key, field))
            if "required" in question and not isinstance(question.get("required"), bool):
                fail("%s intake question required must be bool" % key)
    if question_count < 8:
        fail("%s intake should have at least 8 questions" % key)
    scan_forbidden(data)

def load_helper():
    path = ROOT / "backend" / "exotics_small_mammal_split.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_small_mammal_split", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module

def main() -> None:
    required = [
        "backend/exotics_small_mammal_split.py",
        "docs/clinical_data/EXOTICS_SMALL_MAMMAL_SPLIT_V1.md",
        "docs/clinical_data/EXOTICS_SMALL_MAMMAL_SPLIT_CHECKLIST_V1.csv",
        "docs/clinical_data/EXOTICS_SMALL_MAMMAL_SPLIT_GO_NO_GO_V1.csv",
        "scripts/validate_exotics_small_mammal_split.py",
    ]
    for rel in required:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    index = read_json(KB_DIR / "index.json")
    intake_index = read_json(INTAKE_DIR / "index.json")
    rules = index.get("rules") or []
    templates = intake_index.get("templates") or []
    for key in RULE_KEYS:
        if key not in rules:
            fail("missing KB rule in index: %s" % key)
        if key not in templates:
            fail("missing intake template in index: %s" % key)
    if "rodent" not in rules:
        fail("generic rodent fallback must remain")
    if index.get("small_mammal_split_v1", {}).get("mode") != MODE:
        fail("index small_mammal_split_v1 metadata missing")

    species_map = index.get("species_to_rule") or {}
    expected_species = {
        "guinea_pig": "guinea_pig", "hamster": "hamster", "chinchilla": "chinchilla",
        "rat": "rat_mouse", "mouse": "rat_mouse", "hedgehog": "hedgehog", "sugar_glider": "sugar_glider",
    }
    for species, key in expected_species.items():
        if species_map.get(species) != key:
            fail("species_to_rule.%s expected %s got %r" % (species, key, species_map.get(species)))

    group_map = index.get("group_to_rule") or {}
    if group_map.get("insectivore") != "hedgehog":
        fail("insectivore should map to hedgehog")
    if group_map.get("marsupial") != "sugar_glider":
        fail("marsupial should map to sugar_glider")
    if group_map.get("rodent") != "rodent":
        fail("rodent group fallback should remain rodent")

    for key in RULE_KEYS:
        validate_rule(key)
        validate_intake(key)

    helper = load_helper()
    review = helper.build_small_mammal_split_review()
    if review.get("quality_gate", {}).get("status") != "PASS":
        fail("backend helper quality gate did not PASS")
    if review.get("writes_database") is not False:
        fail("backend helper must be read-only")
    if review.get("returns_drug_dose") is not False:
        fail("backend helper must not return drug dose")
    if review.get("requires_human_review") is not True:
        fail("backend helper requires_human_review must be true")

    ci = (ROOT / "scripts" / "ci_static_checks.sh").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts" / "smoke_petmed.sh").read_text(encoding="utf-8")
    if "validate_exotics_small_mammal_split.py" not in ci:
        fail("ci_static_checks missing small mammal split validator")
    if "Exotics Small Mammal Split V1 validator" not in smoke:
        fail("smoke missing small mammal split validator block")

    print("VALIDATOR=PASS Exotics Small Mammal Split V1")

if __name__ == "__main__":
    main()
