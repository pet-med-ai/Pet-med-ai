# Exotics Drug Dose Source Review Metadata-only Source Collection Activation Governance Signoff Record Validation Report V1

## Purpose

This stage defines a metadata-only report shell for activation governance signoff record validation in the exotics drug-dose source-review workflow.

It does not activate source collection. It does not execute source collection. It is not a dose engine, prescription engine, or treatment-plan engine.

## Current decision

```text
mode=exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_report_v1
current_level=metadata_only_source_collection_activation_governance_signoff_record_validation_report_schema_only_not_activation
source_review_status=metadata_only_source_collection_activation_governance_signoff_record_validation_report_defined_no_activation
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
activation_governance_signoff_defined=true
activation_governance_signoff_completed=false
activation_governance_signoff_record_defined=true
activation_governance_signoff_record_completed=false
activation_governance_signoff_record_validation_defined=true
activation_governance_signoff_record_validation_executed=false
activation_governance_signoff_record_validation_report_defined=true
activation_governance_signoff_record_validation_report_has_collection_results=false
collection_activation_allowed_now=false
collection_execution_started=false
collection_execution_allowed_now=false
pilot_execution_allowed_now=false
governance_decision=NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION
```

## Species groups

- rabbit
- bird
- ferret
- turtle
- lizard
- snake
- amphibian
- fish
- guinea_pig
- hamster
- chinchilla
- rat_mouse
- hedgehog
- sugar_glider

## Review domains

- analgesia_and_pain_control_source_review
- antimicrobial_source_review
- antiparasitic_source_review
- fluid_and_supportive_care_source_review
- sedation_anesthesia_risk_source_review
- emergency_stabilization_source_review

## In scope

- metadata-only activation governance signoff record validation report schema
- per-species and per-review-domain report matrix
- reporting that clinical owner, second reviewer, source access, copyright access, metadata-only policy and value-capture blocker checks are still not verified
- reporting that activation and execution are still not started
- Go/No-Go preservation as NO_GO_TO_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION

## Explicitly forbidden fields

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

## Safety flags

```text
read_only=true
writes_database=false
starts_source_collection_activation=false
starts_source_collection_execution=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_source_collection_activation_governance_signoff_record_validation_report.py
```

## Decision

```text
GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_SOURCE_COLLECTION_ACTIVATION_GOVERNANCE_SIGNOFF_RECORD_FINAL_GO_NO_GO_V1
```
