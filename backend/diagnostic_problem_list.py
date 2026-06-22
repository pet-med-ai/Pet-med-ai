# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE = "diagnostic_assistance_problem_list_v1"

DOSE_OR_ROUTE_PATTERN = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg/kg|mg|mcg/kg|ug/kg|ml/kg|ml|iu/kg|units/kg)\b|\bq\d{1,2}h\b|\b(sid|bid|tid|qid|po|iv|im|sc|sq)\b)",
    re.IGNORECASE,
)

DRUG_TERMS = (
    "maropitant", "ondansetron", "metoclopramide", "omeprazole", "famotidine",
    "prednisone", "prednisolone", "dexamethasone", "meloxicam", "carprofen",
    "robenacoxib", "amoxicillin", "clavulanate", "cefovecin", "enrofloxacin",
    "furosemide", "insulin", "gabapentin", "buprenorphine",
)

FORBIDDEN_CONCLUSION_PATTERN = re.compile(
    r"\b(final diagnosis|confirmed diagnosis|definitive diagnosis|treatment plan|prescription|drug dose|dosage|route|frequency)\b",
    re.IGNORECASE,
)

CRITICAL_TERMS = (
    "collapse", "seizure", "dyspnea", "respiratory distress", "shock",
    "anuria", "hyperkalemia", "hypoglycemia", "critical", "emergency",
)
HIGH_TERMS = (
    "severe", "marked", "bloody", "melena", "hematemesis", "tachycardia",
    "hypothermia", "hyperthermia", "dehydration", "pain", "blocked",
)


def diagnostic_problem_list_safety_flags() -> Dict[str, Any]:
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
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "creates_audit_log": False,
        "writes_audit_log": False,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "treatment_recommendation": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "drug_dose_recommendation": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "releases_to_client": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "problem_list_preview_only": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_snippet(value: Any, limit: int = 220) -> str:
    text = _text(value)
    if not text:
        return ""
    text = DOSE_OR_ROUTE_PATTERN.sub("[dose/route/frequency redacted]", text)
    for term in DRUG_TERMS:
        text = re.sub(r"\b" + re.escape(term) + r"\b", "[medication term redacted]", text, flags=re.IGNORECASE)
    text = FORBIDDEN_CONCLUSION_PATTERN.sub("[blocked clinical conclusion/action redacted]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def _safe_label(value: Any, fallback: str = "item") -> str:
    return _safe_snippet(value, limit=80) or fallback


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


def _flatten_texts(value: Any, limit: int = 30) -> List[str]:
    texts: List[str] = []

    def walk(item: Any, depth: int = 0) -> None:
        if len(texts) >= limit or depth > 4:
            return
        if isinstance(item, str):
            snippet = _safe_snippet(item)
            if snippet:
                texts.append(snippet)
        elif isinstance(item, (int, float, bool)):
            snippet = _safe_snippet(item)
            if snippet:
                texts.append(snippet)
        elif isinstance(item, dict):
            for key in sorted(item.keys()):
                if len(texts) >= limit:
                    return
                if str(key).lower() in {
                    "final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis",
                    "treatment_plan", "prescription", "drug_dose", "dose", "route", "frequency",
                }:
                    continue
                walk(item.get(key), depth + 1)
        elif isinstance(item, list):
            for child in item:
                if len(texts) >= limit:
                    return
                walk(child, depth + 1)

    walk(value)
    return texts


def _severity_from_texts(texts: List[str], default: str = "medium") -> str:
    lowered = " ".join(texts).lower()
    if any(term in lowered for term in CRITICAL_TERMS):
        return "critical"
    if any(term in lowered for term in HIGH_TERMS):
        return "high"
    if lowered:
        return default
    return "unknown"


def _make_evidence(source_type: str, field: str, value: Any, source_strength: str = "reported") -> Optional[Dict[str, Any]]:
    snippet = _safe_snippet(value)
    if not snippet:
        return None
    return {
        "source_type": source_type,
        "field": field,
        "snippet": snippet,
        "source_strength": source_strength,
    }


def _append_problem(
    items: List[Dict[str, Any]],
    *,
    category: str,
    title: str,
    severity_hint: str,
    evidence_sources: List[Dict[str, Any]],
) -> None:
    usable_evidence = [item for item in evidence_sources if isinstance(item, dict) and item.get("snippet")]
    if not usable_evidence:
        return
    items.append({
        "category": category,
        "title": _safe_label(title, fallback="Clinical problem preview item"),
        "severity_hint": severity_hint,
        "evidence_sources": usable_evidence[:6],
        "requires_clinician_review": True,
        "clinician_signoff_required": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
        "dry_run_only": True,
    })


def _deduplicate_and_number(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        key = (item.get("category"), item.get("title"), tuple(e.get("snippet") for e in item.get("evidence_sources", [])[:2]))
        if key in seen:
            continue
        seen.add(key)
        numbered = dict(item)
        numbered["problem_id"] = "problem-%03d" % (len(result) + 1)
        result.append(numbered)
    return result


def _case_problem_candidates(payload: Dict[str, Any], case_context: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    case_summary = payload.get("case_summary") if isinstance(payload.get("case_summary"), dict) else {}
    chief = (
        payload.get("chief_complaint")
        or payload.get("presenting_complaint")
        or case_summary.get("chief_complaint")
        or case_summary.get("presenting_complaint")
    )
    evidence = _make_evidence("case", "chief_complaint", chief, "reported")
    if evidence:
        _append_problem(
            items,
            category="presenting_complaint",
            title="Presenting complaint requires clinician review",
            severity_hint=_severity_from_texts([evidence["snippet"]], default="medium"),
            evidence_sources=[evidence],
        )

    for field in ("history", "dynamic_intake", "intake", "history_summary"):
        texts = _flatten_texts(payload.get(field), limit=8)
        if texts:
            evidence_items = [item for item in (_make_evidence("case", field, text, "reported") for text in texts[:4]) if item]
            _append_problem(
                items,
                category="history_signal",
                title="History signal requires clinician review",
                severity_hint=_severity_from_texts(texts, default="low"),
                evidence_sources=evidence_items,
            )
            break

    if case_context and not items:
        species = _make_evidence("case_context", "species", case_context.get("species"), "case_metadata")
        if species:
            _append_problem(
                items,
                category="case_context",
                title="Case context available for clinician review",
                severity_hint="unknown",
                evidence_sources=[species],
            )
    return items


def _extract_list(summary: Dict[str, Any], *keys: str) -> List[Any]:
    for key in keys:
        value = summary.get(key)
        if isinstance(value, list):
            return value
    return []


def _lab_problem_candidates(lab_summary: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(lab_summary, dict):
        return []
    items: List[Dict[str, Any]] = []
    findings = _extract_list(lab_summary, "abnormal_findings", "abnormal_observations", "findings", "items")
    for finding in findings[:12]:
        if isinstance(finding, dict):
            name = _safe_label(
                finding.get("display_name") or finding.get("name") or finding.get("code") or finding.get("analyte"),
                fallback="lab result",
            )
            snippets = []
            for key in ("display_name", "abnormal_flag", "interpretation", "value_text", "reference_text", "summary"):
                evidence = _make_evidence("lab_abnormal_summary", key, finding.get(key), "structured_summary")
                if evidence:
                    snippets.append(evidence)
            if not snippets:
                snippets = [item for item in (_make_evidence("lab_abnormal_summary", "finding", text, "structured_summary") for text in _flatten_texts(finding, limit=4)) if item]
            _append_problem(
                items,
                category="lab_abnormality",
                title="Laboratory abnormality requires clinician review: %s" % name,
                severity_hint=_severity_from_texts([e.get("snippet", "") for e in snippets], default="medium"),
                evidence_sources=snippets,
            )
        else:
            evidence = _make_evidence("lab_abnormal_summary", "finding", finding, "structured_summary")
            if evidence:
                _append_problem(
                    items,
                    category="lab_abnormality",
                    title="Laboratory abnormality requires clinician review",
                    severity_hint=_severity_from_texts([evidence["snippet"]], default="medium"),
                    evidence_sources=[evidence],
                )
    if not items:
        texts: List[str] = []
        nested_summary = lab_summary.get("summary")
        texts.extend(_flatten_texts(nested_summary, limit=4))
        texts.extend(_flatten_texts(lab_summary.get("headline"), limit=2))
        if texts:
            evidence_items = [item for item in (_make_evidence("lab_abnormal_summary", "summary", text, "structured_summary") for text in texts[:4]) if item]
            _append_problem(
                items,
                category="lab_abnormality",
                title="Laboratory summary requires clinician review",
                severity_hint=_severity_from_texts(texts, default="medium"),
                evidence_sources=evidence_items,
            )
    return items


def _imaging_problem_candidates(imaging_summary: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(imaging_summary, dict):
        return []
    items: List[Dict[str, Any]] = []
    findings = _extract_list(imaging_summary, "findings", "abnormal_findings", "imaging_findings", "items")
    for finding in findings[:8]:
        if isinstance(finding, dict):
            label = _safe_label(
                finding.get("body_part") or finding.get("modality") or finding.get("title") or finding.get("finding"),
                fallback="imaging finding",
            )
            snippets = []
            for key in ("modality", "body_part", "abnormal_flag", "impression", "finding", "summary"):
                evidence = _make_evidence("imaging_report_summary", key, finding.get(key), "structured_summary")
                if evidence:
                    snippets.append(evidence)
            if not snippets:
                snippets = [item for item in (_make_evidence("imaging_report_summary", "finding", text, "structured_summary") for text in _flatten_texts(finding, limit=4)) if item]
            _append_problem(
                items,
                category="imaging_abnormality",
                title="Imaging report finding requires clinician review: %s" % label,
                severity_hint=_severity_from_texts([e.get("snippet", "") for e in snippets], default="medium"),
                evidence_sources=snippets,
            )
        else:
            evidence = _make_evidence("imaging_report_summary", "finding", finding, "structured_summary")
            if evidence:
                _append_problem(
                    items,
                    category="imaging_abnormality",
                    title="Imaging report finding requires clinician review",
                    severity_hint=_severity_from_texts([evidence["snippet"]], default="medium"),
                    evidence_sources=[evidence],
                )
    if not items:
        texts: List[str] = []
        for key in ("summary", "impression", "report_summary", "overall_status"):
            texts.extend(_flatten_texts(imaging_summary.get(key), limit=4))
        if texts:
            evidence_items = [item for item in (_make_evidence("imaging_report_summary", "summary", text, "structured_summary") for text in texts[:4]) if item]
            _append_problem(
                items,
                category="imaging_abnormality",
                title="Imaging report summary requires clinician review",
                severity_hint=_severity_from_texts(texts, default="medium"),
                evidence_sources=evidence_items,
            )
    return items


def _workflow_problem_candidates(workflow_payload: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(workflow_payload, dict):
        return []
    workflow = workflow_payload.get("review_workflow")
    if not isinstance(workflow, dict):
        workflow = workflow_payload
    texts = []
    for key in ("decision", "status", "summary", "overall_status"):
        if workflow.get(key):
            texts.append(_safe_snippet(workflow.get(key)))
    if not texts:
        texts = _flatten_texts(workflow, limit=4)
    if not texts:
        return []
    evidence_items = [item for item in (_make_evidence("clinician_review_workflow", "workflow", text, "review_workflow_preview") for text in texts[:4]) if item]
    items: List[Dict[str, Any]] = []
    _append_problem(
        items,
        category="review_workflow_gap",
        title="Clinician review workflow requires completion",
        severity_hint="high" if "blocked" in " ".join(texts).lower() else "medium",
        evidence_sources=evidence_items,
    )
    return items


def _boundary_problem_candidates(treatment_boundary: Optional[Dict[str, Any]], drug_dose_safety: Optional[Dict[str, Any]], drug_kb_review: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []

    def add_boundary_item(source_type: str, payload: Optional[Dict[str, Any]], category: str, title: str) -> None:
        if not isinstance(payload, dict):
            return
        texts = []
        for key in ("decision", "status", "overall_status"):
            if payload.get(key):
                texts.append(_safe_snippet(payload.get(key)))
        for nested_key in ("boundary", "framework", "knowledge_base_review", "quality_gate"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                for key in ("decision", "status", "summary", "blocked"):
                    if nested.get(key) not in (None, ""):
                        texts.append(_safe_snippet(nested.get(key)))
        for list_key in ("prohibited_items", "blocked_categories", "risk_flags", "warnings", "blocked_items"):
            value = payload.get(list_key)
            if isinstance(value, list) and value:
                texts.extend(_flatten_texts(value[:4], limit=8))
        joined = " ".join(texts).lower()
        if not texts:
            return
        evidence_items = [item for item in (_make_evidence(source_type, "boundary", text, "safety_boundary_preview") for text in texts[:5]) if item]
        _append_problem(
            items,
            category=category,
            title=title,
            severity_hint="high" if any(word in joined for word in ("block", "risk", "warning")) else "medium",
            evidence_sources=evidence_items,
        )

    add_boundary_item("treatment_recommendation_boundary", treatment_boundary, "safety_boundary_flag", "Treatment boundary flag requires clinician review")
    add_boundary_item("drug_dose_safety_framework", drug_dose_safety, "safety_boundary_flag", "Medication safety boundary requires clinician review")
    add_boundary_item("drug_dose_knowledge_base_review", drug_kb_review, "safety_boundary_flag", "Medication knowledge-base safety note requires clinician review")
    return items


def _dangerous_request_detected(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    blocked_keys = []
    for key in ("final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis", "treatment_plan", "prescription", "drug_dose", "drug_route", "drug_frequency"):
        if key in payload:
            blocked_keys.append(key)
    requested_action = _text(payload.get("requested_action")).lower()
    if requested_action in {"final_diagnosis", "confirm_diagnosis", "definitive_diagnosis", "create_treatment_plan", "write_prescription", "return_drug_dose", "release_to_client"}:
        blocked_keys.append("requested_action:%s" % requested_action)
    return bool(blocked_keys), blocked_keys


def build_diagnostic_assistance_problem_list(payload: Dict[str, Any], *, case_id: Optional[int] = None, case_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a deterministic dry-run problem list preview for clinician review.

    This is not a diagnosis engine and not a treatment engine. It does not write to
    the database, produce final/confirmed diagnoses, generate treatment plans, write
    prescriptions, return drug doses, or call external AI/provider services.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    lab_summary = _summary_from_payload(payload, "lab_summary", "ai_lab_summary", "lab_abnormal_summary")
    imaging_summary = _summary_from_payload(payload, "imaging_summary", "ai_imaging_summary", "imaging_report_summary")
    workflow_payload = _summary_from_payload(payload, "clinician_review_workflow", "clinician_review", "review_workflow")
    treatment_boundary = _summary_from_payload(payload, "treatment_boundary", "treatment_recommendation_boundary")
    drug_dose_safety = _summary_from_payload(payload, "drug_dose_safety", "drug_dose_framework")
    drug_kb_review = _summary_from_payload(payload, "drug_dose_kb_review", "drug_dose_knowledge_base_review")

    raw_items: List[Dict[str, Any]] = []
    raw_items.extend(_case_problem_candidates(payload, case_context))
    raw_items.extend(_lab_problem_candidates(lab_summary))
    raw_items.extend(_imaging_problem_candidates(imaging_summary))
    raw_items.extend(_workflow_problem_candidates(workflow_payload))
    raw_items.extend(_boundary_problem_candidates(treatment_boundary, drug_dose_safety, drug_kb_review))

    problem_list_preview = _deduplicate_and_number(raw_items)
    aggregate_evidence: List[Dict[str, Any]] = []
    seen_evidence = set()
    for problem in problem_list_preview:
        for evidence in problem.get("evidence_sources", []):
            key = (evidence.get("source_type"), evidence.get("field"), evidence.get("snippet"))
            if key in seen_evidence:
                continue
            seen_evidence.add(key)
            aggregate_evidence.append(evidence)

    dangerous_requested, blocked_request_keys = _dangerous_request_detected(payload)
    if dangerous_requested:
        decision = "blocked_diagnostic_or_treatment_request_problem_list_preview_only"
    elif problem_list_preview:
        decision = "problem_list_preview_requires_clinician_review"
    else:
        decision = "awaiting_clinical_inputs_for_problem_list_preview"

    source_presence = {
        "case_chief_complaint": bool(_text(payload.get("chief_complaint") or payload.get("presenting_complaint"))),
        "history_or_dynamic_intake": any(isinstance(payload.get(key), (dict, list, str)) for key in ("history", "dynamic_intake", "intake", "history_summary")),
        "lab_abnormal_summary": isinstance(lab_summary, dict),
        "imaging_report_summary": isinstance(imaging_summary, dict),
        "clinician_review_workflow": isinstance(workflow_payload, dict),
        "treatment_boundary": isinstance(treatment_boundary, dict),
        "drug_dose_safety_framework": isinstance(drug_dose_safety, dict),
        "drug_dose_knowledge_base_review": isinstance(drug_kb_review, dict),
    }
    missing_core_sources = [key for key in ("case_chief_complaint", "lab_abnormal_summary", "imaging_report_summary") if not source_presence.get(key)]

    allowed_actions = [
        "preview_problem_list_for_clinician_review",
        "inspect_evidence_sources",
        "request_more_history_or_diagnostic_data",
        "revise_problem_list_preview_without_persistence",
        "prepare_differential_diagnosis_candidates_next_stage_only_after_go",
    ]
    blocked_actions = [
        "generate_final_diagnosis",
        "generate_confirmed_diagnosis",
        "generate_definitive_diagnosis",
        "create_treatment_plan",
        "write_prescription",
        "return_drug_dose",
        "return_drug_route_or_frequency",
        "release_to_client",
        "write_case_or_diagnostic_report",
        "write_observation_or_imaging_study",
        "write_audit_log",
        "call_external_ai_provider",
        "execute_real_lab_lis_dicom_device_ingest",
    ]

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "problem_count": len(problem_list_preview),
        "evidence_source_count": len(aggregate_evidence),
        "missing_core_sources": missing_core_sources,
        "dangerous_requested_action_blocked": dangerous_requested,
        "blocked_request_keys": blocked_request_keys,
        "requires_clinician_review": True,
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
        "blocks_database_write": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription": True,
        "blocks_drug_dose": True,
    }

    safety = diagnostic_problem_list_safety_flags()
    return {
        "mode": DIAGNOSTIC_ASSISTANCE_PROBLEM_LIST_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "decision": decision,
        "source_presence": source_presence,
        "problem_list_preview": problem_list_preview,
        "evidence_sources": aggregate_evidence,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
