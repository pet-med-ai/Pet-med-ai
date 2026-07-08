# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DESIGN_V1

## Purpose

This stage defines the future migration design contract for treatment framework signed review state persistence.

This is a design-only stage. It does not create a migration, does not modify models, does not modify backend endpoints, does not modify frontend UI, and does not write the database.

## Fixed safety flags

- migration_design_only=true
- migration_enabled=false
- migration_file_created=false
- schema_change_enabled=false
- persistence_enabled=false
- signed_review_state_persistence_enabled=false
- review_state_persistence_enabled=false
- migration_dry_run_required_first=true
- migration_readiness_review_completed=true
- migration_readiness_required=true
- migration_model_design_only=true
- no_business_logic_change=true
- no_backend_endpoint_change=true
- no_frontend_ui_change=true
- no_migration=true
- writes_database=false
- no_case_treatment_write=true
- no_case_treatment_persistence=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true
- rollback_plan_required=true
- backup_restore_evidence_required=true
- authenticated_smoke_required_before_write=true
- append_only_audit_linkage_required=true
- requires_human_review=true
- clinician_signoff_required=true

## Candidate future table contract

Candidate future entity name:

```text
treatment_framework_signed_review_states
```

This stage only names the candidate entity and field contract. It does not create the table.

Candidate future fields:

```text
id
case_id
confirmed_diagnosis_label
confirmed_by
confirmation_source
ai_generated
treatment_framework_preview_hash
signed_review_state_preview_hash
review_decision
reviewed_by
signoff_decision
signed_by
audit_log_id
audit_request_id
status
created_at
updated_at
```

## Required design gates before any future write stage

A future migration dry-run stage must prove all of the following before any database write is considered:

```text
migration_file_created=false in this stage
schema_change_enabled=false in this stage
future migration must be additive only
future migration must not touch case treatment field
future migration must not create prescription data
future migration must not store dose route frequency fields
future migration must link append-only audit evidence
future migration must include rollback and backup restore evidence
future migration must require authenticated 200 smoke before write
future migration must keep client release disabled
```

## Explicit prohibitions

- No real migration in this stage.
- No database write in this stage.
- No case treatment field write.
- No prescription write.
- No drug dose output.
- No route or frequency output.
- No client-facing release.
- No external AI/provider call.
- No dangerous feature flag enablement.

## Go / No-Go

- NO_GO_TO_SIGNED_REVIEW_STATE_DATABASE_WRITE
- NO_GO_TO_CASE_TREATMENT_PERSISTENCE
- NO_GO_TO_PRESCRIPTION_WRITE
- NO_GO_TO_DOSE_ROUTE_FREQUENCY_OUTPUT
- GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1

## Decision

decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1
