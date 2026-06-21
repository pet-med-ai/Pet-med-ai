# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

AI_IMAGING_REPORT_SUMMARY_MODE = "ai_imaging_report_summary_v1"


def ai_imaging_report_summary_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_imaging_study": False,
        "writes_imaging_study": False,
        "downloads_attachments": False,
        "queries_pacs": False,
        "reads_raw_dicom": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "treatment_recommendation": False,
        "drug_dose_recommendation": False,
        "requires_human_review": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list_value(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _safe_lower(value: Any) -> str:
    return _text(value).lower()


def _collect_findings(parsed_imaging_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    study_preview = parsed_imaging_metadata.get("study_preview")
    if not isinstance(study_preview, dict):
        study_preview = {}

    metadata = study_preview.get("metadata") if isinstance(study_preview.get("metadata"), dict) else {}
    raw_findings = _list_value(
        parsed_imaging_metadata.get("abnormal_findings")
        or metadata.get("abnormal_findings")
    )

    findings: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_findings, 1):
        if isinstance(item, dict):
            text = _text(item.get("text") or item.get("finding") or item.get("label") or item.get("description"))
            location = _text(item.get("location") or item.get("body_part") or study_preview.get("body_part")) or None
            severity = _text(item.get("severity") or item.get("abnormal_flag") or study_preview.get("abnormal_flag")) or "abnormal"
        else:
            text = _text(item)
            location = _text(study_preview.get("body_part")) or None
            severity = _text(study_preview.get("abnormal_flag")) or "abnormal"
        if not text:
            continue
        findings.append({
            "index": idx,
            "finding": text,
            "location": location,
            "severity_hint": severity,
            "requires_human_review": True,
        })

    report_text = _text(study_preview.get("report_text"))
    if report_text and not findings:
        findings.append({
            "index": 1,
            "finding": report_text[:500],
            "location": _text(study_preview.get("body_part")) or None,
            "severity_hint": _text(study_preview.get("abnormal_flag")) or "report_text_review",
            "requires_human_review": True,
        })

    return findings


def _summary_headline(study_preview: Dict[str, Any], findings: List[Dict[str, Any]]) -> str:
    modality = _text(study_preview.get("modality")) or "imaging"
    body_part = _text(study_preview.get("body_part")) or "unknown body part"
    flag = _safe_lower(study_preview.get("abnormal_flag"))

    if findings or flag in {"abnormal", "high", "low", "critical", "critical_high", "critical_low"}:
        return f"Dry-run imaging report summary: {modality} {body_part} has findings requiring clinician review."
    if flag == "normal":
        return f"Dry-run imaging report summary: {modality} {body_part} preview is marked normal, still requires clinician review."
    return f"Dry-run imaging report summary: {modality} {body_part} preview requires clinician review."


def build_ai_imaging_report_summary(
    parsed_imaging_metadata: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a deterministic dry-run imaging report summary.

    This is not a radiology diagnosis and not a treatment engine. It does not read
    raw DICOM, query PACS, download attachments, create ImagingStudy rows, or call
    external AI/provider services.
    """
    if not isinstance(parsed_imaging_metadata, dict):
        raise ValueError("parsed_imaging_metadata must be a JSON object")

    study_preview = parsed_imaging_metadata.get("study_preview")
    if not isinstance(study_preview, dict):
        raise ValueError("parsed_imaging_metadata.study_preview is required")

    findings = _collect_findings(parsed_imaging_metadata)
    abnormal_flag = _safe_lower(study_preview.get("abnormal_flag"))
    finding_count = len(findings)

    if finding_count:
        overall_status = "review_required"
    elif abnormal_flag == "normal":
        overall_status = "no_abnormality_flagged_in_fixture"
    else:
        overall_status = "review_required"

    review_recommendations = [
        "Review the original imaging study and full radiology report before using this summary clinically.",
        "Correlate imaging findings with signalment, history, physical exam, lab results, and serial imaging when available.",
        "Use this dry-run summary as a clinician review aid only; it is not a diagnosis, prescription, or treatment plan.",
    ]

    if finding_count:
        review_recommendations.append(
            "Abnormal dry-run findings should be verified by a veterinarian and, when appropriate, a radiologist."
        )

    quality_gate = {
        "status": "PASS",
        "finding_count": finding_count,
        "requires_human_review": True,
        "blocks_auto_diagnosis": True,
        "blocks_treatment_recommendation": True,
        "blocks_drug_dose_recommendation": True,
        "blocks_raw_dicom_access": True,
        "blocks_pacs_query": True,
    }

    safety = ai_imaging_report_summary_safety_flags()
    return {
        "mode": AI_IMAGING_REPORT_SUMMARY_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "fixture_id": parsed_imaging_metadata.get("fixture_id"),
        "summary": {
            "headline": _summary_headline(study_preview, findings),
            "overall_status": overall_status,
            "modality": study_preview.get("modality"),
            "body_part": study_preview.get("body_part"),
            "abnormal_flag": study_preview.get("abnormal_flag"),
            "human_review_required": True,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_drug_dose_recommendation": True,
            "not_a_radiologist_report": True,
        },
        "imaging_findings": findings,
        "review_recommendations": review_recommendations,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
