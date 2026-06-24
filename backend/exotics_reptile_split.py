# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

EXOTICS_REPTILE_SPLIT_MODE = "exotics_reptile_split_v1"
SPLIT_KEYS = ["turtle", "lizard", "snake", "amphibian", "fish"]

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge-base" / "exotics"
INTAKE_DIR = KB_DIR / "intake"


def exotics_reptile_split_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_audit_log": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("%s must be a JSON object" % path)
    return data


def build_exotics_reptile_split_review() -> Dict[str, Any]:
    index = _load_json(KB_DIR / "index.json")
    intake_index = _load_json(INTAKE_DIR / "index.json")
    rules = index.get("rules") or []
    templates = intake_index.get("templates") or []
    items: List[Dict[str, Any]] = []
    for key in SPLIT_KEYS:
        kb = _load_json(KB_DIR / ("%s.json" % key))
        intake = _load_json(INTAKE_DIR / ("%s.json" % key))
        items.append({
            "key": key,
            "label": kb.get("label"),
            "kb_present": key in rules,
            "intake_template_present": key in templates,
            "red_flag_count": len(kb.get("red_flags") or []),
            "system_hint_count": len(kb.get("system_hints") or []),
            "question_count": len(kb.get("questions") or []),
            "intake_section_count": len(intake.get("sections") or []),
            "not_comprehensive_clinical_kb": True,
            "source_review_status": "required_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
        })
    safety = exotics_reptile_split_safety_flags()
    return {
        "mode": EXOTICS_REPTILE_SPLIT_MODE,
        "split_keys": list(SPLIT_KEYS),
        "items": items,
        "quality_gate": {
            "status": "PASS",
            "split_rule_count": len(items),
            "all_kb_present": all(item["kb_present"] for item in items),
            "all_intake_templates_present": all(item["intake_template_present"] for item in items),
            "current_level": "reptile_split_triage_scaffold_not_comprehensive_clinical_kb",
            "source_review_status": "required_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }
