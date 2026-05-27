from typing import Dict, Any, Iterable

try:
    from backend.species_context import build_species_context
except ModuleNotFoundError:
    from species_context import build_species_context


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_features(text: str) -> Dict[str, Any]:
    raw_text = text or ""
    text = raw_text.lower()
    species_context = build_species_context(text=raw_text)
    species_group = species_context.get("group")

    vomiting = _has_any(text, [
        "呕吐", "吐了", "吐", "vomit", "vomiting",
    ])

    frequent_vomiting = (
        _has_any(text, [
            "频繁呕吐", "反复呕吐", "多次呕吐", "呕吐多次",
            "一直吐", "不停吐", "连续呕吐", "连续吐",
            "吐很多次", "频繁吐", "反复吐",
        ])
        or ("频繁" in text and vomiting)
        or ("多次" in text and vomiting)
        or ("反复" in text and vomiting)
    )

    persistent_vomiting = (
        _has_any(text, [
            "持续呕吐", "持续吐", "一直吐", "不停吐",
            "连续呕吐", "连续吐", "反复呕吐", "反复吐",
        ])
        or ("持续" in text and vomiting)
    )

    blood_vomit = _has_any(text, [
        "呕血", "吐血", "呕吐带血", "呕吐物带血",
        "呕吐物有血", "血性呕吐", "鲜血", "血丝",
    ])

    coffee_ground_vomit = _has_any(text, [
        "咖啡色呕吐", "咖啡色呕吐物", "咖啡样呕吐",
        "咖啡渣", "咖啡样", "黑褐色呕吐", "褐色呕吐",
    ])

    gi_bleeding = blood_vomit or coffee_ground_vomit or _has_any(text, [
        "便血", "黑便", "柏油样便", "血便",
    ])

    low_energy = _has_any(text, [
        "精神差", "没精神", "精神不好", "精神沉郁",
        "沉郁", "精神萎靡", "嗜睡", "虚弱", "站不稳",
        "不动", "趴着", "闭眼", "反应差",
    ])

    normal_energy = _has_any(text, [
        "精神正常", "精神好", "精神尚可", "精神还可以",
        "精神可以", "精神状态正常", "精神佳",
    ])

    anorexia = _has_any(text, [
        "不吃", "拒食", "食欲废绝", "废绝", "停食",
        "完全不吃", "食欲完全没有", "吃不下", "不采食",
    ])

    appetite_down = anorexia or _has_any(text, [
        "食欲差", "食欲下降", "食欲减退",
        "胃口差", "吃得少", "少食", "采食下降",
    ])

    retching = _has_any(text, [
        "干呕", "干吐", "吐不出来", "想吐吐不出", "呕不出来",
    ])

    abd_distension = _has_any(text, [
        "腹胀", "肚子胀", "腹部胀", "腹部膨大",
        "肚子鼓", "胃胀", "腹围增大", "鼓肚",
    ])

    mild_single_vomit = (
        vomiting
        and _has_any(text, [
            "单次", "一次", "吐了一次", "只吐了一次",
            "轻微呕吐", "轻微吐",
        ])
        and not frequent_vomiting
        and not persistent_vomiting
    )

    diarrhea = _has_any(text, ["腹泻", "拉稀", "软便", "水样便"])
    respiratory_distress = _has_any(text, [
        "呼吸困难", "呼吸急促", "张口呼吸", "伸颈呼吸", "喘不上气",
        "喘", "发绀", "紫绀", "尾巴上下摆", "尾部上下摆", "tail bobbing",
        "open mouth breathing", "dyspnea", "气喘", "呼吸有声", "甩头呼吸",
    ])
    neurologic_signs = _has_any(text, [
        "抽搐", "癫痫", "侧躺", "转圈", "歪头", "瘫痪", "后肢无力",
        "震颤", "昏迷", "意识不清", "seizure", "collapse",
    ])
    collapse = _has_any(text, ["休克", "倒地", "虚脱", "昏迷", "站不起来", "collapse"])
    trauma = _has_any(text, ["摔", "撞", "咬伤", "外伤", "出血不止", "车祸", "夹伤"])
    toxin = _has_any(text, ["中毒", "误食", "毒", "杀虫剂", "老鼠药", "清洁剂", "重金属"])

    no_feces = _has_any(text, ["无粪", "没拉屎", "不排便", "没有粪便", "24小时没拉", "一天没拉", "不拉便"])
    feces_down = no_feces or _has_any(text, ["粪便减少", "便便变少", "粪球变小", "粪少", "排便减少"])
    dental_signs = _has_any(text, ["流口水", "磨牙", "牙", "门齿", "臼齿", "咬合", "下巴湿", "挑食草"])
    egg_binding = _has_any(text, ["蛋滞留", "卡蛋", "难产", "下不出蛋", "产蛋困难"])
    skin_shell_issue = _has_any(text, ["蜕皮", "烂甲", "腐皮", "溃疡", "水肿", "掉鳞", "壳软", "甲壳"])
    husbandry_problem = _has_any(text, [
        "温度", "低温", "高温", "热点", "冷区", "温区", "晒背", "uvb", "uva",
        "湿度", "垫材", "水质", "氨", "过滤", "加热", "灯", "环境", "饲养", "开食",
    ])
    regurgitation = _has_any(text, ["反刍", "返流", "吐食", "甩食", "regurgitation"])

    return {
        "species_context": species_context,
        "species": species_context.get("species"),
        "species_group": species_group,
        "is_exotic": species_context.get("is_exotic"),
        "vomiting": vomiting,
        "frequent_vomiting": frequent_vomiting,
        "persistent_vomiting": persistent_vomiting,
        "blood": gi_bleeding,
        "blood_vomit": blood_vomit,
        "coffee_ground_vomit": coffee_ground_vomit,
        "low_energy": low_energy,
        "normal_energy": normal_energy,
        "anorexia": anorexia,
        "appetite_down": appetite_down,
        "retching": retching,
        "abd_distension": abd_distension,
        "mild_single_vomit": mild_single_vomit,
        "diarrhea": diarrhea,
        "acute": _has_any(text, ["突然", "急性", "刚刚", "今天"]),
        "chronic": _has_any(text, ["几天", "持续", "长期", "反复"]),
        "respiratory_distress": respiratory_distress,
        "neurologic_signs": neurologic_signs,
        "collapse": collapse,
        "trauma": trauma,
        "toxin": toxin,
        "no_feces": no_feces,
        "feces_down": feces_down,
        "dental_signs": dental_signs,
        "egg_binding": egg_binding,
        "skin_shell_issue": skin_shell_issue,
        "husbandry_problem": husbandry_problem,
        "regurgitation": regurgitation,
        "rabbit_gi_stasis_risk": species_group == "lagomorph" and (anorexia or feces_down or abd_distension),
        "small_mammal_dental_gi_risk": species_group in ("lagomorph", "rodent") and (dental_signs or anorexia or feces_down),
        "avian_respiratory_risk": species_group == "avian" and respiratory_distress,
        "reptile_husbandry_risk": species_group in ("reptile", "amphibian", "fish") and husbandry_problem,
    }
