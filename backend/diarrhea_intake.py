"""M7 clinician-entered observations; no diagnosis, dosing or database access."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "knowledge-base/companion/intake/diarrhea.json"
STATES = {"unfilled": "未填写", "not_asked": "未询问", "observed": "已记录",
          "absent": "明确否定", "uncertain": "不确定", "unobservable": "无法观察"}
MAX_TEXT = 6000
MAX_TOTAL = 40000


class DiarrheaIntakeError(ValueError):
    def __init__(self, message="腹泻问卷格式或回答状态无效，请重新核对。", status=422):
        super().__init__(message)
        self.status = status


@lru_cache(maxsize=1)
def _template():
    raw = PATH.read_bytes()
    data = json.loads(raw)
    assert data["key"] == "diarrhea" and data["review_status"] == "clinical_draft"
    seen = set()
    for q in data["questions"]:
        assert q["key"] not in seen and q["kind"] in ("text", "presence")
        assert isinstance(q["label"], str) and q["label"]
        assert not q.get("when") or q["when"] in seen
        seen.add(q["key"])
    data["fingerprint"] = hashlib.sha256(raw).hexdigest()
    return data


def get_template(species):
    if species not in ("dog", "cat"):
        raise DiarrheaIntakeError("腹泻专用问卷仅适用于医生明确选择的犬或猫。")
    template = deepcopy(_template())
    template.update(species=species, states=dict(STATES), max_text=MAX_TEXT, max_total=MAX_TOTAL)
    for q in template["questions"]:
        q["states"] = [s for s in STATES if s != "absent" or q["kind"] == "presence"]
    return template


def _prefix(state, active):
    branch = "当前适用" if active else "当前不适用（原分支输入保留，仅供回看）"
    return f"状态：{STATES[state]}；{branch}\n医生原文：\n"


def build_snapshot(raw):
    if not isinstance(raw, dict) or set(raw) != {"version", "fingerprint", "species", "answers"}:
        raise DiarrheaIntakeError()
    template = get_template(raw["species"])
    if raw["version"] != template["version"] or raw["fingerprint"] != template["fingerprint"]:
        raise DiarrheaIntakeError("腹泻模板已变化；原输入仍需保留，请读取新模板后重新核对。", 409)
    answers = raw["answers"]
    known = {q["key"] for q in template["questions"]}
    if not isinstance(answers, dict) or set(answers) - known:
        raise DiarrheaIntakeError()
    clean = {}
    for q in template["questions"]:
        item = answers.get(q["key"], {"state": "unfilled", "text": ""})
        if not isinstance(item, dict) or set(item) != {"state", "text"}:
            raise DiarrheaIntakeError()
        state, text = item["state"], item["text"]
        if state not in q["states"] or not isinstance(text, str) or len(text) > MAX_TEXT:
            raise DiarrheaIntakeError()
        if state == "observed" and q["kind"] == "text" and not text.strip():
            raise DiarrheaIntakeError("已记录的文字项目需要填写原文，不能把空白作为已观察结果。")
        clean[q["key"]] = {"state": state, "text": text}
    if sum(len(a["text"]) for a in clean.values()) > MAX_TOTAL:
        raise DiarrheaIntakeError("腹泻问卷原文过长；请保留输入并整理后核对。")
    rows = []
    for q in template["questions"]:
        item = clean[q["key"]]
        active = not q.get("when") or clean[q["when"]]["state"] == "observed"
        rows.append({"key": q["key"], "label": q["label"],
                     "answer": _prefix(item["state"], active) + item["text"],
                     "answer_type": f"diarrhea:{item['state']}:{int(active)}",
                     "required": False, "triggered": False})
    return {"version": template["version"] + "+" + template["fingerprint"],
            "template_key": raw["species"], "category": "companion",
            "label": ("犬" if raw["species"] == "dog" else "猫") + "腹泻问诊 · 医生采集 · 临床草稿",
            "sections": [{"key": "diarrhea", "title": "腹泻病史 · 医生采集（临床草稿）", "answers": rows}]}


def is_diarrhea(snapshot):
    sections = snapshot.get("sections") if isinstance(snapshot, dict) else None
    return isinstance(snapshot, dict) and (
        str(snapshot.get("version", "")).startswith("diarrhea-intake-") or
        any(isinstance(s, dict) and s.get("key") == "diarrhea" for s in (sections if isinstance(sections, list) else [])))


def validate_snapshot(snapshot):
    """Validate current submissions. Stored history is displayed without reinterpretation."""
    if not is_diarrhea(snapshot):
        return snapshot
    template = get_template(snapshot.get("template_key"))
    sections = snapshot.get("sections", [])
    if not isinstance(sections, list) or len(sections) != 1 or not isinstance(sections[0], dict) or sections[0].get("key") != "diarrhea":
        raise DiarrheaIntakeError()
    rows = sections[0].get("answers", [])
    if not isinstance(rows, list) or len(rows) != len(template["questions"]):
        raise DiarrheaIntakeError()
    answers = {}
    for q, row in zip(template["questions"], rows):
        if not isinstance(row, dict) or row.get("key") != q["key"] or row.get("label") != q["label"]:
            raise DiarrheaIntakeError()
        try:
            family, state, flag = row["answer_type"].split(":")
            prefix = _prefix(state, flag == "1")
            assert family == "diarrhea" and flag in ("0", "1")
            assert isinstance(row["answer"], str) and row["answer"].startswith(prefix)
        except (KeyError, ValueError, TypeError, AttributeError, AssertionError):
            raise DiarrheaIntakeError() from None
        answers[q["key"]] = {"state": state, "text": row["answer"][len(prefix):]}
    version = snapshot.get("version", "").split("+", 1)
    canonical = build_snapshot({"version": version[0], "fingerprint": version[1] if len(version) == 2 else "",
                                "species": snapshot["template_key"], "answers": answers})
    if canonical != snapshot:
        raise DiarrheaIntakeError("腹泻问卷的来源、题目或条件状态不一致，请重新核对。")
    return canonical


def ai_context(snapshot):
    # The legacy feature extractor matches keywords without understanding negation.
    # Never feed blank/unknown/negative question labels or inactive branches to it.
    # The full original, including all such states, is still retained in history.
    try:
        canonical = validate_snapshot(snapshot)
    except DiarrheaIntakeError:
        return ""  # Historical templates remain readable; do not reclassify them.
    lines = []
    for row in canonical["sections"][0]["answers"]:
        if row["answer_type"] == "diarrhea:observed:1":
            text = row["answer"][len(_prefix("observed", True)):]
            # Free text is a clinician observation, not a machine-verified fact.
            lines.append(row["label"] + "：" + (text or "医生明确记录为已观察"))
    return "医生采集的当前已记录观察（仍需医生核对）：\n" + "\n".join(lines) if lines else ""
