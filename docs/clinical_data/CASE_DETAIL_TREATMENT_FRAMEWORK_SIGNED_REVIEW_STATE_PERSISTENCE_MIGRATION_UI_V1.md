# CASE_DETAIL_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_UI_V1

## Purpose

Add a clinician-facing Case Detail UI panel for the signed review state persistence migration dry-run preview.

This stage is UI-only. It calls the migration dry-run endpoint and renders the returned migration plan preview for clinician/admin review. It does not execute migration, does not create a migration file, does not change schema, does not persist signed review state, does not write case treatment, and does not write prescription.

## Endpoint used

`POST /api/diagnostic-data/dry-run/confirmed-diagnosis/treatment-framework/signed-review-state/persistence/migration/dry-run`

## Required upstream previews

- treatment framework preview
- signed review state preview
- signed review state persistence dry-run preview
- migration design acknowledgement
- migration readiness review completed

## Safety contract

case_detail_signed_review_state_persistence_migration_ui_only=true
migration_dry_run_only=true
migration_enabled=false
migration_file_created=false
schema_change_enabled=false
persistence_enabled=false
signed_review_state_persistence_enabled=false
review_state_persistence_enabled=false
writes_database=false
no_case_treatment_write=true
no_case_treatment_persistence=true
no_prescription_write=true
no_dose_route_frequency=true
not_client_facing=true
requires_human_review=true
clinician_signoff_required=true

## UI behavior

The UI displays:

- migration dry-run requested by
- target table preview
- operation preview
- schema plan preview
- columns preview
- indexes preview
- foreign keys preview
- rollback plan preview
- forbidden write targets
- safety/quality gates

The UI does not expose a button to apply migration.

## Go / No-Go

GO only if:

- validator PASS
- ci_static_checks PASS
- online smoke ALL PASS
- production hard gate remains database_revision=0009_diag_data
- dangerous feature flags remain disabled
- migration dry-run endpoint is registered and protected or validation-gated
- UI static markers are present
- no database write occurs
- no migration file is created
- no schema change is enabled
- no case treatment field write occurs
- no prescription, dose, route, or frequency output occurs

decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_FINAL_GO_NO_GO_V1
