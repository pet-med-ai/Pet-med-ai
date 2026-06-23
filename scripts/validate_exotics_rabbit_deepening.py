#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "knowledge-base/exotics/rabbit.json",
    "knowledge-base/exotics/intake/rabbit.json",
    "backend/exotics_rabbit_deepening.py",
    "docs/clinical_data/EXOTICS_RABBIT_DEEPENING_V1.md",
    "docs/clinical_data/EXOTICS_RABBIT_DEEPENING_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_RABBIT_DEEPENING_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_rabbit_deepening.py",
]

REQUIRED_DOMAINS = [
    "胃肠淤滞/梗阻",
    "牙科/口腔疼痛",
    "呼吸系统",
    "泌尿/肾脏/生殖",
    "神经/头斜",
    "足底皮炎/皮肤",
    "饲养/饮食/环境",
    "急症/全身状态",
]

FORBIDDEN_PATTERNS = [
    r"\\bmg/kg\\b",
    r"\\bmcg/kg\\b",
    r"\\bml/kg\\b",
    r"\\bq\\d{1,2}h\\b",
    r"\\bSID\\b",
    r"\\bBID\\b",
    r"\\bTID\\b",
    r"\\bQID\\b",
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


def load_json(rel: str):
    return json.loads(read(rel))


def assert_kb() -> None:
    kb = load_json("knowledge-base/exotics/rabbit.json")
    if kb.get("key") != "rabbit":
        fail("rabbit KB key mismatch")
    if kb.get("coverage_version") != "rabbit-deepening-v1":
        fail("rabbit KB coverage_version mismatch")
    if kb.get("source_review_status") != "required_not_started":
        fail("source_review_status must remain required_not_started")
    if kb.get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("drug_dose_status must remain not_reviewed_not_enabled")
    if kb.get("requires_human_review") is not True:
        fail("requires_human_review must be true")
    if kb.get("not_a_diagnosis") is not True:
        fail("not_a_diagnosis must be true")

    domains = kb.get("coverage_domains") or []
    for domain in REQUIRED_DOMAINS:
        if domain not in domains:
            fail("rabbit KB missing coverage domain: %s" % domain)

    minimums = {
        "system_hints": 8,
        "red_flags": 8,
        "diseases": 12,
        "checks": 12,
        "actions": 4,
        "questions": 10,
        "differential_categories": 5,
    }
    for key, minimum in minimums.items():
        value = kb.get(key)
        if not isinstance(value, list) or len(value) < minimum:
            fail("rabbit KB %s must contain at least %d items" % (key, minimum))

    text = json.dumps(kb, ensure_ascii=False)
    required_phrases = [
        "胃肠淤滞", "梗阻", "牙科", "臼齿", "呼吸困难",
        "尿泥", "未绝育母兔", "头斜", "足底皮炎", "干草",
    ]
    for phrase in required_phrases:
        if phrase not in text:
            fail("rabbit KB missing phrase: %s" % phrase)

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            fail("rabbit KB must not contain dose/frequency pattern: %s" % pattern)


def assert_intake() -> None:
    intake = load_json("knowledge-base/exotics/intake/rabbit.json")
    if intake.get("key") != "rabbit":
        fail("rabbit intake key mismatch")
    if intake.get("version") != "rabbit-deepening-v1":
        fail("rabbit intake version mismatch")

    sections = intake.get("sections") or []
    if not isinstance(sections, list) or len(sections) < 8:
        fail("rabbit intake must contain at least 8 sections")

    section_keys = {section.get("key") for section in sections if isinstance(section, dict)}
    required = {
        "signalment",
        "food_feces_urine",
        "pain_abdomen",
        "dental_oral",
        "respiratory",
        "urinary_reproductive",
        "neuro_eye_ear",
        "husbandry_diet_environment",
    }
    missing = sorted(required - section_keys)
    if missing:
        fail("rabbit intake missing sections: %s" % ", ".join(missing))

    question_count = 0
    required_count = 0
    for section in sections:
        questions = section.get("questions") or []
        question_count += len(questions)
        required_count += sum(1 for item in questions if item.get("required") is True)

    if question_count < 18:
        fail("rabbit intake question count too low")
    if required_count < 10:
        fail("rabbit intake required question count too low")

    feature_flags = intake.get("feature_flags") or []
    for feature in ("urinary_issue", "reproductive_issue", "head_tilt", "pododermatitis", "hypothermia_signs"):
        if feature not in feature_flags:
            fail("rabbit intake missing feature flag: %s" % feature)


def assert_helper() -> None:
    path = ROOT / "backend" / "exotics_rabbit_deepening.py"
    spec = importlib.util.spec_from_file_location("exotics_rabbit_deepening", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load exotics_rabbit_deepening")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    review = module.build_rabbit_deepening_review()
    if review.get("mode") != "exotics_rabbit_deepening_v1":
        fail("helper mode mismatch")
    if review.get("writes_database") is not False:
        fail("helper must not write database")
    if review.get("returns_drug_dose") is not False:
        fail("helper must not return drug dose")
    if review.get("quality_gate", {}).get("status") != "PASS":
        fail("helper quality gate must PASS")
    if review.get("quality_gate", {}).get("is_comprehensive") is not False:
        fail("helper must mark KB as not comprehensive")


def assert_docs_and_hooks() -> None:
    doc = read("docs/clinical_data/EXOTICS_RABBIT_DEEPENING_V1.md")
    for needle in (
        "Exotics Rabbit Deepening V1",
        "rabbit_deepened_triage_scaffold_not_comprehensive_clinical_kb",
        "drug_dose_status=not_reviewed_not_enabled",
        "GO_TO_EXOTICS_AVIAN_DEEPENING_V1",
    ):
        if needle not in doc:
            fail("doc missing: %s" % needle)

    ci = read("scripts/ci_static_checks.sh")
    if "Exotics Rabbit Deepening V1 static checks" not in ci:
        fail("ci_static_checks missing Exotics Rabbit Deepening V1 block")
    if "python3 scripts/validate_exotics_rabbit_deepening.py" not in ci:
        fail("ci_static_checks missing validator command")

    smoke = read("scripts/smoke_petmed.sh")
    if "Exotics Rabbit Deepening V1 smoke" not in smoke:
        fail("smoke missing Exotics Rabbit Deepening V1 block")
    if "validate_exotics_rabbit_deepening.py" not in smoke:
        fail("smoke missing validator command")


def main() -> None:
    for rel in REQUIRED_FILES:
        read(rel)
    assert_kb()
    assert_intake()
    assert_helper()
    assert_docs_and_hooks()
    print("VALIDATOR=PASS Exotics Rabbit Deepening V1")


if __name__ == "__main__":
    main()
