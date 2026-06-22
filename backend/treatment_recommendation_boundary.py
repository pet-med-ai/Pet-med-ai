# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

TREATMENT_RECOMMENDATION_BOUNDARY_MODE = "treatment_recommendation_boundary_v1"

DOSE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)

DRUG_TERMS = (
    "maropitant",
    "ondansetron",
    "metoclopramide",
    "omeprazole",
    "famotidine",
    "prednisone",
    "prednisolone",
    "dexamethasone",
    "meloxicam",
    "carprofen",
    "robenacoxib",
    "amoxicillin",
    "clavulanate",
    "cefovecin",
    "enrofloxacin",
    "furosemide",
    "insulin",
    "gabapentin",
    "buprenorphine",
)

PROHIBITED_ACTION_TERMS = (
    "prescribe",
    "administer",
    "give ",
    "start ",
    "dispense",
    "dose",
    "dosage",
    "rx",
    "inject",
    "injection",
    "tablet",
    "capsule",
    "syrup",
    "infusion",
    "anesthesia protocol",
    "sedation protocol",
)


def treatment_boundary_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "creates_treatment_plan": False,
        "treatment_recommendation": False,
        "drug_dose_recommendation": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _collect_source_notes(payload: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    for key in ("source_summary", "lab_summary", "imaging_summary", "case_summary", "clinical_context"):
        value = payload.get(key)
        if isinstance(value, dict):
            for subkey in ("headline", "summary", "impression", "overall_status"):
                text = _text(value.get(subkey))
                if text:
                    notes.append(f"{key}.{subkey}: {text}")
        else:
            text = _text(value)
            if text:
                notes.append(f"{key}: {text}")
    return notes[:20]


def _candidate_text(payload: Dict[str, Any]) -> str:
    for key in ("candidate_recommendation", "candidate_text", "recommendation", "text"):
        text = _text(payload.get(key))
        if text:
            return text
    return ""


def _detect_prohibited_items(text: str) -> List[Dict[str, str]]:
    lowered = text.lower()
    prohibited: List[Dict[str, str]] = []

    for match in DOSE_PATTERN.finditer(text):
        item = match.group(0).strip()
        if item:
            prohibited.append({
                "type": "dose_or_route_pattern",
                "value": item,
                "reason": "drug dose, route, or frequency content is outside Treatment Recommendation Boundary V1",
            })

    for term in DRUG_TERMS:
        if term in lowered:
            prohibited.append({
                "type": "drug_name",
                "value": term,
                "reason": "drug-specific recommendations are blocked until Drug Dose Safety Framework V1",
            })

    for term in PROHIBITED_ACTION_TERMS:
        if term in lowered:
            prohibited.append({
                "type": "treatment_action",
                "value": term.strip(),
                "reason": "prescriptive treatment actions are not enabled in this boundary stage",
            })

    dedup: List[Dict[str, str]] = []
    seen = set()
    for item in prohibited:
        key = (item["type"], item["value"].lower())
        if key not in seen:
            seen.add(key)
            dedup.append(item)
    return dedup


def build_treatment_recommendation_boundary(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate whether a proposed text stays inside the treatment-boundary stage.

    This function is deliberately not a treatment recommendation engine. It does not
    produce prescriptions, drug doses, protocols, or treatment plans. It only returns
    boundary status and allowed clinician-review next-step categories.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    candidate = _candidate_text(payload)
    prohibited_items = _detect_prohibited_items(candidate)

    if prohibited_items:
        decision = "blocked_drug_or_dose"
        blocked = True
    elif candidate:
        decision = "review_only"
        blocked = False
    else:
        decision = "boundary_only_no_candidate"
        blocked = False

    allowed_review_actions = [
        "summarize_problem_list_for_clinician_review",
        "recommend_clinician_review_of_lab_and_imaging_abnormalities",
        "suggest_diagnostic_follow_up_categories_without_orders",
        "suggest_monitoring_and_recheck_considerations_without_protocols",
        "flag_emergency_or_referral_consideration_without_treatment_plan",
        "prepare_client_communication_talking_points_without_medication_instructions",
    ]

    blocked_categories = [
        "drug_name_recommendation",
        "drug_dose_recommendation",
        "route_or_frequency_instruction",
        "prescription_write",
        "anesthesia_or_sedation_protocol",
        "automatic_treatment_plan",
        "external_message_delivery",
    ]

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "blocked": blocked,
        "prohibited_item_count": len(prohibited_items),
        "requires_human_review": True,
        "blocks_auto_treatment": True,
        "blocks_drug_dose_recommendation": True,
        "blocks_prescription_write": True,
    }

    safety = treatment_boundary_safety_flags()
    return {
        "mode": TREATMENT_RECOMMENDATION_BOUNDARY_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "candidate_text_present": bool(candidate),
        "source_notes": _collect_source_notes(payload),
        "boundary": {
            "decision": decision,
            "blocked": blocked,
            "human_review_required": True,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_a_drug_dose_recommendation": True,
            "boundary_only": True,
        },
        "prohibited_items": prohibited_items,
        "allowed_review_actions": allowed_review_actions,
        "blocked_categories": blocked_categories,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
