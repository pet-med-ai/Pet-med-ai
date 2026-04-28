from typing import Dict, Any, List


def rank(features: Dict[str, Any], tree_path: List[str]) -> Dict[str, List[str]]:
    diseases: List[str] = []

    if features.get("blood"):
        diseases.extend(["胃肠道出血", "胃溃疡", "异物"])

    if features.get("retching"):
        diseases.extend(["异物", "胃扩张/扭转风险"])

    if features.get("diarrhea"):
        diseases.extend(["胃肠炎", "寄生虫感染", "病毒性肠炎"])

    if features.get("low_energy"):
        diseases.extend(["胰腺炎", "感染性疾病", "代谢性疾病"])

    # 利用 tree_path（你现在虽然没用，但接口必须兼容）
    if "bloody_vomiting" in tree_path:
        diseases.insert(0, "严重胃肠道出血")

    if not diseases:
        diseases.extend(["非特异性胃炎", "饮食性胃肠炎"])

    diseases = list(dict.fromkeys(diseases))

    return {
        "diseases": diseases,
        "checks": ["血常规", "生化", "腹部影像"],
        "actions": ["补液", "止吐", "必要时住院观察"]
    }