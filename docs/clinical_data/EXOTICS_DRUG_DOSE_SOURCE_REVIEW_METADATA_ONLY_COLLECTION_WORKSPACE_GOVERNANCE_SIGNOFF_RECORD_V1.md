# Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff Record V1

## Purpose

This stage defines the metadata-only governance signoff record shell for the exotics source-review workspace.

It remains a record schema only. It does not complete governance signoff, does not execute source collection, does not populate the workspace, does not create a dose engine, does not create a prescription engine, and does not create a treatment-plan engine.

## Current decision

```text
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
current_level=metadata_only_workspace_governance_signoff_record_schema_only_not_collection_execution
source_review_status=metadata_only_workspace_governance_signoff_record_defined_no_collection_execution
drug_dose_status=not_reviewed_not_enabled
dose_output_enabled=false
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
```

## In scope

- Define governance signoff record rows for every species group and review domain.
- Record that clinical owner signoff is required but not recorded.
- Record that second reviewer signoff is required but not recorded.
- Record that source access signoff is required but not recorded.
- Record that copyright access signoff is required but not recorded.
- Record metadata-only policy status without starting collection execution.
- Preserve NO-GO to source collection execution until a later explicit stage.

## Out of scope

- Source collection execution.
- Workspace population.
- Completed governance signoff.
- Evidence table population.
- Source registry population with real source rows.
- Any clinical recommendation output.
- Any client-facing content.
- Any medication instruction.

## Allowed metadata-only fields

```text
governance_signoff_record_id
species_group
review_domain
governance_signoff_id
workspace_scope
clinical_owner_record_status
second_reviewer_record_status
source_access_record_status
copyright_access_record_status
metadata_only_policy_record_status
value_capture_blocker_record_status
collection_execution_status
signoff_record_status
signoff_completed_status
go_no_go_status
human_review_required
clinician_signoff_required
next_required_stage
```

## Forbidden fields

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

## Safety

```text
read_only=true
writes_database=false
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
requires_human_review=true
clinician_signoff_required=true
```

## Decision

```text
decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_VALIDATION_V1
```
