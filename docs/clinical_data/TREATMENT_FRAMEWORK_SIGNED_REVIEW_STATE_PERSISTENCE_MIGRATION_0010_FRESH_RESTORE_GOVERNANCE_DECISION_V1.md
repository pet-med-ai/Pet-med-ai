# Treatment Framework Signed Review State Persistence Migration 0010
## Fresh Restore Governance Decision V1

This repository-only decision package compares the two permitted post-retirement
routes and records Route B as the selected governance route. It does not create
or authorize a target, runner, restore call, migration, deployment, database
connection, archive extraction, or backup modification.

## 1. Canonical governance decision

~~~text
stage_id=PMAI-P0-04
substage=FRESH_RESTORE_GOVERNANCE_DECISION_V1
stage_status=IN_PROGRESS
package_status=GOVERNANCE_DECISION_ONLY
decision_record_id=PMAI-P0-04-FRGD-V1-20260810
decision_authority_source=EXPLICIT_USER_AUTHORIZATION_CONTINUE_DEVELOPMENT_20260810
route_a_evaluated=true
route_b_evaluated=true
selected_route=ROUTE_B_REBUILD_FRESH_RESTORE_GOVERNANCE_CHAIN_FROM_ZERO
fresh_restore_governance_decision_complete=true
fresh_restore_governance_route_b_selected=true
fresh_restore_governance_route_b_approved=true
fresh_restore_governance_approved=true
decision=GO_TO_PMAI_P0_04_FRESH_RESTORE_GOVERNANCE_CHAIN_PREPARATION
next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_PREPARATION_V1
~~~

The approval above is limited to the governance route. It is not authority for
any repository apply, Git publication, external execution, target provisioning,
runner creation, restore attempt, migration, deployment, or resource deletion.

## 2. Trusted entry baseline

~~~text
local_main=0bc76d10af7a0168048fb007dff9e156341b9b4f
origin_main=0bc76d10af7a0168048fb007dff9e156341b9b4f
main_parent=aa045118ed52ddbf54e44a6f2924d1f6afe7498b
github_ci_gate_number=192
github_ci_gate_status=PASS
github_ci_gate_commit=0bc76d10af7a0168048fb007dff9e156341b9b4f
prior_ci_sha256=ccbed9cc605d145450a7a01deb5294799e284d5cbc694741cc95ebd18a095d4d
final_ci_sha256=4b50f28b230853bd57a983a7034aff170e11531bd276964a8c4b93769803c80c
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
production_runtime_baseline=d659aefb
staging_runtime_baseline=8d1dc881
production_database_revision_baseline=0009_diag_data
staging_database_revision_baseline=0009_diag_data
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
active_0010_migration_file_count=0
baseline_source=OPERATOR_HANDOFF_AND_REPOSITORY_BASELINE_NO_PACKAGE_NETWORK_RECHECK
~~~

GitHub CI Gate #192 proves only the named repository commit. Runtime and
database values remain the accepted handoff baseline and are not freshly
verified by this package.

## 3. Completed retirement boundary retained

~~~text
completed_substage=DISPOSABLE_TARGET_RETIREMENT_EXECUTION_EVIDENCE_V1
completed_commit=0bc76d10af7a0168048fb007dff9e156341b9b4f
disposable_target_retirement_evidence_complete=true
disposable_target_retirement_complete=true
retired_target_absence_verified=true
retired_target_reuse_allowed=false
retired_target_recreation_inferred=false
retirement_delete_retry_authorized=false
retirement_delete_retry_performed=false
~~~

The retired target lifecycle is closed. This decision does not rerun the
retirement package, repeat deletion, or permit reconstruction of the retired
service from its former identity.

## 4. Route comparison

### Route A — NO-GO / pause PMAI-P0-04

Route A keeps the stage on HOLD with backup restoreability unverified. It is
valid if the project chooses not to fund or operate a new restore rehearsal.
It cannot be used to bypass the restore hard gate and enter migration work.

### Route B — rebuild a fresh restore governance chain from zero

Route B is selected because the project owner explicitly directed development
to continue. The new chain is fixed as:

~~~text
archive/root contract investigation (list-only; no extraction or write)
corrected runner design and self-test
runner hash review
new disposable target provisioning preparation
separate provisioning authorization
target provisioning evidence
separate restore execution authorization
one controlled restore attempt
read-only post-restore verification
restore evidence
target retirement
~~~

Every line is a separate gate. Selection of Route B does not authorize any of
those later actions and does not permit them to be collapsed into one step.

## 5. Legacy attempt and runner quarantine

~~~text
legacy_external_runner_call_count=3
legacy_first_call_classification=PRE_EXECUTION_ABORT
legacy_second_call_classification=PRE_EXECUTION_ABORT
legacy_third_call_classification=PRE_EXECUTION_ABORT
legacy_third_call_stop_code=BACKUP_DIRECTORY_ROOT_MISMATCH
legacy_restore_execution_started=false
legacy_backup_restoreability_verified=false
legacy_target_reuse_allowed=false
legacy_runner_v1_reuse_allowed=false
legacy_runner_v2_reuse_allowed=false
legacy_authorization_reuse_allowed=false
legacy_attempt_state_reuse_allowed=false
legacy_execution_evidence_reuse_allowed=false
legacy_fourth_external_runner_call_authorized=false
fresh_chain_restore_attempt_budget=1
fresh_chain_restore_attempt_authorized=false
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
~~~

`BACKUP_DIRECTORY_ROOT_MISMATCH` remains a pre-execution contract failure, not
proof that the backup is corrupt and not proof that it is restorable. The new
chain must investigate the archive/root contract before any runner design.

## 6. Immediate next gate

~~~text
ready_for_separate_archive_root_contract_investigation_preparation=true
archive_root_contract_investigation_scope=LIST_ONLY_NO_EXTRACTION_NO_WRITE
archive_root_contract_investigation_authorized=false
archive_root_contract_investigation_started=false
backup_archive_listing_invoked=false
backup_archive_extracted=false
backup_archive_modified=false
backup_archive_repackaged=false
backup_original_bytes_preserved=true
new_restore_runner_design_authorized=false
new_restore_runner_authorized=false
new_disposable_target_authorized=false
new_restore_execution_authorized=false
~~~

A later, separately authorized investigation package may define sanitized
list-only observations such as wrapper depth, directory root, member naming,
TOC location, expected format, and source-client compatibility. It must not
extract, rewrite, repackage, restore, or upload the backup.

## 7. Repository-package boundary

~~~text
repository_only=true
network_access=false
repository_apply_authorized=false
git_stage_authorized=false
git_commit_authorized=false
git_push_authorized=false
database_connection=false
database_write=false
restore_execution=false
pg_restore_invoked=false
psql_invoked=false
alembic_invoked=false
migration_created=false
migration_executed=false
restore_runner_created=false
restore_runner_modified=false
locked_runner_invoked=false
application_deployment=false
render_target_created=false
render_target_deleted=false
external_target_mutated=false
corrected_migration_implementation_authorized=false
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
production_migration_authorized=false
production_migration_executed=false
~~~

The package may be designed and validated locally. Applying it to the
authoritative repository, staging it, committing it, pushing it, and relying on
post-push CI each require their own later authorization or operator action.

## 8. Production and clinical hard gates retained

~~~text
database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false
production_auto_deploy_verified=false
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

## 9. Fail-closed stop conditions

Keep HOLD and stop if the Git baseline, isolated refs, CI Gate #192, protected
hashes, locked runner, active migration absence, or repository cleanliness
differs. Stop if Route B is not explicitly selected or if governance-route
approval is interpreted as external execution authority.

Stop on any attempt to reuse or recreate the retired target; reuse either old
runner; reuse the three-call authorization chain; issue another legacy restore
call; list, extract, modify, repackage, or upload the backup in this package;
create a target or runner; connect to a database; invoke restore, SQL, Alembic,
or the locked runner; create 0010; deploy either application; delete another
resource; expose credentials; enable a dangerous feature flag; or begin P0-05,
P0-06, or any R1/R2/R3 feature.

## 10. Exit meaning and next decision

Passing this package means only:

~~~text
exit_fresh_restore_governance_route_b_approved=true
exit_ready_for_separate_archive_root_contract_investigation_preparation=true
exit_archive_root_contract_investigation_authorized=false
exit_new_restore_runner_authorized=false
exit_new_disposable_target_authorized=false
exit_new_restore_execution_authorized=false
exit_backup_restoreability_verified=false
exit_disposable_restore_rehearsal_complete=false
exit_p0_04_execution_authorized=false
exit_staging_0010_apply_authorized=false
~~~

The next action is a separate repository-only preparation for archive/root
contract investigation. No list operation or external action is authorized by
this decision record.
