from typing import Dict, Any, Iterable


def _has_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def extract_features(text: str) -> Dict[str, Any]:
    text = (text or "").lower()

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
    ])

    normal_energy = _has_any(text, [
        "精神正常", "精神好", "精神尚可", "精神还可以",
        "精神可以", "精神状态正常", "精神佳",
    ])

    anorexia = _has_any(text, [
        "不吃", "拒食", "食欲废绝", "废绝",
        "完全不吃", "食欲完全没有", "吃不下",
    ])

    appetite_down = anorexia or _has_any(text, [
        "食欲差", "食欲下降", "食欲减退",
        "胃口差", "吃得少", "少食",
    ])

    retching = _has_any(text, [
        "干呕", "干吐", "吐不出来", "想吐吐不出", "呕不出来",
    ])

    abd_distension = _has_any(text, [
        "腹胀", "肚子胀", "腹部胀", "腹部膨大",
        "肚子鼓", "胃胀", "腹围增大",
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

    return {
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
        "diarrhea": _has_any(text, ["腹泻", "拉稀", "软便"]),
        "acute": _has_any(text, ["突然", "急性", "刚刚", "今天"]),
        "chronic": _has_any(text, ["几天", "持续", "长期", "反复"]),
    }
