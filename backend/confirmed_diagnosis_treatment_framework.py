# -*- coding: utf-8 -*-
"""
Confirmed Diagnosis Treatment Framework Draft V1.

This module builds a clinician-facing treatment framework preview only after a
clinician-confirmed diagnosis has been supplied. It is deliberately not a
prescription, not a dose engine, not a route/frequency recommender, not a final
client instruction, and not a database writer.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_MODE = "confirmed_diagnosis_treatment_framework_draft_v1"

_ALLOWED_CONFIRMATION_SOURCES = {
    "clinician",
    "clinician_entered",
    "clinician_confirmed",
}

_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def confirmed_diagnosis_treatment_framework_safety_flags() -> Dict[str, bool]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "writes_case_treatment": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }


def _as_non_empty_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError("confirmed diagnosis by clinician is required" if field_name == "confirmed_diagnosis_label" else "%s is required" % field_name)
    return text


def _parse_case_id(value: Any) -> int:
    if value in (None, ""):
        raise ValueError("case_id is required")
    try:
        case_id = int(value)
    except (TypeError, ValueError):
        raise ValueError("case_id must be an integer")
    if case_id <= 0:
        raise ValueError("case_id must be positive")
    return case_id


def _normalize_confirmation_source(value: Any) -> str:
    source = str(value or "").strip().lower()
    if source not in _ALLOWED_CONFIRMATION_SOURCES:
        raise ValueError("confirmed diagnosis by clinician is required")
    return "clinician_entered" if source == "clinician" else source


def _require_ai_generated_false(payload: Dict[str, Any]) -> bool:
    if "ai_generated" not in payload:
        raise ValueError("ai_generated=false is required for clinician confirmed diagnosis input")
    value = payload.get("ai_generated")
    if value is not False:
        raise ValueError("AI generated diagnosis cannot be used as confirmed diagnosis")
    return False


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for nested in _walk_strings(item):
                yield nested
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            for nested in _walk_strings(item):
                yield nested


def scan_preview_for_forbidden_output(preview: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for text in _walk_strings(preview):
        for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
            if pattern.search(text):
                hits.append(text)
                break
    return hits


def _build_preview() -> Dict[str, Any]:
    preview = {
        "treatment_goals": [
            "stabilize patient status under clinician direction",
            "support comfort, hydration, nutrition, and environment after clinician review",
            "monitor objective response and warning signs for clinician review",
        ],
        "care_priority_hint": "clinician_review_required",
        "supportive_care_categories": [
            "comfort_support_review",
            "hydration_and_nutrition_support_review",
            "environment_and_nursing_care_review",
        ],
        "monitoring_parameters": [
            "vital_signs_trend",
            "hydration_status",
            "appetite_and_intake",
            "pain_or_distress_score",
            "key_lab_or_imaging_abnormalities_for_recheck",
        ],
        "recheck_plan_categories": [
            "short_interval_recheck_if_unstable",
            "diagnostic_recheck_based_on_clinician_plan",
            "client_update_topics_for_clinician_review",
        ],
        "contraindication_checks": [
            "species_age_weight_pregnancy_comorbidity_review",
            "current_medication_interaction_review",
            "organ_function_and_allergy_history_review",
        ],
        "referral_or_hospitalization_triggers": [
            "unstable_vital_signs",
            "worsening_pain_or_distress",
            "inability_to_maintain_hydration_or_nutrition",
            "rapid_progression_or_complications",
        ],
        "procedure_or_surgery_review_points": [
            "confirm whether procedural or surgical evaluation is needed by clinician",
            "confirm anesthesia and peri_procedural risk review when applicable",
        ],
        "nutrition_and_environment_support_points": [
            "clinician_to_review_diet_hydration_temperature_rest_environment_as_applicable",
        ],
        "client_communication_topics_for_clinician_review": [
            "explain_that_the_diagnosis_was_confirmed_by_the_clinician",
            "explain_warning_signs_and_recheck_expectations_after_clinician_approval",
        ],
        "medication_class_review_needed": [
            "clinician_to_evaluate_whether_analgesia_support_is_needed",
            "clinician_to_evaluate_whether_antimicrobial_direction_is_needed",
            "clinician_to_evaluate_whether_fluid_or_nutrition_support_is_needed",
        ],
    }
    forbidden = scan_preview_for_forbidden_output(preview)
    if forbidden:
        raise ValueError("forbidden treatment output detected in framework preview")
    return preview


def build_confirmed_diagnosis_treatment_framework(
    payload: Dict[str, Any],
    *,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be an object")

    case_id = _parse_case_id(payload.get("case_id"))
    label = _as_non_empty_text(payload.get("confirmed_diagnosis_label"), "confirmed_diagnosis_label")
    confirmed_by = _as_non_empty_text(payload.get("confirmed_by"), "confirmed_by")
    confirmation_source = _normalize_confirmation_source(payload.get("confirmation_source"))
    ai_generated = _require_ai_generated_false(payload)

    diagnosis_preview = {"label": label}
    if scan_preview_for_forbidden_output(diagnosis_preview):
        raise ValueError("confirmed diagnosis label cannot contain dose, route, frequency, or prescription wording")

    preview = _build_preview()
    quality_gate = {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
    }
    safety = confirmed_diagnosis_treatment_framework_safety_flags()

    return {
        "message": "confirmed_diagnosis_treatment_framework_built",
        "mode": CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_MODE,
        "case_id": case_id,
        "confirmed_diagnosis": {
            "label": label,
            "confirmed_by": confirmed_by,
            "confirmation_source": confirmation_source,
            "ai_generated": ai_generated,
        },
        "treatment_framework_preview": preview,
        "quality_gate": quality_gate,
        "safety": safety,
        "case_context_used": bool(case_context),
        **safety,
    }
