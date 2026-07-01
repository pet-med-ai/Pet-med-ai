# -*- coding: utf-8 -*-
"""
Treatment Framework Clinician Review Workflow V1.

Dry-run clinician review workflow for a confirmed-diagnosis treatment framework
preview. This module never persists review state, never writes the case treatment field,
never creates prescription data, never returns drug dose/route/frequency, and
never produces client-facing output.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_MODE = "treatment_framework_clinician_review_workflow_v1"

_ALLOWED_CONFIRMATION_SOURCES = {
    "clinician",
    "clinician_entered",
    "clinician_confirmed",
}

_DECISION_ALIASES = {
    "approve": "approve_for_clinician_use",
    "approved": "approve_for_clinician_use",
    "approve_for_clinician_use": "approve_for_clinician_use",
    "approve_internal": "approve_for_clinician_use",
    "request_revision": "request_revision",
    "revise": "request_revision",
    "needs_revision": "request_revision",
    "reject": "reject",
    "rejected": "reject",
}

_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def treatment_framework_clinician_review_workflow_safety_flags() -> Dict[str, bool]:
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
        "writes_audit_log": False,
        "persists_review_state": False,
        "review_decision_preview_only": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }


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


def scan_for_forbidden_treatment_output(value: Any) -> List[str]:
    hits: List[str] = []
    for text in _walk_strings(value):
        for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
            if pattern.search(text):
                hits.append(text)
                break
    return hits


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


def _normalize_review_decision(value: Any) -> str:
    raw = str(value or "").strip().lower()
    decision = _DECISION_ALIASES.get(raw)
    if decision is None:
        raise ValueError("review_decision must be approve_for_clinician_use, request_revision, or reject")
    return decision


def _review_status_for_decision(decision: str) -> str:
    if decision == "approve_for_clinician_use":
        return "approved_internal_clinician_preview"
    if decision == "request_revision":
        return "revision_requested_by_clinician"
    return "rejected_by_clinician"


def _require_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    preview = payload.get("treatment_framework_preview") or payload.get("framework_preview")
    if not isinstance(preview, dict) or not preview:
        raise ValueError("treatment_framework_preview is required")
    forbidden = scan_for_forbidden_treatment_output(preview)
    if forbidden:
        raise ValueError("treatment framework preview contains forbidden dose, route, frequency, or prescription wording")
    return preview


def build_treatment_framework_clinician_review_workflow(
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
    reviewer_id = _as_non_empty_text(payload.get("reviewed_by") or payload.get("reviewer_id"), "reviewed_by")
    decision = _normalize_review_decision(payload.get("review_decision"))
    preview = _require_preview(payload)

    diagnosis_preview = {"label": label}
    if scan_for_forbidden_treatment_output(diagnosis_preview):
        raise ValueError("confirmed diagnosis label cannot contain dose, route, frequency, or prescription wording")

    review_note = str(payload.get("review_note") or payload.get("note") or "").strip()
    note_present = bool(review_note)

    blocked_actions = [
        "database_write_blocked",
        "case_record_treatment_field_blocked",
        "regulated_medication_detail_output_blocked",
        "client_release_blocked",
        "external_delivery_blocked",
    ]

    review_workflow = {
        "review_decision": decision,
        "review_status": _review_status_for_decision(decision),
        "reviewed_by": reviewer_id,
        "reviewed_at": "DRY_RUN_PREVIEW",
        "note_present": note_present,
        "dry_run": True,
        "review_decision_preview_only": True,
        "final_signoff_persisted": False,
        "review_status_persisted": False,
        "client_release_allowed": False,
        "persistence_allowed": False,
        "requires_manual_clinician_action": True,
    }

    review_checklist = {
        "confirmed_diagnosis_source_checked": True,
        "framework_preview_present": True,
        "clinician_review_decision_present": True,
        "database_write_blocked": True,
        "regulated_medication_details_blocked": True,
        "client_release_blocked": True,
    }

    quality_gate = {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "review_decision_allowed": True,
        "review_decision_preview_only": True,
        "writes_database": False,
        "writes_case_treatment": False,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }
    safety = treatment_framework_clinician_review_workflow_safety_flags()

    return {
        "message": "treatment_framework_clinician_review_workflow_built",
        "mode": TREATMENT_FRAMEWORK_CLINICIAN_REVIEW_WORKFLOW_MODE,
        "case_id": case_id,
        "confirmed_diagnosis": {
            "label": label,
            "confirmed_by": confirmed_by,
            "confirmation_source": confirmation_source,
            "ai_generated": ai_generated,
        },
        "treatment_framework_preview": preview,
        "review_workflow": review_workflow,
        "review_checklist": review_checklist,
        "blocked_actions": blocked_actions,
        "quality_gate": quality_gate,
        "safety": safety,
        "case_context_used": bool(case_context),
        **safety,
    }
