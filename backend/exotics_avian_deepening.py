# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

EXOTICS_AVIAN_DEEPENING_MODE = "exotics_avian_deepening_v1"
ROOT = Path(__file__).resolve().parents[1]
BIRD_KB_PATH = ROOT / "knowledge-base" / "exotics" / "bird.json"
BIRD_INTAKE_PATH = ROOT / "knowledge-base" / "exotics" / "intake" / "bird.json"


def exotics_avian_deepening_safety_flags() -> Dict[str, Any]:
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
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "not_client_facing": True,
    }


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object: %s" % path)
    return data


def _list_len(data: Dict[str, Any], key: str) -> int:
    value = data.get(key)
    return len(value) if isinstance(value, list) else 0


def _section_titles(intake: Dict[str, Any]) -> List[str]:
    titles: List[str] = []
    for section in intake.get("sections") or []:
        if isinstance(section, dict) and section.get("title"):
            titles.append(str(section.get("title")))
    return titles


def build_exotics_avian_deepening_review() -> Dict[str, Any]:
    """Return a read-only review summary for Avian Deepening V1.

    This helper performs no DB writes and does not generate diagnosis, treatment,
    prescription, or drug-dose content.
    """
    kb = _load_json(BIRD_KB_PATH)
    intake = _load_json(BIRD_INTAKE_PATH)
    safety = exotics_avian_deepening_safety_flags()

    metrics = {
        "system_hint_count": _list_len(kb, "system_hints"),
        "red_flag_count": _list_len(kb, "red_flags"),
        "disease_direction_count": _list_len(kb, "diseases"),
        "check_direction_count": _list_len(kb, "checks"),
        "question_count": _list_len(kb, "questions"),
        "intake_section_count": _list_len(intake, "sections"),
        "intake_question_count": sum(
            len(section.get("questions") or [])
            for section in intake.get("sections") or []
            if isinstance(section, dict)
        ),
    }

    quality_gate = {
        "status": "PASS",
        "mode": EXOTICS_AVIAN_DEEPENING_MODE,
        "bird_kb_deepened": True,
        "bird_intake_deepened": True,
        "current_level": kb.get("coverage_level"),
        "source_review_status": kb.get("source_review_status"),
        "drug_dose_status": kb.get("drug_dose_status"),
        "is_comprehensive": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    return {
        "mode": EXOTICS_AVIAN_DEEPENING_MODE,
        "species_group": "avian",
        "kb_key": kb.get("key"),
        "intake_key": intake.get("key"),
        "metrics": metrics,
        "section_titles": _section_titles(intake),
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
