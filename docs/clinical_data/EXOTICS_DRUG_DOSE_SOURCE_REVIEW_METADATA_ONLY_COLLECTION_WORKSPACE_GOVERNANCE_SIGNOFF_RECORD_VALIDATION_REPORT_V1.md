# Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation Report V1

## Purpose

This stage defines a metadata-only validation report shell for the Exotics Drug Dose Source Review governance signoff record validation.

It remains a governance and safety artifact only. It is not a dose engine, not a prescription engine, not a treatment-plan engine, and not source collection execution.

## Current level

```text
current_level=metadata_only_workspace_governance_signoff_record_validation_report_schema_only_not_collection_execution
source_review_status=metadata_only_workspace_governance_signoff_record_validation_report_defined_no_collection_results
drug_dose_status=not_reviewed_not_enabled
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
```

## Scope

The validation report matrix covers rabbit, bird, ferret, turtle, lizard, snake, amphibian, fish, guinea_pig, hamster, chinchilla, rat_mouse, hedgehog, and sugar_glider.

The review domains cover analgesia_and_pain_control_source_review, antimicrobial_source_review, antiparasitic_source_review, fluid_and_supportive_care_source_review, sedation_anesthesia_risk_source_review, and emergency_stabilization_source_review.

## Explicitly forbidden content

The validation report must not contain usable medication values or instructions:

```text
numeric_dose_value
dose_unit
route_text
frequency_text
duration_text
prescription_direction
treatment_protocol
client_instruction
copied_table_text
copyrighted_full_text
```

These are listed as forbidden schema labels only. They must not become populated data fields.

## Safety boundary

```text
read_only=true
writes_database=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
source_collection_execution=false
collection_execution_started=false
collection_execution_allowed_now=false
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
no DB write
no final diagnosis
no diagnostic conclusion
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation_report.py
bash scripts/ci_static_checks.sh
```

## Go / No-Go

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1
```
