#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import py_compile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "knowledge-base/exotics/bird.json",
    "knowledge-base/exotics/intake/bird.json",
    "backend/exotics_avian_deepening.py",
    "docs/clinical_data/EXOTICS_AVIAN_DEEPENING_V1.md",
    "docs/clinical_data/EXOTICS_AVIAN_DEEPENING_CHECKLIST_V1.csv",
    "docs/clinical_data/EXOTICS_AVIAN_DEEPENING_GO_NO_GO_V1.csv",
    "scripts/validate_exotics_avian_deepening.py",
    "scripts/ci_static_checks.sh",
    "scripts/smoke_petmed.sh",
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


def load_json(rel: str) -> Dict[str, Any]:
    data = json.loads(read(rel))
    if not isinstance(data, dict):
        fail("%s must be a JSON object" % rel)
    return data


def require_list(data: Dict[str, Any], key: str, min_len: int, rel: str) -> List[Any]:
    value = data.get(key)
    if not isinstance(value, list) or len(value) < min_len:
        fail("%s.%s must be a list with at least %d items" % (rel, key, min_len))
    return value


def require_texts(blob: str, needles: List[str], label: str) -> None:
    for needle in needles:
        if needle not in blob:
            fail("%s missing expected text: %s" % (label, needle))


def load_helper():
    path = ROOT / "backend" / "exotics_avian_deepening.py"
    py_compile.compile(str(path), doraise=True)
    spec = importlib.util.spec_from_file_location("exotics_avian_deepening", str(path))
    if spec is None or spec.loader is None:
        fail("unable to load backend/exotics_avian_deepening.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def main() -> None:
    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if not path.exists():
            fail("missing required file: %s" % rel)
        if path.suffix == ".py":
            py_compile.compile(str(path), doraise=True)

    kb = load_json("knowledge-base/exotics/bird.json")
    intake = load_json("knowledge-base/exotics/intake/bird.json")

    if kb.get("key") != "bird":
        fail("bird KB key mismatch")
    if intake.get("key") != "bird":
        fail("bird intake key mismatch")
    if kb.get("coverage_level") != "avian_deepened_triage_scaffold_not_comprehensive_clinical_kb":
        fail("bird KB coverage_level mismatch")
    if kb.get("source_review_status") != "required_not_started":
        fail("bird source_review_status must remain required_not_started")
    if kb.get("drug_dose_status") != "not_reviewed_not_enabled":
        fail("bird drug_dose_status must remain not_reviewed_not_enabled")

    require_list(kb, "system_hints", 8, "bird.json")
    require_list(kb, "red_flags", 8, "bird.json")
    require_list(kb, "diseases", 10, "bird.json")
    require_list(kb, "checks", 10, "bird.json")
    require_list(kb, "actions", 4, "bird.json")
    require_list(kb, "questions", 10, "bird.json")
    require_list(kb, "review_gaps", 3, "bird.json")

    kb_blob = json.dumps(kb, ensure_ascii=False)
    require_texts(
        kb_blob,
        [
            "低应激",
            "粪便三联",
            "嗉囊",
            "蛋滞留",
            "PTFE",
            "出血",
            "创伤",
            "检疫",
            "气囊",
            "not_reviewed_not_enabled",
        ],
        "bird KB",
    )

    sections = intake.get("sections")
    if not isinstance(sections, list) or len(sections) < 7:
        fail("bird intake must have at least 7 sections")
    question_count = 0
    required_count = 0
    for section in sections:
        if not isinstance(section, dict):
            fail("bird intake section must be object")
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            fail("bird intake section questions must be non-empty")
        question_count += len(questions)
        required_count += sum(1 for item in questions if isinstance(item, dict) and item.get("required") is True)
    if question_count < 20:
        fail("bird intake should have at least 20 questions")
    if required_count < 8:
        fail("bird intake should have at least 8 required questions")

    intake_blob = json.dumps(intake, ensure_ascii=False)
    require_texts(
        intake_blob,
        [
            "呼吸急症红旗",
            "粪便三联",
            "嗉囊",
            "繁殖 / 蛋滞留风险",
            "神经 / 创伤 / 中毒暴露",
            "笼舍 / 环境 / 检疫",
            "PTFE",
            "药物剂量",
        ],
        "bird intake",
    )

    helper = load_helper()
    review = helper.build_exotics_avian_deepening_review()
    if review.get("mode") != "exotics_avian_deepening_v1":
        fail("helper mode mismatch")
    if review.get("writes_database") is not False:
        fail("helper must not write database")
    if review.get("returns_drug_dose") is not False:
        fail("helper must not return drug dose")
    if review.get("requires_human_review") is not True:
        fail("helper must require human review")
    if review.get("quality_gate", {}).get("status") != "PASS":
        fail("helper quality gate must PASS")
    if review.get("quality_gate", {}).get("is_comprehensive") is not False:
        fail("helper must mark KB not comprehensive")

    doc = read("docs/clinical_data/EXOTICS_AVIAN_DEEPENING_V1.md")
    require_texts(
        doc,
        [
            "Exotics Avian Deepening V1",
            "avian_deepened_triage_scaffold_not_comprehensive_clinical_kb",
            "source_review_status=required_not_started",
            "drug_dose_status=not_reviewed_not_enabled",
            "GO_TO_EXOTICS_REPTILE_SPLIT_V1",
        ],
        "doc",
    )

    ci = read("scripts/ci_static_checks.sh")
    smoke = read("scripts/smoke_petmed.sh")
    if "validate_exotics_avian_deepening.py" not in ci:
        fail("ci_static_checks missing avian deepening validator")
    if "Exotics Avian Deepening V1" not in smoke:
        fail("smoke missing Exotics Avian Deepening V1 block")

    print("VALIDATOR=PASS Exotics Avian Deepening V1")


if __name__ == "__main__":
    main()
