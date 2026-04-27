from __future__ import annotations

from typing import Any, Callable, Dict, List
import importlib


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _find_callable(module: Any, name: str) -> Callable[..., Any] | None:
    for attr in (name, "run", "predict", "execute"):
        fn = getattr(module, attr, None)
        if callable(fn):
            return fn
    return None


def _call_external_engine(module_name: str, engine_name: str, payload: Dict[str, Any]) -> Any:
    """Try to call external engine module if available; fallback to local implementation."""
    try:
        mod = importlib.import_module(module_name)
    except Exception:
        return None

    fn = _find_callable(mod, engine_name)
    if fn is None:
        return None

    try:
        return fn(payload)
    except TypeError:
        # Backward compatibility with engines that expect text only.
        return fn(payload.get("text", ""))


def _feature_engine_fallback(text: str) -> Dict[str, Any]:
    lowered = (text or "").lower()
    return {
        "text": text,
        "contains_vomit": ("vomit" in lowered) or ("呕吐" in text),
        "contains_blood": ("blood" in lowered) or ("血" in text),
        "contains_diarrhea": ("diarrhea" in lowered) or ("腹泻" in text),
        "contains_toxin": ("toxin" in lowered) or ("毒" in text),
        "contains_pain": ("pain" in lowered) or ("痛" in text),
    }


def _triage_vomiting_call(features: Dict[str, Any]) -> Dict[str, Any]:
    for module_name in ("app.triage_vomiting", "backend.app.triage_vomiting"):
        try:
            mod = importlib.import_module(module_name)
            input_cls = getattr(mod, "VomitingTriageInput")
            triage_fn = getattr(mod, "triage_vomiting")
            inp = input_cls(
                blood="fresh" if features.get("contains_blood") else "none",
                suspected_toxin=bool(features.get("contains_toxin")),
            )
            return triage_fn(inp, locale="zh")
        except Exception:
            continue
    return {"matched_node": None, "priority_level": "routine", "next_questions": [], "signals_hit": []}


def _vomiting_tree_fallback(features: Dict[str, Any]) -> Dict[str, Any]:
    triage = _triage_vomiting_call(features)
    return {
        "matched_node": triage.get("matched_node"),
        "priority_level": triage.get("priority_level", "routine"),
        "next_questions": triage.get("next_questions", []),
        "signals_hit": triage.get("signals_hit", []),
        "raw": triage,
    }


def _risk_engine_fallback(features: Dict[str, Any], tree_result: Dict[str, Any]) -> Dict[str, Any]:
    priority = tree_result.get("priority_level", "routine")
    if priority == "emergency" or features.get("contains_blood"):
        level = "high"
    elif priority == "urgent" or features.get("contains_toxin"):
        level = "medium"
    else:
        level = "low"
    return {"risk_level": level}


def _question_engine_fallback(tree_result: Dict[str, Any]) -> Dict[str, Any]:
    questions = tree_result.get("next_questions", [])
    normalized = []
    for q in questions:
        if isinstance(q, dict):
            normalized.append(q.get("text") or q.get("text_zh") or q.get("id") or "")
        else:
            normalized.append(str(q))
    return {"next_questions": [x for x in normalized if x][:5]}


def _diagnosis_engine_fallback(features: Dict[str, Any], risk: Dict[str, Any]) -> Dict[str, Any]:
    diseases: List[str] = []
    actions: List[str] = []

    if features.get("contains_vomit"):
        diseases += ["胃肠炎", "胃肠异物", "胰腺炎"]
    if features.get("contains_diarrhea"):
        diseases += ["感染性肠炎", "食物不耐受"]
    if features.get("contains_blood"):
        diseases += ["出血性胃肠炎", "胃溃疡"]

    level = risk.get("risk_level", "low")
    if level == "high":
        actions += ["立即就医并进行急诊评估", "优先完成血常规/生化/电解质和腹部影像"]
    elif level == "medium":
        actions += ["尽快门诊复查", "监测精神状态与呕吐频次"]
    else:
        actions += ["居家观察 12-24 小时", "少量多次补液并记录症状变化"]

    return {"diseases": list(dict.fromkeys(diseases)), "actions": actions}


def run_agent(text: str) -> Dict[str, Any]:
    """Semi-automatic orchestrator v1.

    The function tries external engines first, and falls back to local v1 logic.
    Unified output:
    - risk_level
    - tree_path
    - diseases
    - next_questions
    - actions
    """
    # 1) feature_engine
    feature_input = {"text": text}
    features = _call_external_engine("feature_engine", "feature_engine", feature_input)
    if not isinstance(features, dict):
        features = _feature_engine_fallback(text)

    # 2) vomiting_tree
    tree_payload = {"text": text, "features": features}
    tree_result = _call_external_engine("vomiting_tree", "vomiting_tree", tree_payload)
    if not isinstance(tree_result, dict):
        tree_result = _vomiting_tree_fallback(features)

    # 3) risk_engine
    risk_payload = {"text": text, "features": features, "tree": tree_result}
    risk = _call_external_engine("risk_engine", "risk_engine", risk_payload)
    if not isinstance(risk, dict):
        risk = _risk_engine_fallback(features, tree_result)

    # 4) question_engine
    question_payload = {"text": text, "features": features, "tree": tree_result, "risk": risk}
    questions = _call_external_engine("question_engine", "question_engine", question_payload)
    if not isinstance(questions, dict):
        questions = _question_engine_fallback(tree_result)

    # 5) diagnosis_engine
    diagnosis_payload = {
        "text": text,
        "features": features,
        "tree": tree_result,
        "risk": risk,
        "questions": questions,
    }
    diagnosis = _call_external_engine("diagnosis_engine", "diagnosis_engine", diagnosis_payload)
    if not isinstance(diagnosis, dict):
        diagnosis = _diagnosis_engine_fallback(features, risk)

    return {
        "risk_level": risk.get("risk_level", "low"),
        "tree_path": tree_result.get("matched_node") or tree_result.get("tree_path") or "triage.unknown",
        "diseases": _as_list(diagnosis.get("diseases")),
        "next_questions": _as_list(questions.get("next_questions")),
        "actions": _as_list(diagnosis.get("actions")),
    }
