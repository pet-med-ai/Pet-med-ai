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
SPLIT_KEYS = ["turtle", "lizard", "snake", "amphibian", "fish"]

DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)


def fail(message: str) -> None:
    print("VALIDATOR=FAIL")
    print(message)
    raise SystemExit(1)


def read_json(rel: str) -> Dict[str, Any]:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        fail("%s must be a JSON object" % rel)
    return data


def read_text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        fail("missing required file: %s" % rel)
    return path.read_text(encoding="utf-8")


def assert_no_dose_text(rel: str, data: Any) -> None:
    text = json.dumps(data, ensure_ascii=False)
    match = DOSE_PATTERN.search(text)
    if match:
        fail("%s contains drug dose/route/frequency marker: %s" % (rel, match.group(0)))


def assert_kb_rule(key: str) -> None:
    rel = "knowledge-base/exotics/%s.json" % key
    data = read_json(rel)
    if data.get("key") != key:
        fail("%s key mismatch" % rel)
    for field in ("label", "summary"):
        if not isinstance(data.get(field), str) or not data.get(field).strip():
            fail("%s missing non-empty %s" % (rel, field))
    for field in ("system_hints", "red_flags", "diseases", "checks", "actions", "questions"):
        if not isinstance(data.get(field), list) or not data.get(field):
            fail("%s missing non-empty list %s" % (rel, field))
    if len(data.get("system_hints") or []) < 3:
        fail("%s must include at least 3 system hints" % rel)
    if len(data.get("red_flags") or []) < 3:
        fail("%s must include at least 3 red flags" % rel)
    for idx, item in enumerate(data.get("system_hints") or [], 1):
        if not isinstance(item, dict) or not item.get("label") or not isinstance(item.get("features"), list) or not item.get("features"):
            fail("%s system_hints[%d] invalid" % (rel, idx))
    for idx, item in enumerate(data.get("red_flags") or [], 1):
        if not isinstance(item, dict) or item.get("level") not in ("高", "中", "低") or not isinstance(item.get("features"), list) or not item.get("reason"):
            fail("%s red_flags[%d] invalid" % (rel, idx))
    assert_no_dose_text(rel, data)


def assert_intake_template(key: str) -> None:
    rel = "knowledge-base/exotics/intake/%s.json" % key
    data = read_json(rel)
    if data.get("key") != key:
        fail("%s key mismatch" % rel)
    for field in ("label", "summary"):
        if not isinstance(data.get(field), str) or not data.get(field).strip():
            fail("%s missing non-empty %s" % (rel, field))
    if not isinstance(data.get("species_scope"), list) or not data.get("species_scope"):
        fail("%s species_scope missing" % rel)
    if not isinstance(data.get("feature_flags"), list):
        fail("%s feature_flags must be list" % rel)
    if not isinstance(data.get("red_flag_prompts"), list) or not data.get("red_flag_prompts"):
        fail("%s red_flag_prompts missing" % rel)
    sections = data.get("sections")
    if not isinstance(sections, list) or len(sections) < 3:
        fail("%s must include at least 3 sections" % rel)
    question_count = 0
    for section in sections:
        if not isinstance(section, dict):
            fail("%s section invalid" % rel)
        for field in ("key", "title", "priority"):
            if not isinstance(section.get(field), str) or not section.get(field).strip():
                fail("%s section missing %s" % (rel, field))
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            fail("%s section questions missing" % rel)
        for question in questions:
            question_count += 1
            for field in ("key", "label", "answer_type"):
                if not isinstance(question.get(field), str) or not question.get(field).strip():
                    fail("%s question missing %s" % (rel, field))
            if "required" in question and not isinstance(question.get("required"), bool):
                fail("%s question.required must be bool" % rel)
    if question_count < 8:
        fail("%s must include at least 8 questions" % rel)
    assert_no_dose_text(rel, data)


def load_helper():
    path = ROOT / "backend" / "exotics_reptile_split.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_reptile_split", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load exotics_reptile_split helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def main() -> None:
    for rel in (
        "knowledge-base/exotics/index.json",
        "knowledge-base/exotics/intake/index.json",
        "backend/exotics_reptile_split.py",
        "docs/clinical_data/EXOTICS_REPTILE_SPLIT_V1.md",
        "docs/clinical_data/EXOTICS_REPTILE_SPLIT_CHECKLIST_V1.csv",
        "docs/clinical_data/EXOTICS_REPTILE_SPLIT_GO_NO_GO_V1.csv",
        "scripts/validate_exotics_reptile_split.py",
    ):
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    index = read_json("knowledge-base/exotics/index.json")
    rules = index.get("rules") or []
    for key in SPLIT_KEYS:
        if key not in rules:
            fail("index rules missing split key: %s" % key)

    species_map = index.get("species_to_rule") or {}
    for species, expected in {
        "turtle": "turtle",
        "tortoise": "turtle",
        "lizard": "lizard",
        "snake": "snake",
        "amphibian": "amphibian",
        "fish": "fish",
    }.items():
        if species_map.get(species) != expected:
            fail("species_to_rule.%s expected %s got %r" % (species, expected, species_map.get(species)))

    group_map = index.get("group_to_rule") or {}
    for group, expected in {
        "turtle": "turtle",
        "lizard": "lizard",
        "snake": "snake",
        "amphibian": "amphibian",
        "fish": "fish",
    }.items():
        if group_map.get(group) != expected:
            fail("group_to_rule.%s expected %s got %r" % (group, expected, group_map.get(group)))

    intake_index = read_json("knowledge-base/exotics/intake/index.json")
    templates = intake_index.get("templates") or []
    for key in SPLIT_KEYS:
        if key not in templates:
            fail("intake templates missing split key: %s" % key)
        assert_kb_rule(key)
        assert_intake_template(key)

    helper = load_helper()
    review = helper.build_exotics_reptile_split_review()
    if review.get("mode") != "exotics_reptile_split_v1":
        fail("helper mode mismatch")
    if review.get("writes_database") is not False:
        fail("helper must remain read-only")
    if review.get("returns_drug_dose") is not False:
        fail("helper must not return drug dose")
    if review.get("quality_gate", {}).get("status") != "PASS":
        fail("helper quality gate should PASS")

    ci = read_text("scripts/ci_static_checks.sh")
    if "Exotics Reptile Split V1 static checks" not in ci or "validate_exotics_reptile_split.py" not in ci:
        fail("ci_static_checks missing Exotics Reptile Split V1 block")
    smoke = read_text("scripts/smoke_petmed.sh")
    if "Exotics Reptile Split V1 smoke" not in smoke or "validate_exotics_reptile_split.py" not in smoke:
        fail("smoke missing Exotics Reptile Split V1 block")

    print("VALIDATOR=PASS Exotics Reptile Split V1")


if __name__ == "__main__":
    main()
