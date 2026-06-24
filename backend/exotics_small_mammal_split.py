# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

EXOTICS_SMALL_MAMMAL_SPLIT_MODE = "exotics_small_mammal_split_v1"
SMALL_MAMMAL_RULE_KEYS = ["guinea_pig", "hamster", "chinchilla", "rat_mouse", "hedgehog", "sugar_glider"]

ROOT = Path(__file__).resolve().parents[1]
KB_DIR = ROOT / "knowledge-base" / "exotics"
INTAKE_DIR = KB_DIR / "intake"

def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("%s must be a JSON object" % path)
    return data

def small_mammal_split_safety_flags() -> Dict[str, Any]:
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
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

def build_small_mammal_split_review() -> Dict[str, Any]:
    index = _load_json(KB_DIR / "index.json")
    intake_index = _load_json(INTAKE_DIR / "index.json")
    rules = set(index.get("rules") or [])
    templates = set(intake_index.get("templates") or [])
    rows: List[Dict[str, Any]] = []
    for key in SMALL_MAMMAL_RULE_KEYS:
        rule = _load_json(KB_DIR / ("%s.json" % key))
        intake = _load_json(INTAKE_DIR / ("%s.json" % key))
        rows.append({
            "key": key,
            "kb_present": key in rules and rule.get("key") == key,
            "intake_present": key in templates and intake.get("key") == key,
            "red_flag_count": len(rule.get("red_flags") or []),
            "question_count": sum(len(section.get("questions") or []) for section in intake.get("sections") or []),
            "current_level": "small_mammal_split_triage_scaffold_not_comprehensive_clinical_kb",
            "source_review_status": "required_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
        })
    missing = [row["key"] for row in rows if not row["kb_present"] or not row["intake_present"]]
    safety = small_mammal_split_safety_flags()
    return {
        "mode": EXOTICS_SMALL_MAMMAL_SPLIT_MODE,
        "split_keys": SMALL_MAMMAL_RULE_KEYS,
        "rows": rows,
        "missing": missing,
        "quality_gate": {
            "status": "PASS" if not missing else "FAIL",
            "missing_count": len(missing),
            "keeps_generic_rodent_fallback": "rodent" in rules,
            "requires_human_review": True,
            "clinician_signoff_required": True,
            "not_comprehensive_clinical_kb": True,
            "source_review_status": "required_not_started",
            "drug_dose_status": "not_reviewed_not_enabled",
        },
        "safety": safety,
        **safety,
    }
