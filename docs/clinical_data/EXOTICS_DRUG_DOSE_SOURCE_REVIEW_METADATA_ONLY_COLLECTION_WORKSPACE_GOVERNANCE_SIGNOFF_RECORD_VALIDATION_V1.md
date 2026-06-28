# Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record Validation V1

## Purpose

This stage defines a metadata-only governance signoff record validation shell for the exotics drug dose source-review workflow.

It validates whether the prior governance signoff record shell has the required metadata-only controls for every species group and review domain. It does not execute source collection, does not populate the workspace, does not validate real source content, and does not collect or store usable medication values.

## Current decision

```text
current_level=metadata_only_workspace_governance_signoff_record_validation_schema_only_not_collection_execution
source_review_status=metadata_only_workspace_governance_signoff_record_validation_defined_no_collection_execution
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
collection_execution_started=false
collection_execution_allowed_now=false
metadata_only_workspace_defined=true
metadata_only_workspace_populated=false
metadata_only_workspace_validation_defined=true
metadata_only_workspace_validation_executed=false
metadata_only_workspace_validation_report_defined=true
metadata_only_workspace_validation_report_has_collection_results=false
governance_signoff_defined=true
governance_signoff_completed=false
governance_signoff_record_defined=true
governance_signoff_record_completed=false
governance_signoff_record_validation_defined=true
governance_signoff_record_validation_executed=false
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
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

- metadata-only governance signoff record validation schema
- per-species and per-review-domain validation matrix
- clinical owner record gate
- second reviewer record gate
- source access record gate
- copyright access record gate
- metadata-only policy record gate
- value-capture blocker record gate
- Go/No-Go preservation as NO_GO_TO_COLLECTION_EXECUTION

## Out of scope

- source collection execution
- source registry population
- evidence table population
- real source content abstraction
- numeric dose capture
- route or frequency capture
- prescription direction
- treatment protocol
- client instruction
- clinical decision support output

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
creates_case=false
updates_case=false
creates_diagnostic_report=false
updates_diagnostic_report=false
creates_observation=false
updates_observation=false
creates_imaging_study=false
updates_imaging_study=false
writes_ai_summary=false
writes_audit_log=false
executes_source_collection=false
collection_execution_started=false
collection_execution_allowed_now=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff_record_validation.py
```

## Decision

```text
GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_REPORT_V1
```
