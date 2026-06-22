# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

DRUG_DOSE_SAFETY_FRAMEWORK_MODE = "drug_dose_safety_framework_v1"

DOSE_TOKEN_RE = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mcg/kg|ug/kg|ml/kg|iu/kg|units/kg|mg|mcg|ug|ml|iu|units)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq|subq)\b)",
    re.IGNORECASE,
)

KNOWN_DRUG_TERMS = (
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


def drug_dose_safety_framework_flags() -> Dict[str, Any]:
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
        "drug_recommendation": False,
        "drug_dose_recommendation": False,
        "dose_calculation": False,
        "dose_calculation_enabled": False,
        "returns_numeric_dose": False,
        "returns_route_frequency": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _number(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _candidate_text(payload: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in (
        "candidate_text",
        "candidate_recommendation",
        "drug_name",
        "medication",
        "dose_expression",
        "route",
        "frequency",
        "duration",
        "clinical_context",
    ):
        value = payload.get(key)
        if isinstance(value, dict):
            value = " ".join(_text(v) for v in value.values())
        text = _text(value)
        if text:
            parts.append(f"{key}: {text}")
    return "\n".join(parts)


def _detect_dose_tokens(text: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for match in DOSE_TOKEN_RE.finditer(text or ""):
        value = match.group(0).strip()
        if value:
            findings.append({
                "type": "dose_route_or_frequency_token",
                "value": value,
                "reason": "numeric dose, route, or frequency output is disabled in Drug Dose Safety Framework V1",
            })
    return _dedupe(findings)


def _detect_drug_terms(text: str) -> List[Dict[str, str]]:
    lowered = (text or "").lower()
    findings: List[Dict[str, str]] = []
    for term in KNOWN_DRUG_TERMS:
        if term in lowered:
            findings.append({
                "type": "drug_name",
                "value": term,
                "reason": "drug-specific recommendation is blocked until a reviewed drug knowledge base and dose policy exist",
            })
    return _dedupe(findings)


def _dedupe(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    seen = set()
    for item in items:
        key = (item.get("type"), str(item.get("value", "")).lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _input_checks(payload: Dict[str, Any], case_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    species = _text(payload.get("species")) or _text((case_context or {}).get("species"))
    weight = _number(payload.get("weight_kg"))
    age_info = _text(payload.get("age_info"))
    renal_flag = bool(payload.get("renal_risk") or payload.get("azotemia") or payload.get("kidney_disease"))
    hepatic_flag = bool(payload.get("hepatic_risk") or payload.get("liver_disease") or payload.get("elevated_liver_enzymes"))
    pregnancy_lactation_unknown = payload.get("pregnant_or_lactating") is None

    missing = []
    if not species:
        missing.append("species")
    if weight is None:
        missing.append("weight_kg")

    return {
        "species_present": bool(species),
        "weight_kg_present": weight is not None,
        "age_info_present": bool(age_info),
        "renal_risk_flag_present": renal_flag,
        "hepatic_risk_flag_present": hepatic_flag,
        "pregnancy_lactation_unknown": pregnancy_lactation_unknown,
        "missing_minimum_inputs": missing,
        "minimum_inputs_complete": not missing,
        "note": "Input checks are for safety gating only; no dose is calculated or returned.",
    }


def build_drug_dose_safety_framework(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Evaluate a candidate drug/dose request against the disabled dose framework.

    This function intentionally does not calculate or return any dose. It is a dry-run
    safety boundary for later clinician-reviewed dose work.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    candidate = _candidate_text(payload)
    dose_tokens = _detect_dose_tokens(candidate)
    drug_terms = _detect_drug_terms(candidate)
    input_checks = _input_checks(payload, case_context)

    prohibited_items = _dedupe(dose_tokens + drug_terms)
    dose_requested = bool(
        prohibited_items
        or _text(payload.get("drug_name"))
        or _text(payload.get("medication"))
        or _text(payload.get("dose_expression"))
    )

    blocked_reasons = ["dose_calculation_disabled_by_default"]
    if prohibited_items:
        blocked_reasons.append("drug_or_dose_content_detected")
    if input_checks["missing_minimum_inputs"]:
        blocked_reasons.append("minimum_inputs_incomplete")

    decision = "blocked_dose_calculation_disabled" if dose_requested else "framework_only_no_dose_request"

    permitted_next_steps = [
        "collect_species_weight_age_and_reproductive_status",
        "collect_current_medications_and_allergies",
        "review_renal_hepatic_hydration_and_lab_context",
        "route_to_clinician_for_manual_drug_and_dose_review",
        "document_that_no_automatic_dose_was_generated",
    ]

    blocked_categories = [
        "numeric_dose_output",
        "mg_per_kg_calculation",
        "route_frequency_duration_instruction",
        "drug_name_recommendation",
        "prescription_write",
        "client_facing_medication_instruction",
        "automatic_treatment_plan",
    ]

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "blocked": True,
        "dose_requested": dose_requested,
        "prohibited_item_count": len(prohibited_items),
        "requires_human_review": True,
        "dose_calculation_enabled": False,
        "blocks_numeric_dose": True,
        "blocks_prescription_write": True,
        "blocks_client_facing_dose_output": True,
    }

    safety = drug_dose_safety_framework_flags()
    return {
        "mode": DRUG_DOSE_SAFETY_FRAMEWORK_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "framework": {
            "decision": decision,
            "blocked": True,
            "blocked_reasons": blocked_reasons,
            "dose_calculation_enabled": False,
            "returns_numeric_dose": False,
            "returns_route_frequency": False,
            "human_review_required": True,
            "clinician_signoff_required": True,
            "not_a_prescription": True,
            "not_a_treatment_plan": True,
            "not_a_drug_dose_recommendation": True,
        },
        "input_checks": input_checks,
        "prohibited_items": prohibited_items,
        "permitted_next_steps": permitted_next_steps,
        "blocked_categories": blocked_categories,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
