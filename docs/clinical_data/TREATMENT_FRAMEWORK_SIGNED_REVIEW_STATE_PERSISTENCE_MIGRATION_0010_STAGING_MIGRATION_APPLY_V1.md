# Treatment Framework Signed Review State Persistence Migration 0010 Staging Migration Apply V1

## Stage identity

stage_id=PMAI-P0-04
stage_name=Treatment Framework Signed Review State Persistence Migration 0010 Staging Migration Apply V1
stage_type=staging_migration_apply_governance_preparation
PACKAGE_INITIALIZED=true
STAGE_STATUS=IN_PROGRESS
EVIDENCE_COMPLETENESS=PENDING_DISPOSABLE_RESTORE_REHEARSAL_AND_EXTERNAL_EXECUTION
P0_03_PREREQUISITE_COMPLETE=true
P0_04_ENTRY_AUTHORIZED=true
P0_04_GOVERNANCE_PREPARATION_COMPLETE=true
P0_04_EXECUTION_AUTHORIZED=false
STAGING_0010_APPLY_AUTHORIZED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
ACTIVE_0010_MIGRATION_FILE_ALLOWED=false
STAGING_DEPLOY_AUTHORIZED=false
STAGING_0010_MIGRATION_EXECUTED=false
PRODUCTION_MIGRATION_AUTHORIZED=false
PRODUCTION_MIGRATION_EXECUTED=false
PACKAGE_CONNECTS_DATABASE=false
PACKAGE_WRITES_DATABASE=false
RUNNER_EXECUTED_BY_CI=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
MEDICATION_DETAIL_OUTPUT=false
CLIENT_FACING_OUTPUT=false

PMAI-P0-04 is now open only for governance preparation. This package does not
approve a migration implementation, activate revision 0010, deploy a staging
commit, connect to a database, or run Alembic. The future execution runner is
deliberately locked and is not invoked by CI or cumulative smoke.

## Locked prerequisite

initializer_baseline_commit_sha=b85e48a80019e522a5b5d1f3df6531752de2c25c
previous_stage_id=PMAI-P0-03
previous_stage_status=COMPLETE
previous_stage_evidence_sha256=da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213
previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1
source_database_revision=0009_diag_data
source_alembic_head=0009_diag_data
production_database_revision_expected=0009_diag_data

## Inactive draft findings and approved replacement contract

inactive_draft_sha256=bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d
inactive_draft_revision=0010_treatment_framework_signed_review_states
inactive_draft_revision_length=45
alembic_revision_max_length=32
candidate_short_revision=0010_signed_review_states
candidate_short_revision_length=25
candidate_short_revision_approved=true
draft_revision_id_approved=false
draft_audit_log_reference_type=String(120)
expected_audit_log_id_type=String(64)
draft_audit_log_reference_nullable=true
draft_audit_log_reference_index_only=true
draft_audit_log_foreign_key_present=false
draft_idempotency_key_non_null=false
draft_idempotency_unique_constraint_present=false
draft_case_foreign_key_ondelete_specified=false
migration_schema_review_approved=true

schema_contract_resolution_recorded=true
P0_04_SCHEMA_CONTRACT_RESOLUTION_COMPLETE=true
schema_contract_resolution_baseline_commit_sha=5262f1438c7a36137c930301c36f82ed05dc56ff
schema_contract_resolution_document=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_SCHEMA_CONTRACT_RESOLUTION_V1.md
schema_contract_approval_scope=GOVERNANCE_ONLY_NOT_EXECUTION_AUTHORIZATION
corrected_migration_implementation_authorized=false
approved_revision=0010_signed_review_states
approved_revision_length=25
approved_down_revision=0009_diag_data
approved_audit_log_id_type=String(64)
approved_audit_log_same_case_composite_fk=true
approved_audit_log_composite_unique=true
approved_audit_log_id_unique=true
approved_audit_semantics_insert_trigger_required=true
approved_referenced_audit_mutation_protection_required=true
approved_idempotency_key_type=String(64)
approved_idempotency_key_unique=true
approved_idempotency_key_random_opaque=true
approved_payload_sha256_type=String(64)
approved_row_lifecycle=IMMUTABLE_VERSIONED_APPEND_ONLY
approved_supersedes_state_id=true
approved_one_root_per_case_partial_unique_index=true
approved_append_only_trigger_required=true
approved_active_case_insert_trigger_required=true
approved_active_case_insert_lock=FOR_SHARE
approved_updated_at_present=false
approved_finite_vocabulary_enforcement=DATABASE_CHECK_CONSTRAINTS_REQUIRED
approved_input_normalization_mapping_recorded=true

The inactive `.py.txt` draft cannot be activated as written:

1. Its 45-character revision identifier exceeds the repository guardrail of
   32 characters. `0010_signed_review_states` is only a candidate for later
   review; this package does not create or approve it.
2. `audit_log_reference` is nullable `String(120)` and indexed only, while
   `audit_log.log_id` is a `String(64)` primary key. A later review must approve
   an aligned, non-null audit foreign key and its lifecycle behavior.
3. The draft has no non-null idempotency key or unique constraint. A concrete
   idempotency contract must be approved before activation.
4. The `case_id` foreign key does not specify deletion behavior. Its `ondelete`
   and lifecycle contract must be decided explicitly.

The old draft remains blocked exactly as written. The separately reviewed replacement
contract is now recorded in the dedicated schema-contract document, but does not
authorize editing, copying, activation, deployment, database access, or Alembic.

## Deployment isolation blocker

production_backend_service=pet-med-ai-backend
production_auto_deploy_trigger=commit
staging_only_branch_or_commit_pin_verified=true
production_deployment_freeze_verified=false
production_target_excluded=true

deployment_isolation_evidence_document=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_DEPLOYMENT_ISOLATION_EVIDENCE_V1.md
deployment_isolation_evidence_sha256=67fe12a4dc32e8edf91217693bf5ad85a7ab17fee107111aeafde66fabd4525b
isolated_staging_branch=pmai-p0-04-staging-0010
isolated_staging_branch_head_sha=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
deployment_isolation_verified=true
manual_deploy_observed=true
manual_deploy_commit_sha=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
manual_deploy_deviation_recorded=true
manual_deploy_deviation_safely_verified=true
candidate_migration_deployed=false
postdeploy_readonly_verification_passed=true

`render.yaml` records production backend auto-deploy on commit. The isolated
candidate path is now the staging-only branch `pmai-p0-04-staging-0010`, while
production continues to track `main`. `production_target_excluded=true` means
only that production does not track the candidate branch; it is not a production
freeze. Both dashboard manual deployments of the safe governance commit are
truthfully recorded and were closed by post-deploy read-only verification at
`0009_diag_data`. No candidate migration was deployed.

## Mandatory future evidence sequence

fresh_backup_evidence_document=TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_FRESH_POST_P0_03_STAGING_BACKUP_EVIDENCE_V1.md
fresh_backup_evidence_sha256=a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1
fresh_backup_artifact_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7
fresh_backup_pg_restore_toc_sha256=6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c
fresh_backup_integrity_verified=true
fresh_backup_independent_evidence_verification_complete=true
backup_restoreability_verified=false

fresh_post_p0_03_staging_backup_verified=true
disposable_restore_rehearsal_complete=false
disposable_restore_upgrade_complete=false
disposable_restore_downgrade_to_0009_complete=false
rollback_restore_path_verified=false
source_staging_fresh_backup_verified=false
source_commit_sha_pinned=false
active_migration_sha256_pinned=false
exact_target_upgrade_command_approved=false
pre_apply_schema_evidence_complete=false
post_apply_schema_evidence_complete=false
critical_row_parity_verified=false
new_table_row_count_zero_verified=false
production_remains_0009_verified=false
external_execution_evidence_complete=false

The only acceptable future order is:

1. approve the corrected migration schema and a revision identifier no longer
   than 32 characters;
2. establish staging-only deployment isolation and production exclusion;
3. take a fresh staging backup because P0-03 created later staging records;
4. restore that backup into a disposable database and rehearse exact-target
   upgrade, downgrade, and return to `0009_diag_data`;
5. review sanitized rehearsal and rollback/restore evidence;
6. take a new source-staging backup immediately before the real apply;
7. pin source commit SHA and active migration file SHA-256;
8. authorize only `alembic upgrade <approved-exact-revision>`.

`alembic upgrade head`, `alembic stamp head`, manual version-table edits, and
ambiguous targets are forbidden. The later execution evidence must contain
sanitized pre/post schema snapshots, critical-table row parity, zero rows in
the newly created table, and read-only proof that production remains at
`0009_diag_data`.

## Safety boundary

future_confirmation_token=PMAI-P0-04-0010-STAGING-MIGRATION-APPLY
runner_execution_enabled=false
network_access=false
database_connection=false
database_write=false
alembic_invoked=false
migration_created=false
migration_executed=false
external_evidence_committed=false
case_treatment_write=false
prescription_write=false
medication_detail_output=false
production_database_write=false

Any missing or conflicting evidence is `NO_GO_TO_PMAI_P0_04_EXECUTION`.
No credentials, database URLs, emails, JWTs, user IDs, case IDs, or raw
database output belong in this repository package.

## Current decision

decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_RESTORE_REHEARSAL_AND_EXTERNAL_EVIDENCE
next_step=PREPARE_DISPOSABLE_RESTORE_REHEARSAL_UNDER_SEPARATE_GOVERNANCE
