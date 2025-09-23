import os
import json
import pathlib
from typing import Dict, Any, List
import yaml

# 允许不设环境变量时用相对路径兜底（仓库根目录/knowledge-base）
DEFAULT_KB_ROOT = pathlib.Path(__file__).resolve().parents[2] / "knowledge-base"
KB_ROOT = pathlib.Path(os.getenv("KB_ROOT", str(DEFAULT_KB_ROOT))).resolve()

VOMITING_JSON = KB_ROOT / "vomiting" / "data" / "vomiting.json"
PROMPTS_YAML  = KB_ROOT / "vomiting" / "data" / "prompts.yaml"

class KBLoadError(Exception):
    pass

def _read_json(p: pathlib.Path) -> Any:
    if not p.exists():
        raise KBLoadError(f"JSON file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))

def _read_yaml(p: pathlib.Path) -> Any:
    if not p.exists():
        raise KBLoadError(f"YAML file not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def load_vomiting_tree() -> Dict[str, Any]:
    return _read_json(VOMITING_JSON)

def load_prompts_map() -> Dict[str, Dict[str, str]]:
    """
    返回形如:
    {
      "Q_ID": {"zh": "中文问句", "en": "English prompt"},
      ...
    }
    """
    raw = _read_yaml(PROMPTS_YAML) or {}
    items = raw.get("prompts", [])
    out: Dict[str, Dict[str, str]] = {}
    for it in items:
        pid = it.get("id")
        if not pid:
            continue
        out[pid] = {"zh": it.get("zh", ""), "en": it.get("en", "")}
    return out

def _transform_node(node: Dict[str, Any],
                    prompts: Dict[str, Dict[str, str]],
                    locale: str,
                    embed_prompts: bool) -> Dict[str, Any]:
    label = node.get("label_zh") if locale == "zh" else node.get("label_en")
    out: Dict[str, Any] = {
        "id": node["id"],
        "label": label,
        "label_zh": node.get("label_zh"),
        "label_en": node.get("label_en"),
        "tags": node.get("tags", []),
        "signals": node.get("signals", [])
    }
    qids: List[str] = node.get("questions_ref", [])

    if embed_prompts:
        out["prompts"] = [
            {
                "id": qid,
                "text": prompts.get(qid, {}).get(locale, ""),
                "text_zh": prompts.get(qid, {}).get("zh", ""),
                "text_en": prompts.get(qid, {}).get("en", "")
            }
            for qid in qids
        ]
    else:
        out["questions_ref"] = qids

    children = node.get("children", [])
    out["children"] = [
        _transform_node(c, prompts, locale, embed_prompts) for c in children
    ]
    return out

def get_vomiting_payload(locale: str = "zh", embed_prompts: bool = True) -> Dict[str, Any]:
    """
    返回结构：
    {
      "version": "1.0.0",
      "updated_at": "...",
      "root": { ... transformed node ... }
    }
    """
    tree = load_vomiting_tree()
    prompts = load_prompts_map()
    root_node = tree.get("root", {})
    return {
        "version": tree.get("version"),
        "updated_at": tree.get("updated_at"),
        "root": _transform_node(root_node, prompts, locale, embed_prompts)
    }

def get_prompts_by_ids(ids: List[str], locale: str = "zh") -> List[Dict[str, str]]:
    prompts = load_prompts_map()
    res: List[Dict[str, str]] = []
    for qid in ids:
        p = prompts.get(qid)
        if not p:
            continue
        res.append({
            "id": qid,
            "text": p.get(locale, ""),
            "text_zh": p.get("zh", ""),
            "text_en": p.get("en", "")
        })
    return res
