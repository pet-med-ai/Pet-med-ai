# TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_PLAN_V1

## Purpose

Define the staging rehearsal plan for the future signed review state persistence migration.

This stage is a planning checkpoint only. It does not create an active Alembic migration, does not execute a migration command, does not change schema, does not write database rows, and does not enable signed review state persistence.

## Fixed Safety Contract

- staging_rehearsal_plan_only=true
- staging_rehearsal_execution_allowed=false
- staging_rehearsal_dry_run_required_first=true
- active_migration_file_created=false
- active_migration_file_allowed=false
- production_migration_apply_allowed=false
- migration_apply_allowed=false
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
- staging_environment_required=true
- staging_rehearsal_plan_required=true
- rollback_dry_run_required=true
- backup_restore_evidence_required=true
- authenticated_smoke_required_before_write=true
- append_only_audit_linkage_required=true
- requires_human_review=true
- clinician_signoff_required=true

## Rehearsal Plan Requirements

Before any future active migration file is allowed, a separate staging rehearsal dry-run stage must document:

1. target staging environment identity,
2. source commit and inactive 0010 draft reference,
3. backup/restore evidence path,
4. rollback dry-run evidence path,
5. authenticated smoke plan with owned case id,
6. schema validation plan,
7. confirmation that production remains on database_revision=0009_diag_data and alembic_head=0009_diag_data during this plan stage.

## Explicit No-Go Items

- NO_GO_TO_ACTIVE_MIGRATION_FILE_ON_MAIN
- NO_GO_TO_PRODUCTION_MIGRATION_APPLY
- NO_GO_TO_DATABASE_WRITE
- NO_GO_TO_CASE_TREATMENT_PERSISTENCE
- NO_GO_TO_PRESCRIPTION_WRITE
- NO_GO_TO_DOSE_ROUTE_FREQUENCY_OUTPUT
- NO_GO_TO_CLIENT_FACING_RELEASE

## Decision

GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1
