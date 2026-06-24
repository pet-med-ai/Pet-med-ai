# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_FERRET_DEEPENING_MODE = "exotics_ferret_deepening_v1"

REQUIRED_KB_TERMS = [
    "低血糖", "胰岛素瘤", "胃肠异物", "部分梗阻", "腹泻脱水",
    "肾上腺", "排尿困难", "呼吸困难", "肿块", "外伤", "神经异常",
]

REQUIRED_INTAKE_SECTIONS = [
    "signalment",
    "weakness_hypoglycemia",
    "foreign_body_gi",
    "diarrhea_dehydration",
    "urinary_reproductive_endocrine",
    "respiratory_exposure",
    "mass_neuro_trauma",
]


def exotics_ferret_deepening_safety_flags() -> Dict[str, Any]:
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
        "creates_audit_log": False,
        "writes_audit_log": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "not_client_facing": True,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _contains_term(payload: Any, term: str) -> bool:
    if isinstance(payload, dict):
        return any(_contains_term(value, term) for value in payload.values())
    if isinstance(payload, list):
        return any(_contains_term(value, term) for value in payload)
    return term in str(payload or "")


def _section_keys(intake_template: Dict[str, Any]) -> List[str]:
    return [str(section.get("key")) for section in intake_template.get("sections", []) if isinstance(section, dict)]


def summarize_ferret_deepening(ferret_kb: Dict[str, Any], ferret_intake: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(ferret_kb, dict) or ferret_kb.get("key") != "ferret":
        raise ValueError("ferret_kb must be the ferret rule object")
    if not isinstance(ferret_intake, dict) or ferret_intake.get("key") != "ferret":
        raise ValueError("ferret_intake must be the ferret intake template object")

    missing_terms = [term for term in REQUIRED_KB_TERMS if not _contains_term(ferret_kb, term)]
    section_keys = _section_keys(ferret_intake)
    missing_sections = [key for key in REQUIRED_INTAKE_SECTIONS if key not in section_keys]
    safety = exotics_ferret_deepening_safety_flags()
    status = "PASS" if not missing_terms and not missing_sections else "REVIEW"

    return {
        "mode": EXOTICS_FERRET_DEEPENING_MODE,
        "status": status,
        "kb_key": ferret_kb.get("key"),
        "system_hint_count": len(ferret_kb.get("system_hints") or []),
        "red_flag_count": len(ferret_kb.get("red_flags") or []),
        "disease_direction_count": len(ferret_kb.get("diseases") or []),
        "check_direction_count": len(ferret_kb.get("checks") or []),
        "question_count": len(ferret_kb.get("questions") or []),
        "intake_section_count": len(section_keys),
        "missing_terms": missing_terms,
        "missing_intake_sections": missing_sections,
        "current_level": "ferret_deepened_triage_scaffold_not_comprehensive_clinical_kb",
        "source_review_status": "required_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "quality_gate": {
            "status": status,
            "not_comprehensive_clinical_kb": True,
            "requires_source_review": True,
            "blocks_drug_dose": True,
            "requires_human_review": True,
        },
        "safety": safety,
        **safety,
    }
