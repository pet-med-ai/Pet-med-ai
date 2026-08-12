# Treatment Framework Signed Review State Persistence Migration 0010
## Archive Root Contract Investigation Execution Evidence V1

This repository-only package records the sanitized result of the single
authorized metadata-only archive/root investigation. The investigation has
already occurred outside this package. This package does not open, list, or
read the archive, retry the investigation, create or execute another
investigator, create a target or runner, connect to a database, restore data,
create or execute migration 0010, deploy, delete, stage, commit, or push.

## 1. Canonical evidence decision

~~~text
stage_id=PMAI-P0-04
substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1
stage_status=IN_PROGRESS
package_status=EXECUTION_EVIDENCE_RECORD_ONLY
evidence_status=COMPLETE_SINGLE_METADATA_ATTEMPT_HOLD
evidence_record_id=PMAI-P0-04-ARCI-EXEC-EVID-V1-20260811
investigation_execution_performed=true
investigation_process_completed=true
investigation_exit_code=0
archive_listing_attempt_budget=1
archive_listing_attempts_consumed=1
archive_listing_attempts_remaining=0
automatic_retry=false
manual_retry_authorized=false
additional_archive_listing_attempt_authorized=false
root_contract_resolved=false
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
next_action=SEPARATE_STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_REQUIRED_BEFORE_ANY_NEW_INVESTIGATION
~~~

Exit code zero means the fixed investigator completed its authorized scan and
emitted a structurally valid sanitized result. It does not mean the root
contract passed. The controlling result is `root_contract_resolved=false` and
the HOLD decision.

## 2. Repository and authorization baseline

~~~text
authorization_review_commit=7e5e4008ed3613b566aebcf1fc0d12e527ac816c
authorization_review_commit_parent=f521520f96ab28f1a6e696b60fc8f06e4a2eda69
local_main_at_evidence_entry=7e5e4008ed3613b566aebcf1fc0d12e527ac816c
origin_main_at_evidence_entry=7e5e4008ed3613b566aebcf1fc0d12e527ac816c
github_ci_gate_number=195
github_ci_gate_status=PASS
github_ci_gate_commit=7e5e4008ed3613b566aebcf1fc0d12e527ac816c
prior_ci_sha256=cfc3619b6847018a074a06fd0020a06c9443595e0fdf3f670d462f9c4dfe6560
final_ci_sha256=e0497f7ba925d753728cc8ae364efcec95e995b2212648c2eda4ed57a4f4fccb
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
repository_clean_before_investigation=true
repository_clean_after_investigation=true
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
active_0010_migration_file_count=0
baseline_source=OPERATOR_COMMIT_PUSH_OUTPUT_GITHUB_CI_GATE_195_SCREENSHOT_AND_SANITIZED_TERMINAL_RESULT
~~~

GitHub CI Gate 195 proves the authorization-review repository commit. It is not
runtime, database, restore, or archive evidence. Production and staging values
below remain accepted handoff baselines and were not rechecked.

## 3. Consumed one-time authorization

~~~text
authorization_record_id=PMAI-P0-04-ARCI-AUTH-V1-20260811
execution_confirmation_source=EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260811
authorization_scope=ONE_EXACT_ARCHIVE_ONE_METADATA_ONLY_ATTEMPT
execution_attempt_number=1
execution_authorization_was_present=true
execution_authorization_consumed=true
one_time_execution_confirmation_was_present=true
current_archive_root_contract_investigation_execution_authorized=false
current_archive_listing_attempt_authorized=false
authorization_reuse_allowed=false
investigator_reexecution_allowed=false
investigator_v2_creation_authorized=false
investigator_v2_execution_authorized=false
corrected_restore_runner_design_authorized=false
~~~

The one-time confirmation cannot be reused. The completed metadata scan consumes
the only approved attempt even though the process exited zero and the structural
classification remained HOLD.

## 4. Exact archive and implementation binding

~~~text
approved_backup_file_name=2026-08-02T15_16Z.dir.tar.gz
approved_backup_file_size_bytes=22299
approved_backup_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7
approved_archive_sha256_match=true
investigation_implementation_path=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V1.py.txt
investigation_implementation_sha256=2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab
listing_tool_identity=PYTHON_STDLIB_TARFILE_METADATA_SCAN
listing_tool_version=3.9.6
outer_container_classification=GZIP_TAR
archive_external_path_repository_value=FORBIDDEN
raw_archive_bytes_repository_value=FORBIDDEN
raw_member_names_repository_value=FORBIDDEN
~~~

The exact external path, archive bytes, and raw member names are not retained in
Git. The approved archive hash matched before member metadata was classified.

## 5. Sanitized investigation result

~~~text
sanitized_result_canonicalization=EXACT_UTF8_JSON_SORTED_KEYS_COMPACT_NO_TRAILING_NEWLINE
sanitized_investigation_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
sanitized_result_field_count=33
~~~

~~~json
{"all_members_contained_by_common_root":false,"approved_archive_sha256_match":true,"archive_member_count":29,"archive_modified":false,"archive_uncompressed_size_bytes":196874,"authorization_record_id":"PMAI-P0-04-ARCI-AUTH-V1-20260811","automatic_retry":false,"case_collision_count":0,"common_root_sha256":"","decision":"HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED","directory_entry_count":3,"duplicate_normalized_member_count":0,"investigation_implementation_sha256":"2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab","listing_tool_identity":"PYTHON_STDLIB_TARFILE_METADATA_SCAN","listing_tool_version":"3.9.6","member_extraction_performed":false,"member_name_set_sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","member_payload_read":false,"normalized_path_violation_count":29,"outer_container_classification":"GZIP_TAR","raw_external_path_emitted":false,"raw_member_names_emitted":false,"regular_file_count":26,"restore_execution":false,"restore_input_kind_classification":"AMBIGUOUS_OR_UNSUPPORTED","root_contract_resolved":false,"single_common_root_present":false,"stop_code":"STRUCTURAL_PREDICATE_MISMATCH","toc_dat_candidate_count":0,"toc_dat_relation_category":"NONE_OR_AMBIGUOUS","top_level_component_count":0,"unsafe_or_special_member_count":0,"wrapper_depth":0}
~~~

Only this sanitized JSON line is admitted as execution evidence. It contains no
external archive path, raw member name, database secret, connection value, or
member payload.

## 6. Structural classification facts

~~~text
archive_member_count=29
archive_uncompressed_size_bytes=196874
regular_file_count=26
directory_entry_count=3
unsafe_or_special_member_count=0
normalized_path_violation_count=29
duplicate_normalized_member_count=0
case_collision_count=0
top_level_component_count=0
single_common_root_present=false
common_root_sha256_present=false
all_members_contained_by_common_root=false
wrapper_depth=0
toc_dat_candidate_count=0
toc_dat_relation_category=NONE_OR_AMBIGUOUS
member_name_set_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
restore_input_kind_classification=AMBIGUOUS_OR_UNSUPPORTED
stop_code=STRUCTURAL_PREDICATE_MISMATCH
~~~

All 29 metadata entries failed the fixed normalization predicate, leaving no
accepted top-level component or `toc.dat` candidate. The empty-set member-name
hash does not mean the archive is empty; it means the fixed normalized set was
empty.

## 7. Evidence and inference boundary

~~~text
backup_corruption_established=false
backup_safety_established=false
backup_restoreability_established=false
structural_predicate_mismatch_cause_resolved=false
leading_dot_component_hypothesis_status=UNVERIFIED_INFERENCE_ONLY
raw_member_name_followup_performed=false
additional_metadata_scan_performed=false
corrected_predicate_selected=false
route_b_fresh_restore_governance_decision_retained=true
~~~

The uniform rejection may be consistent with a representation such as a leading
dot component, but the sanitized evidence cannot identify the exact cause. That
hypothesis is not a finding and must not be used to bypass a new governance
decision. The result also does not prove that the backup is corrupt.

## 8. Recorded execution safety boundary

~~~text
investigation_archive_file_opened=true
investigation_backup_archive_listing_invoked=true
investigation_backup_archive_member_headers_read=true
investigation_backup_archive_member_payload_read=false
investigation_backup_archive_extracted=false
investigation_backup_archive_copied=false
investigation_backup_archive_uploaded=false
investigation_backup_archive_modified=false
investigation_backup_archive_repackaged=false
investigation_raw_member_names_emitted=false
investigation_raw_external_path_emitted=false
investigation_network_access=false
investigation_database_connection=false
investigation_database_write=false
investigation_restore_execution=false
investigation_pg_restore_invoked=false
investigation_psql_invoked=false
investigation_alembic_invoked=false
investigation_target_created=false
investigation_runner_created=false
investigation_runner_modified=false
investigation_locked_runner_invoked=false
investigation_migration_created=false
investigation_migration_executed=false
investigation_application_deployment=false
investigation_resource_deleted=false
~~~

The three true access markers describe the already completed authorized
metadata attempt. They are evidence facts, not authority for another access.

## 9. Repository-package boundary

~~~text
repository_only=true
network_access=false
external_execution=false
package_archive_file_opened=false
package_backup_archive_listing_invoked=false
package_backup_archive_member_headers_read=false
package_backup_archive_member_payload_read=false
package_backup_archive_extracted=false
package_backup_archive_copied=false
package_backup_archive_uploaded=false
package_backup_archive_modified=false
package_backup_archive_repackaged=false
new_investigator_created=false
new_investigator_executed=false
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
render_target_created=false
render_target_deleted=false
application_deployment=false
resource_deleted=false
repository_apply_authorized=false
git_stage_authorized=false
git_commit_authorized=false
git_push_authorized=false
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
~~~

## 10. Subsequent structural-predicate review pointer

This point-in-time evidence remains unchanged. A later repository-only review
uses the published aggregate result and the inert V1 source without reopening
the backup or reusing the consumed authorization.

~~~text
subsequent_structural_predicate_review_entry_commit=992976b033f115f6872e53f9144c56387c4c4ecf
subsequent_structural_predicate_review_ci_gate=196
subsequent_structural_predicate_review_ci_status=PASS
subsequent_structural_predicate_review_selected_route=ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2
subsequent_new_investigation_authorized=false
~~~

## 11. Production and clinical hard gates retained

~~~text
production_runtime_baseline=d659aefb
staging_runtime_baseline=8d1dc881
production_database_revision_baseline=0009_diag_data
staging_database_revision_baseline=0009_diag_data
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

## 12. Mandatory stop conditions and next gate

The completed attempt must not be rerun. Keep HOLD on any proposal to reuse the
authorization, invoke the V1 investigator again, inspect raw member names,
perform another metadata scan, treat exit code zero as structural success,
infer corruption, create a corrected investigator, design or execute a restore
runner, create a target, connect to a database, restore, create or execute 0010,
deploy, delete, stage, commit, or push without the corresponding separate gate.

The only proposed next governance subject is a separate structural-predicate
review decision. This evidence package neither selects a corrected predicate
nor authorizes a new investigator or another archive access attempt.
