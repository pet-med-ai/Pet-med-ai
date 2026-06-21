# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

MODE = "lab_result_dry_run_fixture_parser_v1"
DRY_RUN_SOURCE_TYPE = "dry_run_lab_fixture"


def lab_parser_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "creates_diagnostic_report": False,
        "creates_observation": False,
        "calls_external_provider": False,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _optional_text(value: Any) -> Optional[str]:
    text = _text(value)
    return text or None


def _float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso_or_none(value: Any) -> Optional[str]:
    text = _text(value)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.isoformat()
    except Exception:
        return text


def _abnormal_flag(
    value_numeric: Optional[float],
    reference_low: Optional[float],
    reference_high: Optional[float],
    explicit_flag: Any = None,
) -> Optional[str]:
    explicit = _text(explicit_flag).lower()
    if explicit in {"high", "h", "above", "critical_high"}:
        return "high"
    if explicit in {"low", "l", "below", "critical_low"}:
        return "low"
    if explicit in {"normal", "n", "none", "not_abnormal"}:
        return None

    if value_numeric is None:
        return None
    if reference_high is not None and value_numeric > reference_high:
        return "high"
    if reference_low is not None and value_numeric < reference_low:
        return "low"
    return None


def _interpretation(flag: Optional[str]) -> Optional[str]:
    if flag == "high":
        return "above_reference_range"
    if flag == "low":
        return "below_reference_range"
    return None


def _report_text(title: str, observations: List[Dict[str, Any]]) -> str:
    lines = [title or "Lab result dry-run preview"]
    if not observations:
        lines.append("No observations parsed.")
        return "\n".join(lines)

    for item in observations:
        code = item.get("code") or "unknown"
        display = item.get("display_name") or code
        value = item.get("value_numeric")
        if value is None:
            value = item.get("value_text") or ""
        unit = item.get("unit") or ""
        flag = item.get("abnormal_flag") or "normal"
        lines.append(f"{code} / {display}: {value} {unit} [{flag}]".strip())
    return "\n".join(lines)


def parse_lab_result_fixture(fixture: Dict[str, Any], *, case_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Convert a synthetic lab dry-run fixture into DiagnosticReport and Observation previews.

    This function is intentionally pure: it does not accept a database session, does not
    create ORM objects, and does not call external lab/LIS/device providers.
    """
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a JSON object")

    errors: List[str] = []
    warnings: List[str] = []

    results = fixture.get("results")
    if results is None:
        results = fixture.get("observations")
    if not isinstance(results, list):
        errors.append("fixture.results must be a list")
        results = []

    fixture_id = _optional_text(fixture.get("fixture_id")) or "inline_lab_result_fixture"
    source_system = _optional_text(fixture.get("source_system")) or "synthetic_lab_fixture"
    source_report_id = _optional_text(fixture.get("source_report_id")) or fixture_id
    title = _optional_text(fixture.get("title")) or "Synthetic lab result dry-run panel"
    report_type = _optional_text(fixture.get("report_type")) or "lab_panel"
    collected_at = _iso_or_none(fixture.get("collected_at"))
    observed_at = _iso_or_none(fixture.get("observed_at")) or collected_at
    specimen_type_default = _optional_text(fixture.get("specimen_type")) or "blood"

    observations_preview: List[Dict[str, Any]] = []
    for idx, raw_item in enumerate(results, 1):
        if not isinstance(raw_item, dict):
            warnings.append(f"result row {idx} is not an object; skipped")
            continue

        code = _optional_text(raw_item.get("code") or raw_item.get("analyte_code"))
        display_name = _optional_text(raw_item.get("display_name") or raw_item.get("name") or code)
        if not code:
            errors.append(f"result row {idx} missing code")
            continue
        if not display_name:
            display_name = code

        value_numeric = _float_or_none(
            raw_item.get("value_numeric")
            if raw_item.get("value_numeric") is not None
            else raw_item.get("value")
        )
        value_text = _optional_text(raw_item.get("value_text"))
        if value_numeric is None and value_text is None and raw_item.get("value") is not None:
            value_text = _optional_text(raw_item.get("value"))

        reference_low = _float_or_none(raw_item.get("reference_low"))
        reference_high = _float_or_none(raw_item.get("reference_high"))
        abnormal_flag = _abnormal_flag(
            value_numeric,
            reference_low,
            reference_high,
            raw_item.get("abnormal_flag") or raw_item.get("flag"),
        )
        value_type = _optional_text(raw_item.get("value_type"))
        if not value_type:
            value_type = "numeric" if value_numeric is not None else "text"

        observation = {
            "case_id": case_id,
            "diagnostic_report_id": None,
            "code": code,
            "display_name": display_name,
            "value_text": value_text,
            "value_numeric": value_numeric,
            "value_type": value_type,
            "unit": _optional_text(raw_item.get("unit")),
            "reference_low": reference_low,
            "reference_high": reference_high,
            "reference_text": _optional_text(raw_item.get("reference_text")),
            "abnormal_flag": abnormal_flag,
            "interpretation": _optional_text(raw_item.get("interpretation")) or _interpretation(abnormal_flag),
            "specimen_type": _optional_text(raw_item.get("specimen_type")) or specimen_type_default,
            "collected_at": _iso_or_none(raw_item.get("collected_at")) or collected_at,
            "observed_at": _iso_or_none(raw_item.get("observed_at")) or observed_at,
            "source_type": DRY_RUN_SOURCE_TYPE,
            "review_status": "preview",
            "metadata": {
                "fixture_id": fixture_id,
                "row_index": idx,
                "synthetic": bool(fixture.get("synthetic", True)),
                "parser_mode": MODE,
                **(raw_item.get("metadata") if isinstance(raw_item.get("metadata"), dict) else {}),
            },
        }
        observations_preview.append(observation)

    abnormal_observations = [
        item
        for item in observations_preview
        if item.get("abnormal_flag") in {"high", "low", "critical_high", "critical_low"}
    ]

    abnormal_summary = None
    if abnormal_observations:
        parts = [
            f"{item.get('code')} {item.get('abnormal_flag')}"
            for item in abnormal_observations
        ]
        abnormal_summary = "Dry-run abnormal observations: " + ", ".join(parts)

    report_preview = {
        "case_id": case_id,
        "report_type": report_type,
        "source_type": DRY_RUN_SOURCE_TYPE,
        "source_system": source_system,
        "source_report_id": source_report_id,
        "status": "preview",
        "title": title,
        "report_text": _report_text(title, observations_preview),
        "abnormal_summary": abnormal_summary,
        "ai_summary": None,
        "ai_summary_status": "not_generated",
        "ordering_clinician": _optional_text(fixture.get("ordering_clinician")),
        "reviewed_by": None,
        "reviewed_at": None,
        "attachment_ref": None,
        "metadata": {
            "fixture_id": fixture_id,
            "synthetic": bool(fixture.get("synthetic", True)),
            "panel": _optional_text(fixture.get("panel")),
            "species": _optional_text(fixture.get("species")),
            "parser_mode": MODE,
            "no_database_write": True,
            "no_external_lab_ingest": True,
        },
    }

    quality_gate = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "parsed_observation_count": len(observations_preview),
        "abnormal_observation_count": len(abnormal_observations),
        "requires_human_review": True,
    }

    safety = lab_parser_safety_flags()
    return {
        "mode": MODE,
        "fixture_id": fixture_id,
        "report_preview": report_preview,
        "observations_preview": observations_preview,
        "abnormal_observations": abnormal_observations,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
