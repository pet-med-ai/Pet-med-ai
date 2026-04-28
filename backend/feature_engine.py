from typing import Dict, Any


def extract_features(text: str) -> Dict[str, Any]:
    text = text.lower()

    return {
        "blood": "血" in text,
        "low_energy": "精神差" in text or "没精神" in text,
        "anorexia": "不吃" in text or "食欲差" in text,
        "retching": "干呕" in text,
        "diarrhea": "腹泻" in text,
        "acute": "突然" in text,
        "chronic": "几天" in text or "持续" in text,
    }