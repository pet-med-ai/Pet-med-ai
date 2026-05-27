from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
INTAKE_DIR = ROOT / "knowledge-base" / "exotics" / "intake"


class ExoticIntakeTemplateError(RuntimeError):
    pass


def _load_json(filename: str) -> Dict[str, Any]:
    path = INTAKE_DIR / filename
    if not path.exists():
        raise ExoticIntakeTemplateError(f"exotic intake template not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ExoticIntakeTemplateError(f"{filename} must be a JSON object")
    return data


def _validate_string_list(template_key: str, field: str, value: Any, allow_empty: bool = False) -> None:
    if not isinstance(value, list):
        raise ExoticIntakeTemplateError(f"{template_key}.{field} must be a list")
    if not allow_empty and not value:
        raise ExoticIntakeTemplateError(f"{template_key}.{field} must not be empty")
    for idx, item in enumerate(value, 1):
        if not isinstance(item, str) or not item.strip():
            raise ExoticIntakeTemplateError(f"{template_key}.{field}[{idx}] must be a non-empty string")


def _validate_question(template_key: str, section_key: str, item: Any, idx: int) -> None:
    if not isinstance(item, dict):
        raise ExoticIntakeTemplateError(f"{template_key}.{section_key}.questions[{idx}] must be an object")
    for field in ("key", "label", "answer_type"):
        if not isinstance(item.get(field), str) or not item.get(field, "").strip():
            raise ExoticIntakeTemplateError(f"{template_key}.{section_key}.questions[{idx}].{field} must be a non-empty string")
    if "required" in item and not isinstance(item.get("required"), bool):
        raise ExoticIntakeTemplateError(f"{template_key}.{section_key}.questions[{idx}].required must be boolean")
    if "trigger_features" in item:
        _validate_string_list(template_key, f"{section_key}.questions[{idx}].trigger_features", item.get("trigger_features"), allow_empty=True)
    if "clinical_reason" in item and not isinstance(item.get("clinical_reason"), str):
        raise ExoticIntakeTemplateError(f"{template_key}.{section_key}.questions[{idx}].clinical_reason must be a string")


def _validate_template(template_key: str, data: Dict[str, Any]) -> None:
    for field in ("key", "label", "summary"):
        if not isinstance(data.get(field), str) or not data.get(field, "").strip():
            raise ExoticIntakeTemplateError(f"{template_key}.{field} must be a non-empty string")
    if data.get("key") != template_key:
        raise ExoticIntakeTemplateError(f"{template_key}.key mismatch: {data.get('key')!r}")
    _validate_string_list(template_key, "species_scope", data.get("species_scope"))
    _validate_string_list(template_key, "feature_flags", data.get("feature_flags"), allow_empty=True)
    _validate_string_list(template_key, "red_flag_prompts", data.get("red_flag_prompts"), allow_empty=True)

    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        raise ExoticIntakeTemplateError(f"{template_key}.sections must be a non-empty list")
    for idx, section in enumerate(sections, 1):
        if not isinstance(section, dict):
            raise ExoticIntakeTemplateError(f"{template_key}.sections[{idx}] must be an object")
        for field in ("key", "title", "priority"):
            if not isinstance(section.get(field), str) or not section.get(field, "").strip():
                raise ExoticIntakeTemplateError(f"{template_key}.sections[{idx}].{field} must be a non-empty string")
        questions = section.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ExoticIntakeTemplateError(f"{template_key}.sections[{idx}].questions must be a non-empty list")
        for q_idx, question in enumerate(questions, 1):
            _validate_question(template_key, str(section.get("key")), question, q_idx)


def _validate_index(data: Dict[str, Any]) -> None:
    templates = data.get("templates")
    if not isinstance(templates, list) or not templates:
        raise ExoticIntakeTemplateError("intake/index.json templates must be a non-empty list")
    for key in templates:
        if not isinstance(key, str) or not key.strip():
            raise ExoticIntakeTemplateError("intake/index.json templates must be non-empty strings")


@lru_cache(maxsize=1)
def load_intake_index() -> Dict[str, Any]:
    data = _load_json("index.json")
    _validate_index(data)
    return data


@lru_cache(maxsize=1)
def load_intake_templates() -> Dict[str, Dict[str, Any]]:
    index = load_intake_index()
    templates: Dict[str, Dict[str, Any]] = {}
    for key in index.get("templates", []):
        data = _load_json(f"{key}.json")
        _validate_template(key, data)
        templates[key] = data
    return templates


def reload_intake_templates() -> Dict[str, Dict[str, Any]]:
    load_intake_index.cache_clear()
    load_intake_templates.cache_clear()
    return load_intake_templates()


def intake_key_for_features(features: Dict[str, Any]) -> str:
    try:
        from backend.exotic_knowledge import kb_key_for_features
    except ModuleNotFoundError:
        from exotic_knowledge import kb_key_for_features

    key = kb_key_for_features(features)
    if key in load_intake_templates():
        return key
    return ""


def _question_payload(question: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    triggers = question.get("trigger_features") or []
    triggered = bool(triggers and any(bool(features.get(name)) for name in triggers))
    payload = {
        "key": question.get("key"),
        "label": question.get("label"),
        "answer_type": question.get("answer_type"),
        "required": bool(question.get("required")),
        "priority": "triggered" if triggered else "routine",
        "clinical_reason": question.get("clinical_reason") or "",
        "trigger_features": triggers,
        "triggered": triggered,
    }
    for optional in ("options", "unit", "placeholder"):
        if optional in question:
            payload[optional] = question[optional]
    return payload


def _section_payload(section: Dict[str, Any], features: Dict[str, Any]) -> Dict[str, Any]:
    questions = [_question_payload(q, features) for q in section.get("questions", [])]
    triggered_count = sum(1 for q in questions if q.get("triggered"))
    required_count = sum(1 for q in questions if q.get("required"))
    return {
        "key": section.get("key"),
        "title": section.get("title"),
        "priority": section.get("priority"),
        "triggered_count": triggered_count,
        "required_count": required_count,
        "questions": questions,
    }


def build_structured_intake(features: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(features, dict):
        return None
    if not features.get("is_exotic"):
        return None

    template_key = intake_key_for_features(features)
    if not template_key:
        return None

    template = load_intake_templates().get(template_key)
    if not template:
        return None

    active_features = [
        name for name in template.get("feature_flags", [])
        if bool(features.get(name))
    ]
    sections = [_section_payload(section, features) for section in template.get("sections", [])]

    return {
        "version": load_intake_index().get("version") or "exotic-structured-intake-v1",
        "template_key": template_key,
        "label": template.get("label"),
        "summary": template.get("summary"),
        "species_scope": template.get("species_scope") or [],
        "species_context": features.get("species_context") or {},
        "active_features": active_features,
        "red_flag_prompts": template.get("red_flag_prompts") or [],
        "sections": sections,
        "disclaimer": "结构化问诊模板用于采集关键病史、饲养环境和红旗信息，不替代兽医临床检查。",
    }
