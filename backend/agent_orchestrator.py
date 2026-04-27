from __future__ import annotations

from typing import Any, Dict, List


def _contains_any(text: str, keywords: List[str]) -> bool:
    return any(k in text for k in keywords)


def run_agent(text: str) -> Dict[str, Any]:
    """
    半自动 Agent v1（实用级）最小编排器：
    - 只做规则路由与风险分层
    - 所有结论都需要医生确认
    """
    raw = (text or "").strip()
    norm = raw.lower()

    vomiting_hit = _contains_any(norm, ["vomit", "vomiting", "呕吐", "吐"])
    low_energy_hit = _contains_any(norm, ["精神差", "嗜睡", "没精神", "萎靡", "letharg", "depressed"])
    anorexia_hit = _contains_any(norm, ["不吃", "厌食", "食欲差", "食欲下降", "anorexia", "not eating"])
    long_duration_hit = _contains_any(norm, ["两天", "2天", "48小时", "2 days", "two days"])
    red_flag_hit = _contains_any(norm, ["血", "黑便", "腹胀", "干呕", "毒物", "无尿", "coffee ground"])

    route_to = "vomiting" if vomiting_hit else "general"

    if red_flag_hit:
        risk_level = "high"
    elif vomiting_hit and (low_energy_hit or anorexia_hit or long_duration_hit):
        risk_level = "high"
    elif vomiting_hit:
        risk_level = "medium"
    else:
        risk_level = "low"

    tree_best_path = ["消化系统", "胃肠道", "急性呕吐"] if route_to == "vomiting" else ["综合评估"]

    candidate_diseases: List[str] = []
    if route_to == "vomiting":
        candidate_diseases = ["急性胃肠炎", "胃肠道异物", "胰腺炎", "毒物相关胃肠道反应"]
    else:
        candidate_diseases = ["待完善分诊信息后生成"]

    checks = [
        "体温/心率/呼吸频率/脱水程度",
        "腹部触诊与疼痛评估",
        "CBC+生化+电解质",
        "必要时腹部X线或超声",
    ]
    actions = [
        "先行止吐与补液支持",
        "若出现红旗信号，立即急诊处理",
        "检查结果回填后由医生确认处置路径",
    ]

    return {
        "agent_mode": "semi_auto_v1",
        "chief_complaint": raw,
        "route_to": route_to,
        "risk_level": risk_level,
        "features": {
            "vomiting": vomiting_hit,
            "low_energy": low_energy_hit,
            "anorexia": anorexia_hit,
            "duration_ge_48h": long_duration_hit,
            "red_flags": red_flag_hit,
        },
        "tree_best_path": tree_best_path,
        "next_questions": [
            "呕吐频次与持续时长？",
            "是否有血性/咖啡色呕吐物？",
            "是否腹痛、腹胀、干呕无物？",
            "近期是否误食异物/毒物？",
            "尿量与精神状态是否进一步下降？",
        ],
        "candidate_diseases": candidate_diseases,
        "checks": checks,
        "actions": actions,
        "doctor_confirmation_required": True,
    }
