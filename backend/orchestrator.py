try:
    from backend.feature_engine import extract_features
    from backend.risk_engine import evaluate
    from backend.question_engine import generate
    from backend.diagnosis_engine import rank
    from backend.exotic_knowledge import knowledge_tree_leaf
except ModuleNotFoundError:
    from feature_engine import extract_features
    from risk_engine import evaluate
    from question_engine import generate
    from diagnosis_engine import rank
    from exotic_knowledge import knowledge_tree_leaf


def _system_path(features):
    kb_leaf = knowledge_tree_leaf(features)
    if kb_leaf:
        return kb_leaf
    if features.get("respiratory_distress"):
        return "呼吸系统急症"
    if features.get("rabbit_gi_stasis_risk") or features.get("vomiting") or features.get("diarrhea") or features.get("anorexia"):
        return "消化系统/采食排泄异常"
    if features.get("reptile_husbandry_risk") or features.get("husbandry_problem"):
        return "饲养环境/代谢相关"
    if features.get("neurologic_signs"):
        return "神经系统急症"
    return "综合分诊"


def run_agent(text: str):
    features = extract_features(text)
    species_context = features.get("species_context") or {}

    risk = evaluate(features)

    tree_path = [
        species_context.get("label") or "未知物种",
        species_context.get("group_label") or species_context.get("group") or "未分组",
        _system_path(features),
    ]

    questions = generate(tree_path, features)

    diseases = rank(features, tree_path)
    actions = diseases.get("actions") or ["建议进一步检查血常规、生化、影像学"]

    return {
        "risk_level": risk,
        "species_context": species_context,
        "tree_path": tree_path,
        "diseases": diseases,
        "next_questions": questions,
        "actions": actions,
    }
