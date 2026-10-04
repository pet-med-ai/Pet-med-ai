"""Versioned clinician observations. No database access or clinical inference."""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "knowledge-base/companion/intake"
TEMPLATES = {"appetite_weight": "食欲下降／消瘦", "polyuria_polydipsia": "多饮多尿", "cough_breathing": "咳嗽／呼吸困难", "syncope_seizure": "晕厥／抽搐", "urinary_abnormality": "排尿异常", "itching_hair_loss": "皮肤瘙痒／脱毛", "lameness_pain": "跛行／疼痛", "fever_lethargy": "发热／精神沉郁", "senior_screening": "老年动物筛查"}
try:
    from . import diarrhea_intake as legacy
except ImportError:
    import diarrhea_intake as legacy
STATES = {"unfilled": "未填写", "not_asked": "未询问", "observed": "已记录",
          "absent": "明确否定", "uncertain": "不确定", "unobservable": "无法观察"}
MAX_TEXT = 6000
MAX_TOTAL = 40000


class IntakeError(ValueError):
    def __init__(self, message="主诉问卷格式或回答状态无效，请重新核对。", status=422):
        super().__init__(message)
        self.status = status


@lru_cache(maxsize=len(TEMPLATES))
def _template(key):
    if key not in TEMPLATES:
        raise IntakeError("未知的主诉问卷。", 404)
    raw = (ROOT / (key + ".json")).read_bytes()
    data = json.loads(raw)
    assert data["key"] == key and data["review_status"] == "clinical_draft"
    seen = set()
    for q in data["questions"]:
        assert q["key"] not in seen and q["kind"] in ("text", "presence")
        assert isinstance(q["label"], str) and q["label"]
        assert not q.get("when") or q["when"] in seen
        seen.add(q["key"])
    data["fingerprint"] = hashlib.sha256(raw).hexdigest()
    return data


def get_template(key, species):
    if species not in ("dog", "cat"):
        raise IntakeError("主诉专用问卷仅适用于医生明确选择的犬或猫。")
    template = deepcopy(_template(key))
    template.update(species=species, states=dict(STATES), max_text=MAX_TEXT, max_total=MAX_TOTAL)
    for q in template["questions"]:
        q["states"] = [s for s in STATES if s != "absent" or q["kind"] == "presence"]
    return template


def _prefix(state, active):
    branch = "当前适用" if active else "当前不适用（原分支输入保留，仅供回看）"
    return f"状态：{STATES[state]}；{branch}\n医生原文：\n"


def build_snapshot(key, raw):
    if not isinstance(raw, dict) or set(raw) != {"version", "fingerprint", "species", "answers"}:
        raise IntakeError()
    template = get_template(key, raw["species"])
    if raw["version"] != template["version"] or raw["fingerprint"] != template["fingerprint"]:
        raise IntakeError("主诉模板已变化；原输入仍需保留，请读取新模板后重新核对。", 409)
    answers = raw["answers"]
    known = {q["key"] for q in template["questions"]}
    if not isinstance(answers, dict) or set(answers) - known:
        raise IntakeError()
    clean = {}
    for q in template["questions"]:
        item = answers.get(q["key"], {"state": "unfilled", "text": ""})
        if not isinstance(item, dict) or set(item) != {"state", "text"}:
            raise IntakeError()
        state, text = item["state"], item["text"]
        if state not in q["states"] or not isinstance(text, str) or len(text) > MAX_TEXT:
            raise IntakeError()
        if state == "observed" and q["kind"] == "text" and not text.strip():
            raise IntakeError("已记录的文字项目需要填写原文，不能把空白作为已观察结果。")
        clean[q["key"]] = {"state": state, "text": text}
    if sum(len(a["text"]) for a in clean.values()) > MAX_TOTAL:
        raise IntakeError("主诉问卷原文过长；请保留输入并整理后核对。")
    rows = []
    for q in template["questions"]:
        item = clean[q["key"]]
        active = not q.get("when") or clean[q["when"]]["state"] == "observed"
        rows.append({"key": q["key"], "label": q["label"],
                     "answer": _prefix(item["state"], active) + item["text"],
                     "answer_type": f"{key}:{item['state']}:{int(active)}",
                     "required": False, "triggered": False})
    return {"version": template["version"] + "+" + template["fingerprint"],
            "template_key": raw["species"], "category": "companion",
            "label": ("犬" if raw["species"] == "dog" else "猫") + TEMPLATES[key] + "问诊 · 医生采集 · 临床草稿",
            "sections": [{"key": key, "title": TEMPLATES[key] + "病史 · 医生采集（临床草稿）", "answers": rows}]}


def is_intake(snapshot):
    if legacy.is_diarrhea(snapshot):
        return True
    if not isinstance(snapshot, dict):
        return False
    sections = snapshot.get("sections")
    return any(str(snapshot.get("version", "")).startswith(key + "-intake-") for key in TEMPLATES) or any(
        isinstance(section, dict) and section.get("key") in TEMPLATES
        for section in (sections if isinstance(sections, list) else []))


def validate_snapshot(snapshot):
    """Validate current submissions. Stored history is displayed without reinterpretation."""
    if legacy.is_diarrhea(snapshot):
        try:
            return legacy.validate_snapshot(snapshot)
        except legacy.DiarrheaIntakeError as error:
            raise IntakeError(str(error), error.status) from error
    if not is_intake(snapshot):
        return snapshot
    key = next((k for k in TEMPLATES if str(snapshot.get("version", "")).startswith(k + "-intake-")), None)
    template = get_template(key, snapshot.get("template_key"))
    sections = snapshot.get("sections", [])
    if not isinstance(sections, list) or len(sections) != 1 or not isinstance(sections[0], dict) or sections[0].get("key") != key:
        raise IntakeError()
    rows = sections[0].get("answers", [])
    if not isinstance(rows, list) or len(rows) != len(template["questions"]):
        raise IntakeError()
    answers = {}
    for q, row in zip(template["questions"], rows):
        if not isinstance(row, dict) or row.get("key") != q["key"] or row.get("label") != q["label"]:
            raise IntakeError()
        try:
            family, state, flag = row["answer_type"].split(":")
            prefix = _prefix(state, flag == "1")
            assert family == key and flag in ("0", "1")
            assert isinstance(row["answer"], str) and row["answer"].startswith(prefix)
        except (KeyError, ValueError, TypeError, AttributeError, AssertionError):
            raise IntakeError() from None
        answers[q["key"]] = {"state": state, "text": row["answer"][len(prefix):]}
    version = snapshot.get("version", "").split("+", 1)
    canonical = build_snapshot(key, {"version": version[0], "fingerprint": version[1] if len(version) == 2 else "",
                                "species": snapshot["template_key"], "answers": answers})
    if canonical != snapshot:
        raise IntakeError("主诉问卷的来源、题目或条件状态不一致，请重新核对。")
    return canonical


def ai_context(snapshot):
    # The legacy feature extractor matches keywords without understanding negation.
    # Never feed blank/unknown/negative question labels or inactive branches to it.
    # The full original, including all such states, is still retained in history.
    if legacy.is_diarrhea(snapshot):
        return legacy.ai_context(snapshot)
    if not is_intake(snapshot):
        return ""
    try:
        canonical = validate_snapshot(snapshot)
    except IntakeError:
        return ""  # Historical templates remain readable; do not reclassify them.
    lines = []
    for row in canonical["sections"][0]["answers"]:
        if row["answer_type"] == canonical["sections"][0]["key"] + ":observed:1":
            text = row["answer"][len(_prefix("observed", True)):]
            # Free text is a clinician observation, not a machine-verified fact.
            lines.append(row["label"] + "：" + (text or "医生明确记录为已观察"))
    return "医生采集的当前已记录观察（仍需医生核对）：\n" + "\n".join(lines) if lines else ""
