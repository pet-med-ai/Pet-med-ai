# -*- coding: utf-8 -*-
"""
Treatment Framework Signed Review State Persistence Migration Dry Run V1.

Builds a clinician-facing dry-run migration plan preview for future signed
review state persistence. This module deliberately does not persist anything:
no database write, no case treatment field write, no prescription, no drug dose,
no route/frequency recommendation, no client-facing release, and no migration
file creation.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_MODE = (
    "treatment_framework_signed_review_state_persistence_migration_dry_run_v1"
)

_ALLOWED_CONFIRMATION_SOURCES = {
    "clinician",
    "clinician_entered",
    "clinician_confirmed",
}

_FORBIDDEN_OUTPUT_PATTERNS = [
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\s*/\s*kg\b", re.IGNORECASE),
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g|ml|mL|iu|IU)\b", re.IGNORECASE),
    re.compile(r"\bq\s*\d+\s*h\b", re.IGNORECASE),
    re.compile(r"\b(?:SID|BID|TID|QID|q12h|q24h|q8h|q6h|q4h)\b", re.IGNORECASE),
    re.compile(r"\b(?:PO|IV|IM|SC|SQ|subcutaneous|intravenous|intramuscular|oral)\b", re.IGNORECASE),
    re.compile(r"\b(?:prescribe|prescription|dispense|administer)\b", re.IGNORECASE),
]


def treatment_framework_signed_review_state_persistence_migration_dry_run_safety_flags() -> Dict[str, bool]:
    return {
        "read_only": True,
        "dry_run": True,
        "migration_dry_run_only": True,
        "migration_enabled": False,
        "migration_file_created": False,
        "schema_change_enabled": False,
        "writes_database": False,
        "creates_case": False,
        "updates_case": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "writes_audit_log": False,
        "creates_signed_review_state": False,
        "persists_signed_review_state": False,
        "signed_review_state_persistence_enabled": False,
        "review_state_persistence_enabled": False,
        "migration_readiness_required": True,
        "migration_design_reference_required": True,
        "rollback_plan_required": True,
        "backup_restore_evidence_required": True,
        "authenticated_smoke_required_before_write": True,
        "not_client_facing": True,
        "client_release_allowed": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "external_ai_provider_call": False,
        "ai_does_not_confirm_diagnosis": True,
    }


def _as_non_empty_text(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        if field_name == "confirmed_diagnosis_label":
            raise ValueError("confirmed diagnosis by clinician is required")
        raise ValueError("{0} is required".format(field_name))
    return text


def _parse_case_id(value: Any) -> int:
    if value in (None, ""):
        raise ValueError("case_id is required")
    try:
        case_id = int(value)
    except (TypeError, ValueError):
        raise ValueError("case_id must be an integer")
    if case_id <= 0:
        raise ValueError("case_id must be positive")
    return case_id


def _normalize_confirmation_source(value: Any) -> str:
    source = str(value or "").strip().lower()
    if source not in _ALLOWED_CONFIRMATION_SOURCES:
        raise ValueError("confirmed diagnosis by clinician is required")
    return "clinician_entered" if source == "clinician" else source


def _require_ai_generated_false(payload: Dict[str, Any]) -> bool:
    if "ai_generated" not in payload:
        raise ValueError("ai_generated=false is required for clinician confirmed diagnosis input")
    value = payload.get("ai_generated")
    if value is not False:
        raise ValueError("AI generated diagnosis cannot be used as confirmed diagnosis")
    return False


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            for nested in _walk_strings(item):
                yield nested
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            for nested in _walk_strings(item):
                yield nested


def scan_for_forbidden_migration_dry_run_output(value: Dict[str, Any]) -> List[str]:
    hits: List[str] = []
    for text in _walk_strings(value):
        for pattern in _FORBIDDEN_OUTPUT_PATTERNS:
            if pattern.search(text):
                hits.append(text)
                break
    return hits


def _require_dict(payload: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict) or not value:
        raise ValueError("{0} is required".format(key))
    forbidden = scan_for_forbidden_migration_dry_run_output(value)
    if forbidden:
        raise ValueError("forbidden treatment output detected in {0}".format(key))
    return value


def _require_truthy(payload: Dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if value is True:
        return True
    if isinstance(value, str) and value.strip().lower() in {"1", "true", "yes", "y"}:
        return True
    raise ValueError("{0}=true is required".format(key))


def build_treatment_framework_signed_review_state_persistence_migration_dry_run(
    payload: Dict[str, Any],
    *,
    case_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("request body must be an object")

    case_id = _parse_case_id(payload.get("case_id"))
    label = _as_non_empty_text(payload.get("confirmed_diagnosis_label"), "confirmed_diagnosis_label")
    confirmed_by = _as_non_empty_text(payload.get("confirmed_by"), "confirmed_by")
    confirmation_source = _normalize_confirmation_source(payload.get("confirmation_source"))
    ai_generated = _require_ai_generated_false(payload)

    diagnosis_preview = {"label": label}
    if scan_for_forbidden_migration_dry_run_output(diagnosis_preview):
        raise ValueError("confirmed diagnosis label cannot contain dose, route, frequency, or prescription wording")

    treatment_framework_preview = _require_dict(payload, "treatment_framework_preview")
    signed_review_state_preview = _require_dict(payload, "signed_review_state_preview")
    persistence_dry_run_preview = _require_dict(payload, "persistence_dry_run_preview")

    _require_truthy(payload, "migration_design_acknowledged")
    _require_truthy(payload, "migration_readiness_review_completed")

    requested_by = _as_non_empty_text(
        payload.get("migration_dry_run_requested_by")
        or payload.get("requested_by")
        or payload.get("signed_by")
        or payload.get("confirmed_by"),
        "migration_dry_run_requested_by",
    )

    migration_plan_preview = {
        "preview_id": "signed-review-state-migration-dry-run-{0}".format(case_id),
        "case_id": case_id,
        "target_table": "treatment_framework_signed_review_states",
        "operation": "migration_plan_preview_only",
        "dry_run": True,
        "migration_dry_run_only": True,
        "migration_enabled": False,
        "migration_file_created": False,
        "schema_change_enabled": False,
        "will_apply_migration": False,
        "writes_database": False,
        "signed_review_state_persistence_enabled": False,
        "review_state_persistence_enabled": False,
        "migration_design_acknowledged": True,
        "migration_readiness_review_completed": True,
        "migration_readiness_required": True,
        "rollback_plan_required": True,
        "backup_restore_evidence_required": True,
        "authenticated_smoke_required_before_write": True,
        "migration_dry_run_requested_by": requested_by,
        "future_schema_plan": {
            "table_name": "treatment_framework_signed_review_states",
            "columns_preview": [
                "id",
                "case_id",
                "confirmed_diagnosis_label",
                "review_decision",
                "signed_review_status",
                "signed_by",
                "audit_log_reference",
                "created_at",
                "updated_at",
            ],
            "indexes_preview": [
                "ix_tfsrs_case_id",
                "ix_tfsrs_audit_log_reference",
                "ix_tfsrs_created_at",
            ],
            "foreign_keys_preview": [
                "case_id -> cases.id",
            ],
        },
        "rollback_plan_preview": [
            "migration must be additive",
            "migration rollback must drop only the new signed review state table if no persisted rows exist",
            "backup and restore evidence required before any future write",
        ],
        "forbidden_write_targets": [
            "case_treatment_field",
            "prescription_record",
            "drug_dose_field",
            "drug_route_field",
            "drug_frequency_field",
            "client_facing_release",
        ],
        "requires_future_go_no_go": True,
    }

    quality_gate = {
        "status": "PASS",
        "requires_confirmed_diagnosis": True,
        "requires_clinician_confirmed_diagnosis": True,
        "ai_does_not_confirm_diagnosis": True,
        "signed_review_state_preview_present": True,
        "persistence_dry_run_preview_present": True,
        "migration_design_acknowledged": True,
        "migration_readiness_review_completed": True,
        "migration_dry_run_only": True,
        "migration_enabled": False,
        "migration_file_created": False,
        "schema_change_enabled": False,
        "writes_database": False,
        "writes_case_treatment": False,
        "persists_treatment_framework": False,
        "persists_signed_review_state": False,
        "signed_review_state_persistence_enabled": False,
        "review_state_persistence_enabled": False,
        "blocks_prescription": True,
        "blocks_dose": True,
        "blocks_route_frequency": True,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "migration_readiness_required": True,
        "rollback_plan_required": True,
        "backup_restore_evidence_required": True,
        "authenticated_smoke_required_before_write": True,
    }
    safety = treatment_framework_signed_review_state_persistence_migration_dry_run_safety_flags()

    return {
        "message": "treatment_framework_signed_review_state_persistence_migration_dry_run_built",
        "mode": TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_MODE,
        "case_id": case_id,
        "confirmed_diagnosis": {
            "label": label,
            "confirmed_by": confirmed_by,
            "confirmation_source": confirmation_source,
            "ai_generated": ai_generated,
        },
        "treatment_framework_preview": treatment_framework_preview,
        "signed_review_state_preview": signed_review_state_preview,
        "persistence_dry_run_preview": persistence_dry_run_preview,
        "migration_plan_preview": migration_plan_preview,
        "quality_gate": quality_gate,
        "safety": safety,
        "case_context_used": bool(case_context),
        **safety,
    }
