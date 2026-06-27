# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DD_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_MODE = (
    "exotics_drug_dose_source_review_metadata_only_collection_workspace_validation_report_v1"
)

SPECIES_GROUPS = [
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

REVIEW_DOMAINS = [
    "analgesia_and_pain_control_source_review",
    "antimicrobial_source_review",
    "antiparasitic_source_review",
    "fluid_and_supportive_care_source_review",
    "sedation_anesthesia_risk_source_review",
    "emergency_stabilization_source_review",
]

ALLOWED_REPORT_FIELDS = [
    "validation_report_id",
    "species_group",
    "review_domain",
    "workspace_validation_scope",
    "validation_report_status",
    "workspace_status",
    "validation_status",
    "coverage_status",
    "forbidden_value_capture_status",
    "numeric_value_capture_status",
    "route_frequency_capture_status",
    "usable_medication_instruction_status",
    "collection_execution_status",
    "go_no_go_status",
    "human_review_required",
    "clinician_signoff_required",
    "next_required_stage",
]

FORBIDDEN_REPORT_FIELDS = [
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


def build_metadata_only_workspace_validation_report_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for species_group in SPECIES_GROUPS:
        for review_domain in REVIEW_DOMAINS:
            rows.append({
                "validation_report_id": f"validation-report::{species_group}::{review_domain}",
                "species_group": species_group,
                "review_domain": review_domain,
                "workspace_validation_scope": "metadata_only_workspace_static_validation_report",
                "validation_report_status": "report_shell_present_no_collection_results",
                "workspace_status": "defined_not_populated",
                "validation_status": "defined_not_run_on_live_collection_data",
                "coverage_status": "species_domain_pair_present",
                "forbidden_value_capture_status": "blocked_by_schema_and_validator",
                "numeric_value_capture_status": "not_captured",
                "route_frequency_capture_status": "not_captured",
                "usable_medication_instruction_status": "not_stored",
                "collection_execution_status": "not_started",
                "go_no_go_status": "NO_GO_TO_COLLECTION_EXECUTION",
                "human_review_required": True,
                "clinician_signoff_required": True,
                "next_required_stage": "metadata_only_collection_workspace_governance_signoff",
            })
    return rows


def build_metadata_only_workspace_validation_report_summary() -> Dict[str, Any]:
    rows = build_metadata_only_workspace_validation_report_rows()
    expected = len(SPECIES_GROUPS) * len(REVIEW_DOMAINS)
    return {
        "mode": EXOTICS_DD_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_VALIDATION_REPORT_MODE,
        "stage": "Exotics Drug Dose Source Review Metadata-only Collection Workspace Validation Report V1",
        "current_level": "metadata_only_workspace_validation_report_shell_only_not_collection_execution",
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "expected_report_rows": expected,
        "actual_report_rows": len(rows),
        "coverage_complete": len(rows) == expected,
        "metadata_only_workspace_defined": True,
        "metadata_only_workspace_populated": False,
        "metadata_only_workspace_validation_defined": True,
        "metadata_only_workspace_validation_executed": False,
        "metadata_only_workspace_validation_report_defined": True,
        "metadata_only_workspace_validation_report_has_collection_results": False,
        "source_review_status": "metadata_only_workspace_validation_report_defined_no_collection_results",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
        "collection_execution_started": False,
        "collection_execution_allowed_now": False,
        "read_only": True,
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
        "creates_treatment_plan": False,
        "writes_prescription": False,
        "returns_drug_dose": False,
        "returns_drug_route": False,
        "returns_drug_frequency": False,
        "client_facing": False,
        "not_client_facing": True,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "governance_decision": "NO_GO_TO_COLLECTION_EXECUTION",
        "decision": "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_V1",
    }


def assert_metadata_only_workspace_validation_report_safe() -> Dict[str, Any]:
    summary = build_metadata_only_workspace_validation_report_summary()
    if not summary["coverage_complete"]:
        raise ValueError("metadata-only workspace validation report coverage is incomplete")
    if summary["dose_output_enabled"]:
        raise ValueError("dose output must remain disabled")
    if summary["captures_numeric_dose_value"]:
        raise ValueError("numeric medication value capture must remain disabled")
    if summary["captures_route_or_frequency_text"]:
        raise ValueError("route or frequency capture must remain disabled")
    if summary["stores_usable_medication_instruction"]:
        raise ValueError("usable medication instruction storage must remain disabled")
    if summary["collection_execution_started"] or summary["collection_execution_allowed_now"]:
        raise ValueError("collection execution must remain blocked")
    return summary
