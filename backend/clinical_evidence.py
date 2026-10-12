"""Bounded, deterministic assertion handling. Original records are never rewritten.

This is an input guard, not general language understanding or a diagnosis model.
Unresolved questions, scope, timing and conflicts must remain visible to clinicians.
"""
import re

VERSION = "clinical-evidence-b4-v1"
PENDING = "待核对"
SPLIT = re.compile(r"[，,。；;\n]+|(?<=[?？])|(?=但是|然而|但|不过)")
UNCERTAIN = re.compile(r"[?？]|吗|不无|未必|不排除|不能排除|未排除|并非|不是没有|不一定|不能确定|不确定|不清楚|未知|不详|未询问|未测|未观察|无法观察|未确认|待核对|疑似|可能|是否|有没有|有无|\b(?:unknown|unsure|possible|maybe)\b", re.I)
NEGATIVE = re.compile(r"未见|未发现|未出现|没有出现|没有发现|否认|没有|未发生|无(?:明显)?|(?:^|[：: ])未(?:呕吐|腹泻|抽搐)|\b(?:no|denies|without|not)\b", re.I)
HISTORICAL = re.compile(r"既往|曾经|以前|去年|上月|过去|既往史|\b(?:previously|history of)\b", re.I)
NEGATIVE_ANSWERS = {"无", "没有", "否", "不是", "未见", "均无", "都没有", "no", "none"}
POSITIVE_ANSWERS = {"有", "是", "是的", "有的", "yes"}
# Negative-looking words which are themselves existing positive clinical signs.
SIGNS = ("没有尿", "没有粪便", "食欲完全没有", "无尿", "无粪", "无便", "无力", "不吃", "不采食", "不排便", "不能站立", "不动", "意识不清")
CONCEPTS = (
    ("blood", "blood_vomit", "coffee_ground_vomit", "gi_bleeding"),
    ("vomiting", "frequent_vomiting", "persistent_vomiting", "mild_single_vomit"),
    ("retching",), ("abd_distension",), ("diarrhea",), ("respiratory_distress",),
    ("neurologic_signs", "seizure_cluster"), ("collapse",), ("trauma", "orthopedic_or_trauma"),
    ("toxin", "toxin_exposure"), ("urinary_issue", "anuria"), ("low_energy",),
    ("anorexia", "appetite_down", "prolonged_anorexia"), ("pruritus",),
    ("oral_dental_issue",), ("jaundice",), ("foreign_body_suspect",),
    ("cardiac_respiratory_risk",),
)


def snapshot_rows(snapshot, source="问卷"):
    """Only called on a validated snapshot; labels are context, not observations."""
    rows = []
    for section in (snapshot or {}).get("sections", []):
        for item in section.get("answers", []):
            kind = item.get("answer_type", "").split(":")
            state, raw = "answer", item.get("answer", "")
            if len(kind) == 3 and kind[1] in {"observed", "absent", "unfilled", "not_asked", "uncertain", "unobservable"}:
                if kind[2] != "1":
                    continue
                state = kind[1]
                raw = raw.split("\n医生原文：\n", 1)[-1]
            rows.append({"source": source + "/" + item.get("key", ""),
                         "question": item.get("label", ""), "text": raw, "state": state})
    return rows


def answer_rows(text, answers):
    rows = [{"source": "主诉", "text": text}]
    for i, item in enumerate(answers or [], 1):
        if "_clinical_rows" in item:
            rows.extend(item["_clinical_rows"])
        else:
            rows.append({"source": f"追问第{i}轮", "question": item.get("question", ""),
                         "text": item.get("answer", ""), "state": "answer"})
    return rows


def _question_subject(question, extract):
    subject = re.sub(r"^(?:请问|请记录|是否|有没有|有无|有)(?:有)?", "", question.strip()).strip("？?。 ")
    features = extract(subject)
    concepts = [keys[0] for keys in CONCEPTS if any(features.get(k) for k in keys)]
    if features.get("respiratory_distress") and "cardiac_respiratory_risk" in concepts:
        concepts.remove("cardiac_respiratory_risk")
    if (features.get("blood") or features.get("retching")) and "vomiting" in concepts:
        concepts.remove("vomiting")
    if features.get("collapse") and "neurologic_signs" in concepts:
        concepts.remove("neurologic_signs")
    # A yes to a compound question does not confirm every symptom in that question.
    if len(concepts) != 1 or re.search(r"[、/／或及和与]|以及", subject):
        return None
    return subject


def collect(rows, extract):
    records, positives = [], []
    for row in rows:
        raw = str(row.get("text") or "")
        question = str(row.get("question") or "")
        state = row.get("state", "text")
        answer = raw.strip().strip("。.!！ ").lower()
        forced = None
        text = raw
        if state in {"unfilled", "not_asked", "uncertain", "unobservable"}:
            forced = "unknown"
        elif state == "absent":
            forced = "negative"
        elif state == "answer" and (not answer or answer in NEGATIVE_ANSWERS):
            forced = "negative" if answer else "unknown"
        elif (state == "answer" and answer in POSITIVE_ANSWERS) or (state == "observed" and not answer):
            subject = _question_subject(question, extract)
            if subject:
                text = subject
            else:
                forced = "unknown"
        segments = [s.strip() for s in SPLIT.split(text) if s.strip()] or [""]
        previous = None
        for segment_index, segment in enumerate(segments):
            masked = segment
            for sign in SIGNS:
                suffix = r"(?!闭|痛|频|少|道|血|困难|问题|异常)" if sign in {"无尿", "没有尿"} else (r"(?!减少|异常|问题)" if sign == "没有粪便" else "")
                masked = re.sub(re.escape(sign) + suffix, "症状", masked)
            status = forced or (
                "unknown" if UNCERTAIN.search(masked) else
                "historical" if HISTORICAL.search(masked) else
                "negative" if NEGATIVE.search(masked) else "positive")
            # "没有黑便，呕吐" has unclear negation scope; never silently choose normal.
            if not forced and previous in {"negative", "unknown", "historical"} and status == "positive":
                if not re.match(r"(?:但|今天|现在|目前|出现|有|仍|开始|随后|精神正常|精神好)", segment):
                    status = "unknown"
            neg = NEGATIVE.search(masked)
            if not forced and status == "negative" and neg and re.search(r"且|仍|却|还有|伴有|并有|同时|出现", masked[neg.end():]):
                status = "unknown"
            features = extract(question + "。" + segment if forced in {"negative", "unknown"} and question else segment)
            keys = sorted(k for k, v in features.items() if v is True and k not in {"is_exotic", "acute", "chronic", "normal_energy"})
            if forced == "negative" and keys:
                # An explicitly absent field containing positive free text is a conflict.
                if state == "absent" and raw.strip() and not NEGATIVE.search(masked):
                    status = "conflict"
            record = {"source": row.get("source", "记录"), "raw": raw if segment_index == 0 else segment, "question": question if segment_index == 0 else "",
                      "text": segment, "state": status, "features": keys}
            records.append(record)
            if status == "positive":
                positives.append(segment)
            previous = status
    positive_keys = {k for r in records if r["state"] == "positive" for k in r["features"]}
    negative_keys = {k for r in records if r["state"] == "negative" for k in r["features"]}
    conflicts = sorted(positive_keys & negative_keys)
    review = bool(conflicts or any(r["state"] in {"unknown", "historical", "conflict"} for r in records))
    return {"version": VERSION, "records": records, "conflicts": conflicts,
            "needs_review": review, "positive_text": "。".join(positives)}
