from typing import Dict, Any, List

try:
    from backend.exotic_knowledge import knowledge_questions
except ModuleNotFoundError:
    from exotic_knowledge import knowledge_questions


def generate(tree_path: List[str], features: Dict[str, Any]) -> Dict[str, List[str]]:
    questions: List[str] = []
    species_context = features.get("species_context") or {}
    species_group = features.get("species_group")

    # 异宠知识库问题优先；后续再叠加通用红旗问题。
    questions.extend(knowledge_questions(features))

    if not questions:
        if species_group == "lagomorph":
            if features.get("anorexia") or features.get("feces_down"):
                questions.append("兔子停食持续多久？粪便是减少、变小，还是完全没有？")
            questions.append("是否腹胀、磨牙、弓背、拒绝活动或触腹疼痛？")
            questions.append("最近饮水和排尿是否减少？是否有流口水、挑食草或牙齿问题？")

        elif species_group == "avian":
            if features.get("respiratory_distress"):
                questions.append("是否张口呼吸、尾部上下摆动、伸颈呼吸或发出呼吸音？")
            questions.append("鸟的粪便、尿酸颜色和量是否改变？近期体重是否下降？")
            questions.append("是否有蓬毛闭眼、站杆不稳、鼻孔分泌物或产蛋异常？")

        elif species_group == "rodent":
            questions.append("采食、饮水和粪便量是否明显下降？是否流口水、磨牙或面部肿胀？")
            questions.append("笼舍温度、垫材、近期换粮或同笼动物状态是否有变化？")

        elif species_group == "mustelid":
            questions.append("是否突然虚弱、流口水、后肢无力、呕吐腹泻或疑似误食橡胶/异物？")
            questions.append("最近食欲、排便、体重和活动量有什么变化？")

        elif species_group in ("reptile", "amphibian", "fish"):
            questions.append("请补充具体品种、环境温度/热点/冷区、湿度或水质，以及 UVB/晒背条件。")
            questions.append("最近进食、排便、蜕皮/换甲、浮水/沉底和活动量是否异常？")
            if features.get("respiratory_distress"):
                questions.append("是否张口呼吸、伸颈、鼻泡、喘鸣或长期泡水/浮水？")

    if features.get("blood"):
        questions.append("呕吐物或粪便里是鲜血、血丝，还是咖啡色/黑色内容物？")

    if features.get("retching"):
        questions.append("是否频繁干呕但吐不出来？腹部是否同时变大或触碰疼痛？")

    if features.get("low_energy"):
        questions.append("精神变差是突然出现还是逐渐加重？目前是否能站立或正常反应？")

    if features.get("diarrhea"):
        questions.append("是否同时有腹泻、黑便、便血或排便次数明显改变？")

    if not questions:
        if species_context.get("is_exotic"):
            questions.append("请补充具体物种、饲养环境、最近一次进食/排便/排尿时间，以及体重变化。")
        else:
            questions.append("症状持续了多久？每天大概几次？精神、食欲和排尿情况如何？")

    # 保持顺序去重，避免动态问诊连续重复。
    return {
        "questions": list(dict.fromkeys(q for q in questions if q))
    }
