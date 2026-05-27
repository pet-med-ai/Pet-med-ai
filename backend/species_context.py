from __future__ import annotations

from typing import Any, Dict, Iterable


SPECIES_GROUP_LABELS: Dict[str, str] = {
    "canine": "犬科伴侣动物",
    "feline": "猫科伴侣动物",
    "lagomorph": "兔形目异宠",
    "rodent": "啮齿类异宠",
    "mustelid": "鼬科异宠",
    "avian": "鸟类异宠",
    "reptile": "爬行动物异宠",
    "amphibian": "两栖类异宠",
    "fish": "水族动物",
    "marsupial": "有袋类异宠",
    "insectivore": "小型食虫类异宠",
    "other_exotic": "其他异宠",
}


SPECIES_PROFILES: Dict[str, Dict[str, Any]] = {
    "dog": {
        "label": "犬",
        "group": "canine",
        "is_exotic": False,
        "aliases": ["dog", "canine", "犬", "狗", "小狗", "狗狗"],
    },
    "cat": {
        "label": "猫",
        "group": "feline",
        "is_exotic": False,
        "aliases": ["cat", "feline", "猫", "猫咪", "小猫"],
    },
    "rabbit": {
        "label": "兔",
        "group": "lagomorph",
        "is_exotic": True,
        "aliases": ["rabbit", "bunny", "lagomorph", "兔", "兔子", "宠物兔", "垂耳兔", "侏儒兔"],
    },
    "guinea_pig": {
        "label": "豚鼠",
        "group": "rodent",
        "is_exotic": True,
        "aliases": ["guinea pig", "guinea_pig", "cavy", "豚鼠", "荷兰猪", "天竺鼠"],
    },
    "hamster": {
        "label": "仓鼠",
        "group": "rodent",
        "is_exotic": True,
        "aliases": ["hamster", "仓鼠", "金丝熊", "熊仔", "侏儒仓鼠"],
    },
    "chinchilla": {
        "label": "龙猫",
        "group": "rodent",
        "is_exotic": True,
        "aliases": ["chinchilla", "龙猫", "毛丝鼠"],
    },
    "rat": {
        "label": "宠物鼠",
        "group": "rodent",
        "is_exotic": True,
        "aliases": ["rat", "mouse", "mice", "大鼠", "小鼠", "花枝鼠", "宠物鼠"],
    },
    "ferret": {
        "label": "雪貂",
        "group": "mustelid",
        "is_exotic": True,
        "aliases": ["ferret", "雪貂", "貂"],
    },
    "bird": {
        "label": "鸟",
        "group": "avian",
        "is_exotic": True,
        "aliases": ["bird", "avian", "parrot", "budgie", "cockatiel", "鸟", "鸟类", "鹦鹉", "玄凤", "虎皮", "文鸟", "八哥", "鸽子", "鹩哥"],
    },
    "reptile": {
        "label": "爬宠",
        "group": "reptile",
        "is_exotic": True,
        "aliases": ["reptile", "爬宠", "爬行动物"],
    },
    "turtle": {
        "label": "龟",
        "group": "reptile",
        "is_exotic": True,
        "aliases": ["turtle", "tortoise", "terrapin", "龟", "乌龟", "陆龟", "水龟", "半水龟"],
    },
    "snake": {
        "label": "蛇",
        "group": "reptile",
        "is_exotic": True,
        "aliases": ["snake", "蛇", "玉米蛇", "球蟒", "王蛇"],
    },
    "lizard": {
        "label": "蜥蜴",
        "group": "reptile",
        "is_exotic": True,
        "aliases": ["lizard", "gecko", "bearded dragon", "iguana", "蜥蜴", "守宫", "鬃狮", "鬃狮蜥", "豹纹守宫", "变色龙"],
    },
    "amphibian": {
        "label": "两栖动物",
        "group": "amphibian",
        "is_exotic": True,
        "aliases": ["amphibian", "frog", "toad", "newt", "salamander", "axolotl", "两栖", "蛙", "青蛙", "角蛙", "蟾蜍", "蝾螈", "六角恐龙"],
    },
    "hedgehog": {
        "label": "刺猬",
        "group": "insectivore",
        "is_exotic": True,
        "aliases": ["hedgehog", "刺猬", "非洲迷你刺猬"],
    },
    "sugar_glider": {
        "label": "蜜袋鼯",
        "group": "marsupial",
        "is_exotic": True,
        "aliases": ["sugar glider", "sugar_glider", "蜜袋鼯"],
    },
    "fish": {
        "label": "观赏鱼",
        "group": "fish",
        "is_exotic": True,
        "aliases": ["fish", "鱼", "观赏鱼", "金鱼", "锦鲤", "热带鱼", "斗鱼"],
    },
    "other": {
        "label": "其他动物",
        "group": "other_exotic",
        "is_exotic": True,
        "aliases": ["other", "exotic", "其他", "异宠", "特殊宠物"],
    },
}


def _clean_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle and needle in text for needle in needles)


def normalize_species(value: Any, default: str = "dog") -> str:
    """把前端 / 历史数据 / 中文输入统一为内部 species key。"""
    raw = str(value or "").strip()
    if not raw:
        return default

    token = _clean_token(raw)
    if token in SPECIES_PROFILES:
        return token

    for key, profile in SPECIES_PROFILES.items():
        aliases = {_clean_token(alias) for alias in profile.get("aliases", [])}
        if token in aliases:
            return key

    # 中文自由文本兜底；别让“龙猫”被短词“猫”抢先命中。
    lowered = raw.lower().replace("-", "_")
    alias_pairs = []
    for key, profile in SPECIES_PROFILES.items():
        for alias in profile.get("aliases", []):
            alias_text = str(alias).strip().lower().replace("-", "_")
            if alias_text:
                alias_pairs.append((len(alias_text), alias_text, key))
    for _, alias_text, key in sorted(alias_pairs, reverse=True):
        if alias_text in lowered:
            return key

    return "other"


def infer_species_from_text(text: Any) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""

    lowered = raw.lower().replace("-", "_")
    alias_pairs = []
    for key, profile in SPECIES_PROFILES.items():
        for alias in profile.get("aliases", []):
            alias_text = str(alias).strip().lower().replace("-", "_")
            if alias_text:
                alias_pairs.append((len(alias_text), alias_text, key))
    for _, alias_text, key in sorted(alias_pairs, reverse=True):
        if alias_text in lowered:
            return key
    return ""


def build_species_context(species: Any = None, text: Any = "") -> Dict[str, Any]:
    normalized = normalize_species(species, default="")
    inferred = infer_species_from_text(text)

    if not normalized:
        normalized = inferred or "dog"
    elif normalized == "other" and inferred:
        normalized = inferred

    profile = SPECIES_PROFILES.get(normalized, SPECIES_PROFILES["other"])
    group = profile.get("group", "other_exotic")

    return {
        "species": normalized,
        "label": profile.get("label", normalized),
        "group": group,
        "group_label": SPECIES_GROUP_LABELS.get(group, "其他异宠"),
        "is_exotic": bool(profile.get("is_exotic", True)),
    }


def species_context_line(context: Dict[str, Any]) -> str:
    label = context.get("label") or context.get("species") or "未知物种"
    group_label = context.get("group_label") or context.get("group") or "未知分组"
    exotic = "异宠" if context.get("is_exotic") else "犬猫"
    return f"物种：{label}（{exotic} / {group_label}）"
