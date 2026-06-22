# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE = "differential_diagnosis_candidates_v1"

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

FORBIDDEN_CLINICAL_ACTION_PATTERN = re.compile(
    r"\b(final diagnosis|confirmed diagnosis|definitive diagnosis|diagnostic conclusion|treatment plan|prescription|drug dose|dosage|route|frequency|client-facing)\b",
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

RULES: List[Dict[str, Any]] = [
    {
        "candidate_key": "gastrointestinal_process_candidate",
        "candidate_label": "Gastrointestinal disease process candidate",
        "system_category": "gastrointestinal",
        "terms": ("vomit", "emesis", "diarrhea", "melena", "hematemesis", "anorexia", "appetite", "abdominal", "foreign body", "gastro", "stool"),
        "review_note": "GI-pattern signal only; clinician must decide whether this is relevant to the case.",
    },
    {
        "candidate_key": "hepatobiliary_process_candidate",
        "candidate_label": "Hepatobiliary involvement candidate",
        "system_category": "hepatobiliary",
        "terms": ("alt", "ast", "alp", "ggt", "bilirubin", "icterus", "jaundice", "liver", "hepatic", "bile", "gallbladder"),
        "review_note": "Hepatobiliary signal only; not a confirmed liver diagnosis.",
    },
    {
        "candidate_key": "renal_or_urinary_process_candidate",
        "candidate_label": "Renal or urinary involvement candidate",
        "system_category": "renal_urinary",
        "terms": ("creatinine", "bun", "azotemia", "usg", "urine", "urinary", "renal", "kidney", "anuria", "pollakiuria", "hematuria", "proteinuria"),
        "review_note": "Renal or urinary signal only; clinician review is required before any conclusion.",
    },
    {
        "candidate_key": "pancreatic_or_adjacent_gi_candidate",
        "candidate_label": "Pancreatic or adjacent gastrointestinal involvement candidate",
        "system_category": "pancreatic_gastrointestinal",
        "terms": ("pancreas", "pancreatic", "pancreatitis", "lipase", "cpl", "fpl", "abdominal pain", "vomiting", "nausea"),
        "review_note": "Pancreatic-adjacent signal only; no treatment or diagnostic order is generated.",
    },
    {
        "candidate_key": "endocrine_or_metabolic_candidate",
        "candidate_label": "Endocrine or metabolic disturbance candidate",
        "system_category": "endocrine_metabolic",
        "terms": ("glucose", "hypoglycemia", "hyperglycemia", "ketone", "diabetes", "thyroid", "cortisol", "electrolyte", "sodium", "potassium", "calcium"),
        "review_note": "Endocrine or metabolic signal only; evidence fit must be checked by the clinician.",
    },
    {
        "candidate_key": "infectious_or_inflammatory_candidate",
        "candidate_label": "Infectious or inflammatory process candidate",
        "system_category": "infectious_inflammatory",
        "terms": ("fever", "pyrexia", "leukocytosis", "neutrophilia", "left shift", "inflammation", "infectious", "infection", "abscess", "sepsis"),
        "review_note": "Inflammatory or infectious signal only; no antimicrobial recommendation is produced.",
    },
    {
        "candidate_key": "respiratory_or_cardiovascular_candidate",
        "candidate_label": "Respiratory or cardiovascular involvement candidate",
        "system_category": "respiratory_cardiovascular",
        "terms": ("cough", "dyspnea", "tachypnea", "respiratory", "cyanosis", "murmur", "arrhythmia", "cardiac", "heart", "pleural", "pulmonary"),
        "review_note": "Respiratory/cardiovascular signal only; urgent clinician triage may be needed.",
    },
    {
        "candidate_key": "neurologic_or_neuromuscular_candidate",
        "candidate_label": "Neurologic or neuromuscular involvement candidate",
        "system_category": "neurologic",
        "terms": ("seizure", "ataxia", "paresis", "paralysis", "vestibular", "tremor", "neurologic", "neurological", "mentation", "collapse"),
        "review_note": "Neurologic signal only; not a final neurologic diagnosis.",
    },
    {
        "candidate_key": "toxic_or_exposure_candidate",
        "candidate_label": "Toxicity or exposure-related candidate",
        "system_category": "toxicity_exposure",
        "terms": ("toxin", "toxic", "poison", "ingestion", "exposure", "garbage", "plant", "chemical", "chocolate", "rodenticide"),
        "review_note": "Exposure signal only; clinician must confirm exposure history.",
    },
    {
        "candidate_key": "imaging_lesion_pattern_candidate",
        "candidate_label": "Imaging-lesion-driven candidate",
        "system_category": "imaging_pattern",
        "terms": ("radiograph", "ultrasound", "x-ray", "ct", "mri", "imaging", "mass", "lesion", "effusion", "obstruction", "opacity"),
        "review_note": "Imaging pattern signal only; imaging interpretation must be reviewed by a clinician.",
    },
]


def differential_diagnosis_candidates_safety_flags() -> Dict[str, Any]:
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
        "generates_diagnostic_conclusion": False,
        "ranks_candidates_as_final_diagnosis": False,
        "returns_probability": False,
        "returns_numeric_confidence": False,
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
        "differential_candidates_preview_only": True,
        "not_a_diagnosis": True,
        "not_a_final_diagnosis": True,
        "not_a_confirmed_diagnosis": True,
        "not_a_definitive_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
    }


def _text(value: Any) -> str:
    return str(value or "").strip()


def _safe_snippet(value: Any, limit: int = 240) -> str:
    text = _text(value)
    if not text:
        return ""
    text = DOSE_OR_ROUTE_PATTERN.sub("[dose/route/frequency redacted]", text)
    for term in DRUG_TERMS:
        text = re.sub(r"\b" + re.escape(term) + r"\b", "[medication term redacted]", text, flags=re.IGNORECASE)
    text = FORBIDDEN_CLINICAL_ACTION_PATTERN.sub("[blocked clinical conclusion/action redacted]", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def _safe_label(value: Any, fallback: str = "clinical signal") -> str:
    return _safe_snippet(value, limit=100) or fallback


def _flatten_texts(value: Any, limit: int = 60) -> List[str]:
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
                    "diagnostic_conclusion", "treatment_plan", "prescription",
                    "drug_dose", "dose", "route", "frequency",
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


def _severity_score(value: Any) -> int:
    text = _text(value).lower()
    mapping = {"unknown": 0, "low": 1, "medium": 2, "moderate": 2, "high": 3, "critical": 4}
    return mapping.get(text, 0)


def _severity_label(score: int) -> str:
    if score >= 4:
        return "critical"
    if score == 3:
        return "high"
    if score == 2:
        return "medium"
    if score == 1:
        return "low"
    return "unknown"


def _severity_from_texts(texts: List[str], default: str = "medium") -> str:
    lowered = " ".join(texts).lower()
    if any(term in lowered for term in CRITICAL_TERMS):
        return "critical"
    if any(term in lowered for term in HIGH_TERMS):
        return "high"
    if lowered:
        return default
    return "unknown"


def _normal_evidence(value: Any, *, source_type: str, field: str, problem_id: str = "") -> Optional[Dict[str, Any]]:
    if isinstance(value, dict):
        source_type = _safe_label(value.get("source_type") or source_type, source_type)
        field = _safe_label(value.get("field") or field, field)
        snippet_value = value.get("snippet")
        if snippet_value is None:
            snippet_value = value.get("summary") or value.get("text") or value.get("value")
        snippet = _safe_snippet(snippet_value)
        source_strength = _safe_label(value.get("source_strength") or "reported", "reported")
    else:
        snippet = _safe_snippet(value)
        source_strength = "reported"
    if not snippet:
        return None
    result = {
        "source_type": source_type,
        "field": field,
        "snippet": snippet,
        "source_strength": source_strength,
    }
    if problem_id:
        result["problem_id"] = problem_id
    return result


def _extract_problem_container(payload: Dict[str, Any]) -> Any:
    for key in ("problem_list_preview", "problems", "problem_items"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    for key in ("problem_list", "diagnostic_problem_list", "problem_list_result", "diagnostic_assistance_problem_list"):
        value = payload.get(key)
        if isinstance(value, dict):
            nested = value.get("problem_list_preview")
            if isinstance(nested, list):
                return nested
    return []


def _problem_items_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_items = _extract_problem_container(payload)
    items: List[Dict[str, Any]] = []

    for index, raw in enumerate(raw_items[:40]):
        problem_id = "problem-%03d" % (index + 1)
        category = "clinical_problem"
        title = "Clinical problem requires clinician review"
        severity_hint = "unknown"
        evidence_sources: List[Dict[str, Any]] = []

        if isinstance(raw, dict):
            problem_id = _safe_label(raw.get("problem_id") or raw.get("id") or problem_id, problem_id)
            category = _safe_label(raw.get("category") or raw.get("problem_category") or category, category)
            title = _safe_label(raw.get("title") or raw.get("label") or raw.get("summary") or title, title)
            severity_hint = _safe_label(raw.get("severity_hint") or raw.get("urgency_hint") or severity_hint, severity_hint)
            source_list = raw.get("evidence_sources")
            if isinstance(source_list, list):
                for evidence in source_list[:10]:
                    item = _normal_evidence(evidence, source_type="problem_list", field="evidence", problem_id=problem_id)
                    if item:
                        evidence_sources.append(item)
            if not evidence_sources:
                for text in _flatten_texts(raw, limit=6):
                    item = _normal_evidence(text, source_type="problem_list", field="problem_item", problem_id=problem_id)
                    if item:
                        evidence_sources.append(item)
        else:
            title = _safe_label(raw, title)
            severity_hint = _severity_from_texts([title], default="medium")
            item = _normal_evidence(raw, source_type="problem_list", field="problem_item", problem_id=problem_id)
            if item:
                evidence_sources.append(item)

        text_parts = [problem_id, category, title, severity_hint]
        text_parts.extend(evidence.get("snippet", "") for evidence in evidence_sources)
        items.append({
            "problem_id": problem_id,
            "category": category,
            "title": title,
            "severity_hint": severity_hint,
            "evidence_sources": evidence_sources,
            "combined_text": " ".join(part for part in text_parts if part).lower(),
        })

    if items:
        return items

    fallback_evidence: List[Dict[str, Any]] = []
    for field in ("chief_complaint", "presenting_complaint", "history", "dynamic_intake", "lab_summary", "imaging_summary", "clinician_review_workflow"):
        value = payload.get(field)
        if value in (None, ""):
            continue
        if isinstance(value, (dict, list)):
            texts = _flatten_texts(value, limit=8)
        else:
            texts = [_safe_snippet(value)]
        for text in texts[:4]:
            item = _normal_evidence(text, source_type="fallback_input", field=field, problem_id="problem-001")
            if item:
                fallback_evidence.append(item)
    if fallback_evidence:
        joined = " ".join(evidence["snippet"] for evidence in fallback_evidence)
        return [{
            "problem_id": "problem-001",
            "category": "fallback_clinical_signal",
            "title": "Clinical signals require clinician review before differential candidates",
            "severity_hint": _severity_from_texts([joined], default="medium"),
            "evidence_sources": fallback_evidence[:10],
            "combined_text": joined.lower(),
        }]
    return []


def _matched_terms(rule: Dict[str, Any], text: str) -> List[str]:
    matches: List[str] = []
    for term in rule.get("terms", ()):
        term_text = str(term).lower()
        if term_text and term_text in text:
            matches.append(term_text)
    return matches


def _evidence_fit_hint(evidence_count: int, severity_score: int, matched_term_count: int) -> str:
    if evidence_count >= 4 and matched_term_count >= 2:
        return "strong_signal_for_review"
    if evidence_count >= 2 or severity_score >= 3 or matched_term_count >= 2:
        return "moderate_signal_for_review"
    if evidence_count >= 1:
        return "limited_signal_for_review"
    return "insufficient_signal"


def _review_priority_hint(severity_score: int, evidence_count: int) -> str:
    if severity_score >= 4:
        return "urgent_clinician_review"
    if severity_score >= 3 or evidence_count >= 4:
        return "priority_clinician_review"
    if evidence_count >= 1:
        return "standard_clinician_review"
    return "awaiting_more_information"


def _missing_evidence_notes(candidate_key: str) -> List[str]:
    base = [
        "Physical examination, vital signs, clinician assessment, and complete diagnostic context are not confirmed by this dry-run preview.",
        "Clinician must decide whether this candidate remains relevant, should be revised, or should be discarded.",
    ]
    if candidate_key == "imaging_lesion_pattern_candidate":
        base.append("Imaging interpretation must be reviewed in the source report or viewer by the clinician.")
    if candidate_key in {"hepatobiliary_process_candidate", "renal_or_urinary_process_candidate", "endocrine_or_metabolic_candidate"}:
        base.append("Laboratory pattern relevance must be checked against species, age, reference interval, sample quality, and clinical context.")
    return base


def _add_candidate(
    candidate_map: Dict[str, Dict[str, Any]],
    rule: Dict[str, Any],
    problem: Dict[str, Any],
    terms: List[str],
) -> None:
    key = str(rule["candidate_key"])
    evidence_sources = problem.get("evidence_sources") if isinstance(problem.get("evidence_sources"), list) else []
    if not evidence_sources:
        evidence = _normal_evidence(problem.get("title"), source_type="problem_list", field="title", problem_id=problem.get("problem_id", ""))
        evidence_sources = [evidence] if evidence else []

    existing = candidate_map.get(key)
    if existing is None:
        existing = {
            "candidate_key": key,
            "candidate_label": str(rule["candidate_label"]),
            "system_category": str(rule["system_category"]),
            "review_note": str(rule["review_note"]),
            "related_problem_ids": [],
            "matched_signal_terms": [],
            "supporting_evidence_sources": [],
            "_max_severity_score": 0,
        }
        candidate_map[key] = existing

    problem_id = _safe_label(problem.get("problem_id"), "problem")
    if problem_id not in existing["related_problem_ids"]:
        existing["related_problem_ids"].append(problem_id)

    for term in terms:
        if term not in existing["matched_signal_terms"]:
            existing["matched_signal_terms"].append(term)

    seen_evidence = set(
        (item.get("source_type"), item.get("field"), item.get("snippet"), item.get("problem_id"))
        for item in existing["supporting_evidence_sources"]
    )
    for evidence in evidence_sources[:10]:
        if not isinstance(evidence, dict):
            continue
        marker = (evidence.get("source_type"), evidence.get("field"), evidence.get("snippet"), evidence.get("problem_id"))
        if marker in seen_evidence:
            continue
        seen_evidence.add(marker)
        existing["supporting_evidence_sources"].append(evidence)

    severity_score = max(
        _severity_score(problem.get("severity_hint")),
        _severity_score(_severity_from_texts([problem.get("combined_text", "")], default="unknown")),
    )
    if severity_score > existing["_max_severity_score"]:
        existing["_max_severity_score"] = severity_score


def _fallback_candidate(problem_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not problem_items:
        return None
    evidence_sources: List[Dict[str, Any]] = []
    related_problem_ids: List[str] = []
    max_score = 0
    for problem in problem_items[:8]:
        problem_id = _safe_label(problem.get("problem_id"), "problem")
        if problem_id not in related_problem_ids:
            related_problem_ids.append(problem_id)
        score = _severity_score(problem.get("severity_hint"))
        if score > max_score:
            max_score = score
        for evidence in problem.get("evidence_sources", [])[:4]:
            if isinstance(evidence, dict):
                evidence_sources.append(evidence)
    return {
        "candidate_key": "undifferentiated_clinical_problem_candidate",
        "candidate_label": "Undifferentiated clinical problem candidate",
        "system_category": "undifferentiated",
        "review_note": "Fallback candidate because no deterministic system-pattern rule matched the supplied problem list.",
        "related_problem_ids": related_problem_ids,
        "matched_signal_terms": [],
        "supporting_evidence_sources": evidence_sources[:8],
        "_max_severity_score": max_score,
    }


def _materialize_candidates(candidate_map: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    raw_candidates = list(candidate_map.values())

    def sort_key(item: Dict[str, Any]) -> Tuple[int, int, str]:
        return (
            -int(item.get("_max_severity_score") or 0),
            -len(item.get("supporting_evidence_sources") or []),
            str(item.get("candidate_label") or ""),
        )

    raw_candidates.sort(key=sort_key)
    result: List[Dict[str, Any]] = []
    for index, item in enumerate(raw_candidates[:12]):
        evidence_count = len(item.get("supporting_evidence_sources") or [])
        severity_score = int(item.get("_max_severity_score") or 0)
        matched_terms = item.get("matched_signal_terms") if isinstance(item.get("matched_signal_terms"), list) else []
        candidate_key = str(item.get("candidate_key") or "candidate")
        materialized = {
            "candidate_id": "ddx-candidate-%03d" % (index + 1),
            "candidate_key": candidate_key,
            "candidate_label": _safe_label(item.get("candidate_label"), "Differential candidate preview"),
            "candidate_type": "differential_candidate_preview",
            "system_category": _safe_label(item.get("system_category"), "undifferentiated"),
            "evidence_fit_hint": _evidence_fit_hint(evidence_count, severity_score, len(matched_terms)),
            "review_priority_hint": _review_priority_hint(severity_score, evidence_count),
            "severity_hint": _severity_label(severity_score),
            "related_problem_ids": item.get("related_problem_ids") or [],
            "matched_signal_terms": matched_terms[:10],
            "supporting_evidence_sources": (item.get("supporting_evidence_sources") or [])[:10],
            "contradicting_or_missing_evidence": _missing_evidence_notes(candidate_key),
            "review_note": _safe_snippet(item.get("review_note"), 220),
            "requires_clinician_review": True,
            "clinician_signoff_required": True,
            "not_a_diagnosis": True,
            "not_a_final_diagnosis": True,
            "not_a_confirmed_diagnosis": True,
            "not_a_definitive_diagnosis": True,
            "not_a_treatment_plan": True,
            "not_a_prescription": True,
            "not_client_facing": True,
            "dry_run_only": True,
        }
        result.append(materialized)
    return result


def _dangerous_request_detected(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    blocked_keys: List[str] = []
    for key in (
        "final_diagnosis", "confirmed_diagnosis", "definitive_diagnosis",
        "diagnostic_conclusion", "treatment_plan", "prescription",
        "drug_dose", "drug_route", "drug_frequency", "client_facing_conclusion",
    ):
        if key in payload:
            blocked_keys.append(key)
    requested_action = _text(payload.get("requested_action")).lower()
    if requested_action in {
        "final_diagnosis", "confirm_diagnosis", "confirmed_diagnosis",
        "definitive_diagnosis", "create_treatment_plan", "write_prescription",
        "return_drug_dose", "return_drug_route", "return_drug_frequency",
        "release_to_client", "client_facing_conclusion",
    }:
        blocked_keys.append("requested_action:%s" % requested_action)
    return bool(blocked_keys), blocked_keys


def build_differential_diagnosis_candidates(
    payload: Dict[str, Any],
    *,
    case_id: Optional[int] = None,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build deterministic dry-run differential candidate previews for clinician review.

    This is not an automatic diagnostic engine. It does not produce final, confirmed,
    or definitive diagnoses; does not generate treatment plans or prescriptions; does
    not return drug dose, route, or frequency; does not write database rows; and does
    not call external AI/provider services.
    """
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")

    problem_items = _problem_items_from_payload(payload)
    candidate_map: Dict[str, Dict[str, Any]] = {}

    for problem in problem_items:
        combined_text = _text(problem.get("combined_text")).lower()
        if not combined_text:
            continue
        matched_any = False
        for rule in RULES:
            terms = _matched_terms(rule, combined_text)
            if terms:
                matched_any = True
                _add_candidate(candidate_map, rule, problem, terms)
        if not matched_any and "imaging" in _text(problem.get("category")).lower():
            for rule in RULES:
                if rule.get("candidate_key") == "imaging_lesion_pattern_candidate":
                    _add_candidate(candidate_map, rule, problem, ["imaging"])
                    break

    if not candidate_map:
        fallback = _fallback_candidate(problem_items)
        if fallback:
            candidate_map[str(fallback["candidate_key"])] = fallback

    candidates_preview = _materialize_candidates(candidate_map)
    aggregate_evidence: List[Dict[str, Any]] = []
    seen = set()
    for candidate in candidates_preview:
        for evidence in candidate.get("supporting_evidence_sources", []):
            marker = (evidence.get("source_type"), evidence.get("field"), evidence.get("snippet"), evidence.get("problem_id"))
            if marker in seen:
                continue
            seen.add(marker)
            aggregate_evidence.append(evidence)

    dangerous_requested, blocked_request_keys = _dangerous_request_detected(payload)
    if dangerous_requested:
        decision = "blocked_final_diagnosis_or_treatment_request_candidates_preview_only"
    elif candidates_preview:
        decision = "differential_candidates_preview_requires_clinician_review"
    else:
        decision = "awaiting_problem_list_for_differential_candidates_preview"

    source_presence = {
        "problem_list_preview": bool(problem_items),
        "case_context": isinstance(case_context, dict),
        "chief_complaint": bool(_text(payload.get("chief_complaint") or payload.get("presenting_complaint"))),
        "lab_summary": isinstance(payload.get("lab_summary"), dict) or isinstance(payload.get("ai_lab_summary"), dict),
        "imaging_summary": isinstance(payload.get("imaging_summary"), dict) or isinstance(payload.get("ai_imaging_summary"), dict),
        "clinician_review_workflow": isinstance(payload.get("clinician_review_workflow"), dict) or isinstance(payload.get("review_workflow"), dict),
        "treatment_boundary": isinstance(payload.get("treatment_boundary"), dict),
        "drug_dose_safety_framework": isinstance(payload.get("drug_dose_safety"), dict) or isinstance(payload.get("drug_dose_framework"), dict),
    }

    allowed_actions = [
        "preview_differential_candidates_for_clinician_review",
        "inspect_supporting_evidence_sources",
        "mark_candidate_as_needs_more_evidence_preview_only",
        "remove_or_reword_candidate_preview_without_persistence",
        "prepare_evidence_trace_next_stage_only_after_go",
    ]
    blocked_actions = [
        "generate_final_diagnosis",
        "generate_confirmed_diagnosis",
        "generate_definitive_diagnosis",
        "rank_candidate_as_final_or_most_likely_diagnosis",
        "return_probability_or_numeric_confidence",
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
        "candidate_count": len(candidates_preview),
        "problem_count": len(problem_items),
        "evidence_source_count": len(aggregate_evidence),
        "dangerous_requested_action_blocked": dangerous_requested,
        "blocked_request_keys": blocked_request_keys,
        "requires_clinician_review": True,
        "not_a_diagnosis": True,
        "not_a_final_diagnosis": True,
        "not_a_confirmed_diagnosis": True,
        "not_a_definitive_diagnosis": True,
        "not_a_treatment_plan": True,
        "not_a_prescription": True,
        "not_client_facing": True,
        "blocks_database_write": True,
        "blocks_final_diagnosis": True,
        "blocks_treatment_plan": True,
        "blocks_prescription": True,
        "blocks_drug_dose": True,
        "blocks_numeric_probability": True,
    }

    safety = differential_diagnosis_candidates_safety_flags()
    return {
        "mode": DIFFERENTIAL_DIAGNOSIS_CANDIDATES_MODE,
        "case_id": case_id,
        "case_context": case_context or None,
        "decision": decision,
        "source_presence": source_presence,
        "differential_diagnosis_candidates_preview": candidates_preview,
        "evidence_sources": aggregate_evidence,
        "allowed_actions": allowed_actions,
        "blocked_actions": blocked_actions,
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }
