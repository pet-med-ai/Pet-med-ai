# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record V1

## Purpose

This stage creates a metadata-only governance signoff record shell for activation of exotics drug-dose source review source collection.

It is not source collection activation. It is not source collection execution. It is not a dose engine, prescription engine, or treatment-plan engine.

## Current decision

```text
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
```

## Scope

This stage defines signoff record rows for each species group and review domain. These records are schema-only governance artifacts.

Species groups:

```text
rabbit
bird
ferret
turtle
lizard
snake
amphibian
fish
guinea_pig
hamster
chinchilla
rat_mouse
hedgehog
sugar_glider
```

Review domains:

```text
analgesia_and_pain_control_source_review
antimicrobial_source_review
antiparasitic_source_review
fluid_and_supportive_care_source_review
sedation_anesthesia_risk_source_review
emergency_stabilization_source_review
```

## Metadata-only record fields

```text
activation_governance_signoff_record_id
species_group
review_domain
activation_governance_signoff_id
activation_readiness_report_final_go_no_go_id
workspace_scope
clinical_owner_record_status
second_reviewer_record_status
source_access_record_status
copyright_access_record_status
metadata_only_policy_record_status
value_capture_blocker_record_status
activation_scope_record_status
halt_rule_record_status
collection_activation_status
collection_execution_status
signoff_record_status
signoff_completed_status
go_no_go_status
governance_decision
human_review_required
clinician_signoff_required
next_required_stage
```

## Explicitly forbidden values and fields

The following are prohibited in this stage and must remain absent from CSV headers and data cells except in documentation describing prohibition:

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

## Safety boundary

```text
read_only=true
writes_database=false
no DB write
no Case write
no DiagnosticReport write
no Observation write
no ImagingStudy write
no ai_summary write
no audit log write
no source collection activation
no source collection execution
no final diagnosis
no diagnostic conclusion
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency
no client-facing output
no external AI/provider call
no real EMR/lab/DICOM/device ingest
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff.py
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record.py
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record.py
```

Primary validator for this stage:

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record.py
```

## Go / No-Go

```text
current_level=metadata_only_source_collection_activation_governance_signoff_record_schema_only_not_activation
source_review_status=metadata_only_source_collection_activation_governance_signoff_record_defined_no_activation
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
activation_governance_signoff_defined=true
activation_governance_signoff_completed=false
activation_governance_signoff_record_defined=true
activation_governance_signoff_record_completed=false
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1
```
