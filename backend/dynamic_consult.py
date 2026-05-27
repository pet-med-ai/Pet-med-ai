from typing import Any, Dict, List, Optional


try:
    from backend.orchestrator import run_agent
    from backend.species_context import build_species_context
    from backend.exotic_knowledge import fallback_questions_from_text
except ModuleNotFoundError:
    from orchestrator import run_agent
    from species_context import build_species_context
    from exotic_knowledge import fallback_questions_from_text


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


def _join_answer_context(
    text: str,
    answers: Optional[List[Dict[str, str]]] = None,
) -> str:
    parts = [(text or "").strip()]
    for item in answers or []:
        parts.append(_get_value(item, "question").strip())
        parts.append(_get_value(item, "answer").strip())
    return " ".join(p for p in parts if p)


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize_question_text(question: Any) -> str:
    """
    清洗 run_agent 可能生成的机械/病句式追问。
    这里不改变诊断结果，只规范 next_questions 文案。
    """
    q = str(question or "").strip()
    if not q:
        return ""

    q = q.replace("？？", "？").replace("??", "?")
    q = q.replace("持续持续", "持续")
    q = q.replace("逐渐解锁", "逐渐加重")

    if (
        "是否胃肠不呕吐出不出来" in q
        or "不呕吐出不出来" in q
        or "是否胃干呕" in q
        or "胃干呕" in q
    ):
        return "是否出现反复干呕但吐不出来、腹胀加重、流涎或明显不安？"

    if (
        "目前是否持续呕吐" in q
        or "停止呕吐大约多久" in q
        or "距离上次呕吐" in q
        or "持续呕吐大约多久" in q
    ):
        return "目前是否仍在持续呕吐或干呕？最近一次呕吐大约是什么时候？"

    # 明显不是临床问诊语句的内容直接丢弃，后面使用兜底追问。
    bad_fragments = [
        "是否胃肠",
        "是否胃干呕",
        "胃干呕",
        "安置",
        "解锁",
        "默认",
        "undefined",
        "None",
        "null",
    ]
    if _has_any(q, bad_fragments):
        return ""

    if not q.endswith(("？", "?")):
        q = f"{q}？"

    return q


def _is_repeated_question(question: str, answered_questions: List[str]) -> bool:
    q = question.strip()
    if not q:
        return True

    for answered in answered_questions:
        a = answered.strip()
        if not a:
            continue

        if q == a or q in a or a in q:
            return True

        # 语义上避免重复问“精神突然/逐渐”这类已回答问题。
        if "精神" in q and "精神" in a and _has_any(q + a, ["突然", "逐渐", "加重"]):
            return True

        # 避免连续重复问同一类“呕吐多久/上次呕吐”问题。
        q_is_vomit_time = _has_any(q, ["呕吐", "干呕"]) and _has_any(q, ["多久", "几次", "频率", "上次", "最近一次"])
        a_is_vomit_time = _has_any(a, ["呕吐", "干呕"]) and _has_any(a, ["多久", "几次", "频率", "上次", "最近一次"])
        if q_is_vomit_time and a_is_vomit_time:
            return True

    return False


def _fallback_questions(
    text: str,
    answers: Optional[List[Dict[str, str]]] = None,
) -> List[str]:
    context = _join_answer_context(text, answers)
    species_context = build_species_context(text=context)
    species_group = species_context.get("group")

    kb_questions = fallback_questions_from_text(context)
    if kb_questions:
        return kb_questions

    if species_group == "lagomorph":
        return [
            "兔子停食持续多久？粪便是减少、变小，还是完全没有？",
            "是否腹胀、磨牙、弓背、拒绝活动或触腹疼痛？",
            "最近饮水和排尿是否减少？是否有流口水、挑食草或牙齿问题？",
        ]

    if species_group == "avian":
        return [
            "是否张口呼吸、尾部上下摆动、伸颈呼吸或发出呼吸音？",
            "是否蓬毛闭眼、站杆不稳、体重下降或粪便/尿酸改变？",
            "是否有鼻孔分泌物、呕吐甩食、产蛋异常或近期环境温度变化？",
        ]

    if species_group in ("reptile", "amphibian", "fish"):
        return [
            "请补充具体物种、环境温度/热点/冷区、湿度或水质，以及 UVB/晒背条件。",
            "最近进食、排便、蜕皮/换甲、浮水/沉底和活动量是否异常？",
            "是否张口呼吸、伸颈、鼻泡、喘鸣、外伤或皮肤/甲壳异常？",
        ]

    if species_group in ("rodent", "mustelid", "insectivore", "marsupial"):
        return [
            "采食、饮水和粪便量是否明显下降？体重最近是否下降？",
            "是否流口水、磨牙、腹胀、呼吸异常或活动量明显下降？",
            "笼舍温度、垫材、近期换粮或同笼动物状态是否有变化？",
        ]

    if _has_any(context, ["呕吐", "干呕", "吐", "腹胀", "肚子胀", "腹部胀"]):
        return [
            "是否出现反复干呕但吐不出来、腹胀加重、流涎或明显不安？",
            "目前是否仍在持续呕吐或干呕？最近一次呕吐大约是什么时候？",
            "牙龈颜色是否苍白或发紫？四肢是否发凉、站立不稳？",
            "腹部是否明显膨大、触碰疼痛，或狗是否无法安静卧下？",
            "目前能否饮水？饮水后是否马上再次呕吐？",
            "最近一次排尿是什么时候？尿量是否明显减少？",
        ]

    return [
        "目前精神、食欲、饮水和排尿情况分别如何？",
        "症状是突然出现还是逐渐加重？大约持续了多久？",
        "是否伴随发热、疼痛、呼吸异常或明显虚弱？",
        "近期是否更换食物、误食异物、接触毒物或使用新药？",
    ]


def _filter_repeated_questions(
    result: Dict[str, Any],
    text: str = "",
    answers: Optional[List[Dict[str, str]]] = None,
) -> None:
    """
    V1.1：
    - 已经回答过的问题不再重复。
    - 清洗机械病句式追问。
    - 每轮只保留 1 个清晰追问。
    - 如果 AI 追问不可用，按当前上下文给出临床兜底追问。
    """
    answers = answers or []

    answered_questions = [
        _get_value(item, "question").strip()
        for item in answers
        if _get_value(item, "question").strip()
    ]

    current_questions = [_normalize_question_text(q) for q in _extract_questions(result)]
    filtered = [
        q for q in current_questions
        if q and not _is_repeated_question(q, answered_questions)
    ]

    if filtered:
        _set_questions(result, [filtered[0]])
        return

    for q in _fallback_questions(text, answers):
        normalized = _normalize_question_text(q)
        if normalized and not _is_repeated_question(normalized, answered_questions):
            _set_questions(result, [normalized])
            return

    _set_questions(result, [])


def clean_consult_result(
    result: Dict[str, Any],
    text: str = "",
    answers: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    清洗普通 /ai/consult 和动态 /ai/consult/dynamic 的追问文案。
    不改诊断、风险、检查和治疗，只规范 next_questions。
    """
    if isinstance(result, dict):
        _filter_repeated_questions(result, text, answers or [])
    return result


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
                "questions": [_fallback_questions(text, answers)[0]]
            },
            "actions": ["建议结合体征与实验室检查进一步判断。"],
            "dynamic": {
                "mode": "dynamic_consult_v1",
                "round": len(answers) + 1,
                "answered_count": len(answers),
                "fallback": True,
            },
        }

    _filter_repeated_questions(result, text, answers)

    result["dynamic"] = {
        "mode": "dynamic_consult_v1",
        "round": len(answers) + 1,
        "answered_count": len(answers),
    }

    return result
