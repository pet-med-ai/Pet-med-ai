from typing import Any, Dict, List, Optional


try:
    from backend.orchestrator import run_agent
except ModuleNotFoundError:
    from orchestrator import run_agent


def _get_value(item: Any, key: str, default: str = "") -> str:
    if isinstance(item, dict):
        return str(item.get(key, default) or "")
    return str(getattr(item, key, default) or "")


def build_dynamic_context(
    text: str,
    answers: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    动态问诊 V1：
    不做数据库会话，只把初始主诉 + 已回答追问拼成上下文，再交给 run_agent。
    """
    parts: List[str] = []

    base_text = (text or "").strip()
    if base_text:
        parts.append(f"初始主诉：{base_text}")

    for idx, item in enumerate(answers or [], start=1):
        question = _get_value(item, "question").strip()
        answer = _get_value(item, "answer").strip()

        if not question and not answer:
            continue

        parts.append(
            f"第{idx}轮追问：{question}\n"
            f"第{idx}轮回答：{answer}"
        )

    return "\n".join(parts).strip()


def _extract_questions(result: Dict[str, Any]) -> List[str]:
    raw = result.get("next_questions") or {}

    if isinstance(raw, list):
        return [str(q) for q in raw if str(q).strip()]

    if isinstance(raw, dict):
        questions = raw.get("questions") or []
        if isinstance(questions, list):
            return [str(q) for q in questions if str(q).strip()]

    return []


def _set_questions(result: Dict[str, Any], questions: List[str]) -> None:
    result["next_questions"] = {
        "questions": questions
    }


def _filter_repeated_questions(
    result: Dict[str, Any],
    answers: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    已经回答过的问题，不再原样重复。
    如果过滤后没有问题，给一个更具体的下一步追问。
    """
    answers = answers or []

    answered_questions = {
        _get_value(item, "question").strip()
        for item in answers
        if _get_value(item, "question").strip()
    }

    current_questions = _extract_questions(result)
    filtered = [
        q for q in current_questions
        if q.strip() and q.strip() not in answered_questions
    ]

    if filtered:
        _set_questions(result, filtered)
        return

    fallback_questions = [
        "目前是否仍在持续呕吐？距离上次呕吐大约多久？",
        "腹部是否仍持续膨大、疼痛，或频繁干呕但吐不出来？",
        "牙龈颜色是否苍白或发紫？四肢是否发凉、站立不稳？",
        "目前能否饮水？饮水后是否马上再次呕吐？",
        "最近一次排尿是什么时候？尿量是否明显减少？",
    ]

    for q in fallback_questions:
        if q not in answered_questions:
            _set_questions(result, [q])
            return

    _set_questions(result, [])


def run_dynamic_consult(
    text: str,
    answers: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    answers = answers or []
    context_text = build_dynamic_context(text, answers)

    result = run_agent(context_text)

    if not isinstance(result, dict):
        return {
            "risk_level": "中",
            "tree_path": [],
            "diseases": {},
            "next_questions": {
                "questions": ["请补充目前精神、食欲、呕吐次数和腹部状态。"]
            },
            "actions": ["建议结合体征与实验室检查进一步判断。"],
            "dynamic": {
                "mode": "dynamic_consult_v1",
                "round": len(answers) + 1,
                "answered_count": len(answers),
                "fallback": True,
            },
        }

    _filter_repeated_questions(result, answers)

    result["dynamic"] = {
        "mode": "dynamic_consult_v1",
        "round": len(answers) + 1,
        "answered_count": len(answers),
    }

    return result
