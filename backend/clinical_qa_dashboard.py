# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

CLINICAL_QA_DASHBOARD_MODE = "clinical_qa_dashboard_v2"

_REVIEWED_STATUSES = {"reviewed", "accepted", "approved", "clinician_reviewed"}
_PENDING_STATUSES = {"", "draft", "pending", "pending_review", "pending_clinician_review", "not_reviewed"}
_NORMAL_FLAGS = {"", "normal", "none", "not_abnormal", "within_reference_range"}


def clinical_qa_dashboard_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": False,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "writes_diagnostic_report": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "returns_probability": False,
        "returns_numeric_confidence": False,
        "client_facing": False,
        "not_client_facing": True,
        "downloads_attachments": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "queries_pacs": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _lower(value: Any) -> str:
    return _text(value).lower().replace("-", "_").replace(" ", "_")


def _is_reviewed(value: Any) -> bool:
    return _lower(value) in _REVIEWED_STATUSES


def _is_pending(value: Any) -> bool:
    return _lower(value) in _PENDING_STATUSES


def _is_abnormal_flag(value: Any) -> bool:
    return _lower(value) not in _NORMAL_FLAGS


def _safe_list(payload: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = payload.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("%s must be a list" % key)
    items: List[Dict[str, Any]] = []
    for item in value[:1000]:
        if isinstance(item, dict):
            items.append(item)
    return items


def _percent(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) * 100.0 / float(denominator), 2)


def _qa_item(
    *,
    key: str,
    label: str,
    count: int,
    severity_hint: str,
    recommended_action: str,
    sample_ids: Optional[List[Any]] = None,
) -> Dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "count": int(count),
        "severity_hint": severity_hint,
        "recommended_action": recommended_action,
        "sample_ids": [str(x) for x in (sample_ids or [])[:20] if x not in (None, "")],
        "requires_human_review": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }


def build_clinical_qa_dashboard(
    payload: Dict[str, Any],
    *,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a read-only clinical QA dashboard summary for reviewed diagnostic data.

    This function aggregates already-stored diagnostic data and review metadata.
    It does not infer final diagnoses, propose treatment plans, output drug doses,
    persist rows, call external AI, query PACS, download attachments, or release
    client-facing content.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    cases = _safe_list(payload, "cases")
    reports = _safe_list(payload, "diagnostic_reports")
    observations = _safe_list(payload, "observations")
    imaging_studies = _safe_list(payload, "imaging_studies")
    audit_logs = _safe_list(payload, "audit_logs")

    report_reviewed = [r for r in reports if _is_reviewed(r.get("status"))]
    report_pending = [r for r in reports if not _is_reviewed(r.get("status"))]
    ai_summary_reports = [
        r for r in reports
        if bool(r.get("has_ai_summary")) or bool(_text(r.get("ai_summary_status")) and _lower(r.get("ai_summary_status")) not in {"not_generated", "none"})
    ]
    ai_summary_review_gaps = [r for r in ai_summary_reports if not _is_reviewed(r.get("status"))]

    abnormal_observations = [o for o in observations if _is_abnormal_flag(o.get("abnormal_flag"))]
    observation_review_gaps = [o for o in abnormal_observations if not _is_reviewed(o.get("review_status"))]

    abnormal_imaging = [i for i in imaging_studies if _is_abnormal_flag(i.get("abnormal_flag"))]
    imaging_review_gaps = [i for i in imaging_studies if _is_abnormal_flag(i.get("abnormal_flag")) or _is_pending(i.get("review_status"))]
    imaging_review_gaps = [i for i in imaging_review_gaps if not _is_reviewed(i.get("review_status"))]

    diagnostic_summary_audit_logs = [
        a for a in audit_logs
        if _lower(a.get("event_type")) == "diagnostic_summary_review" or "diagnostic_summary" in _lower(a.get("source"))
    ]
    audit_gap_count = max(0, len(report_reviewed) + len(ai_summary_reports) - len(diagnostic_summary_audit_logs))

    qa_queue: List[Dict[str, Any]] = []
    if report_pending:
        qa_queue.append(_qa_item(
            key="diagnostic_report_review_gap",
            label="Diagnostic reports pending clinician review",
            count=len(report_pending),
            severity_hint="medium",
            recommended_action="review_existing_diagnostic_report_status_without_writing_ai_summary",
            sample_ids=[r.get("report_id") for r in report_pending],
        ))
    if ai_summary_review_gaps:
        qa_queue.append(_qa_item(
            key="ai_summary_review_gap",
            label="AI summary present before completed clinician review",
            count=len(ai_summary_review_gaps),
            severity_hint="high",
            recommended_action="confirm_clinician_review_and_audit_log_before_summary_release",
            sample_ids=[r.get("report_id") for r in ai_summary_review_gaps],
        ))
    if observation_review_gaps:
        qa_queue.append(_qa_item(
            key="observation_abnormal_flag_review_gap",
            label="Abnormal observations pending review",
            count=len(observation_review_gaps),
            severity_hint="medium",
            recommended_action="review_abnormal_observation_flags_without_creating_diagnosis",
            sample_ids=[o.get("observation_id") for o in observation_review_gaps],
        ))
    if imaging_review_gaps:
        qa_queue.append(_qa_item(
            key="imagingstudy_review_gap",
            label="Imaging studies pending review workflow",
            count=len(imaging_review_gaps),
            severity_hint="medium",
            recommended_action="review_imaging_metadata_without_pacs_query_or_image_download",
            sample_ids=[i.get("imaging_study_id") for i in imaging_review_gaps],
        ))
    if audit_gap_count:
        qa_queue.append(_qa_item(
            key="diagnostic_summary_audit_gap",
            label="Reviewed diagnostic summaries may need audit-log evidence",
            count=audit_gap_count,
            severity_hint="medium",
            recommended_action="append_diagnostic_summary_audit_log_before_downstream_persistence",
            sample_ids=[],
        ))

    total_review_targets = len(reports) + len(abnormal_observations) + len(imaging_studies)
    completed_review_targets = len(report_reviewed) + (len(abnormal_observations) - len(observation_review_gaps)) + (len(imaging_studies) - len(imaging_review_gaps))

    cards = [
        {
            "key": "diagnostic_report_review_coverage",
            "label": "Diagnostic report review coverage",
            "value": _percent(len(report_reviewed), len(reports)),
            "numerator": len(report_reviewed),
            "denominator": len(reports),
            "unit": "percent",
        },
        {
            "key": "observation_abnormal_review_gap_count",
            "label": "Abnormal observation review gaps",
            "value": len(observation_review_gaps),
            "unit": "count",
        },
        {
            "key": "imaging_review_gap_count",
            "label": "Imaging review gaps",
            "value": len(imaging_review_gaps),
            "unit": "count",
        },
        {
            "key": "diagnostic_summary_audit_log_count",
            "label": "Diagnostic summary audit logs",
            "value": len(diagnostic_summary_audit_logs),
            "unit": "count",
        },
        {
            "key": "overall_clinical_review_completion",
            "label": "Overall clinical review completion",
            "value": _percent(completed_review_targets, total_review_targets),
            "numerator": completed_review_targets,
            "denominator": total_review_targets,
            "unit": "percent",
        },
    ]

    metrics = {
        "cases_total": len(cases),
        "diagnostic_reports_total": len(reports),
        "diagnostic_reports_reviewed": len(report_reviewed),
        "diagnostic_reports_pending_review": len(report_pending),
        "diagnostic_reports_with_ai_summary": len(ai_summary_reports),
        "ai_summary_review_gap_count": len(ai_summary_review_gaps),
        "observations_total": len(observations),
        "abnormal_observations_total": len(abnormal_observations),
        "observation_abnormal_flag_review_gap_count": len(observation_review_gaps),
        "imaging_studies_total": len(imaging_studies),
        "abnormal_imaging_studies_total": len(abnormal_imaging),
        "imagingstudy_review_gap_count": len(imaging_review_gaps),
        "diagnostic_summary_audit_log_count": len(diagnostic_summary_audit_logs),
        "diagnostic_summary_audit_gap_count": audit_gap_count,
        "qa_queue_item_count": len(qa_queue),
    }

    quality_gate = {
        "status": "PASS",
        "decision": "clinical_qa_dashboard_read_only_preview",
        "read_only": True,
        "writes_database": False,
        "qa_queue_item_count": len(qa_queue),
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_output": True,
        "blocks_client_release": True,
    }

    safety = clinical_qa_dashboard_safety_flags()
    return {
        "mode": CLINICAL_QA_DASHBOARD_MODE,
        "case_context": case_context or None,
        "cards": cards,
        "metrics": metrics,
        "qa_queue": qa_queue,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
