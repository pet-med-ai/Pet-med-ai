# Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1

## Stage identity

stage_id=PMAI-P0-03
stage_name=Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1
stage_type=authenticated_staging_smoke
PACKAGE_INITIALIZED=true
STAGE_STATUS=COMPLETE
EVIDENCE_COMPLETENESS=COMPLETE
AUTHENTICATED_STAGING_SMOKE_COMPLETE=true
EVIDENCE_INTEGRITY_VERIFIED=true
STAGING_BACKEND_PROVISIONED=true
STAGING_BACKEND_ISOLATED=true
STAGING_DATABASE_REVISION_VERIFIED=true
AUTHENTICATION_VERIFIED=true
OWNER_SCOPE_VERIFIED=true
CROSS_USER_DENIAL_VERIFIED=true
TREATMENT_FRAMEWORK_BUILD_VERIFIED=true
CLINICIAN_REVIEW_VERIFIED=true
APPEND_ONLY_AUDIT_LINK_VERIFIED=true
SIGNED_REVIEW_STATE_PREVIEW_VERIFIED=true
PERSISTENCE_PREPARE_VERIFIED=true
MIGRATION_PATH_PREVIEW_VERIFIED=true
READBACK_VERIFIED=true
IDEMPOTENCY_STRATEGY_VERIFIED=true
FAILURE_NO_PARTIAL_WRITE_VERIFIED=true
STAGING_SYNTHETIC_USERS_WRITE_EXECUTED=true
STAGING_SYNTHETIC_CASE_WRITE_EXECUTED=true
STAGING_APPEND_ONLY_AUDIT_WRITE_EXECUTED=true
STAGING_APPEND_ONLY_AUDIT_WRITE_COUNT=1
SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false
PRODUCTION_MIGRATION_EXECUTED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
PRODUCTION_DATABASE_WRITE_PERFORMED=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
CLIENT_FACING_RELEASE_PERFORMED=false
CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false
STAGING_DATABASE_URL_RECORDED=false
STAGING_CREDENTIAL_RECORDED=false
RUNNER_REQUIRES_EXPLICIT_CONFIRMATION=true
RUNNER_EXECUTED_BY_CI=false
PACKAGE_CONNECTS_DATABASE=false
PACKAGE_WRITES_DATABASE=false
P0_04_ENTRY_AUTHORIZED=true
STAGING_0010_APPLY_AUTHORIZED=false
PRODUCTION_MIGRATION_AUTHORIZED=false

PMAI-P0-03 is complete. A real authenticated smoke run was executed only
against the isolated staging backend. The resulting external JSON artifact
was sanitized, permission-checked, SHA-256 verified, and deliberately kept
outside the repository. Completion authorizes entry into P0-04 governance;
it does not itself create or execute migration 0010.

## Entry and reproducible baseline

baseline_commit_sha=b37362a2a343b068926edce4862b6f7d7c62a19d
smoke_execution_commit_sha=4ef91255e8eb1ca15be17579a1dceb2587d7b575
smoke_execution_repo_head=4ef9125
previous_stage_document=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md
previous_stage_status=COMPLETE
previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
rollback_restore_evidence_complete=true

## Sanitized external evidence summary

evidence_artifact_basename=PMAI_P0_03_AUTHENTICATED_STAGING_SMOKE_V1.json
evidence_artifact_sha256=da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213
evidence_artifact_committed=false
evidence_artifact_storage=external_local_workspace_not_committed
evidence_integrity_verified=true
evidence_file_mode=600
evidence_workspace_mode=700
smoke_started_at_utc=2026-07-29T14:50:33Z
smoke_completed_at_utc=2026-07-29T14:51:18Z
staging_service_label=pet-med-ai-backend-staging-ohio
staging_region=Ohio_US_East
staging_revision=0009_diag_data
production_revision=0009_diag_data
operator_role=release_operator
incident_owner_role=backend_owner

No staging URL, database connection URI, credential, token, email address,
raw user identifier, raw case identifier, or raw audit identifier is stored
in this package.

## Verified authentication and owner scope

unauthenticated_request_blocked=true
user_a_authenticated=true
user_b_authenticated=true
cross_user_case_read_blocked=true
cross_user_treatment_chain_blocked=true
cross_user_audit_readback_blocked=true
owner_scoped_audit_readback_verified=true

## Verified workflow chain

treatment_framework_build_verified=true
clinician_review_verified=true
append_only_audit_link_verified=true
signed_review_state_preview_verified=true
persistence_prepare_preview_verified=true
migration_path_preview_verified=true
readback_verified=true
case_snapshot_unchanged=true

## Verified idempotency and failure behavior

idempotency_strategy=write_once_audit_append_plus_deterministic_read_only_replay
audit_dry_run_repeated=true
actual_audit_append_replayed=false
read_only_chain_repeated=true
server_unique_request_constraint_claimed=false
dry_run_replay_deterministic=true
missing_audit_reference_blocked=true
missing_migration_ack_blocked=true
forbidden_medication_detail_blocked=true
no_partial_write_after_failures=true

## Controlled staging write scope

synthetic_users_created=2
synthetic_cases_created=1
append_only_audit_rows_created=1
signed_review_state_rows_created=0
case_treatment_write=false
prescription_write=false
medication_detail_output=false
production_database_write=false
active_0010_created=false
migration_executed=false

The two users and one case are synthetic staging-only records. The single
audit row is append-only and is the only treatment-chain persistence created
by the successful smoke. This promotion performs no cleanup of earlier
failed-attempt staging records.

## Production hard gate remains unchanged

database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false

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

## Completion boundary

authenticated_staging_smoke_complete=true
p0_04_entry_authorized=true
staging_0010_apply_authorized=false
production_migration_authorized=false

P0-04 may now be initialized as a separate controlled stage. Before any
staging schema apply, P0-04 must establish its own target files, validator,
explicit confirmation, rollback boundary, and staging-only execution gate.
This promotion does not create an active migration file and does not execute
Alembic.

## Explicit non-goals retained

- no active backend/migrations/versions/0010*.py in this promotion
- no signed-review 0010 staging migration execution
- no production migration or production schema change
- no Case.treatment write
- no prescription write
- no medication amount, route, or frequency output
- no client-facing AI diagnosis
- no real EMR, LIS, DICOM, PACS, device, or gateway ingest
- no automatic SMS, WeChat, or email delivery
- no real invoice write

## Decision

previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1
completion_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1
