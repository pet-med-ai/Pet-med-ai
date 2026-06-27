# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_MODE = "exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_v1"

EXPECTED_SPECIES_GROUPS = [
    "rabbit",
    "bird",
    "ferret",
    "turtle",
    "lizard",
    "snake",
    "amphibian",
    "fish",
    "guinea_pig",
    "hamster",
    "chinchilla",
    "rat_mouse",
    "hedgehog",
    "sugar_glider",
]

EXPECTED_REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

REQUIRED_WORKSPACE_FIELDS = [
    "workspace_id",
    "species_group",
    "review_domain",
    "workspace_scope",
    "workspace_status",
    "metadata_only_policy",
    "source_collection_execution_status",
    "named_collector_required",
    "second_reviewer_required",
    "source_access_required",
    "copyright_access_required",
    "value_capture_blocker_status",
    "numeric_value_capture_status",
    "route_frequency_capture_status",
    "usable_medication_instruction_status",
    "deidentification_required",
    "human_review_required",
    "clinician_signoff_required",
    "go_no_go_status",
]

FORBIDDEN_VALUE_FIELDS = [
    "numeric_dose_value",
    "dose_unit",
    "route_text",
    "frequency_text",
    "duration_text",
    "prescription_direction",
    "treatment_protocol",
    "client_instruction",
    "copied_table_text",
    "copyrighted_full_text",
]


def metadata_only_collection_workspace_validation_safety_flags() -> Dict[str, Any]:
    return {
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
        "writes_audit_log": False,
        "generates_final_diagnosis": False,
        "generates_diagnostic_conclusion": False,
        "creates_treatment_plan": False,
        "writes_treatment_plan": False,
        "creates_prescription": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_collection_execution_started": False,
        "source_collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "workspace_allows_numeric_values": False,
        "workspace_allows_route_frequency": False,
        "workspace_allows_medication_instruction": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "client_facing": False,
        "not_client_facing": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }


def _load_previous_workspace_module() -> Any:
    path = Path(__file__).with_name("exotics_drug_dose_source_review_metadata_only_collection_workspace.py")
    if not path.exists():
        raise RuntimeError("metadata-only collection workspace module is required before validation")
    spec = importlib.util.spec_from_file_location("metadata_only_collection_workspace", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load metadata-only collection workspace module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    return bool(value)


def _workspace_rows() -> List[Dict[str, Any]]:
    module = _load_previous_workspace_module()
    rows = module.build_metadata_only_collection_workspace_matrix()
    if not isinstance(rows, list):
        raise RuntimeError("workspace matrix must be a list")
    return rows


def _validate_workspace_row(row: Dict[str, Any]) -> Dict[str, Any]:
    keys = set(row.keys())
    missing_required = [field for field in REQUIRED_WORKSPACE_FIELDS if field not in keys]
    forbidden_present = [field for field in FORBIDDEN_VALUE_FIELDS if field in keys]

    field_presence_ok = not missing_required
    forbidden_absence_ok = not forbidden_present
    numeric_ok = row.get("numeric_value_capture_status") == "blocked"
    route_ok = row.get("route_frequency_capture_status") == "blocked"
    instruction_ok = row.get("usable_medication_instruction_status") == "blocked"
    execution_ok = row.get("source_collection_execution_status") == "not_started"
    collector_ok = _as_bool(row.get("named_collector_required")) is True
    second_ok = _as_bool(row.get("second_reviewer_required")) is True
    access_ok = _as_bool(row.get("source_access_required")) is True
    copyright_ok = _as_bool(row.get("copyright_access_required")) is True
    human_ok = _as_bool(row.get("human_review_required")) is True and _as_bool(row.get("clinician_signoff_required")) is True

    all_ok = all([
        field_presence_ok,
        forbidden_absence_ok,
        numeric_ok,
        route_ok,
        instruction_ok,
        execution_ok,
        collector_ok,
        second_ok,
        access_ok,
        copyright_ok,
        human_ok,
    ])

    workspace_id = str(row.get("workspace_id") or "workspace:unknown:unknown")
    return {
        "validation_id": "validation:%s" % workspace_id,
        "workspace_id": workspace_id,
        "species_group": row.get("species_group"),
        "review_domain": row.get("review_domain"),
        "validation_scope": "metadata_only_workspace_static_preflight",
        "required_workspace_status": "defined_not_populated",
        "required_metadata_only_policy": "metadata_only_no_medication_values",
        "field_presence_check": "PASS" if field_presence_ok else "FAIL:%s" % ";".join(missing_required),
        "forbidden_column_absence_check": "PASS" if forbidden_absence_ok else "FAIL:%s" % ";".join(forbidden_present),
        "numeric_value_capture_check": "PASS" if numeric_ok else "FAIL",
        "route_frequency_capture_check": "PASS" if route_ok else "FAIL",
        "usable_medication_instruction_check": "PASS" if instruction_ok else "FAIL",
        "source_collection_execution_check": "PASS" if execution_ok else "FAIL",
        "named_collector_gate_check": "PASS" if collector_ok else "FAIL",
        "second_reviewer_gate_check": "PASS" if second_ok else "FAIL",
        "source_access_gate_check": "PASS" if access_ok else "FAIL",
        "copyright_access_gate_check": "PASS" if copyright_ok else "FAIL",
        "human_review_gate_check": "PASS" if human_ok else "FAIL",
        "validation_execution_status": "static_validation_defined_not_collection_execution",
        "go_no_go_status": "NO_GO_TO_SOURCE_COLLECTION_EXECUTION",
        "static_validation_passed": all_ok,
        "notes": "validates metadata-only workspace shell; no source collection, dose, route, frequency, prescription, treatment protocol, or client instruction",
    }


def build_metadata_only_collection_workspace_validation_matrix() -> List[Dict[str, Any]]:
    rows = _workspace_rows()
    return [_validate_workspace_row(row) for row in rows]


def build_metadata_only_collection_workspace_validation_summary() -> Dict[str, Any]:
    rows = build_metadata_only_collection_workspace_validation_matrix()
    safety = metadata_only_collection_workspace_validation_safety_flags()
    expected_count = len(EXPECTED_SPECIES_GROUPS) * len(EXPECTED_REVIEW_DOMAINS)
    species_seen = sorted({str(row.get("species_group")) for row in rows})
    domains_seen = sorted({str(row.get("review_domain")) for row in rows})
    all_static_rows_pass = all(bool(row.get("static_validation_passed")) for row in rows)
    coverage_ok = len(rows) == expected_count and set(species_seen) == set(EXPECTED_SPECIES_GROUPS) and set(domains_seen) == set(EXPECTED_REVIEW_DOMAINS)
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_MODE,
        "current_level": "metadata_only_workspace_validation_schema_only_not_collection_execution",
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "source_review_status": "metadata_only_workspace_validation_defined_not_run",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "static_workspace_validation_available": True,
        "static_workspace_validation_passed": all_static_rows_pass and coverage_ok,
        "species_group_count": len(EXPECTED_SPECIES_GROUPS),
        "review_domain_count": len(EXPECTED_REVIEW_DOMAINS),
        "validation_row_count": len(rows),
        "expected_validation_row_count": expected_count,
        "forbidden_fields": FORBIDDEN_VALUE_FIELDS,
        "quality_gate": {
            "status": "PASS" if all_static_rows_pass and coverage_ok else "FAIL",
            "metadata_only": True,
            "go_no_go_status": "NO_GO_TO_SOURCE_COLLECTION_EXECUTION",
            "blocks_numeric_dose_capture": True,
            "blocks_route_frequency_capture": True,
            "blocks_usable_medication_instruction": True,
            "blocks_collection_execution": True,
            "requires_human_review": True,
            "clinician_signoff_required": True,
        },
        "safety": safety,
        **safety,
    }


if __name__ == "__main__":
    summary = build_metadata_only_collection_workspace_validation_summary()
    print("%s rows=%s status=%s" % (
        summary["mode"],
        summary["validation_row_count"],
        summary["quality_gate"]["status"],
    ))
