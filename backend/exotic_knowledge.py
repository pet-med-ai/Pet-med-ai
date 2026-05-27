from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


Risk = Optional[str]


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword and keyword in text for keyword in keywords)


def _dedupe(items: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))


def _text(value: Any) -> str:
    return str(value or "").strip().lower()


# 分科规则库 V1：只做分诊/鉴别/检查方向，不给药物剂量。
# 重点覆盖门诊高频和急诊红旗：
# - rabbit：停食/少粪/腹胀/牙科相关胃肠淤滞风险
# - bird：呼吸困难、蓬毛闭眼、产蛋异常、甩食/返流
# - reptile：温湿度/UVB/水质/蜕皮/甲壳/呼吸/神经/泄殖腔问题
# - ferret：低血糖样虚弱、胃肠异物、消化道症状
# - rodent：采食下降、牙科、湿尾/腹泻、呼吸道、体重下降
EXOTIC_KB: Dict[str, Dict[str, Any]] = {
    "rabbit": {
        "label": "兔科/兔形目",
        "system_hints": [
            ("消化系统/采食排泄异常", ["anorexia", "feces_down", "no_feces", "abd_distension", "dental_signs"]),
            ("呼吸系统异常", ["respiratory_distress"]),
            ("神经系统/头斜异常", ["neurologic_signs", "head_tilt"]),
            ("泌尿生殖异常", ["urinary_issue", "reproductive_issue"]),
        ],
        "red_flags": [
            ("高", ["anorexia", "no_feces"], "停食合并无粪/粪便显著减少，警惕胃肠淤滞或梗阻。"),
            ("高", ["abd_distension", "low_energy"], "腹胀合并精神差，需优先排查疼痛、积气、脱水和梗阻。"),
            ("高", ["respiratory_distress"], "张口/明显用力呼吸属于兔急症红旗。"),
            ("中", ["dental_signs"], "流涎、磨牙、挑食草提示牙科或疼痛相关采食下降。"),
        ],
        "diseases": ["兔胃肠淤滞", "胃肠梗阻/积气", "牙科疾病相关采食下降", "疼痛/脱水相关精神沉郁"],
        "checks": ["体重和脱水评估", "腹部触诊", "腹部影像评估胃肠积气/梗阻", "口腔及臼齿检查", "血糖、电解质和肾功能按需评估"],
        "actions": ["兔子停食、无粪、腹胀或精神差时按异宠急诊优先处理，先评估疼痛、脱水和梗阻风险。", "记录最近一次进食、排便、排尿、饮水和体重变化。"],
        "questions": [
            "兔子停食持续多久？粪便是减少、变小，还是完全没有？",
            "是否腹胀、磨牙、弓背、拒绝活动或触腹疼痛？",
            "最近饮水和排尿是否减少？是否有流口水、挑食草或牙齿问题？",
            "最近是否换粮、减少干草、摄入过多零食，或有应激/疼痛/外伤？",
        ],
    },
    "bird": {
        "label": "鸟类",
        "system_hints": [
            ("呼吸系统急症", ["respiratory_distress", "nasal_ocular_discharge", "voice_change"]),
            ("繁殖系统/蛋滞留风险", ["egg_binding", "reproductive_issue"]),
            ("消化系统/返流甩食", ["regurgitation", "appetite_down", "diarrhea"]),
            ("全身性疾病/应激", ["low_energy", "weight_loss"]),
        ],
        "red_flags": [
            ("高", ["respiratory_distress"], "鸟类张口呼吸、尾部上下摆或明显呼吸用力需要立即分诊。"),
            ("高", ["egg_binding", "low_energy"], "疑似卡蛋/产蛋困难合并精神差属于繁殖相关急症。"),
            ("高", ["collapse"], "站立不稳、虚脱或不能站杆为高风险。"),
            ("中", ["ruffled_feathers", "appetite_down"], "蓬毛闭眼合并采食下降提示全身性疾病。"),
        ],
        "diseases": ["鸟类呼吸道/气囊疾病", "衣原体/支原体/真菌等感染性疾病", "营养缺乏相关上皮问题", "蛋滞留/繁殖相关疾病", "消化道返流或全身性疾病"],
        "checks": ["安静低应激观察呼吸", "体重和体况评分", "粪便/尿酸颜色和量", "口腔、鼻孔和眼部分泌物检查", "必要时影像、血检和病原检测"],
        "actions": ["鸟类呼吸困难先低应激稳定，避免不必要抓取；必要时氧疗后再检查。", "记录笼舍温度、饮食结构、同笼鸟状态和近期气溶胶/烟雾/PTFE 暴露。"],
        "questions": [
            "是否张口呼吸、尾部上下摆动、伸颈呼吸或发出呼吸音？",
            "是否蓬毛闭眼、站杆不稳、体重下降或粪便/尿酸改变？",
            "是否有鼻孔/眼部分泌物、声音改变、甩食返流或近期环境刺激物暴露？",
            "母鸟是否近期产蛋、腹部膨大、频繁蹲伏或疑似卡蛋？",
        ],
    },
    "reptile": {
        "label": "爬行动物/两栖/水族",
        "system_hints": [
            ("饲养环境/代谢相关", ["husbandry_problem", "uvb_issue", "temperature_issue", "humidity_issue"]),
            ("骨骼肌肉/营养代谢异常", ["mbd_signs", "weakness", "appetite_down"]),
            ("呼吸系统异常", ["respiratory_distress", "nasal_ocular_discharge"]),
            ("皮肤/甲壳/蜕皮异常", ["skin_shell_issue", "dysecdysis"]),
            ("泄殖腔/繁殖异常", ["vent_prolapse", "egg_binding", "reproductive_issue"]),
            ("神经系统异常", ["neurologic_signs"]),
        ],
        "red_flags": [
            ("高", ["respiratory_distress"], "爬宠张口呼吸、伸颈、鼻泡或明显呼吸困难需优先处理。"),
            ("高", ["vent_prolapse"], "泄殖腔/组织脱出需要尽快处理并查找原发原因。"),
            ("高", ["neurologic_signs"], "翻正困难、抽搐、星望或严重无力属于高风险。"),
            ("中", ["husbandry_problem", "appetite_down"], "温湿度、UVB、水质或晒背条件异常合并拒食，需按环境/代谢问题分诊。"),
            ("中", ["skin_shell_issue"], "腐皮、烂甲、蜕皮异常或壳软提示环境、营养或感染问题。"),
        ],
        "diseases": ["饲养环境相关疾病", "营养性继发性甲旁亢/代谢性骨病", "呼吸道感染", "寄生虫或消化道疾病", "皮肤/甲壳感染或蜕皮异常", "繁殖相关疾病"],
        "checks": ["具体物种、年龄、体重和饲养年限", "热点/冷区温度、夜温、湿度、UVB 和晒背距离", "水质或垫材记录", "体况、脱水、口腔、皮肤/甲壳检查", "粪检、影像、血钙磷/尿酸按需"],
        "actions": ["爬宠诊断先校正物种对应的温度、湿度、UVB、水质和饮食信息；环境参数错误会直接影响代谢、免疫和用药反应。", "出现呼吸困难、泄殖腔脱出、神经症状或严重脱水时按急症处理。"],
        "questions": [
            "请补充具体品种、环境温度/热点/冷区、夜间温度、湿度或水质，以及 UVB/晒背条件。",
            "最近进食、排便、排尿酸、蜕皮/换甲、浮水/沉底和活动量是否异常？",
            "是否张口呼吸、伸颈、鼻泡、喘鸣、外伤或皮肤/甲壳异常？",
            "是否有翻正困难、抽搐、星望、泄殖腔脱出或疑似产蛋困难？",
        ],
    },
    "ferret": {
        "label": "雪貂",
        "system_hints": [
            ("内分泌/低血糖样虚弱", ["hypoglycemia_signs", "weakness", "drooling"]),
            ("消化系统/异物风险", ["vomiting", "regurgitation", "abd_distension", "foreign_body_risk"]),
            ("呼吸系统异常", ["respiratory_distress"]),
            ("泌尿生殖/全身性疾病", ["urinary_issue", "low_energy"]),
        ],
        "red_flags": [
            ("高", ["hypoglycemia_signs"], "雪貂突然虚弱、流涎、后肢无力或发呆，需优先排查低血糖样问题。"),
            ("高", ["foreign_body_risk", "vomiting"], "雪貂呕吐/腹痛合并疑似啃咬橡胶、泡棉或异物，需排查胃肠异物。"),
            ("高", ["collapse"], "虚脱或不能站立为高风险。"),
            ("中", ["appetite_down", "diarrhea"], "食欲下降合并腹泻需评估脱水、感染和胃肠疾病。"),
        ],
        "diseases": ["低血糖/胰岛素瘤相关虚弱", "胃肠异物", "胃肠炎", "脱水或疼痛相关精神沉郁", "肾上腺/内分泌相关问题"],
        "checks": ["即刻血糖", "腹部触诊和影像", "脱水与疼痛评分", "粪便评估", "体重和采食记录"],
        "actions": ["雪貂突然虚弱、流涎或后肢无力时，先按高风险稳定并查血糖。", "询问是否啃咬橡胶、泡棉、玩具、布料或其他异物。"],
        "questions": [
            "是否突然虚弱、发呆、流口水、后肢无力、抽搐或不能站立？",
            "最近是否呕吐、腹泻、腹痛，或啃咬橡胶/泡棉/玩具等异物？",
            "最近食欲、排便、体重和活动量有什么变化？",
        ],
    },
    "rodent": {
        "label": "啮齿类小型哺乳动物",
        "system_hints": [
            ("牙科/采食排泄异常", ["dental_signs", "anorexia", "feces_down", "weight_loss"]),
            ("胃肠系统异常", ["diarrhea", "abd_distension", "no_feces"]),
            ("呼吸系统异常", ["respiratory_distress", "nasal_ocular_discharge"]),
            ("皮肤/寄生虫/外伤", ["skin_shell_issue", "trauma"]),
        ],
        "red_flags": [
            ("高", ["anorexia", "low_energy"], "小型啮齿类拒食合并精神差进展快，需优先评估脱水、疼痛和低血糖/胃肠问题。"),
            ("高", ["diarrhea", "low_energy"], "腹泻合并精神差或虚弱为高风险。"),
            ("高", ["respiratory_distress"], "呼吸困难、张口呼吸或明显喘促为高风险。"),
            ("中", ["dental_signs"], "流涎、磨牙、面部肿胀或挑食提示牙科疾病。"),
        ],
        "diseases": ["牙科疾病", "胃肠功能异常/肠道菌群紊乱", "呼吸道感染", "脱水或疼痛相关精神沉郁", "饲养环境相关问题"],
        "checks": ["体重趋势", "口腔/门齿和臼齿检查", "粪便性状和数量", "胸腹部听诊/影像按需", "垫材、温度和同笼动物状态"],
        "actions": ["小型啮齿类体型小、代谢快，采食下降或精神差不要长期观察。", "记录过去 12–24 小时进食、饮水、粪便和体重变化。"],
        "questions": [
            "采食、饮水和粪便量是否明显下降？体重最近是否下降？",
            "是否流口水、磨牙、挑食、面部肿胀、腹胀或活动量明显下降？",
            "是否腹泻、肛周潮湿、呼吸异常，或同笼动物也有症状？",
            "笼舍温度、垫材、近期换粮或应激事件是否有变化？",
        ],
    },
}


GROUP_TO_KB = {
    "lagomorph": "rabbit",
    "avian": "bird",
    "reptile": "reptile",
    "amphibian": "reptile",
    "fish": "reptile",
    "mustelid": "ferret",
    "rodent": "rodent",
    "insectivore": "rodent",
    "marsupial": "rodent",
}


def kb_key_for_features(features: Dict[str, Any]) -> str:
    species = str(features.get("species") or "").strip()
    if species == "ferret":
        return "ferret"
    if species in ("rabbit",):
        return "rabbit"
    if species in ("bird",):
        return "bird"
    if species in ("reptile", "turtle", "snake", "lizard", "amphibian", "fish"):
        return "reptile"
    if species in ("guinea_pig", "hamster", "chinchilla", "rat", "hedgehog", "sugar_glider"):
        return "rodent"

    group = str(features.get("species_group") or "").strip()
    return GROUP_TO_KB.get(group, "")


def get_kb(features: Dict[str, Any]) -> Dict[str, Any]:
    return EXOTIC_KB.get(kb_key_for_features(features), {})


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

    for level, required, _reason in kb.get("red_flags", []):
        if all(bool(features.get(name)) for name in required):
            return level
    return None


def knowledge_risk_reasons(features: Dict[str, Any]) -> List[str]:
    kb = get_kb(features)
    reasons: List[str] = []
    for _level, required, reason in kb.get("red_flags", []):
        if all(bool(features.get(name)) for name in required):
            reasons.append(reason)
    return _dedupe(reasons)


def knowledge_tree_leaf(features: Dict[str, Any]) -> Optional[str]:
    kb = get_kb(features)
    if not kb:
        return None

    for label, keys in kb.get("system_hints", []):
        if any(bool(features.get(key)) for key in keys):
            return label
    return "异宠综合分诊"


def knowledge_questions(features: Dict[str, Any]) -> List[str]:
    kb = get_kb(features)
    if not kb:
        return []

    questions: List[str] = []
    # 红旗命中时，把最关键追问提前。
    for _level, required, reason in kb.get("red_flags", []):
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
