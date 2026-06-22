# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

CLINICIAN_REVIEW_WORKFLOW_MODE = "clinician_review_workflow_for_diagnostic_summaries_v1"


def clinician_review_workflow_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "writes_diagnostic_report": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "signs_report": False,
        "persists_review_status": False,
        "releases_to_client": False,
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
        "clinician_signoff_required": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _summary_from_payload(payload: Dict[str, Any], *keys: str) -> Optional[Dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    summaries = payload.get("summaries")
    if isinstance(summaries, dict):
        for key in keys:
            value = summaries.get(key)
            if isinstance(value, dict):
                return value
    return None


def _source_summary_text(value: Dict[str, Any]) -> str:
    for key in ("headline", "summary", "impression", "overall_status", "decision", "status"):
        text = _text(value.get(key))
        if text:
            return text
    nested = value.get("summary")
    if isinstance(nested, dict):
        for key in ("headline", "overall_status", "decision"):
            text = _text(nested.get(key))
            if text:
                return text
    nested = value.get("boundary")
    if isinstance(nested, dict):
        text = _text(nested.get("decision"))
        if text:
            return text
    nested = value.get("framework")
    if isinstance(nested, dict):
        text = _text(nested.get("decision"))
        if text:
            return text
    nested = value.get("knowledge_base_review")
    if isinstance(nested, dict):
        text = _text(nested.get("decision"))
        if text:
            return text
    return "summary_present"


def _make_review_item(source_type: str, value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    return {
        "source_type": source_type,
        "source_present": True,
        "summary_text": _source_summary_text(value),
        "review_status_preview": "pending_clinician_review",
        "human_review_required": True,
        "can_persist_status": False,
        "can_sign_final_report": False,
        "can_release_to_client": False,
    }


def build_clinician_review_workflow(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a dry-run clinician review workflow preview for diagnostic summaries.

    This function intentionally does not persist review status, create audit log rows,
    sign reports, release client-facing content, write AI summaries, write prescriptions,
    or call external providers.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    lab_summary = _summary_from_payload(payload, "lab_summary", "ai_lab_summary", "lab_abnormal_summary")
    imaging_summary = _summary_from_payload(payload, "imaging_summary", "ai_imaging_summary", "imaging_report_summary")
    treatment_boundary = _summary_from_payload(payload, "treatment_boundary", "treatment_recommendation_boundary")
    drug_dose_safety = _summary_from_payload(payload, "drug_dose_safety", "drug_dose_framework")
    drug_kb_review = _summary_from_payload(payload, "drug_dose_kb_review", "drug_dose_knowledge_base_review")

    candidates = [
        ("ai_lab_abnormal_summary", lab_summary),
        ("ai_imaging_report_summary", imaging_summary),
        ("treatment_recommendation_boundary", treatment_boundary),
        ("drug_dose_safety_framework", drug_dose_safety),
        ("drug_dose_knowledge_base_review", drug_kb_review),
    ]
    review_items = [item for item in (_make_review_item(name, value) for name, value in candidates) if item]

    missing_sources = [
        name for name, value in candidates[:2]
        if not isinstance(value, dict)
    ]

    requested_action = _text(payload.get("requested_action"))
    dangerous_requested = requested_action.lower() in {
        "sign_final_report",
        "release_to_client",
        "persist_review_status",
        "write_ai_summary",
        "write_prescription",
        "approve_treatment_plan",
    }

    decision = "clinician_review_required"
    workflow_status = "pending_clinician_review"
    if not review_items:
        decision = "awaiting_diagnostic_summaries"
        workflow_status = "awaiting_summary_inputs"
    if dangerous_requested:
        decision = "blocked_persistent_or_client_facing_action"
        workflow_status = "blocked_by_review_boundary"

    allowed_actions = [
        "review_summary_preview",
        "request_summary_revision",
        "mark_reviewed_preview_only",
        "prepare_clinician_signoff_preview_without_persistence",
        "document_manual_review_requirements",
    ]

    blocked_actions = [
        "persist_review_status",
        "write_ai_summary_to_diagnostic_report",
        "write_abnormal_summary_to_diagnostic_report",
        "sign_final_report",
        "release_summary_to_client",
        "create_or_write_prescription",
        "create_treatment_plan",
        "send_external_message",
        "call_external_ai_provider",
    ]

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "review_item_count": len(review_items),
        "missing_core_summary_sources": missing_sources,
        "dangerous_requested_action_blocked": dangerous_requested,
        "requires_human_review": True,
        "blocks_persistence": True,
        "blocks_client_release": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
    }

    safety = clinician_review_workflow_safety_flags()
    return {
        "mode": CLINICIAN_REVIEW_WORKFLOW_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "review_workflow": {
            "decision": decision,
            "status": workflow_status,
            "dry_run_only": True,
            "human_review_required": True,
            "clinician_signoff_required": True,
            "signoff_preview_only": True,
            "final_signoff_persisted": False,
            "review_status_persisted": False,
            "client_release_allowed": False,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
        },
        "review_items": review_items,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
