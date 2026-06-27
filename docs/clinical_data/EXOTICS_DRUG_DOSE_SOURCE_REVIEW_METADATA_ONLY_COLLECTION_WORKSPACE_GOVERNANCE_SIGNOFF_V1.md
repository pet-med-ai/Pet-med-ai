# Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff V1

## Purpose

This stage defines the governance signoff gate for the exotics drug-dose source-review metadata-only collection workspace.

It remains a governance shell only. It does not execute source collection, does not populate the workspace, does not create a dose engine, does not create a prescription engine, and does not create a treatment-plan engine.

## Current decision

```text
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
current_level=metadata_only_workspace_governance_signoff_schema_only_not_collection_execution
source_review_status=metadata_only_workspace_governance_signoff_defined_no_collection_execution
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
```

## In scope

- Define governance signoff rows for every species group and review domain.
- Require named clinical owner assignment before source collection.
- Require second reviewer assignment before source collection.
- Require source access verification before source collection.
- Require copyright access verification before source collection.
- Confirm metadata-only workspace policy.
- Confirm value-capture blocker status.
- Preserve NO-GO to source collection execution until a later explicit stage.

## Out of scope

- Source collection execution.
- Workspace population.
- Evidence table population.
- Source registry population with real source rows.
- Any clinical recommendation output.
- Any client-facing content.
- Any medication instruction.

## Allowed metadata-only fields

```text
governance_signoff_id
species_group
review_domain
workspace_scope
workspace_status
workspace_validation_status
validation_report_status
named_clinical_owner_status
second_reviewer_status
source_access_status
copyright_access_status
metadata_only_policy
value_capture_blocker_status
collection_execution_status
governance_signoff_status
go_no_go_status
human_review_required
clinician_signoff_required
next_required_stage
```

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

## Safety boundary

```text
is_dose_engine=false
is_prescription_engine=false
is_treatment_plan_engine=false
dose_output_enabled=false
captures_numeric_dose_value=false
captures_route_or_frequency_text=false
stores_usable_medication_instruction=false
writes_database=false
creates_case=false
updates_case=false
writes_ai_summary=false
writes_audit_log=false
final diagnosis=false
treatment plan=false
prescription=false
client-facing output=false
requires_human_review=true
clinician_signoff_required=true
```

## Validation

```bash
python3 scripts/validate_exotics_drug_dose_source_review_metadata_only_collection_workspace_governance_signoff.py
bash scripts/ci_static_checks.sh
```

## Decision

```text
Exotics Drug Dose Source Review Metadata-only Collection Workspace Governance Signoff V1 is complete only when:
validator=PASS
ci_static_checks=PASS
online_smoke=ALL_PASS
metadata_only_workspace_governance_signoff_matrix_present=true
governance_decision=NO_GO_TO_COLLECTION_EXECUTION
no DB write
no final diagnosis
no treatment plan
no prescription
no drug dose
no drug route
no drug frequency

decision=GO_TO_EXOTICS_DRUG_DOSE_SOURCE_REVIEW_METADATA_ONLY_COLLECTION_WORKSPACE_GOVERNANCE_SIGNOFF_RECORD_V1
```
