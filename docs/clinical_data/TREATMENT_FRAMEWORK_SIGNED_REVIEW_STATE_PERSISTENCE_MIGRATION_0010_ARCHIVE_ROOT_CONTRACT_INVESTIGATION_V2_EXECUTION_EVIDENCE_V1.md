# Treatment Framework Signed Review State Persistence Migration 0010
## Archive Root Contract Investigation V2 Execution Evidence V1

This repository-only package records the sanitized result of the already
completed, single authorized V2 metadata-only archive/root investigation. It
does not reopen, list, or read the backup, retry the investigation, create,
activate, or execute an investigator, create a target or runner, connect to a
database, restore, create or execute migration 0010, deploy, delete, stage,
commit, or push.

## 1. Canonical evidence decision

~~~text
stage_id=PMAI-P0-04
substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1
stage_status=IN_PROGRESS
package_status=V2_EXECUTION_EVIDENCE_RECORD_ONLY
evidence_status=COMPLETE_SINGLE_V2_METADATA_ATTEMPT_HOLD
evidence_record_id=PMAI-P0-04-ARCI-V2-EXEC-EVID-V1-20260812
investigation_execution_performed=true
investigation_process_completed=true
investigation_exit_code=0
v1_archive_listing_attempts_consumed=1
v2_archive_listing_attempt_budget=1
v2_archive_listing_attempts_consumed=1
v2_archive_listing_attempts_remaining=0
cumulative_archive_listing_attempts_consumed=2
cumulative_archive_listing_attempts_remaining=0
automatic_retry=false
manual_retry_authorized=false
additional_archive_listing_attempt_authorized=false
root_contract_resolved=false
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
next_action=SEPARATE_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_REQUIRED_BEFORE_ANY_NEW_INVESTIGATION
~~~

Exit code zero means that the reviewed candidate completed the metadata scan
and emitted valid sanitized JSON. It does not mean the root contract passed.
The controlling result is `root_contract_resolved=false` and the HOLD decision.

## 2. Repository and authorization baseline

~~~text
authorization_review_commit=9f00393543ec435353d5deadc6c74972aed4f6c2
authorization_review_commit_parent=abeec6d7f1f5a592fc1435b4a370bd6cffb3a4ce
local_main_at_evidence_entry=9f00393543ec435353d5deadc6c74972aed4f6c2
origin_main_at_evidence_entry=9f00393543ec435353d5deadc6c74972aed4f6c2
github_ci_gate_number=199
github_ci_gate_status=PASS
github_ci_gate_commit=9f00393543ec435353d5deadc6c74972aed4f6c2
prior_ci_sha256=73d3665a7e7645f2fbd7acf043f76094cf1b05527a9500e1565a03b3ced1e0f2
final_ci_sha256=87605430bdb1c71d8edf7cace65bc554f5e8e888e6e8eed807ccb33cc32dbe18
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
repository_clean_before_investigation=true
repository_clean_after_investigation=true
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
active_0010_migration_file_count=0
baseline_source=OPERATOR_COMMIT_PUSH_OUTPUT_GITHUB_CI_GATE_199_SCREENSHOT_AND_SANITIZED_V2_TERMINAL_RESULT
~~~

Gate 199 proves only the authorization-review repository commit. It is not
runtime, database, restore, or archive evidence. Production and staging values
below remain accepted handoff baselines and were not rechecked.

## 3. Consumed V2 one-time authorization

~~~text
authorization_record_id=PMAI-P0-04-ARCI-V2-AUTH-V1-20260812
execution_confirmation_source=EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260812
authorization_scope=ONE_EXACT_ARCHIVE_ONE_V2_METADATA_ONLY_ATTEMPT
v2_attempt_number=1
cumulative_archive_listing_attempt_number=2
execution_authorization_was_present=true
execution_authorization_consumed=true
one_time_execution_confirmation_was_present=true
current_v2_investigation_authorized=false
current_v2_investigation_execution_authorized=false
current_v2_archive_listing_attempt_authorized=false
authorization_reuse_allowed=false
v2_investigator_reexecution_allowed=false
v3_investigator_creation_authorized=false
v3_investigator_execution_authorized=false
restore_runner_design_authorized=false
~~~

The one-time V2 confirmation cannot be reused. The completed metadata scan
consumes the only approved V2 attempt even though the process exited zero and
the structural classification remained HOLD.

## 4. Exact archive and implementation binding

~~~text
approved_backup_file_name=2026-08-02T15_16Z.dir.tar.gz
approved_backup_file_size_bytes=22299
approved_backup_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7
approved_archive_sha256_match=true
investigation_implementation_path=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_ARCHIVE_ROOT_CONTRACT_METADATA_INVESTIGATOR_V2_AUTHORIZED_CANDIDATE.py.txt
investigation_implementation_sha256=ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6
listing_tool_identity=PYTHON_STDLIB_TARFILE_METADATA_SCAN
listing_tool_version=3.9.6
outer_container_classification=GZIP_TAR
archive_external_path_repository_value=FORBIDDEN
raw_archive_bytes_repository_value=FORBIDDEN
raw_member_names_repository_value=FORBIDDEN
~~~

The exact external path, archive bytes, and raw member names are not retained in
Git. The approved archive hash matched before member metadata was classified.

## 5. Sanitized V2 investigation result

~~~text
sanitized_result_canonicalization=EXACT_UTF8_JSON_SORTED_KEYS_COMPACT_NO_TRAILING_NEWLINE
sanitized_v2_investigation_result_sha256=3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028
sanitized_v2_result_field_count=37
prior_v1_sanitized_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
~~~

~~~json
{"all_members_contained_by_logical_root":false,"approved_archive_sha256_match":true,"archive_member_count":29,"archive_modified":false,"archive_uncompressed_size_bytes":196874,"authorization_record_id":"PMAI-P0-04-ARCI-V2-AUTH-V1-20260812","automatic_retry":false,"case_collision_count":0,"cumulative_archive_listing_attempt_number":2,"decision":"HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED","directory_entry_count":3,"duplicate_normalized_member_count":0,"implementation_sha256":"ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6","leading_dot_prefix_member_count":28,"listing_tool_identity":"PYTHON_STDLIB_TARFILE_METADATA_SCAN","listing_tool_version":"3.9.6","logical_root_fingerprint_sha256":"","member_extraction_performed":false,"member_name_set_sha256":"3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229","member_payload_read":false,"normalization_reason_counts":{"ACCEPTED_CANONICAL_RELATIVE":0,"ACCEPTED_LEADING_DOT_PREFIX":28,"ACCEPTED_ROOT_MARKER":1,"REJECT_ABSOLUTE_PATH":0,"REJECT_BACKSLASH":0,"REJECT_CONTROL_CHARACTER":0,"REJECT_DRIVE_PREFIX":0,"REJECT_EMPTY_COMPONENT":0,"REJECT_EMPTY_PATH":0,"REJECT_INTERNAL_DOT_COMPONENT":0,"REJECT_PARENT_COMPONENT":0,"REJECT_ROOT_MARKER_NON_DIRECTORY":0},"normalized_path_violation_count":0,"outer_container_classification":"GZIP_TAR","raw_external_path_emitted":false,"raw_member_names_emitted":false,"regular_file_count":26,"restore_execution":false,"restore_input_kind_classification":"AMBIGUOUS_OR_UNSUPPORTED","root_contract_resolved":false,"root_layout_classification":"NONE_OR_AMBIGUOUS","root_marker_count":1,"stop_code":"V2_STRUCTURAL_PREDICATE_MISMATCH","toc_dat_candidate_count":1,"toc_dat_relation_category":"NONE_OR_AMBIGUOUS","unsafe_or_special_member_count":0,"v2_attempt_number":1,"wrapper_depth":-1}
~~~

Only this sanitized JSON line is admitted as execution evidence. It contains no
external archive path, raw member name, database secret, connection value, or
member payload.

## 6. V2 structural classification facts

~~~text
archive_member_count=29
archive_uncompressed_size_bytes=196874
regular_file_count=26
directory_entry_count=3
unsafe_or_special_member_count=0
accepted_canonical_relative_count=0
accepted_leading_dot_prefix_count=28
accepted_root_marker_count=1
normalized_path_violation_count=0
duplicate_normalized_member_count=0
case_collision_count=0
leading_dot_prefix_member_count=28
root_marker_count=1
all_members_contained_by_logical_root=false
logical_root_fingerprint_sha256_present=false
wrapper_depth=-1
toc_dat_candidate_count=1
toc_dat_relation_category=NONE_OR_AMBIGUOUS
root_layout_classification=NONE_OR_AMBIGUOUS
member_name_set_sha256=3a509a2084dd279e644c95d83d77babe555f21de76950c1c092421952a75e229
restore_input_kind_classification=AMBIGUOUS_OR_UNSUPPORTED
stop_code=V2_STRUCTURAL_PREDICATE_MISMATCH
~~~

V2 accepted all 29 entries: 28 had the aggregate leading-dot-prefix reason and
one was the accepted root marker. This resolves the V1 predicate coverage gap
for that representation. A single `toc.dat` candidate was found, but the
sanitized result did not classify it as an immediate child of an accepted
logical root, so the root layout remains unresolved.

## 7. Evidence and inference boundary

~~~text
v1_leading_dot_predicate_coverage_gap_resolved_by_v2=true
observed_archive_leading_dot_prefix_count_confirmed=true
observed_archive_root_marker_count_confirmed=true
observed_toc_dat_candidate_count_confirmed=true
toc_dat_logical_depth_established=false
mixed_top_level_layout_established=false
deep_wrapper_layout_established=false
backup_corruption_established=false
backup_safety_established=false
backup_restoreability_established=false
v2_structural_predicate_mismatch_cause_resolved=false
raw_member_name_followup_performed=false
additional_metadata_scan_performed=false
corrected_v3_predicate_selected=false
new_governance_route_selected=false
~~~

The aggregate result proves the accepted reason counts and one `toc.dat`
candidate. It does not expose the candidate's depth or raw member layout, so it
cannot distinguish a deeper wrapper from mixed top-level content or another
unsupported arrangement. None of those possibilities may be promoted to fact.

## 8. Recorded completed execution boundary

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

The three true access markers describe the completed authorized V2 metadata
attempt. They are evidence facts and never grant authority for another access.

## 9. Repository evidence-package boundary

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
investigation_retry=false
new_investigator_created=false
new_investigator_activated=false
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

## 10. Production and clinical hard gates retained

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

## 11. Mandatory stop conditions and next gate

The completed V2 attempt must not be rerun. Keep HOLD on any proposal to reuse
either consumed authorization, access the archive again, inspect raw member
names, perform another metadata scan, treat exit code zero as structural
success, infer corruption or a specific hidden layout, create, activate, or
execute another investigator, design or execute a restore runner, create a
target, connect to a database, restore, create or execute 0010, deploy, delete,
stage, commit, or push without the corresponding separate gate.

The only proposed next governance subject is a separate V2 post-execution
structural review decision. This evidence package selects neither a new route
nor a corrected predicate and grants no additional archive access.

## 12. Subsequent V2 post-execution structural review pointer

This later pointer records a separately reviewed governance decision. It
does not alter the point-in-time V2 result or authorize V3 execution.

~~~text
subsequent_v2_post_execution_structural_review_entry_commit=da837e6eb35819457b340d9fe9fd3a4336dc6673
subsequent_v2_post_execution_structural_review_ci_gate=200
subsequent_v2_post_execution_structural_review_ci_status=PASS
subsequent_v2_post_execution_structural_review_selected_route=ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3
subsequent_v3_investigation_authorized=false
~~~
