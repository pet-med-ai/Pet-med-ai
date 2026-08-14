# Treatment Framework Signed Review State Persistence Migration 0010
## Archive Root Contract Investigation V3 Preparation V1

This repository-only package prepares an inert, depth-aware V3 metadata
investigation design after the published V2 post-execution structural review
decision. It does not access the approved backup and does not authorize a third
metadata attempt.

## 1. Purpose and decision

~~~text
stage_id=PMAI-P0-04
substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_V1
package_status=V3_INERT_DESIGN_PREPARATION_ONLY
preparation_record_id=PMAI-P0-04-ARCI-V3-PREP-V1-20260813
current_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1
proposed_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_V1
selected_route=ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3
selected_route_status=RETAINED
decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW
next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_AUTHORIZATION_REVIEW_REQUIRED
~~~

The decision authorizes preparation only. The V3 source remains a `.py.txt`
artifact with execution disabled. A later authorization review must separately
accept or reject the design, lock the exact reviewed hash, define a one-time
record and attempt budget, and produce a separate operator command.

## 2. Published baseline

~~~text
v2_post_structural_decision_commit=98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3
v2_post_structural_decision_parent=da837e6eb35819457b340d9fe9fd3a4336dc6673
local_main_at_preparation_entry=98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3
origin_main_at_preparation_entry=98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3
github_ci_gate_number=201
github_ci_gate_status=PASS
github_ci_gate_commit=98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3
prior_ci_sha256=e0497f7ba925d753728cc8ae364efcec95e995b2212648c2eda4ed57a4f4fccb
final_ci_sha256=9d02f180ffac1f69ab4f93f0d160bf82cb18205003703d042720b5fda421c7c9
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
authorized_investigator_v2_sha256=ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6
v3_inert_source_sha256=52fc4310065b0877152f592b4394c5f74d27e4812a6a30d71eb50cd94d0f4b55
sanitized_v1_investigation_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
sanitized_v2_investigation_result_sha256=3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028
active_0010_migration_file_count=0
user_direction_source=EXPLICIT_USER_AUTHORIZATION_FOR_V3_PREPARATION_DESIGN_AND_DRY_RUN_20260813
~~~

Gate 201 proves publication of the Route C governance decision. It does not
prove the archive layout, backup safety, or restoreability and grants no archive
access or third metadata attempt.

## 3. Controlling evidence and inference boundary

~~~text
v1_archive_listing_attempts_consumed=1
v2_archive_listing_attempts_consumed=1
cumulative_archive_listing_attempts_consumed=2
cumulative_archive_listing_attempts_remaining=0
v2_toc_dat_candidate_count=1
v2_toc_dat_relation_category=NONE_OR_AMBIGUOUS
v2_root_layout_classification=NONE_OR_AMBIGUOUS
v2_wrapper_depth=-1
v2_root_contract_resolved=false
v2_stop_code=V2_STRUCTURAL_PREDICATE_MISMATCH
v2_decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
v2_structural_observability_gap_confirmed=true
toc_dat_presence_established=true
actual_archive_layout_cause_resolved=false
backup_corruption_established=false
backup_restoreability_established=false
~~~

V3 preparation must not treat a deep wrapper, mixed top level, divergent
subtree, corruption, or missing data as an observed archive fact. The inert
design only adds bounded classifications needed to distinguish those cases if
a future attempt is separately approved.

## 4. Inert V3 source contract

~~~text
v3_inert_design_created=true
active_v3_investigator_created=false
v3_source_storage_suffix=.py.txt
v3_source_execution_enabled=false
v3_source_default_mode=CONTRACT_ONLY
v3_source_contains_dormant_archive_access_path=true
v3_source_executed_during_preparation=false
v3_authorization_record_id=PENDING_SEPARATE_V3_AUTHORIZATION_REVIEW
v3_authorization_record_effective=false
v3_execution_requires_explicit_flag=true
v3_member_payload_read_allowed=false
v3_member_extraction_allowed=false
v3_archive_write_allowed=false
v3_automatic_retry_allowed=false
v3_candidate_design_selected_for_authorization_review=true
v3_implementation_authorized=false
~~~

Even if the text were copied to a `.py` file, `--execute` stops at
`V3_EXECUTION_NOT_ENABLED` before prompting for or opening an archive. The
preparation validator uses AST and source inspection only; it never imports or
executes the V3 source.

## 5. V3 logical-path safety predicate

V3 retains V2 path safety and adds fixed upper bounds. Exactly one conventional
leading `.` component may be removed for logical classification. It is not a
general normalization operation.

~~~text
v3_allows_one_optional_leading_dot_prefix=true
v3_allows_directory_root_marker=true
v3_rejects_internal_dot_component=true
v3_rejects_parent_component=true
v3_rejects_absolute_path=true
v3_rejects_backslash=true
v3_rejects_control_character=true
v3_rejects_empty_component=true
v3_rejects_drive_prefix=true
v3_rejects_special_member_for_success=true
v3_rejects_excessive_component_depth=true
v3_rejects_excessive_member_name_bytes=true
v3_general_normpath_forbidden=true
v3_max_normalized_component_depth=64
v3_max_member_name_utf8_bytes=4096
~~~

Repeated leading-dot components, internal dot components, parent traversal,
absolute paths, backslashes, control characters, empty components, drive
prefixes, excessive depth, and excessive encoded name length fail closed.

## 6. Depth-aware sanitized metrics

V3 derives only aggregate counts, bounded depths, fixed enums, and digests from
member headers. It does not output raw names or root prefixes.

~~~text
v3_toc_dat_normalized_depth_metric=true
v3_shared_prefix_depth_metric=true
v3_top_level_component_count_metric=true
v3_member_depth_min_metric=true
v3_member_depth_max_metric=true
v3_wrapper_depth_metric=true
v3_numeric_metrics_bounded=true
v3_numeric_saturation_flag_required=true
v3_max_sanitized_count=30
v3_max_sanitized_uncompressed_size_bytes=1073741824
v3_logical_root_fingerprint_sha256_required=true
v3_member_name_set_sha256_required=true
v3_raw_root_prefix_output_allowed=false
~~~

`toc_dat_normalized_depth` is the number of normalized ancestor components
before the sole regular `toc.dat`. Member depths are normalized component
counts. Shared-prefix depth is calculated across regular files only. A future
result must expose saturation rather than emit an unbounded numeric value.

## 7. Root-layout classifications

~~~text
v3_unwrapped_root_classification=PG_DIRECTORY_ROOT_UNWRAPPED
v3_single_wrapper_classification=PG_DIRECTORY_ROOT_WRAPPED
v3_deep_wrapper_classification=PG_DIRECTORY_ROOT_DEEP_WRAPPED
v3_mixed_top_level_classification=MIXED_TOP_LEVEL
v3_divergent_subtree_classification=SHARED_TOP_LEVEL_DIVERGENT_SUBTREE
v3_ambiguous_classification=NONE_OR_AMBIGUOUS
v3_toc_relation_success=IMMEDIATE_CHILD_OF_IDENTIFIED_LOGICAL_ROOT
v3_toc_candidate_count_required=1
v3_root_marker_count_maximum=1
v3_duplicate_normalized_member_count_required=0
v3_case_collision_count_required=0
v3_unsafe_or_special_member_count_required=0
v3_normalized_path_violation_count_required=0
v3_all_members_contained_by_identified_root_required=true
~~~

For a wrapped or deeply wrapped root, accepted entries may be descendants of
the identified root or directory-only ancestors on the root path. A file that
escapes that root prevents success. An unwrapped `toc.dat` identifies the
archive logical root. Classification success never bypasses path-safety gates.

## 8. Synthetic-only fixtures

The validator models invented names independently from the candidate source.
No candidate import, candidate execution, archive access, or external input is
used.

~~~text
synthetic_fixture_set_id=PMAI-P0-04-ARCI-V3-PREP-SYNTH-V1
synthetic_fixture_count=18
synthetic_fixtures_are_archive_evidence=false
synthetic_unwrapped_depth_zero_expected=PG_DIRECTORY_ROOT_UNWRAPPED
synthetic_single_wrapper_depth_one_expected=PG_DIRECTORY_ROOT_WRAPPED
synthetic_deep_wrapper_depth_two_expected=PG_DIRECTORY_ROOT_DEEP_WRAPPED
synthetic_deep_wrapper_with_ancestor_directories_expected=PG_DIRECTORY_ROOT_DEEP_WRAPPED
synthetic_mixed_top_level_expected=MIXED_TOP_LEVEL
synthetic_divergent_subtree_expected=SHARED_TOP_LEVEL_DIVERGENT_SUBTREE
synthetic_missing_toc_expected=NONE_OR_AMBIGUOUS
synthetic_duplicate_toc_expected=NONE_OR_AMBIGUOUS
synthetic_root_marker_expected=PASS_DIRECTORY_ONLY
synthetic_internal_dot_expected=REJECT
synthetic_repeated_leading_dot_expected=REJECT
synthetic_parent_expected=REJECT
synthetic_absolute_expected=REJECT
synthetic_backslash_expected=REJECT
synthetic_empty_component_expected=REJECT
synthetic_drive_prefix_expected=REJECT
synthetic_excessive_depth_expected=REJECT
synthetic_control_character_expected=REJECT
~~~

Passing fixtures proves only internal design consistency. It does not predict
the approved archive outcome or consume an investigation attempt.

## 9. Sanitized future-result contract

~~~text
v3_sanitized_reason_counters_required=true
v3_sanitized_fixed_layout_enum_required=true
v3_raw_member_names_output_allowed=false
v3_raw_external_path_output_allowed=false
v3_archive_path_echo_allowed=false
v3_member_payload_read_allowed_in_future=false
v3_member_extraction_allowed_in_future=false
v3_archive_modification_allowed_in_future=false
v3_restore_execution_allowed_in_future=false
v3_single_attempt_budget_required=true
v3_expected_attempt_number=1
v3_expected_cumulative_attempt_number=3
~~~

The attempt numbers are a future contract requirement, not a granted budget.
A separate authorization review may reject or change the candidate before any
execution record becomes effective.

## 10. Current authorization state

~~~text
repository_only=true
network_access=false
external_execution=false
archive_file_opened=false
backup_archive_listing_invoked=false
backup_archive_member_headers_read=false
backup_archive_member_payload_read=false
backup_archive_extracted=false
backup_archive_copied=false
backup_archive_uploaded=false
backup_archive_modified=false
backup_archive_repackaged=false
investigation_retry=false
automatic_retry=false
manual_retry_authorized=false
additional_archive_listing_attempt_authorized=false
authorization_reuse_allowed=false
v3_investigation_authorized=false
v3_archive_listing_attempt_authorized=false
v3_operator_command_authorized=false
v3_source_activation_authorized=false
new_active_investigator_created=false
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

Keep HOLD on any proposal to access or list the backup, read member payloads,
reuse a consumed authorization, perform a third metadata scan, activate or
execute V3, create an active investigator, target, or runner, connect to a
database, restore, create or execute migration 0010, deploy, delete, stage,
commit, or push without the corresponding separate authorization.

The only proposed next subject after publication is a separate V3 Authorization
Review V1. That review may accept, reject, or require changes to this inert
candidate; this preparation does not predetermine execution authorization.

## 13. Subsequent V3 authorization-review pointer

This later pointer records a separately reviewed repository-only authorization record.
It does not alter the preparation facts or grant current archive access or execution.

~~~text
subsequent_v3_authorization_review_entry_commit=0e6dfdd876227d88003bebc9edd966f0821c0b41
subsequent_v3_authorization_review_ci_gate=202
subsequent_v3_authorization_review_ci_status=PASS
subsequent_v3_authorized_candidate_sha256=6800bc57c018ad17deb84b2c821baad4752e23f9aa432b01d64f9518737d5e14
subsequent_current_v3_investigation_authorized=false
~~~
