# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, Dict, List

EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_MODE = "exotics_drug_dose_source_review_source_collection_execution_readiness_v1"

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

READINESS_DECISION = "GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_CONTROLLED_PILOT_V1"


def exotics_source_collection_execution_readiness_safety_flags() -> Dict[str, Any]:
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
        "writes_abnormal_summary": False,
        "creates_audit_log": False,
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
        "dose_output_enabled": False,
        "calls_external_ai": False,
        "calls_external_provider": False,
        "downloads_attachments": False,
        "sends_external_message": False,
        "executes_real_import": False,
        "executes_real_lab_ingest": False,
        "executes_real_dicom_ingest": False,
        "executes_real_device_ingest": False,
        "is_dose_engine": False,
        "is_prescription_engine": False,
        "is_treatment_plan_engine": False,
        "requires_human_review": True,
        "clinician_signoff_required": True,
        "not_client_facing": True,
    }


def _readiness_row(species_group: str, review_domain: str) -> Dict[str, Any]:
    return {
        "execution_readiness_id": "exec-ready-%s-%s" % (species_group.replace("_", "-"), review_domain.replace("_", "-")),
        "species_group": species_group,
        "review_domain": review_domain,
        "source_collection_protocol_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_PROTOCOL_V1",
        "source_registry_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_REGISTRY_V1",
        "evidence_table_reference": "EXOTICS_DRUG_DOSE_SOURCE_REVIEW_EVIDENCE_TABLES_V1",
        "collector_assignment_status": "required_not_assigned",
        "second_reviewer_status": "required_not_assigned",
        "source_access_status": "required_not_verified",
        "copyright_access_status": "required_not_verified",
        "workspace_status": "required_not_created",
        "deidentification_required": True,
        "value_capture_policy": "metadata_only_no_medication_values",
        "dose_output_enabled": False,
        "route_or_frequency_capture_enabled": False,
        "collection_execution_status": "not_started",
        "go_no_go": "NO_GO_FOR_COLLECTION_EXECUTION_UNTIL_REVIEWERS_ACCESS_AND_WORKSPACE_ARE_APPROVED",
    }


def build_exotics_source_collection_execution_readiness() -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = [
        _readiness_row(species_group, review_domain)
        for species_group in SPECIES_GROUPS
        for review_domain in REVIEW_DOMAINS
    ]
    safety = exotics_source_collection_execution_readiness_safety_flags()
    summary = {
        "species_group_count": len(SPECIES_GROUPS),
        "review_domain_count": len(REVIEW_DOMAINS),
        "readiness_row_count": len(rows),
        "collector_assignment_ready": False,
        "second_reviewer_assignment_ready": False,
        "source_access_verified": False,
        "copyright_access_verified": False,
        "collection_workspace_ready": False,
        "collection_execution_started": False,
        "current_level": "source_collection_execution_readiness_only_not_execution",
        "source_review_status": "execution_readiness_defined_not_started",
        "drug_dose_status": "not_reviewed_not_enabled",
        "dose_output_enabled": False,
        "captures_numeric_dose_value": False,
        "captures_route_or_frequency_text": False,
        "stores_usable_medication_instruction": False,
    }
    quality_gate = {
        "status": "PASS",
        "decision": READINESS_DECISION,
        "read_only": True,
        "writes_database": False,
        "collection_execution_allowed": False,
        "requires_reviewer_assignment": True,
        "requires_source_access_approval": True,
        "requires_copyright_access_check": True,
        "requires_metadata_only_workspace": True,
        "blocks_numeric_dose_capture": True,
        "blocks_route_or_frequency_capture": True,
        "blocks_prescription_direction": True,
        "requires_human_review": True,
        "clinician_signoff_required": True,
    }
    return {
        "mode": EXOTICS_DRUG_DOSE_SOURCE_REVIEW_SOURCE_COLLECTION_EXECUTION_READINESS_MODE,
        "summary": summary,
        "readiness_matrix": rows,
        "quality_gate": quality_gate,
        "safety": safety,
        **summary,
        **safety,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(build_exotics_source_collection_execution_readiness(), ensure_ascii=False, indent=2))
