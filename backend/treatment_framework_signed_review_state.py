# -*- coding: utf-8 -*-
"""
Treatment Framework Signed Review State Dry Run V1.

Builds a clinician-facing signed review state preview for a previously generated
confirmed-diagnosis treatment framework. This is deliberately dry-run only:
no database write, no Case treatment field write, no prescription, no drug dose,
no route/frequency recommendation, and no client-facing release.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_MODE = "treatment_framework_signed_review_state_dry_run_v1"

_ALLOWED_CONFIRMATION_SOURCES = {
    "clinician",
    "clinician_entered",
    "clinician_confirmed",
}

_ALLOWED_SIGNOFF_DECISIONS = {
    "sign_internal_review": "signed_internal_review_preview",
    "signed_internal_review": "signed_internal_review_preview",
    "approve_signed_review": "signed_internal_review_preview",
    "request_revision": "revision_requested_preview",
    "revision_requested": "revision_requested_preview",
    "reject": "rejected_preview",
    "rejected": "rejected_preview",
}

_ALLOWED_REVIEW_DECISIONS = {
    "approve_for_clinician_use",
    "request_revision",
    "reject",
}

_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def treatment_framework_signed_review_state_safety_flags() -> Dict[str, bool]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "creates_signed_review_state": False,
        "persists_signed_review_state": False,
        "signed_review_state_preview_only": True,
        "review_state_persistence_enabled": False,
        "not_client_facing": True,
        "client_release_allowed": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }


def _as_non_empty_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        if field_name == "confirmed_diagnosis_label":
            raise ValueError("confirmed diagnosis by clinician is required")
        raise ValueError("{0} is required".format(field_name))
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


def _normalize_signoff_decision(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw not in _ALLOWED_SIGNOFF_DECISIONS:
        raise ValueError("signoff_decision must be sign_internal_review, request_revision, or reject")
    return raw


def _normalize_review_decision(value: Any) -> str:
    raw = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw not in _ALLOWED_REVIEW_DECISIONS:
        raise ValueError("review_decision must be approve_for_clinician_use, request_revision, or reject")
    return raw


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


def scan_for_forbidden_signed_review_output(value: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for text in _walk_strings(value):
        for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
            if pattern.search(text):
                hits.append(text)
                break
    return hits


def _require_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    preview = payload.get("treatment_framework_preview")
    if not isinstance(preview, dict) or not preview:
        raise ValueError("treatment_framework_preview is required")
    forbidden = scan_for_forbidden_signed_review_output(preview)
    if forbidden:
        raise ValueError("forbidden treatment output detected in treatment_framework_preview")
    return preview


def _audit_reference_present(payload: Dict[str, Any]) -> bool:
    audit_log_result = payload.get("audit_log_result")
    audit_event = payload.get("audit_event")
    if isinstance(audit_log_result, dict) and audit_log_result:
        return True
    if isinstance(audit_event, dict) and audit_event:
        return True
    for key in ("audit_log_id", "audit_request_id", "audit_event_id", "request_id"):
        if str(payload.get(key) or "").strip():
            return True
    return False


def build_treatment_framework_signed_review_state(
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
    if scan_for_forbidden_signed_review_output(diagnosis_preview):
        raise ValueError("confirmed diagnosis label cannot contain dose, route, frequency, or prescription wording")

    treatment_framework_preview = _require_preview(payload)
    reviewed_by = _as_non_empty_text(payload.get("reviewed_by") or payload.get("reviewer_id"), "reviewed_by")
    review_decision = _normalize_review_decision(payload.get("review_decision"))
    signed_by = _as_non_empty_text(payload.get("signed_by") or payload.get("signer_id") or payload.get("clinician_signoff_by"), "signed_by")
    signoff_decision = _normalize_signoff_decision(payload.get("signoff_decision") or payload.get("signed_review_decision"))

    audit_reference_present = _audit_reference_present(payload)
    if not audit_reference_present:
        raise ValueError("audit log reference is required before signed review state preview")

    signoff_status = _ALLOWED_SIGNOFF_DECISIONS[signoff_decision]
    signed_review_state_preview = {
        "state_preview_id": "signed-review-state-preview-{0}".format(case_id),
        "case_id": case_id,
        "review_decision": review_decision,
        "reviewed_by": reviewed_by,
        "signoff_decision": signoff_decision,
        "signed_review_status": signoff_status,
        "signed_by": signed_by,
        "signed_at_preview": "DRY_RUN_PREVIEW",
        "dry_run": True,
        "persisted": False,
        "signed_review_state_persisted": False,
        "case_treatment_persisted": False,
        "prescription_created": False,
        "client_release_allowed": False,
        "not_client_facing": True,
        "review_state_persistence_enabled": False,
        "review_state_persistence_requires_future_go_no_go": True,
    }

    quality_gate = {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "audit_log_reference_present": True,
        "signed_review_state_preview_only": True,
        "review_state_persistence_enabled": False,
        "writes_database": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }
    safety = treatment_framework_signed_review_state_safety_flags()

    return {
        "message": "treatment_framework_signed_review_state_built",
        "mode": TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_MODE,
        "case_id": case_id,
        "confirmed_diagnosis": {
            "label": label,
            "confirmed_by": confirmed_by,
            "confirmation_source": confirmation_source,
            "ai_generated": ai_generated,
        },
        "treatment_framework_preview": treatment_framework_preview,
        "review_context": {
            "review_decision": review_decision,
            "reviewed_by": reviewed_by,
            "audit_log_reference_present": audit_reference_present,
        },
        "signed_review_state_preview": signed_review_state_preview,
        "quality_gate": quality_gate,
        "safety": safety,
        "case_context_used": bool(case_context),
        **safety,
    }
