from typing import Dict, Any

try:
    from backend.exotic_knowledge import knowledge_risk_level
except ModuleNotFoundError:
    from exotic_knowledge import knowledge_risk_level


def evaluate(features: Dict[str, Any]) -> str:
    species_group = features.get("species_group")
    vomiting = features.get("vomiting")
    frequent_vomiting = features.get("frequent_vomiting")
    persistent_vomiting = features.get("persistent_vomiting")
    blood = features.get("blood")
    blood_vomit = features.get("blood_vomit")
    coffee_ground_vomit = features.get("coffee_ground_vomit")
    low_energy = features.get("low_energy")
    normal_energy = features.get("normal_energy")
    anorexia = features.get("anorexia")
    appetite_down = features.get("appetite_down")
    retching = features.get("retching")
    abd_distension = features.get("abd_distension")
    mild_single_vomit = features.get("mild_single_vomit")

    # 通用急症红旗：不依赖物种，先按高风险收口。
    if (
        features.get("collapse")
        or features.get("neurologic_signs")
        or features.get("trauma")
        or features.get("toxin")
        or features.get("respiratory_distress")
    ):
        return "高"

    # 异宠知识库优先判定。
    kb_risk = knowledge_risk_level(features)
    if kb_risk:
        return kb_risk

    # 异宠物种特异红旗兜底。
    if species_group == "lagomorph" and features.get("rabbit_gi_stasis_risk"):
        return "高"

    if species_group == "avian" and (features.get("avian_respiratory_risk") or features.get("egg_binding")):
        return "高"

    if species_group in ("reptile", "amphibian", "fish"):
        if low_energy and (anorexia or features.get("skin_shell_issue") or features.get("mbd_signs")):
            return "中"
        if features.get("reptile_husbandry_risk") and (appetite_down or low_energy):
            return "中"

    if species_group in ("rodent", "mustelid", "insectivore", "marsupial"):
        if anorexia and low_energy:
            return "高"
        if features.get("small_mammal_dental_gi_risk"):
            return "中"

    # 高风险：消化道出血 / 呕血 / 咖啡色呕吐物
    if blood or blood_vomit or coffee_ground_vomit:
        return "高"

    # 高风险：干呕 + 腹胀，警惕胃扩张/扭转
    if retching and abd_distension:
        return "高"

    # 高风险：频繁呕吐 + 精神差 + 腹胀
    if vomiting and frequent_vomiting and low_energy and abd_distension:
        return "高"

    # 高风险：持续呕吐 + 食欲废绝
    if vomiting and persistent_vomiting and anorexia:
        return "高"

    # 高风险兜底：呕吐 + 腹胀 + 精神差/频繁呕吐
    if vomiting and abd_distension and (low_energy or frequent_vomiting):
        return "高"

    # 高风险兜底：干呕 + 精神差
    if retching and low_energy:
        return "高"

    # 低风险：单次轻微呕吐 + 精神正常，无其他危险信号
    if (
        vomiting
        and mild_single_vomit
        and normal_energy
        and not appetite_down
        and not low_energy
        and not abd_distension
        and not retching
    ):
        return "低"

    # 中风险：呕吐 + 食欲下降但精神尚可
    if vomiting and appetite_down and (normal_energy or not low_energy):
        return "中"

    # 中风险：有呕吐并伴随非立即危急异常
    if vomiting and (
        frequent_vomiting
        or persistent_vomiting
        or low_energy
        or appetite_down
        or abd_distension
        or retching
    ):
        return "中"

    # 中风险：非呕吐主诉但有精神差、厌食、腹泻等
    if low_energy or anorexia or features.get("diarrhea"):
        return "中"

    return "低"
