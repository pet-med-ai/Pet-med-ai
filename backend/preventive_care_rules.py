# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


STATUS_DRAFT = "draft"
STATUS_DUE_SOON = "due_soon"
STATUS_DUE = "due"
STATUS_OVERDUE = "overdue"
STATUS_ACTIVE = "active"

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "docs" / "preventive_care" / "VACCINE_DEWORMING_RULES_V1.csv"


@dataclass(frozen=True)
class PreventiveCareRule:
    rule_id: str
    species: str
    life_stage: str
    category: str
    trigger_basis: str
    interval_days: Optional[int]
    due_window_days: int
    lead_days: int
    requires_clinician_confirmation: bool
    requires_client_consent: bool
    allow_auto_send: bool
    recommended_stage: str
    source_note: str
    notes: str


def parse_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    # Support ISO date or datetime values.
    try:
        if "T" in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text[:10])
    except Exception:
        return None


def parse_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y"}


def parse_int(value: Any) -> Optional[int]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def load_preventive_care_rules(path: Path | str = DEFAULT_RULES_PATH) -> List[PreventiveCareRule]:
    csv_path = Path(path)
    rows = list(csv.DictReader(csv_path.read_text(encoding="utf-8").splitlines()))
    rules: List[PreventiveCareRule] = []
    for row in rows:
        rules.append(
            PreventiveCareRule(
                rule_id=str(row.get("rule_id") or "").strip(),
                species=str(row.get("species") or "").strip(),
                life_stage=str(row.get("life_stage") or "all").strip(),
                category=str(row.get("category") or "").strip(),
                trigger_basis=str(row.get("trigger_basis") or "").strip(),
                interval_days=parse_int(row.get("interval_days")),
                due_window_days=parse_int(row.get("due_window_days")) or 0,
                lead_days=parse_int(row.get("lead_days")) or 0,
                requires_clinician_confirmation=str(row.get("requires_clinician_confirmation") or "").strip().lower() == "yes",
                requires_client_consent=str(row.get("requires_client_consent") or "").strip().lower() == "yes",
                allow_auto_send=str(row.get("allow_auto_send") or "").strip().lower() == "yes",
                recommended_stage=str(row.get("recommended_stage") or "").strip(),
                source_note=str(row.get("source_note") or "").strip(),
                notes=str(row.get("notes") or "").strip(),
            )
        )
    return [rule for rule in rules if rule.rule_id]


def normalize_species(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"dog", "canine", "犬", "狗"}:
        return "dog"
    if text in {"cat", "feline", "猫"}:
        return "cat"
    if text in {"dog_cat", "dog/cat", "canine_feline"}:
        return "dog_cat"
    return text or "other"


def normalize_life_stage(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "puppy": "juvenile",
        "kitten": "juvenile",
        "幼犬": "juvenile",
        "幼猫": "juvenile",
        "成犬": "adult",
        "成猫": "adult",
        "老年": "senior",
    }
    return aliases.get(text, text or "adult")


def species_matches(rule_species: str, pet_species: str) -> bool:
    rule = normalize_species(rule_species)
    pet = normalize_species(pet_species)
    return rule == "dog_cat" or rule == pet


def life_stage_matches(rule_life_stage: str, pet_life_stage: str) -> bool:
    rule = normalize_life_stage(rule_life_stage)
    pet = normalize_life_stage(pet_life_stage)
    if rule in {"all", ""}:
        return True
    if rule == "kitten_or_at_risk":
        return pet in {"juvenile", "kitten_or_at_risk", "at_risk"}
    return rule == pet


def trigger_date_for_rule(pet: Dict[str, Any], rule: PreventiveCareRule) -> Optional[date]:
    trigger = rule.trigger_basis
    if trigger in pet:
        return parse_date(pet.get(trigger))

    # Allow compact pet payloads that use category-style keys.
    fallback_map = {
        "age_or_last_deworming_date": "last_deworming_date",
        "last_core_vaccine_date": "last_vaccine_date",
        "last_lifestyle_vaccine_date": "last_vaccine_date",
        "last_preventive_date": "last_external_parasite_prevention_date",
    }
    fallback = fallback_map.get(trigger)
    if fallback:
        return parse_date(pet.get(fallback))
    return None


def status_for_due_window(as_of: date, due_date: date, due_window_start: date, due_window_end: date) -> str:
    if as_of > due_window_end:
        return STATUS_OVERDUE
    if as_of >= due_date:
        return STATUS_DUE
    if as_of >= due_window_start:
        return STATUS_DUE_SOON
    return STATUS_ACTIVE


def reminder_preview_for_rule(
    *,
    pet: Dict[str, Any],
    rule: PreventiveCareRule,
    as_of_date: date,
) -> Dict[str, Any]:
    last_date = trigger_date_for_rule(pet, rule)
    missing_trigger = last_date is None

    if missing_trigger:
        due_date = as_of_date
        due_window_start = as_of_date
        due_window_end = as_of_date + timedelta(days=max(rule.due_window_days, 0))
        status = STATUS_DUE
        reason = "missing_trigger_date"
    else:
        interval = rule.interval_days or 0
        due_date = last_date + timedelta(days=interval)
        due_window_start = due_date - timedelta(days=max(rule.lead_days, 0))
        due_window_end = due_date + timedelta(days=max(rule.due_window_days, 0))
        status = status_for_due_window(as_of_date, due_date, due_window_start, due_window_end)
        reason = "computed_from_last_event"

    return {
        "message": "preventive_care_reminder_preview",
        "mode": "preventive_care_rule_engine_dry_run_v1",
        "pet_name": str(pet.get("pet_name") or pet.get("name") or "").strip() or "unknown",
        "owner_id": pet.get("owner_id"),
        "case_id": pet.get("case_id"),
        "pet_id": pet.get("pet_id"),
        "species": normalize_species(pet.get("species")),
        "life_stage": normalize_life_stage(pet.get("life_stage")),
        "category": rule.category,
        "rule_id": rule.rule_id,
        "source_rule_id": rule.rule_id,
        "trigger_basis": rule.trigger_basis,
        "last_event_date": last_date.isoformat() if last_date else None,
        "due_date": due_date.isoformat(),
        "due_window_start": due_window_start.isoformat(),
        "due_window_end": due_window_end.isoformat(),
        "reminder_lead_days": rule.lead_days,
        "status": status,
        "reason": reason,
        "missing_trigger_date": missing_trigger,
        "requires_clinician_confirmation": rule.requires_clinician_confirmation,
        "requires_client_consent": rule.requires_client_consent,
        "allow_auto_send": False,
        "sends_external_message": False,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "executes_real_import": False,
        "notes": rule.notes,
    }


def compute_preventive_care_reminders(
    pet: Dict[str, Any],
    *,
    as_of: str | date | datetime | None = None,
    rules: Optional[Iterable[PreventiveCareRule]] = None,
    include_active: bool = True,
) -> Dict[str, Any]:
    as_of_date = parse_date(as_of) or date.today()
    pet_species = normalize_species(pet.get("species"))
    pet_stage = normalize_life_stage(pet.get("life_stage"))
    active_rules = list(rules or load_preventive_care_rules())

    previews = []
    for rule in active_rules:
        if not species_matches(rule.species, pet_species):
            continue
        if not life_stage_matches(rule.life_stage, pet_stage):
            continue
        preview = reminder_preview_for_rule(pet=pet, rule=rule, as_of_date=as_of_date)
        if include_active or preview["status"] != STATUS_ACTIVE:
            previews.append(preview)

    summary: Dict[str, int] = {}
    for item in previews:
        summary[item["status"]] = summary.get(item["status"], 0) + 1

    return {
        "message": "preventive_care_rule_engine_dry_run",
        "mode": "preventive_care_rule_engine_dry_run_v1",
        "as_of_date": as_of_date.isoformat(),
        "pet": {
            "pet_name": str(pet.get("pet_name") or pet.get("name") or "").strip() or "unknown",
            "species": pet_species,
            "life_stage": pet_stage,
            "owner_id": pet.get("owner_id"),
            "case_id": pet.get("case_id"),
            "pet_id": pet.get("pet_id"),
        },
        "summary": {
            "total": len(previews),
            "by_status": summary,
        },
        "items": sorted(previews, key=lambda item: (item["due_date"], item["category"], item["rule_id"])),
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "sends_external_message": False,
        "executes_real_import": False,
    }
