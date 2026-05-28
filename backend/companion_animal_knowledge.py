from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


Risk = Optional[str]
KB_DIR = Path(__file__).resolve().parents[1] / "knowledge-base" / "companion"
REQUIRED_LIST_FIELDS = ("system_hints", "red_flags", "diseases", "checks", "actions", "questions")
RULE_KEYS = ("dog", "cat")


class CompanionKnowledgeError(RuntimeError):
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
        raise CompanionKnowledgeError(f"犬猫知识库文件不存在：{file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise CompanionKnowledgeError(f"犬猫知识库 JSON 解析失败：{file_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise CompanionKnowledgeError(f"犬猫知识库文件必须是 JSON object：{file_path}")
    return data


def _validate_string_list(rule_key: str, field: str, value: Any) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise CompanionKnowledgeError(f"{rule_key}.{field} 必须是非空字符串数组")


def _validate_rule(rule_key: str, data: Dict[str, Any]) -> None:
    if data.get("key") != rule_key:
        raise CompanionKnowledgeError(f"{rule_key}.json 的 key 字段不匹配：{data.get('key')!r}")

    if not isinstance(data.get("label"), str) or not data.get("label", "").strip():
        raise CompanionKnowledgeError(f"{rule_key}.label 必须是非空字符串")

    if not isinstance(data.get("species_scope"), list) or not data.get("species_scope"):
        raise CompanionKnowledgeError(f"{rule_key}.species_scope 必须是非空数组")

    for field in REQUIRED_LIST_FIELDS:
        if field not in data or not isinstance(data.get(field), list):
            raise CompanionKnowledgeError(f"{rule_key}.{field} 必须存在且为数组")

    for idx, item in enumerate(data.get("system_hints", []), 1):
        if not isinstance(item, dict):
            raise CompanionKnowledgeError(f"{rule_key}.system_hints[{idx}] 必须是对象")
        if not isinstance(item.get("label"), str) or not item.get("label", "").strip():
            raise CompanionKnowledgeError(f"{rule_key}.system_hints[{idx}].label 必须是非空字符串")
        _validate_string_list(rule_key, f"system_hints[{idx}].features", item.get("features"))

    for idx, item in enumerate(data.get("red_flags", []), 1):
        if not isinstance(item, dict):
            raise CompanionKnowledgeError(f"{rule_key}.red_flags[{idx}] 必须是对象")
        if item.get("level") not in ("高", "中", "低"):
            raise CompanionKnowledgeError(f"{rule_key}.red_flags[{idx}].level 必须是 高/中/低")
        _validate_string_list(rule_key, f"red_flags[{idx}].features", item.get("features"))
        if not isinstance(item.get("reason"), str) or not item.get("reason", "").strip():
            raise CompanionKnowledgeError(f"{rule_key}.red_flags[{idx}].reason 必须是非空字符串")

    for field in ("diseases", "checks", "actions", "questions"):
        _validate_string_list(rule_key, field, data.get(field))


def _validate_index(data: Dict[str, Any]) -> None:
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        raise CompanionKnowledgeError("index.json 的 rules 必须是非空数组")
    if not all(isinstance(key, str) and key.strip() for key in rules):
        raise CompanionKnowledgeError("index.json 的 rules 必须全部是非空字符串")
    for mapping_field in ("species_to_rule", "group_to_rule"):
        mapping = data.get(mapping_field)
        if not isinstance(mapping, dict):
            raise CompanionKnowledgeError(f"index.json 的 {mapping_field} 必须是对象")
        for source, target in mapping.items():
            if not isinstance(source, str) or not isinstance(target, str):
                raise CompanionKnowledgeError(f"index.json 的 {mapping_field} key/value 必须是字符串")
            if target not in rules:
                raise CompanionKnowledgeError(f"index.json 的 {mapping_field}.{source} 指向未知规则：{target}")


@lru_cache(maxsize=1)
def load_index() -> Dict[str, Any]:
    data = _load_json("index.json")
    _validate_index(data)
    return data


@lru_cache(maxsize=1)
def load_companion_kb() -> Dict[str, Dict[str, Any]]:
    index = load_index()
    keys = index.get("rules") or list(RULE_KEYS)
    kb: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        rule = _load_json(f"{key}.json")
        _validate_rule(key, rule)
        kb[key] = rule
    return kb


def reload_companion_kb() -> Dict[str, Dict[str, Any]]:
    load_index.cache_clear()
    load_companion_kb.cache_clear()
    return load_companion_kb()


def companion_kb_key_for_features(features: Dict[str, Any]) -> str:
    index = load_index()
    species_to_rule = index.get("species_to_rule") or {}
    group_to_rule = index.get("group_to_rule") or {}

    species = str(features.get("species") or "").strip()
    if species in species_to_rule:
        return str(species_to_rule[species])

    group = str(features.get("species_group") or "").strip()
    return str(group_to_rule.get(group) or "")


def get_companion_kb(features: Dict[str, Any]) -> Dict[str, Any]:
    return load_companion_kb().get(companion_kb_key_for_features(features), {})


def augment_companion_animal_features(features: Dict[str, Any], raw_text: Any) -> Dict[str, Any]:
    """补充犬猫高频/高危问诊特征。只服务 canine/feline，不影响异宠规则。"""
    text = _text(raw_text)
    species_group = features.get("species_group")
    if species_group not in ("canine", "feline"):
        return features

    toxin_keywords = [
        "中毒", "误食", "毒", "巧克力", "咖啡", "咖啡因", "葡萄", "葡萄干",
        "木糖醇", "xylitol", "洋葱", "大蒜", "韭菜", "百合", "老鼠药",
        "杀虫剂", "除草剂", "布洛芬", "对乙酰氨基酚", "扑热息痛", "药片",
        "异烟肼", "酒精", "防冻液", "乙二醇",
    ]
    urinary_keywords = [
        "排尿困难", "尿不出来", "尿闭", "无尿", "少尿", "尿少", "滴尿",
        "尿频", "频繁蹲", "蹲猫砂", "蹲盆", "血尿", "尿血", "尿痛",
        "尿道堵", "尿道阻塞", "排不出尿", "一直蹲",
    ]
    anuria_keywords = ["尿不出来", "尿闭", "无尿", "排不出尿", "没有尿", "尿道堵", "尿道阻塞"]
    male_cat_keywords = ["公猫", "雄猫", "未绝育公猫", "绝育公猫", "男猫"]
    prolonged_anorexia_keywords = [
        "24小时", "一天", "1天", "两天", "2天", "三天", "3天", "48小时", "72小时",
        "几天", "多天", "超过一天", "一天多",
    ]
    jaundice_keywords = ["黄疸", "皮肤黄", "眼白黄", "耳朵黄", "牙龈黄", "尿黄", "巩膜黄", "黏膜黄"]
    oral_dental_keywords = ["口炎", "牙龈红", "牙结石", "口臭", "口腔溃疡", "流口水", "流涎", "咀嚼疼", "牙疼"]
    pruritus_keywords = ["瘙痒", "痒", "抓挠", "舔咬", "蹭", "掉毛", "脱毛", "红疹", "皮屑", "结痂", "耳朵痒"]
    ortho_keywords = ["跛行", "瘸", "不敢着地", "抬脚", "骨折", "关节肿", "疼痛", "扭伤", "外伤", "车祸", "摔"]
    foreign_body_keywords = ["异物", "吞了", "吃了袜子", "袜子", "玩具", "骨头", "玉米芯", "塑料", "布料", "海绵", "线", "绳"]
    cardiac_keywords = ["心脏病", "心衰", "晕厥", "舌头紫", "牙龈发紫", "咳嗽夜间", "运动不耐受"]
    bleeding_keywords = ["便血", "血便", "黑便", "柏油样便", "呕血", "吐血", "出血不止"]
    seizure_cluster_keywords = ["连续抽搐", "抽搐两次", "多次抽搐", "抽搐不止", "癫痫持续", "意识不清"]

    urinary_issue = _has_any(text, urinary_keywords)
    anuria = _has_any(text, anuria_keywords)
    toxin_exposure = bool(features.get("toxin") or _has_any(text, toxin_keywords))
    prolonged_anorexia = bool(features.get("anorexia") and _has_any(text, prolonged_anorexia_keywords))
    jaundice = _has_any(text, jaundice_keywords)
    oral_dental_issue = _has_any(text, oral_dental_keywords)
    pruritus = _has_any(text, pruritus_keywords)
    orthopedic_or_trauma = bool(features.get("trauma") or _has_any(text, ortho_keywords))
    foreign_body_suspect = _has_any(text, foreign_body_keywords)
    cardiac_respiratory_risk = bool(features.get("respiratory_distress") or _has_any(text, cardiac_keywords))
    seizure_cluster = bool(features.get("neurologic_signs") and _has_any(text, seizure_cluster_keywords))
    gi_bleeding = bool(features.get("blood") or _has_any(text, bleeding_keywords))

    dog_gdv_risk = bool(
        species_group == "canine"
        and (
            (features.get("retching") and features.get("abd_distension"))
            or (
                _has_any(text, ["胃扭转", "胃扩张", "gdv", "bloat", "腹部胀大", "肚子鼓", "吐不出来"])
                and (features.get("retching") or _has_any(text, ["干呕", "流口水", "坐立不安"]))
            )
        )
    )
    dog_ahds_risk = bool(species_group == "canine" and features.get("diarrhea") and gi_bleeding and (features.get("low_energy") or features.get("collapse")))
    dog_toxin_risk = bool(species_group == "canine" and toxin_exposure)

    cat_urinary_obstruction_risk = bool(
        species_group == "feline"
        and (
            anuria
            or (urinary_issue and _has_any(text, male_cat_keywords))
            or (urinary_issue and (features.get("low_energy") or features.get("anorexia") or features.get("vomiting")))
        )
    )
    cat_anorexia_high_risk = bool(
        species_group == "feline"
        and features.get("anorexia")
        and (prolonged_anorexia or features.get("low_energy") or features.get("vomiting") or _has_any(text, ["体重下降", "消瘦", "变瘦"]))
    )
    cat_respiratory_risk = bool(species_group == "feline" and features.get("respiratory_distress"))
    cat_jaundice_risk = bool(species_group == "feline" and jaundice)

    features.update({
        "toxin": toxin_exposure,
        "toxin_exposure": toxin_exposure,
        "urinary_issue": urinary_issue,
        "anuria": anuria,
        "prolonged_anorexia": prolonged_anorexia,
        "jaundice": jaundice,
        "oral_dental_issue": oral_dental_issue,
        "pruritus": pruritus,
        "orthopedic_or_trauma": orthopedic_or_trauma,
        "foreign_body_suspect": foreign_body_suspect,
        "cardiac_respiratory_risk": cardiac_respiratory_risk,
        "seizure_cluster": seizure_cluster,
        "gi_bleeding": gi_bleeding,
        "dog_gdv_risk": dog_gdv_risk,
        "dog_ahds_risk": dog_ahds_risk,
        "dog_toxin_risk": dog_toxin_risk,
        "cat_urinary_obstruction_risk": cat_urinary_obstruction_risk,
        "cat_anorexia_high_risk": cat_anorexia_high_risk,
        "cat_respiratory_risk": cat_respiratory_risk,
        "cat_jaundice_risk": cat_jaundice_risk,
    })
    return features


def companion_knowledge_risk_level(features: Dict[str, Any]) -> Risk:
    kb = get_companion_kb(features)
    if not kb:
        return None

    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        if all(bool(features.get(name)) for name in required):
            return str(item.get("level") or "") or None
    return None


def companion_knowledge_risk_reasons(features: Dict[str, Any]) -> List[str]:
    kb = get_companion_kb(features)
    reasons: List[str] = []
    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        if all(bool(features.get(name)) for name in required):
            reasons.append(str(item.get("reason") or ""))
    return _dedupe(reasons)


def companion_knowledge_tree_leaf(features: Dict[str, Any]) -> Optional[str]:
    kb = get_companion_kb(features)
    if not kb:
        return None

    for item in kb.get("system_hints", []):
        label = str(item.get("label") or "").strip()
        keys = item.get("features") or []
        if label and any(bool(features.get(key)) for key in keys):
            return label
    return str(kb.get("default_tree_leaf") or "犬猫综合分诊")


def companion_knowledge_questions(features: Dict[str, Any]) -> List[str]:
    kb = get_companion_kb(features)
    if not kb:
        return []

    questions: List[str] = []
    for item in kb.get("red_flags", []):
        required = item.get("features") or []
        reason = str(item.get("reason") or "")
        if all(bool(features.get(name)) for name in required):
            if "GDV" in reason or "胃扩张" in reason:
                questions.append("是否反复干呕但吐不出来？腹部是否快速胀大、流涎、坐立不安或牙龈苍白？")
            elif "尿闭" in reason or "尿道阻塞" in reason:
                questions.append("最近一次明确排出尿液是什么时候？每次是否只有几滴、是否叫唤或频繁舔尿道口？")
            elif "中毒" in reason or "毒物" in reason:
                questions.append("请记录疑似摄入物、摄入时间、估计量、包装成分、体重以及是否已出现呕吐/抽搐/心率异常。")
            elif "呼吸" in reason:
                questions.append("是否张口呼吸、舌色/牙龈发紫、不能平卧、呼吸频率明显升高或虚脱？")
            elif "不吃" in reason or "脂肪肝" in reason:
                questions.append("完全不吃持续多久？是否呕吐、黄疸、体重下降或有基础病/肥胖史？")

    questions.extend(kb.get("questions", []))
    return _dedupe(questions)


def companion_knowledge_diagnosis(features: Dict[str, Any]) -> Dict[str, List[str]]:
    kb = get_companion_kb(features)
    if not kb:
        return {"diseases": [], "checks": [], "actions": []}

    diseases = list(kb.get("diseases", []))
    checks = list(kb.get("checks", []))
    actions = list(kb.get("actions", []))

    reasons = companion_knowledge_risk_reasons(features)
    if reasons:
        actions.insert(0, "红旗提示：" + "；".join(reasons))

    if features.get("dog_gdv_risk"):
        diseases.insert(0, "胃扩张/扭转（GDV）风险")
        checks.insert(0, "循环状态、腹部膨胀和右侧腹部影像评估")
    if features.get("dog_toxin_risk"):
        diseases.insert(0, "犬可疑中毒/毒物暴露")
        checks.insert(0, "毒物名称、摄入时间、估计剂量、体重和生命体征记录")
    if features.get("cat_urinary_obstruction_risk"):
        diseases.insert(0, "猫尿道阻塞/尿闭风险")
        checks.insert(0, "膀胱充盈度、血钾/肾功能、电解质和疼痛状态评估")
    if features.get("cat_anorexia_high_risk"):
        diseases.insert(0, "猫持续厌食/脂肪肝风险")
        checks.insert(0, "体重趋势、黄疸检查、肝胆指标和脱水评估")
    if features.get("respiratory_distress"):
        diseases.insert(0, "呼吸困难/呼吸系统急症")
        checks.insert(0, "低应激呼吸状态评估，必要时先供氧稳定再检查")
    if features.get("neurologic_signs"):
        diseases.append("神经系统异常/中毒/代谢异常鉴别")
        checks.append("神经定位、血糖/电解质及毒物暴露史评估")
    if features.get("pruritus"):
        diseases.append("过敏性皮肤病/寄生虫/感染性皮肤病鉴别")
        checks.append("皮肤刮片、耳检、细胞学和寄生虫筛查按需")
    if features.get("orthopedic_or_trauma"):
        diseases.append("骨科/创伤相关疼痛、骨折或软组织损伤")
        checks.append("疼痛评分、步态观察、触诊和影像按需")

    return {
        "diseases": _dedupe(diseases),
        "checks": _dedupe(checks),
        "actions": _dedupe(actions),
    }


def companion_fallback_questions_from_text(text: Any) -> List[str]:
    try:
        from backend.feature_engine import extract_features
    except ModuleNotFoundError:
        from feature_engine import extract_features

    features = extract_features(str(text or ""))
    return companion_knowledge_questions(features)
