from typing import Dict, Any, List


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys(item for item in items if item))


def rank(features: Dict[str, Any], tree_path: List[str]) -> Dict[str, List[str]]:
    diseases: List[str] = []
    checks: List[str] = []
    actions: List[str] = []
    species_context = features.get("species_context") or {}
    species_group = features.get("species_group")

    if species_group == "lagomorph":
        diseases.extend(["兔胃肠淤滞风险", "牙科疾病相关采食下降", "胃肠梗阻/疼痛相关厌食"])
        checks.extend(["体重与脱水评估", "腹部触诊和腹部影像", "口腔/臼齿检查", "血糖/电解质评估"])
        actions.extend(["按兔异宠急诊分诊：停食、无粪或腹胀时优先评估疼痛、脱水和梗阻风险。"])

    elif species_group == "avian":
        diseases.extend(["鸟类呼吸道/气囊问题", "应激或全身性疾病", "消化道/肝胆问题"])
        if features.get("egg_binding"):
            diseases.insert(0, "蛋滞留/繁殖相关急症")
        checks.extend(["体重和体况评分", "呼吸状态与鼻孔/口腔检查", "粪便与尿酸评估", "必要时影像检查"])
        actions.extend(["鸟类出现呼吸异常、蓬毛闭眼或站立不稳时按高风险先稳定再检查。"])

    elif species_group == "rodent":
        diseases.extend(["牙科疾病", "胃肠功能异常", "呼吸道感染", "饲养环境相关问题"])
        checks.extend(["体重趋势", "口腔/牙齿检查", "粪便评估", "胸腹部影像按需"])
        actions.extend(["小型啮齿类采食下降进展快，应重点记录进食、饮水、粪便和体重变化。"])

    elif species_group == "mustelid":
        diseases.extend(["胃肠异物", "胃肠炎", "低血糖/胰岛素瘤相关虚弱", "肾上腺/内分泌问题"])
        checks.extend(["血糖", "腹部触诊和影像", "粪便评估", "脱水与疼痛评分"])
        actions.extend(["雪貂突然虚弱、流涎或后肢无力时优先排查低血糖和异物风险。"])

    elif species_group in ("reptile", "amphibian"):
        diseases.extend(["饲养环境/温湿度相关疾病", "感染性疾病", "代谢性骨病/营养问题", "寄生虫或消化道问题"])
        checks.extend(["具体物种与饲养参数记录", "温区/湿度/UVB 或水质评估", "体重和脱水评估", "粪检/影像按需"])
        actions.extend(["爬宠/两栖类诊断必须把温度、湿度、UVB、水质和近期采食排便作为核心病史。"])

    elif species_group == "fish":
        diseases.extend(["水质相关应激", "感染性疾病", "寄生虫", "营养或环境问题"])
        checks.extend(["水温、pH、氨氮/亚硝酸盐记录", "同缸动物状态", "皮肤/鳃/游姿观察"])
        actions.extend(["水族病例先记录水质、同缸发病和近期换水/加药史。"])

    elif species_context.get("is_exotic"):
        diseases.extend(["异宠非特异性全身疾病", "饲养环境相关问题", "消化或呼吸系统疾病"])
        checks.extend(["具体物种确认", "饲养环境记录", "体重趋势", "基础体检和影像/粪检按需"])
        actions.extend(["先补齐物种、饲养环境、进食排泄和体重变化，再细化鉴别诊断。"])

    if features.get("blood"):
        diseases.extend(["胃肠道出血", "胃肠溃疡/糜烂", "异物或严重炎症"])

    if features.get("retching"):
        diseases.extend(["异物", "胃扩张/扭转风险"])

    if features.get("diarrhea"):
        diseases.extend(["胃肠炎", "寄生虫感染", "病毒性/细菌性肠炎"])

    if features.get("low_energy"):
        diseases.extend(["感染性疾病", "代谢性疾病", "疼痛或脱水相关精神沉郁"])

    if "bloody_vomiting" in tree_path:
        diseases.insert(0, "严重胃肠道出血")

    if not diseases:
        diseases.extend(["非特异性胃肠不适", "饮食或环境变化相关问题"])

    if not checks:
        checks.extend(["血常规", "生化", "腹部影像"])

    if not actions:
        actions.extend(["结合体征、实验室检查和影像进一步判断；高风险时先稳定生命体征。"])

    return {
        "diseases": _dedupe(diseases),
        "checks": _dedupe(checks),
        "actions": _dedupe(actions),
    }
