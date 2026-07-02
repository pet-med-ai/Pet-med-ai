# -*- coding: utf-8 -*-
"""
Treatment Framework Audit Log V1.

Builds an append-only audit log event for a clinician-reviewed treatment
framework preview. This module does not write the database itself. The API layer
may append exactly one AuditLog row only when dry_run=false and the explicit
confirmation string is supplied.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional
from uuid import uuid4

TREATMENT_FRAMEWORK_AUDIT_LOG_MODE = "treatment_framework_audit_log_v1"
TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION = "I_UNDERSTAND_THIS_APPENDS_TREATMENT_FRAMEWORK_AUDIT_LOG_ONLY"

_ALLOWED_CONFIRMATION_SOURCES = {"clinician", "clinician_entered", "clinician_confirmed"}
_ALLOWED_REVIEW_DECISIONS = {
    "approve_for_clinician_use": "treatment_framework_review_approved",
    "request_revision": "treatment_framework_review_revision_requested",
    "reject": "treatment_framework_review_rejected",
}
_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def treatment_framework_audit_log_safety_flags(*, dry_run: bool = True, writes_audit_log: bool = False) -> Dict[str, Any]:
    writes = bool(writes_audit_log) and not bool(dry_run)
    return {
        "read_only": not writes,
        "dry_run": bool(dry_run),
        "writes_database": writes,
        "creates_case": False,
        "updates_case": False,
        "writes_case_treatment": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "creates_audit_log": writes,
        "writes_audit_log": writes,
        "append_only_audit_log": True,
        "updates_audit_log": False,
        "deletes_audit_log": False,
        "persists_treatment_framework": False,
        "persists_review_state": False,
        "final_signoff_persisted": False,
        "review_status_persisted": False,
        "client_release_allowed": False,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
        "treatment_framework_audit_log_only": True,
    }


def _text(value: Any, max_len: int = 1000) -> str:
    text = str(value or "").strip()
    return text[:max_len] if len(text) > max_len else text


def _bool(value: Any, *, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


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


def _require_text(value: Any, field_name: str) -> str:
    text = _text(value, max_len=200)
    if not text:
        if field_name == "confirmed_diagnosis_label":
            raise ValueError("confirmed diagnosis by clinician is required")
        raise ValueError("%s is required" % field_name)
    return text


def _normalize_confirmation_source(value: Any) -> str:
    source = _text(value, max_len=80).lower()
    if source not in _ALLOWED_CONFIRMATION_SOURCES:
        raise ValueError("confirmed diagnosis by clinician is required")
    return "clinician_entered" if source == "clinician" else source


def _require_ai_generated_false(payload: Dict[str, Any]) -> bool:
    if "ai_generated" not in payload:
        raise ValueError("ai_generated=false is required for clinician confirmed diagnosis input")
    if payload.get("ai_generated") is not False:
        raise ValueError("AI generated diagnosis cannot be used as confirmed diagnosis")
    return False


def _normalize_review_decision(value: Any) -> str:
    decision = _text(value, max_len=100).lower().replace("-", "_").replace(" ", "_")
    aliases = {"approve": "approve_for_clinician_use", "approved": "approve_for_clinician_use", "revision_requested": "request_revision", "needs_revision": "request_revision", "rejected": "reject"}
    decision = aliases.get(decision, decision)
    if decision not in _ALLOWED_REVIEW_DECISIONS:
        raise ValueError("review_decision must be approve_for_clinician_use, request_revision, or reject")
    return decision


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
    return hits[:20]


def _require_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    preview = payload.get("treatment_framework_preview")
    if not isinstance(preview, dict) or not preview:
        raise ValueError("treatment_framework_preview is required")
    if scan_for_forbidden_treatment_output(preview):
        raise ValueError("treatment_framework_preview contains forbidden dose, route, frequency, or prescription wording")
    return preview


def _preview_summary(preview: Dict[str, Any]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for key, value in preview.items():
        if isinstance(value, list):
            counts[str(key)] = len(value)
        elif isinstance(value, dict):
            counts[str(key)] = len(value.keys())
    return {"keys": sorted(str(key) for key in preview.keys()), "item_counts": counts, "contains_full_preview": False}


def build_treatment_framework_audit_log_event(payload: Dict[str, Any], *, case_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be an object")

    case_id = _parse_case_id(payload.get("case_id"))
    label = _require_text(payload.get("confirmed_diagnosis_label"), "confirmed_diagnosis_label")
    confirmed_by = _require_text(payload.get("confirmed_by"), "confirmed_by")
    confirmation_source = _normalize_confirmation_source(payload.get("confirmation_source"))
    ai_generated = _require_ai_generated_false(payload)
    reviewer = _require_text(payload.get("reviewed_by") or payload.get("reviewer_id") or payload.get("clinician_id"), "reviewed_by")
    review_decision = _normalize_review_decision(payload.get("review_decision"))
    review_action = _ALLOWED_REVIEW_DECISIONS[review_decision]
    preview = _require_preview(payload)

    if scan_for_forbidden_treatment_output({"confirmed_diagnosis_label": label}):
        raise ValueError("confirmed diagnosis label cannot contain dose, route, frequency, or prescription wording")
    review_note = _text(payload.get("review_note") or payload.get("note"), max_len=1000)
    if scan_for_forbidden_treatment_output({"review_note": review_note}):
        raise ValueError("review_note contains forbidden dose, route, frequency, or prescription wording")

    dry_run = _bool(payload.get("dry_run"), default=True)
    confirmation = _text(payload.get("audit_log_confirmation") or payload.get("confirmation"), max_len=200)
    if not dry_run and confirmation != TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION:
        raise ValueError("audit_log_confirmation must equal %s" % TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION)

    request_id = _text(payload.get("request_id"), max_len=100) or "treatment-framework-audit-%s-%s" % (case_id, uuid4().hex[:12])
    session_uid = _text(payload.get("session_uid"), max_len=64) or None
    will_append = not dry_run
    safety = treatment_framework_audit_log_safety_flags(dry_run=dry_run, writes_audit_log=will_append)

    metadata = {
        "stage": TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
        "case_id": case_id,
        "confirmed_diagnosis_label": label,
        "confirmed_by": confirmed_by,
        "confirmation_source": confirmation_source,
        "ai_generated": ai_generated,
        "review_decision": review_decision,
        "review_action": review_action,
        "review_decision_preview_only": True,
        "case_context_present": bool(case_context),
        "treatment_framework_preview_summary": _preview_summary(preview),
        "full_treatment_framework_preview_persisted": False,
        "confirmation_required": will_append,
        "confirmation_valid": (not will_append) or confirmation == TREATMENT_FRAMEWORK_AUDIT_LOG_CONFIRMATION,
        "audit_scope": "treatment_framework_review_audit_only",
        "append_only_audit_log": True,
        "blocked_writes": ["case.treatment", "prescription", "drug_dose", "drug_route", "drug_frequency", "client_facing_output", "treatment_framework_persistence"],
        "not_a_prescription": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    audit_event = {
        "request_id": request_id,
        "patient_token": "case:%s" % case_id,
        "clinician_id": reviewer,
        "model_version": TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
        "confidence": None,
        "suggested_action": "treatment_framework_audit_only:%s" % review_decision,
        "action_taken": review_action,
        "override_reason": _text(payload.get("override_reason") or payload.get("reason"), max_len=1000) or None,
        "note": review_note or None,
        "case_id": case_id,
        "session_uid": session_uid,
        "event_type": "treatment_framework_review",
        "source": TREATMENT_FRAMEWORK_AUDIT_LOG_MODE,
        "metadata": metadata,
    }

    audit_log_result = {"decision": "audit_log_append_preview" if dry_run else "audit_log_append_requested", "dry_run": dry_run, "will_append_audit_log": will_append, "persisted": False, "audit_log_id": None, "append_only": True, "can_update": False, "can_delete": False, "case_id": case_id, "review_decision": review_decision, "action_taken": review_action, "not_a_prescription": True, "not_client_facing": True}
    quality_gate = {"status": "PASS", "decision": audit_log_result["decision"], "requires_confirmed_diagnosis": True, "requires_clinician_confirmed_diagnosis": True, "ai_does_not_confirm_diagnosis": True, "review_decision_allowed": True, "audit_log_append_only": True, "writes_database": bool(safety["writes_database"]), "writes_audit_log": bool(safety["writes_audit_log"]), "writes_case_treatment": False, "persists_treatment_framework": False, "blocks_prescription": True, "blocks_dose": True, "blocks_route_frequency": True, "not_client_facing": True, "requires_human_review": True, "clinician_signoff_required": True}

    return {"message": "treatment_framework_audit_log_built", "mode": TREATMENT_FRAMEWORK_AUDIT_LOG_MODE, "case_id": case_id, "confirmed_diagnosis": {"label": label, "confirmed_by": confirmed_by, "confirmation_source": confirmation_source, "ai_generated": ai_generated}, "review_workflow": {"review_decision": review_decision, "review_action": review_action, "reviewed_by": reviewer, "review_decision_preview_only": True, "final_signoff_persisted": False, "review_status_persisted": False, "client_release_allowed": False, "persistence_allowed": False}, "treatment_framework_preview_summary": metadata["treatment_framework_preview_summary"], "audit_event": audit_event, "audit_log_result": audit_log_result, "quality_gate": quality_gate, "safety": safety, "case_context_used": bool(case_context), **safety}
