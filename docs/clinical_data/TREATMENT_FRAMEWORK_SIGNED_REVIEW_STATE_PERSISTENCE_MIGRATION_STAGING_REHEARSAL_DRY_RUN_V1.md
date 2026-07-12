# Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1

## Stage intent

stage_name=Treatment Framework Signed Review State Persistence Migration Staging Rehearsal Dry Run V1
stage_type=staging_rehearsal_dry_run_only
STAGING_REHEARSAL_DRY_RUN_ONLY=true
REAL_STAGING_MIGRATION_EXECUTED=false
PRODUCTION_MIGRATION_EXECUTED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
SCHEMA_CHANGE_APPLIED=false
DATABASE_WRITE_PERFORMED=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
CLIENT_FACING_RELEASE_PERFORMED=false
CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false

This phase records the rehearsal dry-run evidence contract only. It does not apply a staging migration and does not create an active Alembic migration file.

## Production hard gate remains unchanged

database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false

## Required rehearsal inputs for a future evidence phase

- inactive_0010_draft_reference_required=true
- staging_environment_requirement_defined=true
- staging_environment_must_be_isolated_from_production=true
- backup_restore_evidence_required=true
- rollback_dry_run_required=true
- authenticated_smoke_required_before_future_write=true
- production_hard_gate_must_remain_0009=true
- active_migration_file_must_not_exist=true
- no_database_write_must_be_preserved=true
- no_case_treatment_write_must_be_preserved=true
- no_prescription_write_must_be_preserved=true
- no_client_facing_release_must_be_preserved=true

## Dangerous feature flags remain disabled

- ENABLE_EMR_REAL_IMPORT=false
- ENABLE_EMR_IMPORT_CASE_UPDATE=false
- ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
- ENABLE_PREVENTIVE_AUTO_DELIVERY=false
- ENABLE_PREVENTIVE_SMS_DELIVERY=false
- ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
- ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
- ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
- ENABLE_DEVICE_REAL_INGEST=false
- ENABLE_BILLING_REAL_WRITE=false

## Dry-run evidence contract

The future staging rehearsal evidence package must include all of the following before any real apply rehearsal is considered:

1. A named inactive 0010 draft reference, reviewed as a reference artifact only.
2. A staging environment declaration that confirms isolation from production services and production data.
3. Backup and restore evidence for the target rehearsal environment.
4. Rollback dry-run evidence, including the exact command plan and expected restored state.
5. Authenticated smoke evidence collected before any future write-capable operation.
6. A final confirmation that production still reports database_revision=0009_diag_data and alembic_head=0009_diag_data.
7. A final confirmation that no active backend/migrations/versions/0010*.py file exists in this phase.

## Static validation scope

The validator for this phase checks documentation markers, checklist coverage, go/no-go coverage, shell-script wiring, production hard-gate markers, dangerous feature-flag markers, and active migration-file absence. It intentionally does not import backend application code and intentionally does not open a database connection.

## Explicit non-goals

- no real EMR import
- no real EMR case update
- no EMR attachment download
- no real device, LIS, DICOM, PACS, or gateway ingestion
- no structured prescription write
- no automated medication-detail recommendation
- no owner-facing AI diagnosis release
- no owner-facing medication-detail output
- no automated outbound delivery
- no invoice real write

## Decision

previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_DRY_RUN_V1
decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1
