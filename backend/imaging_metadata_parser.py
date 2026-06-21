# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

IMAGING_METADATA_DRY_RUN_MODE = "imaging_metadata_dry_run_fixture_parser_v1"

REQUIRED_STUDY_FIELDS = ("modality", "body_part", "taken_at", "study_uid")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _first_text(*values: Any) -> Optional[str]:
    for value in values:
        text = _text(value)
        if text:
            return text
    return None


def _parse_dt_text(value: Any) -> Optional[str]:
    text = _text(value)
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except Exception:
        if len(text) >= 10:
            return text
        return None


def _normalise_modality(value: Any) -> str:
    raw = _text(value).upper()
    mapping = {
        "RADIOGRAPH": "XR",
        "RADIOGRAPHY": "XR",
        "X-RAY": "XR",
        "XRAY": "XR",
        "ULTRASOUND": "US",
        "SONOGRAPHY": "US",
    }
    return mapping.get(raw, raw or "OTHER")


def _metadata_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_value(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _abnormal_flag(study: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
    explicit = _first_text(study.get("abnormal_flag"), payload.get("abnormal_flag"))
    if explicit:
        return explicit

    abnormal_findings = _list_value(study.get("abnormal_findings") or payload.get("abnormal_findings"))
    if abnormal_findings:
        return "abnormal"

    impression = _text(study.get("impression") or payload.get("impression")).lower()
    if any(term in impression for term in ("abnormal", "mass", "obstruction", "effusion", "foreign body", "异常", "梗阻", "异物")):
        return "abnormal"

    return "normal"


def _report_text(study: Dict[str, Any], payload: Dict[str, Any]) -> Optional[str]:
    text = _first_text(study.get("report_text"), payload.get("report_text"))
    if text:
        return text

    findings = _list_value(study.get("findings") or payload.get("findings"))
    impression = _text(study.get("impression") or payload.get("impression"))
    lines = []
    if findings:
        lines.append("Findings:")
        for item in findings:
            item_text = _text(item)
            if item_text:
                lines.append(f"- {item_text}")
    if impression:
        lines.append(f"Impression: {impression}")
    return "\n".join(lines) if lines else None


def _quality_gate(study: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    missing = []
    for field in REQUIRED_STUDY_FIELDS:
        if not _text(study.get(field) or payload.get(field)):
            missing.append(field)

    blocked = []
    for forbidden_key in (
        "raw_dicom_bytes",
        "dicom_bytes",
        "dicom_file",
        "dicom_url",
        "pacs_query",
        "download_url",
        "device_connection",
    ):
        if forbidden_key in payload or forbidden_key in study:
            blocked.append(forbidden_key)

    warnings = []
    modality = _normalise_modality(study.get("modality") or payload.get("modality"))
    if modality == "OTHER":
        warnings.append("unknown_or_missing_modality_normalized_to_OTHER")

    return {
        "status": "PASS" if not missing and not blocked else "FAIL",
        "missing_required_fields": missing,
        "blocked_real_ingest_fields": blocked,
        "warnings": warnings,
        "requires_clinical_review": True,
        "read_only": True,
        "dry_run": True,
    }


def parse_imaging_metadata_fixture(payload: Dict[str, Any], *, case_id: Optional[int] = None) -> Dict[str, Any]:
    """Convert a synthetic imaging metadata fixture into an ImagingStudy preview.

    This parser is intentionally dry-run only. It does not read DICOM files,
    query PACS, download attachments, create ImagingStudy rows, or call any
    external imaging system.
    """
    if not isinstance(payload, dict):
        raise ValueError("imaging metadata payload must be an object")

    study = payload.get("imaging_study")
    if not isinstance(study, dict):
        study = payload.get("study")
    if not isinstance(study, dict):
        study = payload

    fixture_id = _first_text(payload.get("fixture_id"), study.get("fixture_id"))
    modality = _normalise_modality(study.get("modality") or payload.get("modality"))
    body_part = _first_text(study.get("body_part"), payload.get("body_part"))
    taken_at = _parse_dt_text(study.get("taken_at") or payload.get("taken_at"))
    abnormal_flag = _abnormal_flag(study, payload)
    report_text = _report_text(study, payload)
    quality_gate = _quality_gate(study, payload)

    series = _list_value(study.get("series") or payload.get("series"))
    abnormal_findings = _list_value(study.get("abnormal_findings") or payload.get("abnormal_findings"))

    metadata = {
        "parser_mode": IMAGING_METADATA_DRY_RUN_MODE,
        "fixture_id": fixture_id,
        "source": _metadata_dict(payload.get("source")),
        "image_count": study.get("image_count") or payload.get("image_count"),
        "series": series,
        "abnormal_findings": abnormal_findings,
        "quality_gate": quality_gate,
        "dry_run_only": True,
        "no_raw_dicom": True,
        "no_pacs_query": True,
        "no_download": True,
    }

    study_preview = {
        "case_id": case_id,
        "modality": modality,
        "body_part": body_part,
        "taken_at": taken_at,
        "is_planned_review": bool(study.get("is_planned_review", payload.get("is_planned_review", False))),
        "tag": _first_text(study.get("tag"), payload.get("tag")),
        "report_url": None,
        "viewer_url": None,
        "thumbnail_url": None,
        "metadata": metadata,
        "study_uid": _first_text(study.get("study_uid"), payload.get("study_uid")),
        "accession_number": _first_text(study.get("accession_number"), payload.get("accession_number")),
        "source_type": "dry_run_fixture",
        "source_system": _first_text(study.get("source_system"), payload.get("source_system"), "synthetic_imaging_fixture"),
        "report_text": report_text,
        "abnormal_flag": abnormal_flag,
        "ai_summary": None,
        "ai_summary_status": "not_generated",
        "review_status": "dry_run_preview",
        "reviewed_by": None,
        "reviewed_at": None,
        "attachment_ref": _first_text(study.get("attachment_ref"), payload.get("attachment_ref")),
    }

    safety = {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_imaging_study": False,
        "downloads_attachments": False,
        "queries_pacs": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }

    return {
        "message": "imaging_metadata_dry_run_parse",
        "mode": IMAGING_METADATA_DRY_RUN_MODE,
        "fixture_id": fixture_id,
        "study_preview": study_preview,
        "abnormal_findings": abnormal_findings,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
