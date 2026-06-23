# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

EXOTICS_RABBIT_DEEPENING_MODE = "exotics_rabbit_deepening_v1"

ROOT = Path(__file__).resolve().parents[1]
RABBIT_KB_PATH = ROOT / "knowledge-base" / "exotics" / "rabbit.json"
RABBIT_INTAKE_PATH = ROOT / "knowledge-base" / "exotics" / "intake" / "rabbit.json"

REQUIRED_DOMAINS = (
    "胃肠淤滞/梗阻",
    "牙科/口腔疼痛",
    "呼吸系统",
    "泌尿/肾脏/生殖",
    "神经/头斜",
    "足底皮炎/皮肤",
    "饲养/饮食/环境",
    "急症/全身状态",
)


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("%s must contain a JSON object" % path)
    return data


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def build_rabbit_deepening_review() -> Dict[str, Any]:
    """Read rabbit KB and intake template coverage; this helper is read-only."""
    kb = _load_json(RABBIT_KB_PATH)
    intake = _load_json(RABBIT_INTAKE_PATH)

    domains = _list(kb.get("coverage_domains"))
    missing_domains = [domain for domain in REQUIRED_DOMAINS if domain not in domains]

    metrics = {
        "system_hint_count": len(_list(kb.get("system_hints"))),
        "red_flag_count": len(_list(kb.get("red_flags"))),
        "disease_direction_count": len(_list(kb.get("diseases"))),
        "check_direction_count": len(_list(kb.get("checks"))),
        "question_count": len(_list(kb.get("questions"))),
        "intake_section_count": len(_list(intake.get("sections"))),
        "intake_feature_flag_count": len(_list(intake.get("feature_flags"))),
    }

    quality_gate = {
        "status": "PASS" if not missing_domains and metrics["red_flag_count"] >= 8 else "REVIEW",
        "missing_required_domains": missing_domains,
        "is_comprehensive": False,
        "current_level": "rabbit_deepened_triage_scaffold_not_comprehensive_clinical_kb",
        "source_review_status": kb.get("source_review_status") or "required_not_started",
        "drug_dose_status": kb.get("drug_dose_status") or "not_reviewed_not_enabled",
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    safety = {
        "read_only": True,
        "dry_run": True,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "creates_diagnostic_report": False,
        "updates_diagnostic_report": False,
        "creates_observation": False,
        "updates_observation": False,
        "creates_imaging_study": False,
        "updates_imaging_study": False,
        "writes_ai_summary": False,
        "writes_abnormal_summary": False,
        "writes_audit_log": False,
        "persists_reasoning_trace": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }

    return {
        "mode": EXOTICS_RABBIT_DEEPENING_MODE,
        "kb_key": kb.get("key"),
        "intake_key": intake.get("key"),
        "coverage_domains": domains,
        "metrics": metrics,
        "known_gaps": _list(kb.get("known_gaps")),
        "quality_gate": quality_gate,
        "safety": safety,
        **safety,
    }


if __name__ == "__main__":
    print(json.dumps(build_rabbit_deepening_review(), ensure_ascii=False, indent=2))
