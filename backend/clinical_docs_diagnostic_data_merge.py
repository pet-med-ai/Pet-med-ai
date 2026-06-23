# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE = "clinical_docs_diagnostic_data_merge_v1"

_FREE_TEXT_BLOCKLIST = (
    "final diagnosis",
    "confirmed diagnosis",
    "definitive diagnosis",
    "diagnostic conclusion",
    "treatment plan",
    "prescription",
    "drug dose",
    "client-facing",
)

_DOSE_OR_ROUTE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mcg/kg|ug/kg|ml/kg|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)


def clinical_docs_diagnostic_data_merge_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
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
        "creates_audit_log": False,
        "writes_audit_log": False,
        "persists_problem_list": False,
        "persists_differential_candidates": False,
        "persists_reasoning_trace": False,
        "signs_final_report": False,
        "releases_to_client": False,
        "client_release_allowed": False,
        "client_facing": False,
        "not_client_facing": True,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "returns_probability": False,
        "returns_numeric_confidence": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "downloads_attachments": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "queries_pacs": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "clinical_docs_diagnostic_data_merge_only": True,
    }


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text(value: Any, fallback: str = "") -> str:
    raw = str(value if value is not None else "").strip()
    return raw or fallback


def _date_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return _text(value)


def _safe_free_text(value: Any, *, max_len: int = 420) -> str:
    text = _text(value)
    if not text:
        return ""
    lowered = text.lower()
    if any(term in lowered for term in _FREE_TEXT_BLOCKLIST):
        return "[omitted: final diagnosis / treatment / client-facing wording blocked by Clinical Docs Diagnostic Data Merge V1]"
    if _DOSE_OR_ROUTE_PATTERN.search(text):
        return "[omitted: medication dose / route / frequency text blocked by Clinical Docs Diagnostic Data Merge V1]"
    if len(text) > max_len:
        return text[:max_len].rstrip() + "…"
    return text


def _is_reviewed_status(value: Any) -> bool:
    text = _text(value).lower().replace("-", "_").replace(" ", "_")
    return text in {"reviewed", "accepted", "approved", "final", "completed"}


def _report_item(report: Any) -> Dict[str, Any]:
    ai_summary_status = _text(_value(report, "ai_summary_status"), "not_generated")
    report_status = _text(_value(report, "status"), "draft")
    reviewed = _is_reviewed_status(ai_summary_status) or _is_reviewed_status(report_status)
    ai_summary_excerpt = ""
    if reviewed:
        ai_summary_excerpt = _safe_free_text(_value(report, "ai_summary"))
    return {
        "report_id": _value(report, "id") or _value(report, "report_id"),
        "report_type": _text(_value(report, "report_type"), "diagnostic_report"),
        "title": _text(_value(report, "title"), "Diagnostic report"),
        "status": report_status,
        "ai_summary_status": ai_summary_status,
        "reviewed_by": _text(_value(report, "reviewed_by")),
        "reviewed_at": _date_text(_value(report, "reviewed_at")),
        "reviewed_summary_excerpt": ai_summary_excerpt,
        "human_review_required": True,
        "not_a_final_diagnosis": True,
    }


def _observation_item(item: Any) -> Dict[str, Any]:
    value_numeric = _value(item, "value_numeric")
    value_text = _text(_value(item, "value_text"))
    value_display = _text(value_numeric) if value_numeric not in (None, "") else value_text
    unit = _text(_value(item, "unit"))
    if unit:
        value_display = (value_display + " " + unit).strip()
    return {
        "observation_id": _value(item, "id") or _value(item, "observation_id"),
        "code": _text(_value(item, "code")),
        "display_name": _text(_value(item, "display_name"), "Observation"),
        "value_display": value_display,
        "abnormal_flag": _text(_value(item, "abnormal_flag"), "unmarked"),
        "review_status": _text(_value(item, "review_status"), "draft"),
        "observed_at": _date_text(_value(item, "observed_at")),
        "human_review_required": True,
    }


def _imaging_item(item: Any) -> Dict[str, Any]:
    return {
        "imaging_study_id": _value(item, "id") or _value(item, "imaging_study_id"),
        "modality": _text(_value(item, "modality"), "imaging"),
        "body_part": _text(_value(item, "body_part")),
        "taken_at": _date_text(_value(item, "taken_at")),
        "abnormal_flag": _text(_value(item, "abnormal_flag"), "unmarked"),
        "review_status": _text(_value(item, "review_status"), "draft"),
        "reviewed_by": _text(_value(item, "reviewed_by")),
        "reviewed_at": _date_text(_value(item, "reviewed_at")),
        "human_review_required": True,
    }


def _line_join(lines: Iterable[str], *, empty: str) -> str:
    clean = [line for line in (_text(line) for line in lines) if line]
    return "\n".join(clean) if clean else empty


def _build_section_text(reports: List[Dict[str, Any]], observations: List[Dict[str, Any]], imaging: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("Diagnostic data merge / 诊断数据合并（医生复核用）")
    lines.append("Boundary: not a final diagnosis, not a treatment plan, not a prescription, not client-facing.")
    lines.append("Counts: reports=%d; observations=%d; imaging_studies=%d." % (len(reports), len(observations), len(imaging)))

    if reports:
        lines.append("Reports:")
        for item in reports[:8]:
            title = item.get("title") or item.get("report_type") or "Diagnostic report"
            meta = "status=%s; ai_summary_status=%s" % (item.get("status") or "—", item.get("ai_summary_status") or "—")
            lines.append("- %s (%s)" % (title, meta))
            if item.get("reviewed_summary_excerpt"):
                lines.append("  reviewed summary excerpt: %s" % item["reviewed_summary_excerpt"])

    if observations:
        lines.append("Reviewed / abnormal observations:")
        for item in observations[:12]:
            lines.append(
                "- %s: %s; abnormal_flag=%s; review_status=%s"
                % (
                    item.get("display_name") or "Observation",
                    item.get("value_display") or "—",
                    item.get("abnormal_flag") or "—",
                    item.get("review_status") or "—",
                )
            )

    if imaging:
        lines.append("Imaging review metadata:")
        for item in imaging[:8]:
            label = " ".join([str(item.get("modality") or "imaging"), str(item.get("body_part") or "")]).strip()
            lines.append(
                "- %s; abnormal_flag=%s; review_status=%s"
                % (label, item.get("abnormal_flag") or "—", item.get("review_status") or "—")
            )

    return "\n".join(lines)


def build_clinical_docs_diagnostic_data_merge(
    diagnostic_reports: Iterable[Any],
    observations: Iterable[Any],
    imaging_studies: Iterable[Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    reports = [_report_item(item) for item in list(diagnostic_reports or [])[:20]]
    obs_items = [_observation_item(item) for item in list(observations or [])[:50]]
    imaging_items = [_imaging_item(item) for item in list(imaging_studies or [])[:20]]

    reviewed_reports = [item for item in reports if _is_reviewed_status(item.get("status")) or _is_reviewed_status(item.get("ai_summary_status"))]
    abnormal_observations = [item for item in obs_items if _text(item.get("abnormal_flag")).lower() not in {"", "normal", "unmarked"}]
    reviewed_imaging = [item for item in imaging_items if _is_reviewed_status(item.get("review_status")) or _text(item.get("abnormal_flag")).lower() not in {"", "normal", "unmarked"}]

    section_text = _build_section_text(reviewed_reports, abnormal_observations, reviewed_imaging)
    safety = clinical_docs_diagnostic_data_merge_safety_flags()

    document_context = {
        "diagnostic.reports.summary": _line_join(
            ["%s: status=%s; ai_summary_status=%s" % (item.get("title"), item.get("status"), item.get("ai_summary_status")) for item in reviewed_reports[:8]],
            empty="No reviewed DiagnosticReport summary available for document merge.",
        ),
        "diagnostic.observations.summary": _line_join(
            ["%s: %s; abnormal_flag=%s; review_status=%s" % (item.get("display_name"), item.get("value_display"), item.get("abnormal_flag"), item.get("review_status")) for item in abnormal_observations[:12]],
            empty="No abnormal Observation review data available for document merge.",
        ),
        "diagnostic.imaging.summary": _line_join(
            ["%s %s: abnormal_flag=%s; review_status=%s" % (item.get("modality"), item.get("body_part"), item.get("abnormal_flag"), item.get("review_status")) for item in reviewed_imaging[:8]],
            empty="No reviewed ImagingStudy metadata available for document merge.",
        ),
        "diagnostic.data.safety": "read_only=true; writes_database=false; not_a_final_diagnosis=true; not_client_facing=true; clinician review required",
        "__diagnostic_data_section": section_text,
    }

    quality_gate = {
        "status": "PASS",
        "decision": "diagnostic_data_merged_into_clinical_doc_context",
        "case_id": case_id,
        "report_count": len(reports),
        "reviewed_report_count": len(reviewed_reports),
        "observation_count": len(obs_items),
        "abnormal_observation_count": len(abnormal_observations),
        "imaging_study_count": len(imaging_items),
        "reviewed_or_flagged_imaging_count": len(reviewed_imaging),
        "writes_database": False,
        "generates_final_diagnosis": False,
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    return {
        "mode": CLINICAL_DOCS_DIAGNOSTIC_DATA_MERGE_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "diagnostic_data_merge": {
            "reports": reviewed_reports,
            "observations": abnormal_observations,
            "imaging_studies": reviewed_imaging,
            "section_text": section_text,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_client_facing": True,
        },
        "document_context": document_context,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
