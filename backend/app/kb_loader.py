import os, json, pathlib, yaml
from typing import Dict, Any, List

DEFAULT_KB_ROOT = pathlib.Path(__file__).resolve().parents[2] / "knowledge-base"
KB_ROOT = pathlib.Path(os.getenv("KB_ROOT", str(DEFAULT_KB_ROOT))).resolve()

VOMITING_JSON = KB_ROOT / "vomiting" / "data" / "vomiting.json"
PROMPTS_YAML  = KB_ROOT / "vomiting" / "data" / "prompts.yaml"

class KBLoadError(Exception): pass

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
    raw = _read_yaml(PROMPTS_YAML) or {}
    items = raw.get("prompts", [])
    out = {}
    for it in items:
        pid = it.get("id")
        if pid:
            out[pid] = {
                "zh": it.get("zh", ""),
                "en": it.get("en", "")
            }
    return out

def _transform_node(node, prompts, locale="zh", embed_prompts=True):
    raw_zh = node.get("label_zh", "")
    raw_en = node.get("label_en", "")
    label = raw_zh if locale == "zh" else (raw_en or raw_zh)

    out = {
        "id": node["id"],
        "label": label,
        "label_zh": raw_zh,
        "label_en": raw_en,
        "tags": node.get("tags", []),
        "signals": node.get("signals", [])
    }

    qids = node.get("questions_ref", [])
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
        _transform_node(child, prompts, locale, embed_prompts)
        for child in children
    ]
    return out

def get_vomiting_payload(locale="zh", embed_prompts=True):
    tree = load_vomiting_tree()
    prompts = load_prompts_map() if embed_prompts else {}
    root = tree.get("root", {})
    return {
        "version": tree.get("version"),
        "updated_at": tree.get("updated_at"),
        "root": _transform_node(root, prompts, locale, embed_prompts)
    }

def get_prompts_by_ids(ids, locale="zh"):
    prompts = load_prompts_map()
    res = []
    for qid in ids:
        if qid in prompts:
            res.append({
                "id": qid,
                "text": prompts[qid].get(locale, ""),
                "text_zh": prompts[qid].get("zh", ""),
                "text_en": prompts[qid].get("en", "")
            })
    return res
