# Treatment Framework Signed Review State Persistence Migration 0010
## Disposable Restore Execution Authorization Review V1

This is a proposed, one-target and one-attempt restore authorization
record. The repository package itself performs no connection or restore.
Its authority can become effective only after exact operator approval,
repository commit and push, and a passing GitHub CI gate. Actual execution
remains blocked on a separately reviewed external runner hash, a fresh
target recheck, and a one-time execution confirmation.

## 1. Canonical authorization record

~~~text
stage_id=PMAI-P0-04
substage=DISPOSABLE_RESTORE_EXECUTION_AUTHORIZATION_REVIEW_V1
stage_status=IN_PROGRESS
package_status=AUTHORIZATION_RECORD_ONLY
review_status=APPROVED_DISPOSABLE_RESTORE_ONLY
authorization_record_id=PMAI-P0-04-DRER-V1-20260808
authorization_recorded_date=2026-08-08
approval_statement=批准 PMAI-P0-04 仅对 pet-med-ai-db-p0-04-disposable-restore-ohio 执行一次受控备份恢复演练；不授权 production、staging source、Alembic、0010 migration、locked runner 或任何应用部署。
approval_statement_sha256=888079b954b8a5e601e7b16c31b328a2070dd77e7de839a1a11fef1f5fdad4c2
approver_role=PROJECT_OWNER_OPERATOR
operator_role=PROJECT_OWNER_OPERATOR
authorization_scope=ONE_DISPOSABLE_TARGET_ONE_BACKUP_ONE_ATTEMPT_ONLY
authorization_record_effective_gate=PACKAGE_COMMITTED_PUSHED_AND_CI_GATE_PASS
restore_execution_start_gate=FRESH_TARGET_RECHECK_EXTERNAL_RUNNER_HASH_REVIEW_AND_ONE_TIME_CONFIRMATION
disposable_restore_execution_authorized=true
disposable_restore_database_connection_authorized=true
disposable_restore_database_write_authorized=true
restore_execution_authorization_requested=true
explicit_restore_execution_approval_present=true
restore_command_reviewed=true
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
decision=GO_TO_EXTERNAL_RESTORE_RUNNER_PREPARATION_AND_HASH_REVIEW_ONLY
next_action=PREPARE_EXTERNAL_FAIL_CLOSED_RESTORE_RUNNER_WITHOUT_EXECUTION
evidence_completeness=AUTHORIZATION_REVIEW_COMPLETE_PENDING_EXTERNAL_RUNNER_AND_EXECUTION_EVIDENCE
~~~

No authority beyond the exact approval statement may be inferred. In
particular, this record is not permission for a staging 0010 apply,
production migration, application deployment, or clinical write.

## 2. Trusted baseline and prerequisites

~~~text
local_main=9bae479760bb9a5f5940e9aa3cbb41ddfe46acc3
origin_main=9bae479760bb9a5f5940e9aa3cbb41ddfe46acc3
main_parent=9cf311610aae72537c1c57d98ff9e5c8b60edb94
github_ci_gate_number=188
github_ci_gate_status=PASS
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
production_runtime_baseline=d659aefb
staging_runtime_baseline=8d1dc881
production_database_revision_baseline=0009_diag_data
staging_database_revision_baseline=0009_diag_data
production_auto_deploy_verified=false
provisioning_evidence_complete=true
disposable_restore_database_created=true
restore_execution_authorization_preparation_complete=true
ready_for_restore_execution_authorization_review=true
provisioning_evidence_set_sha256=f2bc5bb7337bcfcd7b50df207f036e4c91dc78d9cdfca7084e1ebf7b112c7eb3
final_ci_sha256=a1684935365edfbe4db7ac08aa9b08e264d9dde533ca15685cd8bbb122b5f248
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
~~~

GitHub CI is not Render Auto-Deploy evidence. Neither a deployment nor a
runtime recheck is performed by this repository package.

## 3. Exact target and exclusion boundary

~~~text
target_logical_name=pet-med-ai-db-p0-04-disposable-restore-ohio
target_provider=Render
target_region=Ohio (US East)
target_postgresql_major_version=18
target_instance_type=Basic-256mb
target_storage_gb=1
target_storage_autoscaling=false
target_read_replica_count=0
target_high_availability=false
target_application_attachment_count=0
target_service_identifier_sha256=fcd569994776e091f001f7213cd02432339e172e51889b2acf0a3987e0be7b48
target_service_identifier_repository_value=HASH_ONLY
target_must_be_available=true
target_must_be_empty_before_restore=true
target_empty_application_data_verified=false
target_empty_state_must_be_verified_by_read_only_preflight=true
production_target_excluded=true
staging_source_target_excluded=true
all_other_database_targets_excluded=true
application_traffic_disabled=true
authorized_network_scope=ONE_DISPOSABLE_TARGET_ONLY
~~~

The external runner must hash the target identity derived in memory and
compare it with the approved hash before any connection. The raw service
identifier, hostname, connection value, or credential must never enter
repository files, command output, logs, evidence JSON, or shell history.

## 4. Exact backup and archive trust boundary

~~~text
backup_artifact_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7
backup_external_sanitized_evidence_sha256=a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1
backup_toc_sha256=6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c
backup_toc_entry_count=433
backup_pg_restore_version=18.4
backup_format=custom_or_directory_archive_recognized_by_pg_restore
backup_required_table_01=alembic_version
backup_required_table_02=users
backup_required_table_03=cases
backup_required_table_04=audit_log
source_archive_trust_scope=ONLY_CONTROLLED_STAGING_BACKUP_WITH_EXACT_APPROVED_HASHES
archive_hash_recheck_required_before_database_connection=true
toc_hash_and_count_recheck_required_before_database_connection=true
archive_ownership=EXTERNAL_OPERATOR_CUSTODY_NOT_REPOSITORY
raw_backup_committed=false
raw_backup_content_printed=false
~~~

Archive restore can execute objects defined by the source archive. The
authorization therefore applies only to the controlled staging backup
identified by the exact hashes above; any mismatch is a hard stop.

## 5. Reviewed inert restore argv contract

~~~text
restore_argv_canonicalization=ONE_ARGUMENT_PER_LINE_WITH_FINAL_NEWLINE
restore_argv_sha256=cf80e22e4fd0914d2b52ca253489b5123859900d1ce1d8e4adddf871ee534c51
restore_argv_01=pg_restore
restore_argv_02=--dbname=service=pmai_p0_04_disposable_restore
restore_argv_03=--no-owner
restore_argv_04=--no-privileges
restore_argv_05=--no-tablespaces
restore_argv_06=--no-publications
restore_argv_07=--no-subscriptions
restore_argv_08=--single-transaction
restore_argv_09=--exit-on-error
restore_argv_10=--verbose
restore_argv_11=--no-password
restore_argv_12=<APPROVED_BACKUP_PATH>
restore_shell_interpolation=false
restore_clean=false
restore_create=false
restore_jobs=1
restore_single_transaction=true
restore_exit_on_error=true
restore_owner_replay=false
restore_privilege_replay=false
restore_tablespace_replay=false
restore_publication_replay=false
restore_subscription_replay=false
restore_automatic_retry=false
~~~

The argv is a reviewed data contract, not a command executed by this
package. Any argument change requires a new authorization review.

## 6. Credential and connection contract for the future runner

~~~text
credential_entry=HIDDEN_INTERACTIVE_PROMPT_ONLY
connection_value_printed=false
connection_value_persisted=false
connection_value_committed=false
connection_value_in_shell_history=false
password_environment_variable_used=false
libpq_service_name=pmai_p0_04_disposable_restore
temporary_directory_mode=0700
temporary_pg_service_file_mode=0600
temporary_pgpass_file_mode=0600
sslmode=require
connect_timeout_seconds=10
preflight_statement_timeout_seconds=30
restore_wall_timeout_seconds=1800
postcheck_statement_timeout_seconds=60
temporary_secret_cleanup_required=true
~~~

The runner must parse the secret in memory, write only short-lived 0600
libpq service/pass files inside a 0700 temporary directory, and remove
them in a finally path. It must not use a password environment variable.

## 7. Preflight, transaction, postcheck, and evidence

~~~text
fresh_control_plane_recheck_max_age_minutes=15
read_only_preflight_required=true
preflight_postgresql_major_version=18
preflight_ssl_required=true
preflight_user_relation_count=0
preflight_alembic_version_relation_present=false
single_transaction_all_or_none_required=true
ambiguous_result_policy=HOLD_READ_ONLY_INSPECTION_NO_RETRY
postcheck_read_only=true
postcheck_database_revision_expected=0009_diag_data
postcheck_required_table_count=4
postcheck_sanitized_row_counts_only=true
postcheck_raw_clinical_rows_printed=false
external_execution_evidence_required=true
external_evidence_repository_policy=HASHES_AND_SANITIZED_FACTS_ONLY
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
~~~

Preflight and postcheck may read only sanitized structural facts and row
counts. They must not print patient, owner, case, audit, credential, or
connection content. An ambiguous timeout or transport loss is not a basis
for automatic retry.

## 8. Target lifetime and cleanup

~~~text
target_operational_delete_deadline_local=2026-08-11T00:00_OPERATOR_SCREENSHOT_LOCAL_TIME
target_hard_expiry_not_later_than_local=2026-08-11T00:08_OPERATOR_SCREENSHOT_LOCAL_TIME
target_delete_within_hours_after_restore_evidence=24
deletion_rule=EARLIEST_OF_24_HOURS_AFTER_EVIDENCE_OR_OPERATIONAL_DEADLINE
target_cost_ceiling_usd=1.00
deletion_owner=PROJECT_OWNER_OPERATOR
target_deleted=false
cleanup_evidence_required=true
cleanup_evidence_complete=false
~~~

Do not start if the remaining lifetime cannot accommodate the restore,
verification, evidence capture, and safe deletion window.

## 9. Package execution boundary retained

~~~text
repository_only=true
network_access=false
database_connection=false
database_write=false
restore_execution=false
pg_restore_invoked=false
psql_invoked=false
alembic_invoked=false
migration_created=false
migration_executed=false
restore_runner_created=false
restore_runner_execution_enabled=false
restore_runner_executed_by_ci=false
restore_runner_hash_review_complete=false
one_time_execution_confirmation_present=false
restore_attempt_started=false
restore_attempt_completed=false
connection_value_captured=false
raw_service_identifier_recorded=false
external_evidence_content_copied=false
external_evidence_artifact_committed=false
corrected_migration_implementation_authorized=false
active_0010_migration_file_created=false
staging_0010_migration_executed=false
production_migration_authorized=false
production_migration_executed=false
~~~

## 10. Production and clinical hard gates retained

~~~text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
~~~

## 11. Mandatory stop conditions

Stop and retain HOLD if any repository ref, protected hash, CI gate,
runner hash, archive hash, TOC hash/count, target identity hash, target
parameter, target emptiness predicate, TLS predicate, time budget, cost
ceiling, credential safeguard, single-transaction guarantee, or evidence
boundary differs. Also stop if the target is attached, shared, resized,
replicated, unavailable, non-empty, outside Ohio, or could be production
or staging source; if an automatic retry, clean/create/jobs option,
deployment, migration, locked runner, application write, clinical write,
raw evidence capture, or secret output is proposed; or if explicit
approval, repository commit/push/CI, fresh recheck, runner hash review, and
one-time confirmation are not all independently present.

This record authorizes no action against production or staging source and
no Alembic, 0010, deployment, treatment, prescription, dose, route,
frequency, messaging, EMR, device, or billing operation.
