# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE = "diagnostic_reasoning_evidence_trace_v1"

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

BOUNDARY_TERM_PATTERN = re.compile(
    r"\b(final diagnosis|confirmed diagnosis|definitive diagnosis|diagnostic conclusion|treatment plan|prescription|drug dose|dosage|client-facing conclusion)\b",
    re.IGNORECASE,
)

TREATMENT_ACTION_PATTERN = re.compile(
    r"\b(prescribe|administer|dispense|inject|injection|tablet|capsule|infusion|sedation protocol|anesthesia protocol)\b",
    re.IGNORECASE,
)

SEVERITY_ORDER = {
    "unknown": 0,
    "low": 1,
    "medium": 2,
    "moderate": 2,
    "high": 3,
    "critical": 4,
}

SYSTEM_TERMS: Dict[str, Tuple[str, ...]] = {
    "gastrointestinal": (
        "vomit", "emesis", "diarrhea", "melena", "hematemesis", "anorexia",
        "appetite", "abdominal", "foreign body", "gastro", "stool", "nausea",
    ),
    "hepatobiliary": (
        "alt", "ast", "alp", "ggt", "bilirubin", "icterus", "jaundice",
        "liver", "hepatic", "bile", "gallbladder",
    ),
    "renal_urinary": (
        "creatinine", "bun", "azotemia", "usg", "urine", "urinary", "renal",
        "kidney", "anuria", "pollakiuria", "hematuria", "proteinuria",
    ),
    "pancreatic_gastrointestinal": (
        "pancreas", "pancreatic", "pancreatitis", "lipase", "cpl", "fpl",
        "abdominal pain", "vomiting", "nausea",
    ),
    "endocrine_metabolic": (
        "glucose", "hypoglycemia", "hyperglycemia", "ketone", "diabetes",
        "thyroid", "cortisol", "electrolyte", "sodium", "potassium", "calcium",
    ),
    "infectious_inflammatory": (
        "fever", "pyrexia", "leukocytosis", "neutrophilia", "left shift",
        "inflammation", "infectious", "infection", "abscess", "sepsis",
    ),
    "respiratory_cardiovascular": (
        "cough", "dyspnea", "tachypnea", "respiratory", "cyanosis", "murmur",
        "arrhythmia", "cardiac", "heart", "pleural", "pulmonary",
    ),
    "neurologic": (
        "seizure", "ataxia", "paresis", "paralysis", "vestibular", "tremor",
        "neurologic", "neurological", "mentation", "collapse",
    ),
    "toxicity_exposure": (
        "toxin", "toxic", "poison", "ingestion", "exposure", "garbage",
        "plant", "chemical", "chocolate", "rodenticide",
    ),
    "imaging_pattern": (
        "radiograph", "ultrasound", "x-ray", "ct", "mri", "imaging", "mass",
        "lesion", "effusion", "obstruction", "opacity",
    ),
}

GENERIC_MISSING_EVIDENCE = (
    "history details may be incomplete",
    "physical examination findings may be incomplete",
    "serial trend data may be unavailable",
    "clinician interpretation has not been persisted",
)


def diagnostic_reasoning_evidence_trace_safety_flags() -> Dict[str, Any]:
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
        "persists_reasoning_trace": False,
        "generates_final_diagnosis": False,
        "generates_confirmed_diagnosis": False,
        "generates_definitive_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "returns_probability": False,
        "returns_numeric_confidence": False,
        "ranks_candidates_as_final_diagnosis": False,
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
        "not_a_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_text(value: Any, max_len: int = 280) -> str:
    text = _text(value)
    if not text:
        return ""
    text = DOSE_OR_ROUTE_PATTERN.sub("[redacted_dose_route_frequency]", text)
    for term in DRUG_TERMS:
        text = re.sub(r"\b" + re.escape(term) + r"\b", "[redacted_drug_reference]", text, flags=re.IGNORECASE)
    text = BOUNDARY_TERM_PATTERN.sub("[redacted_boundary_term]", text)
    text = TREATMENT_ACTION_PATTERN.sub("[redacted_treatment_action]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_len:
        return text[: max_len - 3].rstrip() + "..."
    return text


def _slug(value: Any, fallback: str) -> str:
    text = _safe_text(value, max_len=80).lower()
    text = re.sub(r"[^a-z0-9_\-]+", "_", text).strip("_")
    return text or fallback


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _first_list(payload: Dict[str, Any], keys: Sequence[str]) -> List[Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested_key in keys:
                nested = value.get(nested_key)
                if isinstance(nested, list):
                    return nested
    summaries = payload.get("summaries")
    if isinstance(summaries, dict):
        for key in keys:
            value = summaries.get(key)
            if isinstance(value, list):
                return value
    return []


def _normalize_severity(value: Any) -> str:
    text = _text(value).lower()
    if text in ("critical", "emergency"):
        return "critical"
    if text in ("high", "severe"):
        return "high"
    if text in ("medium", "moderate"):
        return "medium"
    if text in ("low", "mild"):
        return "low"
    return "unknown"


def _max_severity(values: Sequence[Any]) -> str:
    current = "unknown"
    current_score = 0
    for value in values:
        normalized = _normalize_severity(value)
        score = SEVERITY_ORDER.get(normalized, 0)
        if score > current_score:
            current = normalized
            current_score = score
    return current


def _source_from_dict(raw: Dict[str, Any], default_source_type: str, index: int, relation: str) -> Dict[str, Any]:
    source_type = _safe_text(raw.get("source_type") or raw.get("type") or default_source_type, max_len=80) or default_source_type
    field = _safe_text(raw.get("field") or raw.get("name") or raw.get("code") or raw.get("display_name"), max_len=80)
    snippet = ""
    for key in ("snippet", "summary", "title", "finding", "interpretation", "text", "value_text", "problem_title"):
        snippet = _safe_text(raw.get(key), max_len=320)
        if snippet:
            break
    if not snippet:
        snippet = "source_present"
    return {
        "evidence_source_id": _safe_text(raw.get("evidence_source_id") or raw.get("source_id") or raw.get("id") or ("evidence-%03d" % index), max_len=80),
        "source_type": source_type,
        "field": field or "unspecified",
        "snippet": snippet,
        "relation": relation,
        "requires_clinician_review": True,
        "not_client_facing": True,
    }


def _evidence_from_raw(raw: Any, default_source_type: str, index: int, relation: str) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return _source_from_dict(raw, default_source_type, index, relation)
    return {
        "evidence_source_id": "evidence-%03d" % index,
        "source_type": default_source_type,
        "field": "text",
        "snippet": _safe_text(raw, max_len=320) or "source_present",
        "relation": relation,
        "requires_clinician_review": True,
        "not_client_facing": True,
    }


def _dedup_sources(sources: Sequence[Dict[str, Any]], limit: int = 60) -> List[Dict[str, Any]]:
    dedup: List[Dict[str, Any]] = []
    seen = set()
    for item in sources:
        key = (
            item.get("source_type"),
            item.get("field"),
            item.get("snippet"),
            item.get("relation"),
        )
        if key in seen:
            continue
        seen.add(key)
        copy = dict(item)
        copy["evidence_source_id"] = copy.get("evidence_source_id") or ("evidence-%03d" % (len(dedup) + 1))
        dedup.append(copy)
        if len(dedup) >= limit:
            break
    return dedup


def _collect_problem_sources(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    problems = _first_list(payload, ("problem_list_preview", "problems_preview", "problems", "problem_list"))
    sources: List[Dict[str, Any]] = []
    normalized_problems: List[Dict[str, Any]] = []
    index = 1
    for problem_index, problem in enumerate(problems, 1):
        if not isinstance(problem, dict):
            problem = {"title": problem}
        problem_id = _safe_text(problem.get("problem_id") or problem.get("id") or ("problem-%03d" % problem_index), max_len=80)
        title = _safe_text(problem.get("title") or problem.get("problem") or problem.get("label") or "problem requires clinician review", max_len=220)
        severity = _normalize_severity(problem.get("severity_hint"))
        normalized_problem = {
            "problem_id": problem_id,
            "title": title,
            "category": _safe_text(problem.get("category") or "unspecified", max_len=80),
            "severity_hint": severity,
        }
        normalized_problems.append(normalized_problem)
        sources.append({
            "evidence_source_id": "problem-%03d" % problem_index,
            "source_type": "problem_list_preview",
            "field": normalized_problem["category"] or "problem",
            "snippet": title or "problem_present",
            "relation": "problem_context",
            "problem_id": problem_id,
            "requires_clinician_review": True,
            "not_client_facing": True,
        })
        index += 1
        for raw_source in _as_list(problem.get("evidence_sources")):
            if raw_source in (None, ""):
                continue
            source = _evidence_from_raw(raw_source, "problem_list_preview", index, "problem_support")
            source["problem_id"] = problem_id
            source["problem_title"] = title
            sources.append(source)
            index += 1
    return _dedup_sources(sources), normalized_problems


def _collect_summary_sources(payload: Dict[str, Any], start_index: int) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    index = start_index
    summary_specs = [
        ("lab_abnormal_summary", ("lab_summary", "ai_lab_summary", "lab_abnormal_summary")),
        ("imaging_report_summary", ("imaging_summary", "ai_imaging_summary", "imaging_report_summary")),
        ("clinician_review_workflow", ("clinician_review_workflow", "review_workflow")),
        ("treatment_boundary", ("treatment_boundary", "treatment_recommendation_boundary")),
        ("drug_dose_safety_framework", ("drug_dose_safety", "drug_dose_framework")),
        ("drug_dose_kb_safety_shell", ("drug_dose_kb_review", "drug_dose_knowledge_base_review")),
    ]
    for source_type, keys in summary_specs:
        value = None
        for key in keys:
            if isinstance(payload.get(key), dict):
                value = payload.get(key)
                break
        summaries = payload.get("summaries")
        if value is None and isinstance(summaries, dict):
            for key in keys:
                if isinstance(summaries.get(key), dict):
                    value = summaries.get(key)
                    break
        if not isinstance(value, dict):
            continue
        text = ""
        for key in ("headline", "summary", "impression", "overall_status", "decision", "status"):
            text = _safe_text(value.get(key), max_len=320)
            if text:
                break
        if text:
            sources.append({
                "evidence_source_id": "summary-%03d" % index,
                "source_type": source_type,
                "field": "summary",
                "snippet": text,
                "relation": "summary_context",
                "requires_clinician_review": True,
                "not_client_facing": True,
            })
            index += 1
        for list_key in ("abnormal_findings", "review_recommendations", "review_items", "source_notes"):
            for raw_item in _as_list(value.get(list_key)):
                if raw_item in (None, ""):
                    continue
                sources.append(_evidence_from_raw(raw_item, source_type, index, "summary_detail"))
                index += 1
    return _dedup_sources(sources)


def _candidate_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_candidates = _first_list(
        payload,
        (
            "differential_diagnosis_candidates_preview",
            "differential_candidates_preview",
            "differential_candidates",
            "candidate_differentials",
            "candidates",
        ),
    )
    candidates: List[Dict[str, Any]] = []
    for index, raw in enumerate(raw_candidates, 1):
        if isinstance(raw, dict):
            candidates.append(raw)
        else:
            candidates.append({"candidate_label": raw, "candidate_key": "candidate-%03d" % index})
    return candidates[:20]


def _derived_candidates_from_sources(sources: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    combined = " ".join(_text(item.get("snippet")) for item in sources).lower()
    derived: List[Dict[str, Any]] = []
    label_map = {
        "gastrointestinal": "Gastrointestinal process candidate",
        "hepatobiliary": "Hepatobiliary involvement candidate",
        "renal_urinary": "Renal or urinary involvement candidate",
        "pancreatic_gastrointestinal": "Pancreatic or adjacent gastrointestinal involvement candidate",
        "endocrine_metabolic": "Endocrine or metabolic disturbance candidate",
        "infectious_inflammatory": "Infectious or inflammatory process candidate",
        "respiratory_cardiovascular": "Respiratory or cardiovascular involvement candidate",
        "neurologic": "Neurologic or neuromuscular involvement candidate",
        "toxicity_exposure": "Toxicity or exposure-related candidate",
        "imaging_pattern": "Imaging-lesion-driven candidate",
    }
    for category, terms in SYSTEM_TERMS.items():
        if any(term in combined for term in terms):
            derived.append({
                "candidate_key": category + "_derived_candidate",
                "candidate_label": label_map.get(category, category.replace("_", " ").title()),
                "system_category": category,
                "derived_from_problem_list": True,
            })
    if not derived and sources:
        derived.append({
            "candidate_key": "unmapped_problem_context_candidate",
            "candidate_label": "Unmapped problem-context candidate for clinician review",
            "system_category": "unmapped",
            "derived_from_problem_list": True,
        })
    return derived[:8]


def _candidate_terms(candidate: Dict[str, Any]) -> Tuple[str, ...]:
    category = _text(candidate.get("system_category") or candidate.get("category")).lower()
    terms: List[str] = []
    if category in SYSTEM_TERMS:
        terms.extend(SYSTEM_TERMS[category])
    label = _safe_text(candidate.get("candidate_label") or candidate.get("title") or candidate.get("label"), max_len=160).lower()
    for token in re.split(r"[^a-z0-9]+", label):
        if len(token) >= 4:
            terms.append(token)
    key = _safe_text(candidate.get("candidate_key") or candidate.get("candidate_id"), max_len=100).lower()
    for token in re.split(r"[^a-z0-9]+", key):
        if len(token) >= 4:
            terms.append(token)
    dedup: List[str] = []
    seen = set()
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            dedup.append(term)
    return tuple(dedup)


def _source_matches_candidate(source: Dict[str, Any], candidate: Dict[str, Any]) -> bool:
    haystack = " ".join([
        _text(source.get("source_type")),
        _text(source.get("field")),
        _text(source.get("snippet")),
        _text(source.get("problem_title")),
    ]).lower()
    terms = _candidate_terms(candidate)
    if not terms:
        return True
    return any(term in haystack for term in terms)


def _candidate_support_sources(candidate: Dict[str, Any], all_sources: Sequence[Dict[str, Any]], trace_index: int) -> List[Dict[str, Any]]:
    support: List[Dict[str, Any]] = []
    base_index = trace_index * 100
    for idx, raw in enumerate(_as_list(candidate.get("supporting_evidence_sources")), 1):
        if raw in (None, ""):
            continue
        support.append(_evidence_from_raw(raw, "differential_candidate", base_index + idx, "candidate_support"))
    for source in all_sources:
        if _source_matches_candidate(source, candidate):
            support.append(dict(source))
    if not support:
        for source in all_sources[:3]:
            support.append(dict(source))
    return _dedup_sources(support, limit=10)


def _candidate_missing_or_contradicting(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    raw_items = []
    raw_items.extend(_as_list(candidate.get("contradicting_or_missing_evidence")))
    raw_items.extend(_as_list(candidate.get("missing_evidence")))
    raw_items.extend(_as_list(candidate.get("contradicting_evidence")))
    for idx, raw in enumerate(raw_items, 1):
        if raw in (None, ""):
            continue
        if isinstance(raw, dict):
            text = _safe_text(raw.get("snippet") or raw.get("summary") or raw.get("item") or raw.get("text"), max_len=240)
            evidence_type = _safe_text(raw.get("type") or raw.get("relation") or "missing_or_contradicting", max_len=80)
        else:
            text = _safe_text(raw, max_len=240)
            evidence_type = "missing_or_contradicting"
        if text:
            items.append({
                "item_id": "gap-%03d" % idx,
                "type": evidence_type,
                "description": text,
                "requires_clinician_review": True,
            })
    if not items:
        for idx, text in enumerate(GENERIC_MISSING_EVIDENCE, 1):
            items.append({
                "item_id": "gap-%03d" % idx,
                "type": "missing_context",
                "description": text,
                "requires_clinician_review": True,
            })
    return items[:8]


def _evidence_fit_hint(support_count: int, missing_count: int, candidate: Dict[str, Any]) -> str:
    existing = _text(candidate.get("evidence_fit_hint"))
    allowed = {
        "strong_signal_for_review",
        "moderate_signal_for_review",
        "limited_signal_for_review",
        "insufficient_signal",
    }
    if existing in allowed and support_count > 0:
        return existing
    if support_count >= 3 and missing_count <= 4:
        return "strong_signal_for_review"
    if support_count >= 2:
        return "moderate_signal_for_review"
    if support_count == 1:
        return "limited_signal_for_review"
    return "insufficient_signal"


def _review_questions(candidate_label: str, support_count: int, severity_hint: str) -> List[str]:
    questions = [
        "Do the listed evidence sources actually support this candidate in the full clinical context?",
        "What key history, examination, laboratory, or imaging details are missing before clinician interpretation?",
        "Are there contradictions that should lower the clinician's concern for this candidate?",
    ]
    if severity_hint in ("high", "critical"):
        questions.append("Does the severity context require urgent clinician triage or escalation?")
    if support_count <= 1:
        questions.append("Is the evidence too limited to keep this candidate on the clinician review list?")
    return questions[:5]


def _reasoning_steps(support_sources: Sequence[Dict[str, Any]], missing_items: Sequence[Dict[str, Any]], fit_hint: str) -> List[Dict[str, Any]]:
    source_refs = [item.get("evidence_source_id") for item in support_sources if item.get("evidence_source_id")]
    steps = [
        {
            "step": 1,
            "trace_type": "source_collection",
            "statement": "Structured problem, summary, and candidate-preview sources were gathered for clinician review.",
            "evidence_source_refs": source_refs[:10],
            "requires_clinician_review": True,
        },
        {
            "step": 2,
            "trace_type": "qualitative_support_mapping",
            "statement": "Supporting signals were mapped qualitatively without probability or numeric confidence.",
            "evidence_source_refs": source_refs[:10],
            "evidence_fit_hint": fit_hint,
            "requires_clinician_review": True,
        },
        {
            "step": 3,
            "trace_type": "gap_and_contradiction_check",
            "statement": "Missing or potentially contradicting context was listed as review questions rather than a conclusion.",
            "missing_or_contradicting_item_count": len(missing_items),
            "requires_clinician_review": True,
        },
        {
            "step": 4,
            "trace_type": "boundary_check",
            "statement": "Trace remains preview-only and must stay inside diagnostic assistance boundaries; it is not client-facing.",
            "requires_clinician_review": True,
        },
    ]
    return steps


def build_diagnostic_reasoning_evidence_trace(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a dry-run diagnostic reasoning evidence trace preview.

    The trace is a clinician-review aid only. It does not persist data, create audit log
    rows, create final diagnoses, rank diagnoses as confirmed, create treatment plans,
    write prescriptions, return drug dosing, or call external AI/providers.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    problem_sources, normalized_problems = _collect_problem_sources(payload)
    summary_sources = _collect_summary_sources(payload, len(problem_sources) + 1)
    all_sources = _dedup_sources(list(problem_sources) + list(summary_sources), limit=80)

    candidates = _candidate_list(payload)
    candidate_input_present = bool(candidates)
    if not candidates:
        candidates = _derived_candidates_from_sources(all_sources)

    traces: List[Dict[str, Any]] = []
    severity_inputs = [problem.get("severity_hint") for problem in normalized_problems]
    for trace_index, candidate in enumerate(candidates[:12], 1):
        candidate_key = _slug(candidate.get("candidate_key") or candidate.get("candidate_id"), "candidate_%03d" % trace_index)
        candidate_label = _safe_text(
            candidate.get("candidate_label") or candidate.get("title") or candidate.get("label") or candidate_key.replace("_", " ").title(),
            max_len=180,
        )
        system_category = _safe_text(candidate.get("system_category") or candidate.get("category") or "unspecified", max_len=80)
        support_sources = _candidate_support_sources(candidate, all_sources, trace_index)
        missing_items = _candidate_missing_or_contradicting(candidate)
        candidate_severity = _normalize_severity(candidate.get("severity_hint"))
        severity_hint = candidate_severity if candidate_severity != "unknown" else _max_severity(severity_inputs)
        fit_hint = _evidence_fit_hint(len(support_sources), len(missing_items), candidate)
        trace = {
            "trace_id": "trace-%03d" % trace_index,
            "candidate_key": candidate_key,
            "candidate_label": candidate_label,
            "system_category": system_category,
            "evidence_fit_hint": fit_hint,
            "severity_hint": severity_hint,
            "supporting_evidence_sources": support_sources,
            "contradicting_or_missing_evidence": missing_items,
            "reasoning_trace_steps": _reasoning_steps(support_sources, missing_items, fit_hint),
            "review_questions": _review_questions(candidate_label, len(support_sources), severity_hint),
            "requires_clinician_review": True,
            "clinician_signoff_required": True,
            "not_a_diagnosis": True,
            "not_a_final_diagnosis": True,
            "not_a_confirmed_diagnosis": True,
            "not_a_definitive_diagnosis": True,
            "not_a_diagnostic_conclusion": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_a_drug_dose": True,
            "not_client_facing": True,
        }
        traces.append(trace)

    if not all_sources:
        decision = "awaiting_problem_list_or_candidate_sources"
    elif not candidate_input_present:
        decision = "derived_trace_preview_requires_clinician_review"
    else:
        decision = "evidence_trace_preview_requires_clinician_review"

    allowed_actions = [
        "review_evidence_trace_preview",
        "request_problem_list_revision",
        "request_candidate_revision",
        "document_missing_evidence_questions_preview_only",
        "prepare_case_detail_ui_preview_without_persistence",
    ]
    blocked_actions = [
        "persist_reasoning_trace",
        "write_audit_log",
        "create_final_diagnosis",
        "create_confirmed_diagnosis",
        "create_definitive_diagnosis",
        "return_probability_or_numeric_confidence",
        "create_treatment_plan",
        "write_prescription",
        "return_drug_dose_route_or_frequency",
        "release_to_client",
        "call_external_ai_provider",
    ]

    quality_gate = {
        "status": "PASS",
        "decision": decision,
        "trace_count": len(traces),
        "evidence_source_count": len(all_sources),
        "candidate_input_present": candidate_input_present,
        "problem_count": len(normalized_problems),
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "blocks_persistence": True,
        "blocks_audit_log_write": True,
        "blocks_final_diagnosis": True,
        "blocks_probability": True,
        "blocks_numeric_confidence": True,
        "blocks_treatment_plan": True,
        "blocks_prescription_write": True,
        "blocks_drug_dose_route_frequency": True,
        "blocks_client_release": True,
    }

    safety = diagnostic_reasoning_evidence_trace_safety_flags()
    return {
        "mode": DIAGNOSTIC_REASONING_EVIDENCE_TRACE_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "source_readiness": {
            "problem_list_preview_present": bool(normalized_problems),
            "differential_candidate_preview_present": candidate_input_present,
            "summary_source_count": len(summary_sources),
            "evidence_source_count": len(all_sources),
            "dry_run_only": True,
        },
        "evidence_source_index": all_sources,
        "diagnostic_reasoning_evidence_trace_preview": traces,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
