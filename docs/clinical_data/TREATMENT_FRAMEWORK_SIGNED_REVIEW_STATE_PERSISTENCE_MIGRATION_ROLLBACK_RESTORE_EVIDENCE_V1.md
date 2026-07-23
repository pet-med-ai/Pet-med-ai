# Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1

## Stage identity

stage_id=PMAI-P0-02
stage_name=Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1
stage_type=rollback_restore_evidence_collection
PACKAGE_INITIALIZED=true
STAGE_STATUS=COMPLETE
EVIDENCE_COMPLETENESS=COMPLETE
ROLLBACK_RESTORE_EVIDENCE_COMPLETE=true
BACKUP_EVIDENCE_COMPLETE=true
RESTORE_EVIDENCE_COMPLETE=true
ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=true
DATA_VERIFICATION_COMPLETE=true
CLINICAL_CASE_READBACK_COMPLETE=true
FAILURE_PATH_OWNER_RECORDED=true

# Legacy migration markers below are scoped only to the signed-review 0010 migration.
STAGING_MIGRATION_EXECUTED=false
STAGING_MIGRATION_EXECUTED_SCOPE=signed_review_0010_only
SCHEMA_CHANGE_APPLIED=false
SCHEMA_CHANGE_APPLIED_SCOPE=signed_review_0010_only
SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false
SIGNED_REVIEW_0010_SCHEMA_CHANGE_APPLIED=false
STAGING_BASELINE_0001_TO_0009_PREPARATION_EXECUTED=true
STAGING_SYNTHETIC_FIXTURE_WRITE_EXECUTED=true
STAGING_DATABASE_WRITE_PERFORMED=true
STAGING_DATABASE_WRITE_SCOPE=0001_to_0009_baseline_and_synthetic_fixture_only
PRODUCTION_MIGRATION_EXECUTED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
APPLICATION_DATABASE_WRITE_PERFORMED=false
PRODUCTION_DATABASE_WRITE_PERFORMED=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
CLIENT_FACING_RELEASE_PERFORMED=false
CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false
STAGING_DATABASE_URL_RECORDED=false
STAGING_CREDENTIAL_RECORDED=false
STAMP_HEAD_USED=false
MANUAL_ALEMBIC_REVISION_EDIT_USED=false
STAGING_APPLY_AUTHORIZED=false
AUTHENTICATED_STAGING_SMOKE_AUTHORIZED=true
PRODUCTION_MIGRATION_AUTHORIZED=false

PMAI-P0-02 is complete because a real point-in-time restore was created from an
isolated Ohio staging source, the restored target remained at 0009_diag_data, and
revision, row-count, referential-integrity, and pseudonymized sample readback
checks matched. This completion authorizes only PMAI-P0-03 authenticated staging
smoke. It does not authorize signed-review 0010 apply, production migration,
Case.treatment write, prescription write, or medication-detail output.

## Production hard gate remains unchanged

database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false

## Reproducible baseline

baseline_commit_sha=8d118180ced24b4df9af987790d47ab049346786
completion_baseline_commit_sha=e248d4650f6e19e77868adb089d23aef9dc30209
completion_baseline_remote_ref=origin/main
previous_evidence_document=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1.md
previous_evidence_document_sha256=0f91dd34b0489fc66b378628520955a6b3d9bf2108918b4ed3fa6819e3ee38d3
inactive_0010_draft_path=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt
inactive_0010_draft_sha256=bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d
inactive_0010_reference_only=true
active_0010_migration_file_must_not_exist=true

## Sanitized evidence summary

evidence_directory=docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1
evidence_manifest=docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/SHA256SUMS.txt
evidence_manifest_sha256=88e21047d467effceee74735268390697b48b6189a1ece62a088aa2f4a7cc69c
staging_service_label=pet-med-ai-db-staging-source-ohio
database_engine=PostgreSQL 18
source_environment=staging
isolated_from_production=true
production_backend_attached=false
application_writers_suspended_or_absent=true
recovery_method=PITR
backup_id=render-pitr-point-20260722T152600Z
backup_created_at_utc=2026-07-22T15:26:00Z
backup_integrity_status=VERIFIED
restore_target_label=pet-med-ai-db-p0-02-restore-ohio-202607221526
restore_started_at_utc=2026-07-22T16:02:27Z
restore_completed_at_utc=2026-07-22T16:16:51Z
restore_duration_seconds=864
source_database_revision=0009_diag_data
restore_database_revision=0009_diag_data
source_capture_sha256=8ae93ff3e3781518c6ed2b44313c2f05f155f5cc9094b4307e0609840c8474af
restore_capture_sha256=8ae93ff3e3781518c6ed2b44313c2f05f155f5cc9094b4307e0609840c8474af
comparison_sha256=d0cdfbcf6b7b1bfca2453527d4ea806ce9a08e1a6f0403f4d6687e928ca54dc8
row_count_parity=MATCH
sample_case_readback=MATCH
referential_integrity=PASS
operator_role=release_operator
incident_owner_role=backend_owner
synthetic_fixture_only=true
staging_baseline_database_name=pet_med_ai_staging_source_088v

## Evidence files

- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/00_README.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/01_environment_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/02_provider_backup_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/03_provider_restore_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/04_failure_ownership_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/05_staging_baseline_preparation_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/10_source_readonly_verification.csv
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/11_restore_readonly_verification.csv
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/12_restore_comparison_sanitized.txt
- docs/clinical_data/evidence/PMAI_P0_02_ROLLBACK_RESTORE_V1/SHA256SUMS.txt

The evidence files are sanitized text or CSV artifacts. The manifest covers each
artifact by filename and SHA-256. No connection URI, password, token, owner contact
information, raw backup, or unredacted clinical text is committed.

## Verified restore facts

- Source and restore revisions are 0009_diag_data.
- The inactive signed-review table remains absent.
- cases, consult_sessions, diagnostic_reports, observations, imaging_studies, and
  audit_log row counts match exactly.
- All checked diagnostic, observation, imaging, and audit references remain valid.
- The pseudonymized synthetic case token and five linked records match.
- The restore target is disposable and isolated from production.
- `alembic stamp head` and manual Alembic revision edits were not used.
- The only staging write was the controlled 0001-to-0009 baseline plus one
  synthetic, non-clinical fixture. No Case.treatment column write occurred.

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

## Explicit non-goals

- no signed-review 0010 staging migration apply
- no production migration
- no active Alembic 0010 migration
- no production schema change
- no application business-data write
- no Case.treatment write
- no prescription write
- no medication amount, route, or frequency output
- no client-facing AI diagnosis
- no real EMR, LIS, DICOM, PACS, device, or gateway ingest
- no automatic SMS, WeChat, or email delivery
- no invoice real write

## Decision

previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1
decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
completion_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
