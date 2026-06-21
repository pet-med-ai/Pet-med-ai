# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List, Optional

AI_LAB_ABNORMAL_SUMMARY_MODE = "ai_lab_abnormal_summary_v1"


def ai_lab_abnormal_summary_safety_flags() -> Dict[str, Any]:
    return {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "creates_observation": False,
        "writes_diagnostic_report": False,
        "writes_observation": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "treatment_recommendation": False,
        "drug_dose_recommendation": False,
        "requires_human_review": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _num(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reference_range(item: Dict[str, Any]) -> str:
    low = item.get("reference_low")
    high = item.get("reference_high")
    unit = _text(item.get("unit"))
    if low is not None and high is not None:
        return f"{low}-{high} {unit}".strip()
    if low is not None:
        return f">= {low} {unit}".strip()
    if high is not None:
        return f"<= {high} {unit}".strip()
    return _text(item.get("reference_text")) or "not_provided"


def _severity_hint(item: Dict[str, Any]) -> str:
    flag = _text(item.get("abnormal_flag")).lower()
    value = _num(item.get("value_numeric"))
    low = _num(item.get("reference_low"))
    high = _num(item.get("reference_high"))

    if flag in {"critical_high", "critical_low"}:
        return flag
    if flag == "high":
        if value is not None and high not in (None, 0) and value >= high * 2:
            return "marked_high"
        return "high"
    if flag == "low":
        if value is not None and low not in (None, 0) and value <= low * 0.5:
            return "marked_low"
        return "low"
    return "abnormal"


def _clinical_note(code: str, flag: str) -> str:
    key = code.upper()
    flag = flag.lower()

    if key == "WBC" and flag == "high":
        return "Leukocytosis pattern in this dry-run preview; correlate with inflammation, stress response, infection, steroid effect, and differential count."
    if key == "WBC" and flag == "low":
        return "Leukopenia pattern in this dry-run preview; verify sample and correlate with clinical status and differential count."
    if key == "ALT" and flag == "high":
        return "Hepatocellular enzyme elevation pattern in this dry-run preview; correlate with medications, toxins, hypoxia, hepatobiliary disease, and clinical signs."
    if key in {"AST", "ALP", "GGT", "TBIL"} and flag == "high":
        return "Hepatobiliary-associated abnormality in this dry-run preview; interpret alongside the full chemistry panel and exam findings."
    if key in {"CREA", "BUN", "SDMA"} and flag == "high":
        return "Renal/azotemia-associated abnormality in this dry-run preview; correlate with hydration, urinalysis, urine output, and serial values."
    if key == "GLU" and flag == "low":
        return "Hypoglycemia pattern in this dry-run preview; confirm sample handling and assess whether urgent clinical review is needed if signs are present."
    if key == "GLU" and flag == "high":
        return "Hyperglycemia pattern in this dry-run preview; correlate with stress, diabetes risk, medications, and urinalysis."
    if key in {"HCT", "PCV", "RBC", "HGB"} and flag == "low":
        return "Anemia-associated abnormality in this dry-run preview; correlate with hydration, reticulocytes, bleeding/hemolysis markers, and clinical signs."
    if key in {"PLT", "PLATELET"} and flag == "low":
        return "Thrombocytopenia-associated abnormality in this dry-run preview; confirm smear/platelet clumps and bleeding risk clinically."
    return "Dry-run abnormal lab value; interpret with the full panel, exam findings, species, age, medications, and sample quality."


def _value_text(item: Dict[str, Any]) -> str:
    value = item.get("value_numeric")
    if value is None:
        value = item.get("value_text")
    unit = _text(item.get("unit"))
    return f"{value} {unit}".strip() if value is not None else "not_provided"


def _collect_abnormal_observations(parsed_lab_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    abnormal = parsed_lab_result.get("abnormal_observations")
    if isinstance(abnormal, list) and abnormal:
        return [item for item in abnormal if isinstance(item, dict)]

    observations = parsed_lab_result.get("observations_preview") or []
    if not isinstance(observations, list):
        return []
    return [
        item for item in observations
        if isinstance(item, dict) and _text(item.get("abnormal_flag")).lower() in {"high", "low", "critical_high", "critical_low"}
    ]


def build_ai_lab_abnormal_summary(
    parsed_lab_result: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a deterministic dry-run abnormal lab summary from parsed lab-result previews.

    This is deliberately not a treatment engine and not a dose engine. It does not call
    external AI providers, does not write DiagnosticReport.ai_summary, and does not
    persist any Observation or DiagnosticReport rows.
    """
    if not isinstance(parsed_lab_result, dict):
        raise ValueError("parsed_lab_result must be a JSON object")

    abnormal_items = _collect_abnormal_observations(parsed_lab_result)
    findings: List[Dict[str, Any]] = []

    for item in abnormal_items:
        code = _text(item.get("code")) or "UNKNOWN"
        flag = _text(item.get("abnormal_flag")).lower() or "abnormal"
        finding = {
            "code": code,
            "display_name": _text(item.get("display_name")) or code,
            "abnormal_flag": flag,
            "severity_hint": _severity_hint(item),
            "value": _value_text(item),
            "reference_range": _reference_range(item),
            "interpretation": _text(item.get("interpretation")) or None,
            "clinical_note": _clinical_note(code, flag),
            "requires_human_review": True,
        }
        findings.append(finding)

    codes = [f"{item['code']} {item['abnormal_flag']}" for item in findings]
    if findings:
        headline = "Dry-run abnormal lab summary: " + ", ".join(codes)
        overall_status = "review_required"
    else:
        headline = "Dry-run lab summary: no abnormal observations detected in parsed fixture."
        overall_status = "no_abnormality_detected"

    urgent_markers = {
        finding["code"].upper()
        for finding in findings
        if finding["severity_hint"] in {"marked_high", "marked_low", "critical_high", "critical_low"}
        or (finding["code"].upper() == "GLU" and finding["abnormal_flag"] == "low")
    }
    if urgent_markers:
        overall_status = "urgent_review_consideration"

    review_recommendations = [
        "Confirm abnormal values against the full lab report, species-specific reference intervals, and sample quality.",
        "Correlate with signalment, history, physical exam, medications, hydration, and serial trends.",
        "Use this summary as a clinician review aid only; it is not a diagnosis, prescription, or treatment plan.",
    ]
    if urgent_markers:
        review_recommendations.append(
            "Some dry-run abnormalities may warrant prompt clinician review if the patient is clinically unstable."
        )

    quality_gate = {
        "status": "PASS",
        "abnormal_finding_count": len(findings),
        "requires_human_review": True,
        "blocks_auto_diagnosis": True,
        "blocks_treatment_recommendation": True,
        "blocks_drug_dose_recommendation": True,
    }

    safety = ai_lab_abnormal_summary_safety_flags()
    return {
        "mode": AI_LAB_ABNORMAL_SUMMARY_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "fixture_id": parsed_lab_result.get("fixture_id"),
        "summary": {
            "headline": headline,
            "overall_status": overall_status,
            "abnormal_codes": codes,
            "human_review_required": True,
            "not_a_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_drug_dose_recommendation": True,
        },
        "abnormal_findings": findings,
        "review_recommendations": review_recommendations,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
