# backend/app/triage_vomiting.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .kb_loader import load_vomiting_tree, load_prompts_map, get_prompts_by_ids

# ---- Input schema (keep simple for v1) ----
@dataclass
class VomitingTriageInput:
    duration_hours: Optional[float] = None
    vomit_count_24h: Optional[int] = None
    energy_level: Optional[str] = None  # normal|reduced|severe
    blood: Optional[str] = None         # none|fresh|coffee_ground
    abd_distension: Optional[bool] = None
    unproductive_retching: Optional[bool] = None
    suspected_toxin: Optional[bool] = None
    urine: Optional[str] = None         # normal|oliguria|anuria|unknown
    black_stool: Optional[bool] = None

def _find_child_by_id(children: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
    for c in children:
        if c.get("id") == node_id:
            return c
    return None

def _ensure_triage_first(tree: Dict[str, Any]) -> Dict[str, Any]:
    root = (tree or {}).get("root", {})
    children = root.get("children", []) or []
    if not children:
        raise ValueError("KB root.children is empty")
    if children[0].get("id") != "triage":
        # For safety: still allow, but warn via exception in hospital setting
        raise ValueError("KB triage node must be the first child of root.children")
    return tree

def _derive_signals(inp: VomitingTriageInput) -> List[str]:
    """Convert structured input into the 'signals' vocabulary used by triage nodes."""
    sig: List[str] = []

    # Blood-related
    if inp.blood == "fresh":
        sig.append("blood_vomit")
    elif inp.blood == "coffee_ground":
        sig.append("coffee_ground_emesis")

    # Abdomen / GDV-like
    if inp.abd_distension:
        sig.append("abdominal_distension")
    if inp.unproductive_retching:
        sig.append("unproductive_retching")

    # Toxin
    if inp.suspected_toxin:
        sig.append("suspected_toxin")

    # Urine
    if inp.urine == "anuria":
        sig.append("anuria")
    elif inp.urine == "oliguria":
        sig.append("oliguria")

    # Melena/black stool
    if inp.black_stool:
        sig.append("black_stool")

    # General severity heuristic
    if inp.energy_level == "severe":
        sig.append("severe_lethargy")

    # Onset
    if inp.duration_hours is not None and inp.duration_hours <= 24:
        sig.append("sudden_onset")
    if inp.duration_hours is not None and inp.duration_hours >= 72:
        sig.append("recurrent")  # crude: >=3 days treat as recurrent v1

    return sig

def _match_node(node: Dict[str, Any], signals: List[str]) -> Tuple[int, List[str]]:
    """Return (score, matched_signals). Simple intersection scoring."""
    node_signals = node.get("signals", []) or []
    matched = [s for s in node_signals if s in signals]
    return (len(matched), matched)

def triage_vomiting(inp: VomitingTriageInput, locale: str = "zh") -> Dict[str, Any]:
    """
    Hospital-facing triage:
    - triage-first
    - red-flag hit => emergency flow suggestion
    - otherwise return next questions + candidate branches
    """
    tree = _ensure_triage_first(load_vomiting_tree())
    prompts = load_prompts_map()

    root = tree["root"]
    triage = root["children"][0]  # enforced
    triage_children = triage.get("children", []) or []

    signals = _derive_signals(inp)

    # 1) Try red flags first
    red = _find_child_by_id(triage_children, "triage.red_flags")
    red_score, red_hit = _match_node(red or {}, signals) if red else (0, [])
    if red_score > 0:
        # Hospital output (not for pet owners)
        # Suggest first actions / tests (v1 hardcoded; v2 move into KB fields)
        return {
            "kb_version": tree.get("version"),
            "updated_at": tree.get("updated_at"),
            "priority_level": "emergency",
            "matched_node": "triage.red_flags",
            "signals_hit": red_hit,
            "next_questions": [
                {"id": q.get("id"), "text": q.get("text")}
                for q in get_prompts_by_ids(triage.get("questions_ref", []), locale=locale)
            ],
            "suggested_first_actions": [
                "T/HR/RR/BP/SpO2/CRT",
                "POCUS/腹部快速超声（如可用）",
                "血糖/PCV-TP/乳酸（按院内流程）"
            ],
            "suggested_first_tests": [
                "CBC + 生化 + 电解质（Na/K/Cl）",
                "腹部X线（异物/GDV/梗阻风险）",
                "必要时凝血/血气"
            ],
            "note_for_staff": "红旗命中：优先分诊处理；先稳定后完善病史与影像。",
        }

    # 2) No red flags: decide acute vs chronic node to guide questioning
    acute = _find_child_by_id(triage_children, "triage.acute")
    chronic = _find_child_by_id(triage_children, "triage.chronic")

    acute_score, acute_hit = _match_node(acute or {}, signals) if acute else (0, [])
    chronic_score, chronic_hit = _match_node(chronic or {}, signals) if chronic else (0, [])

    matched = None
    if acute_score >= chronic_score and acute_score > 0:
        matched = ("triage.acute", acute_hit)
    elif chronic_score > 0:
        matched = ("triage.chronic", chronic_hit)

    # 3) Suggest candidate branches (very rough v1: map by tags/signals only)
    # Here we just return the top-level branches as candidates.
    candidates = []
    for child in root.get("children", [])[1:]:  # skip triage itself
        score, hit = _match_node(child, signals)
        candidates.append({
            "id": child.get("id"),
            "label_zh": child.get("label_zh", ""),
            "label_en": child.get("label_en", ""),
            "score": score,
            "signals_hit": hit
        })
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # 4) Return “what to ask next” for staff
    # Use triage node prompts as a baseline
    triage_qs = [
        {
            "id": qid,
            "text": prompts.get(qid, {}).get(locale, ""),
            "text_zh": prompts.get(qid, {}).get("zh", ""),
            "text_en": prompts.get(qid, {}).get("en", "")
        }
        for qid in (triage.get("questions_ref", []) or [])
    ]

    priority = "urgent" if (inp.energy_level == "reduced" or (inp.vomit_count_24h or 0) >= 5) else "routine"

    return {
        "kb_version": tree.get("version"),
        "updated_at": tree.get("updated_at"),
        "priority_level": priority,
        "matched_node": matched[0] if matched else None,
        "signals_hit": matched[1] if matched else [],
        "derived_signals": signals,
        "next_questions": triage_qs,
        "ddx_candidates": candidates[:5],
        "note_for_staff": "v1：基于signals的粗分诊；v2建议把required_slots/recommended_tests写入KB节点。",
    }
