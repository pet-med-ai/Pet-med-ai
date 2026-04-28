from typing import Dict, Any, List


def generate(tree_path: List[str], features: Dict[str, Any]) -> Dict[str, List[str]]:
    questions: List[str] = []

    if features.get("blood"):
        questions.append("呕吐物里是鲜血、血丝，还是咖啡色液体？")

    if features.get("retching"):
        questions.append("是否频繁干呕但吐不出来？")

    if features.get("low_energy"):
        questions.append("精神变差是突然出现还是逐渐加重？")

    if features.get("diarrhea"):
        questions.append("是否同时有腹泻、黑便或便血？")

    if not questions:
        questions.append("呕吐持续了多久？每天大概几次？")

    return {
        "questions": questions
    }
