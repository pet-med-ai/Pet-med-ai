from typing import Dict, Any


def evaluate(features: Dict[str, Any]) -> str:
    if features.get("blood") or features.get("retching"):
        return "高"
    if features.get("low_energy") or features.get("anorexia"):
        return "中"
    return "低"