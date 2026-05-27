from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


Risk = Optional[str]
KB_DIR = Path(__file__).resolve().parents[1] / "knowledge-base" / "exotics"
REQUIRED_LIST_FIELDS = ("system_hints", "red_flags", "diseases", "checks", "actions", "questions")
RULE_KEYS = ("rabbit", "bird", "reptile", "ferret", "rodent")


class ExoticKnowledgeError(RuntimeError):
    pass


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _dedupe(items: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _load_json(filename: str) -> Dict[str, Any]:
    file_path = KB_DIR / filename
    if not file_path.exists():
        raise ExoticKnowledgeError(f"异宠知识库文件不存在：{file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ExoticKnowledgeError(f"异宠知识库 JSON 解析失败：{file_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ExoticKnowledgeError(f"异宠知识库文件必须是 JSON object：{file_path}")
    return data


def _validate_string_list(rule_key: str, field: str, value: Any) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ExoticKnowledgeError(f"{rule_key}.{field} 必须是非空字符串数组")


def _validate_rule(rule_key: str, data: Dict[str, Any]) -> None:
    if data.get("key") != rule_key:
        raise ExoticKnowledgeError(f"{rule_key}.json 的 key 字段不匹配：{data.get('key')!r}")

    if not isinstance(data.get("label"), str) or not data.get("label", "").strip():
        raise ExoticKnowledgeError(f"{rule_key}.label 必须是非空字符串")

    for field in REQUIRED_LIST_FIELDS:
        if field not in data or not isinstance(data.get(field), list):
            raise ExoticKnowledgeError(f"{rule_key}.{field} 必须存在且为数组")

    for idx, item in enumerate(data.get("system_hints", []), 1):
        if not isinstance(item, dict):
            raise ExoticKnowledgeError(f"{rule_key}.system_hints[{idx}] 必须是对象")
        if not isinstance(item.get("label"), str) or not item.get("label", "").strip():
            raise ExoticKnowledgeError(f"{rule_key}.system_hints[{idx}].label 必须是非空字符串")
        _validate_string_list(rule_key, f"system_hints[{idx}].features", item.get("features"))

    for idx, item in enumerate(data.get("red_flags", []), 1):
        if not isinstance(item, dict):
            raise ExoticKnowledgeError(f"{rule_key}.red_flags[{idx}] 必须是对象")
        if item.get("level") not in ("高", "中", "低"):
            raise ExoticKnowledgeError(f"{rule_key}.red_flags[{idx}].level 必须是 高/中/低")
        _validate_string_list(rule_key, f"red_flags[{idx}].features", item.get("features"))
        if not isinstance(item.get("reason"), str) or not item.get("reason", "").strip():
            raise ExoticKnowledgeError(f"{rule_key}.red_flags[{idx}].reason 必须是非空字符串")

    for field in ("diseases", "checks", "actions", "questions"):
        _validate_string_list(rule_key, field, data.get(field))


def _validate_index(data: Dict[str, Any]) -> None:
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ExoticKnowledgeError("index.json 的 rules 必须是非空数组")
    if not all(isinstance(key, str) and key.strip() for key in rules):
        raise ExoticKnowledgeError("index.json 的 rules 必须全部是非空字符串")
    for mapping_field in ("species_to_rule", "group_to_rule"):
        mapping = data.get(mapping_field)
        if not isinstance(mapping, dict):
            raise ExoticKnowledgeError(f"index.json 的 {mapping_field} 必须是对象")
        for source, target in mapping.items():
            if not isinstance(source, str) or not isinstance(target, str):
                raise ExoticKnowledgeError(f"index.json 的 {mapping_field} key/value 必须是字符串")
            if target not in rules:
                raise ExoticKnowledgeError(f"index.json 的 {mapping_field}.{source} 指向未知规则：{target}")


@lru_cache(maxsize=1)
def load_index() -> Dict[str, Any]:
    data = _load_json("index.json")
    _validate_index(data)
    return data


@lru_cache(maxsize=1)
def load_exotic_kb() -> Dict[str, Dict[str, Any]]:
    index = load_index()
    keys = index.get("rules") or list(RULE_KEYS)
    kb: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        rule = _load_json(f"{key}.json")
        _validate_rule(key, rule)
        kb[key] = rule
    return kb


def reload_exotic_kb() -> Dict[str, Dict[str, Any]]:
    load_index.cache_clear()
    load_exotic_kb.cache_clear()
    return load_exotic_kb()


def kb_key_for_features(features: Dict[str, Any]) -> str:
    index = load_index()
    species_to_rule = index.get("species_to_rule") or {}
    group_to_rule = index.get("group_to_rule") or {}

    species = str(features.get("species") or "").strip()
    if species in species_to_rule:
        return str(species_to_rule[species])

    group = str(features.get("species_group") or "").strip()
    return str(group_to_rule.get(group) or "")


def get_kb(features: Dict[str, Any]) -> Dict[str, Any]:
    return load_exotic_kb().get(kb_key_for_features(features), {})


def augment_exotic_features(features: Dict[str, Any], raw_text: Any) -> Dict[str, Any]:
    text = _text(raw_text)
    species_group = features.get("species_group")

    appetite_down = bool(features.get("appetite_down") or features.get("anorexia"))
    weakness = bool(features.get("low_energy") or _has_any(text, ["无力", "瘫软", "软趴", "不能站", "站不稳", "虚弱", "没力气"]))
    drooling = _has_any(text, ["流口水", "流涎", "口水", "下巴湿", "甩口水"])
    head_tilt = _has_any(text, ["歪头", "头斜", "转圈", "眼震"])
    nasal_ocular_discharge = _has_any(text, ["流鼻涕", "鼻涕", "鼻孔分泌物", "眼分泌物", "流眼泪", "眼睛分泌物", "结膜"])
    voice_change = _has_any(text, ["声音变", "叫声变", "失声", "沙哑"])
    ruffled_feathers = _has_any(text, ["蓬毛", "炸毛", "闭眼", "缩成一团", "羽毛蓬松"])
    weight_loss = _has_any(text, ["体重下降", "消瘦", "变瘦", "掉秤", "瘦了", "weight loss"])
    urinary_issue = _has_any(text, ["尿血", "血尿", "尿少", "无尿", "排尿困难", "尿闭", "尿酸异常"])
    reproductive_issue = _has_any(text, ["产蛋", "卡蛋", "蛋滞留", "难产", "下蛋", "卵泡", "泄殖腔"])
    vent_prolapse = _has_any(text, ["泄殖腔脱出", "脱肛", "组织脱出", "外翻", "vent prolapse", "prolapse"])
    uvb_issue = _has_any(text, ["uvb", "uva", "晒背灯", "晒背", "太阳灯", "钙粉", "维生素d", "维生素 d", "d3"])
    temperature_issue = _has_any(text, ["温度", "低温", "高温", "热点", "冷区", "温区", "夜温", "加热垫", "陶瓷灯"])
    humidity_issue = _has_any(text, ["湿度", "太干", "太湿", "喷雾", "水盆", "水质"])
    mbd_signs = _has_any(text, ["壳软", "腿软", "骨折", "下颌软", "抽搐", "走路异常", "不能爬", "软壳", "畸形", "缺钙"])
    dysecdysis = _has_any(text, ["蜕皮不全", "卡皮", "眼皮没蜕", "残皮", "蜕皮困难"])
    foreign_body_risk = _has_any(text, ["异物", "橡胶", "泡棉", "海绵", "布料", "玩具", "咬坏", "吞了", "误食"])
    hypoglycemia_signs = _has_any(text, ["低血糖", "发呆", "流口水", "流涎", "后肢无力", "后腿无力", "抽搐", "突然虚弱"])

    features.update({
        "weakness": weakness,
        "drooling": drooling,
        "head_tilt": head_tilt,
        "nasal_ocular_discharge": nasal_ocular_discharge,
        "voice_change": voice_change,
        "ruffled_feathers": ruffled_feathers,
        "weight_loss": weight_loss,
        "urinary_issue": urinary_issue,
        "reproductive_issue": reproductive_issue,
        "vent_prolapse": vent_prolapse,
        "uvb_issue": uvb_issue,
        "temperature_issue": temperature_issue,
        "humidity_issue": humidity_issue,
        "mbd_signs": mbd_signs,
        "dysecdysis": dysecdysis,
        "foreign_body_risk": foreign_body_risk,
        "hypoglycemia_signs": hypoglycemia_signs,
    })

    if species_group == "avian":
        features["egg_binding"] = bool(features.get("egg_binding") or reproductive_issue)
        features["avian_respiratory_risk"] = bool(features.get("respiratory_distress"))

    if species_group in ("reptile", "amphibian", "fish"):
        features["husbandry_problem"] = bool(features.get("husbandry_problem") or uvb_issue or temperature_issue or humidity_issue)
        features["reptile_husbandry_risk"] = bool(features.get("husbandry_problem") and (appetite_down or weakness or features.get("skin_shell_issue") or mbd_signs))

    if species_group == "mustelid":
        features["ferret_hypoglycemia_risk"] = bool(hypoglycemia_signs or (drooling and weakness))
        features["ferret_foreign_body_risk"] = bool(foreign_body_risk and (features.get("vomiting") or appetite_down or features.get("abd_distension")))

    if species_group in ("lagomorph", "rodent"):
        features["small_mammal_dental_gi_risk"] = bool(features.get("small_mammal_dental_gi_risk") or features.get("dental_signs") or drooling or features.get("feces_down") or appetite_down)

    return features


def knowledge_risk_level(features: Dict[str, Any]) -> Risk:
    kb = get_kb(features)
    if not kb:
        return None

    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        if all(bool(features.get(name)) for name in required):
            return str(item.get("level") or "") or None
    return None


def knowledge_risk_reasons(features: Dict[str, Any]) -> List[str]:
    kb = get_kb(features)
    reasons: List[str] = []
    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        if all(bool(features.get(name)) for name in required):
            reasons.append(str(item.get("reason") or ""))
    return _dedupe(reasons)


def knowledge_tree_leaf(features: Dict[str, Any]) -> Optional[str]:
    kb = get_kb(features)
    if not kb:
        return None

    for item in kb.get("system_hints", []):
        label = str(item.get("label") or "").strip()
        keys = item.get("features") or []
        if label and any(bool(features.get(key)) for key in keys):
            return label
    return "异宠综合分诊"


def knowledge_questions(features: Dict[str, Any]) -> List[str]:
    kb = get_kb(features)
    if not kb:
        return []

    questions: List[str] = []
    # 红旗命中时，把最关键追问提前。
    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        reason = str(item.get("reason") or "")
        if all(bool(features.get(name)) for name in required):
            if "呼吸" in reason:
                questions.append("目前是否张口呼吸、伸颈呼吸、尾部上下摆或出现发绀/虚脱？")
            elif "无粪" in reason or "停食" in reason:
                questions.append("最近一次主动进食和排便分别是什么时候？粪便是否完全停止？")
            elif "低血糖" in reason:
                questions.append("是否突然虚弱、发呆、流口水、后肢无力、抽搐或不能站立？")

    questions.extend(kb.get("questions", []))
    return _dedupe(questions)


def knowledge_diagnosis(features: Dict[str, Any]) -> Dict[str, List[str]]:
    kb = get_kb(features)
    if not kb:
        return {"diseases": [], "checks": [], "actions": []}

    diseases = list(kb.get("diseases", []))
    checks = list(kb.get("checks", []))
    actions = list(kb.get("actions", []))

    reasons = knowledge_risk_reasons(features)
    if reasons:
        actions.insert(0, "红旗提示：" + "；".join(reasons))

    # 特征驱动补充，不覆盖原有规则。
    if features.get("respiratory_distress"):
        diseases.insert(0, "呼吸困难/呼吸系统急症")
        checks.insert(0, "低应激呼吸状态评估，必要时先稳定再进一步检查")
    if features.get("neurologic_signs"):
        diseases.append("神经系统异常/中毒/代谢异常鉴别")
        checks.append("神经定位、血糖/电解质及毒物暴露史评估")
    if features.get("toxin"):
        diseases.append("毒物或刺激性暴露")
        checks.append("详细暴露史、摄入时间和可能毒物记录")
    if features.get("trauma"):
        diseases.append("外伤相关疼痛/出血/骨折")
        checks.append("疼痛评分、创口检查和影像按需")

    return {
        "diseases": _dedupe(diseases),
        "checks": _dedupe(checks),
        "actions": _dedupe(actions),
    }


def fallback_questions_from_text(text: Any) -> List[str]:
    try:
        from backend.feature_engine import extract_features
    except ModuleNotFoundError:
        from feature_engine import extract_features

    features = extract_features(str(text or ""))
    return knowledge_questions(features)
