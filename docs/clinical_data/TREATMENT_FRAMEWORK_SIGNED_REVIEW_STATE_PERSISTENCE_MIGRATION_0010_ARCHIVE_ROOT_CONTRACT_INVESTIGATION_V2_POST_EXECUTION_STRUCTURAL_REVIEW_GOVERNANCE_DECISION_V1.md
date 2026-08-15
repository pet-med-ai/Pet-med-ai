# Treatment Framework Signed Review State Persistence Migration 0010
## Archive Root Contract Investigation V2 Post-Execution Structural Review Governance Decision V1

This repository-only record reviews the published, sanitized V2 execution
evidence and the inert reviewed V2 source. It does not reopen, list, or read the
backup, execute an investigator, or convert an unobserved archive layout into a
fact.

## 1. Decision

~~~text
stage_id=PMAI-P0-04
substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1
package_status=GOVERNANCE_DECISION_ONLY
decision_record_id=PMAI-P0-04-V2-POST-SPR-GOV-DEC-V1-20260812
current_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_EXECUTION_EVIDENCE_V1
proposed_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_POST_EXECUTION_STRUCTURAL_REVIEW_GOVERNANCE_DECISION_V1
prior_route=ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2
selected_route=ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3
selected_route_status=APPROVED_GOVERNANCE_ONLY
decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION
next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V3_PREPARATION_REQUIRED
~~~

The selected route authorizes no V3 source, archive access, third metadata
attempt, target, runner, restore, migration, or deployment. It only permits a
later, separately authorized repository-only V3 preparation to be proposed.

## 2. Published baseline

~~~text
evidence_commit=da837e6eb35819457b340d9fe9fd3a4336dc6673
evidence_commit_parent=9f00393543ec435353d5deadc6c74972aed4f6c2
local_main_at_decision_entry=da837e6eb35819457b340d9fe9fd3a4336dc6673
origin_main_at_decision_entry=da837e6eb35819457b340d9fe9fd3a4336dc6673
github_ci_gate_number=200
github_ci_gate_status=PASS
github_ci_gate_commit=da837e6eb35819457b340d9fe9fd3a4336dc6673
prior_ci_sha256=7cba5137d959d9f37a5e4f7a70798ff5090fc130ead6ce9d124c457c9a682811
final_ci_sha256=87605430bdb1c71d8edf7cace65bc554f5e8e888e6e8eed807ccb33cc32dbe18
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
authorized_investigator_v2_sha256=ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6
sanitized_v1_investigation_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
sanitized_v2_investigation_result_sha256=3eef22eeab17779b4e5499f53c22caf22fd5d0fd7c107cdaca6cbb8926ebf028
active_0010_migration_file_count=0
user_direction_source=EXPLICIT_USER_AUTHORIZATION_TO_CONTINUE_FOLLOWUP_GOVERNANCE_20260812
~~~

Gate 200 proves the published V2 execution-evidence repository commit. It does
not prove the archive root contract, backup safety, or restoreability and does
not grant another archive access.

## 3. Controlling V2 evidence facts

~~~text
investigation_execution_performed=true
investigation_exit_code=0
v1_archive_listing_attempts_consumed=1
v2_archive_listing_attempt_budget=1
v2_archive_listing_attempts_consumed=1
v2_archive_listing_attempts_remaining=0
cumulative_archive_listing_attempts_consumed=2
cumulative_archive_listing_attempts_remaining=0
approved_archive_sha256_match=true
archive_member_count=29
archive_uncompressed_size_bytes=196874
regular_file_count=26
directory_entry_count=3
unsafe_or_special_member_count=0
accepted_leading_dot_prefix_count=28
accepted_root_marker_count=1
normalized_path_violation_count=0
duplicate_normalized_member_count=0
case_collision_count=0
toc_dat_candidate_count=1
toc_dat_relation_category=NONE_OR_AMBIGUOUS
root_layout_classification=NONE_OR_AMBIGUOUS
wrapper_depth=-1
root_contract_resolved=false
restore_input_kind_classification=AMBIGUOUS_OR_UNSUPPORTED
stop_code=V2_STRUCTURAL_PREDICATE_MISMATCH
evidence_decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
~~~

Exit code zero means only that the bounded V2 scan completed and emitted its
sanitized result. The HOLD decision and `root_contract_resolved=false` remain
controlling.

## 4. Static review of the V2 structural predicate

The reviewed V2 source remains a repository `.py.txt` artifact. This decision
parses and inspects the source without importing or executing it. V2 correctly
accepts one conventional leading `./` prefix and an explicit root marker. It
can classify only two successful `toc.dat` placements: an unwrapped logical
root and exactly one wrapper component.

~~~text
v2_static_source_review_performed=true
v2_investigator_executed_during_review=false
v2_normalization_coverage_gap_resolved=true
v2_optional_leading_dot_prefix_policy_present=true
v2_explicit_root_marker_policy_present=true
v2_unwrapped_root_classification_present=true
v2_single_wrapper_classification_present=true
v2_deep_wrapper_classification_present=false
v2_mixed_top_level_classification_present=false
v2_toc_normalized_depth_emitted=false
v2_shared_prefix_depth_emitted=false
v2_top_level_component_count_emitted=false
v2_member_depth_range_emitted=false
v2_structural_observability_gap_confirmed=true
~~~

The confirmed gap is in structural classification and sanitized observability,
not in path-safety normalization. V2 reports one candidate but does not emit
enough bounded relationship metadata to distinguish a deeper wrapper from
mixed top-level content or another unsupported arrangement.

## 5. Evidence and inference boundary

~~~text
aggregate_result_causal_attribution_possible=false
toc_dat_presence_established=true
toc_dat_at_logical_root_established=false
deep_wrapper_layout_hypothesis_status=PLAUSIBLE_BUT_UNVERIFIED
mixed_top_level_layout_hypothesis_status=PLAUSIBLE_BUT_UNVERIFIED
other_unsupported_layout_hypothesis_status=PLAUSIBLE_BUT_UNVERIFIED
actual_archive_layout_cause_resolved=false
backup_corruption_established=false
backup_safety_established=false
backup_restoreability_established=false
v2_structural_predicate_mismatch_cause_resolved=false
~~~

No route may treat `wrapper_depth=-1` as proof of a deep wrapper, mixed
top-level content, corruption, or missing data. The only established `toc.dat`
fact is the sanitized candidate count of one.

## 6. Route review

### Route A: declare the approved backup invalid or replace it

~~~text
route_a=ROUTE_A_DECLARE_BACKUP_INVALID_OR_REPLACE
route_a_status=REJECTED_AT_THIS_GATE
~~~

V2 did not establish corruption or unsafe member paths. Replacement may be
reviewed later, but it is not justified as a fact-based consequence here.

### Route B: proceed directly to runner or restore

~~~text
route_b=ROUTE_B_DIRECT_RUNNER_OR_RESTORE
route_b_status=REJECTED
~~~

The root contract and restore input kind remain unresolved. No target, runner,
database access, or restore is authorized.

### Route C: rebuild a depth-aware metadata investigation chain V3

~~~text
route_c=ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3
route_c_status=APPROVED_GOVERNANCE_ONLY
~~~

Route C starts with a separate repository-only preparation. It may specify
bounded numeric and enum outputs that classify logical depth without exposing
raw names. It may not create an active investigator or access the archive at
this gate.

### Route D: reuse or rerun V2

~~~text
route_d=ROUTE_D_REUSE_OR_RERUN_V2
route_d_status=REJECTED
~~~

The V2 one-time authorization and attempt are consumed. Automatic or manual
retry and authorization reuse remain forbidden.

## 7. Requirements for a future V3 preparation

These are design requirements only. They do not constitute a V3 implementation
or permission for another metadata attempt.

~~~text
v3_require_exactly_one_optional_leading_dot_prefix_policy=true
v3_require_explicit_root_marker_policy=true
v3_require_internal_dot_component_rejection=true
v3_require_parent_component_rejection=true
v3_require_absolute_path_rejection=true
v3_require_backslash_rejection=true
v3_require_control_character_rejection=true
v3_require_empty_component_rejection=true
v3_require_drive_prefix_rejection=true
v3_require_special_member_rejection=true
v3_require_toc_dat_normalized_depth_metric=true
v3_require_shared_prefix_depth_metric=true
v3_require_top_level_component_count_metric=true
v3_require_member_depth_min_max_metrics=true
v3_require_unwrapped_root_classification=true
v3_require_single_wrapper_classification=true
v3_require_deep_wrapper_classification=true
v3_require_mixed_top_level_classification=true
v3_require_toc_dat_at_logical_root=true
v3_require_bounded_numeric_outputs=true
v3_require_sanitized_enum_outputs=true
v3_require_raw_member_names_suppressed=true
v3_require_raw_external_path_suppressed=true
v3_require_member_payload_read_false=true
v3_require_extraction_false=true
v3_require_archive_write_false=true
v3_require_automatic_retry_false=true
v3_require_synthetic_depth_zero_fixture=true
v3_require_synthetic_depth_one_fixture=true
v3_require_synthetic_deep_wrapper_fixture=true
v3_require_synthetic_mixed_top_level_fixture=true
v3_require_separate_implementation_hash_review=true
v3_require_separate_one_time_execution_authorization=true
v3_require_explicit_single_attempt_budget=true
v3_predicate_requirements_selected=true
v3_predicate_implementation_selected=false
~~~

A later preparation must keep output categories bounded and must not emit raw
member names, raw prefixes, absolute paths, payloads, or secrets. It must fail
closed on unsafe paths, special members, duplicates, case collisions, excessive
depth, or ambiguous classification.

## 8. Current authorization state

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
new_investigator_created=false
new_investigator_activated=false
new_investigator_executed=false
investigator_v3_creation_authorized=false
investigator_v3_activation_authorized=false
investigator_v3_execution_authorized=false
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

## 9. Production and clinical hard gates retained

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

## 10. Mandatory stop conditions and next gate

Keep HOLD on any attempt to access the backup, list member headers, read member
payloads, reuse either consumed authorization, perform a third metadata scan,
create, activate, or execute V3, create a target or runner, connect to a
database, restore, create or execute migration 0010, deploy, delete, stage,
commit, or push without the corresponding separate authorization.

The only proposed next subject is Archive Root Contract Investigation V3
Preparation V1. This decision provides route selection and design requirements
only.

## 11. Subsequent V3 preparation pointer

This later pointer records a separately reviewed repository-only inert design.
It does not alter the V2 evidence or authorize V3 archive access or execution.

~~~text
subsequent_v3_preparation_entry_commit=98fe4d902d4b24bf13837aaf0ea7e5f7bdc9d1f3
subsequent_v3_preparation_ci_gate=201
subsequent_v3_preparation_ci_status=PASS
subsequent_v3_preparation_selected_route=ROUTE_C_REBUILD_DEPTH_AWARE_METADATA_INVESTIGATION_CHAIN_V3
subsequent_v3_investigation_authorized=false
~~~
