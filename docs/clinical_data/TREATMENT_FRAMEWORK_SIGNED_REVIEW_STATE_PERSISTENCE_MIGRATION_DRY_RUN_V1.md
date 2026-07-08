# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_DRY_RUN_V1

## Purpose

This stage defines and exposes a dry-run-only migration plan preview for future
Treatment Framework Signed Review State persistence.

It does not create an Alembic migration, does not change the schema, does not
write the database, does not persist signed review state, and does not write
the case treatment field.

## Fixed boundaries

- migration_dry_run_only=true
- migration_enabled=false
- migration_file_created=false
- schema_change_enabled=false
- persistence_enabled=false
- signed_review_state_persistence_enabled=false
- review_state_persistence_enabled=false
- writes_database=false
- no_case_treatment_write=true
- no_case_treatment_persistence=true
- no_prescription_write=true
- no_dose_route_frequency=true
- not_client_facing=true
- requires_human_review=true
- clinician_signoff_required=true

## Endpoint

```text
POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/migration/dry-run
```

## Required input

- case_id
- confirmed_diagnosis_label
- confirmed_by
- confirmation_source=clinician
- ai_generated=false
- treatment_framework_preview
- signed_review_state_preview
- persistence_dry_run_preview
- migration_design_acknowledged=true
- migration_readiness_review_completed=true
- migration_dry_run_requested_by

## Output

The endpoint returns `migration_plan_preview` only.

It may include future table, column, index, foreign key, rollback and backup
planning information, but it must not create a migration file or apply a
migration.

## Forbidden output and behavior

- no database write
- no schema change
- no Alembic migration execution
- no real migration file creation
- no case treatment field write
- no prescription write
- no drug dose
- no route
- no frequency
- no client-facing release

## Go / No-Go

This stage is GO only to a Case Detail migration dry-run UI preview.

It is explicitly NO-GO to real migration, real signed review state persistence,
case treatment persistence, prescription writing, dose output, route output or
frequency output.

decision=GO_TO_CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1
