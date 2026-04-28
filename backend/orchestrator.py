try:
    from backend.feature_engine import extract_features
    from backend.risk_engine import evaluate
    from backend.question_engine import generate
    from backend.diagnosis_engine import rank
except ModuleNotFoundError:
    from feature_engine import extract_features
    from risk_engine import evaluate
    from question_engine import generate
    from diagnosis_engine import rank


def run_agent(text: str):
    features = extract_features(text)

    risk = evaluate(features)

    tree_path = ["消化系统", "胃肠道", "急性呕吐"]

    questions = generate(tree_path, features)

    diseases = rank(features, tree_path)

    return {
    "risk_level": risk,
    "tree_path": tree_path,
    "diseases": diseases,
    "next_questions": questions,   # 保持 list
    "actions": ["建议进一步检查血常规、生化、影像学"]
}