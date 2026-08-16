# Treatment Framework Signed Review State Persistence Migration 0010 Structural Predicate Review Governance Decision V1

## 1. Decision

This repository-only record reviews the V1 structural predicate against the
already published, sanitized execution evidence. It does not inspect the
backup again and does not convert an aggregate hypothesis into an archive fact.

~~~text
stage_id=PMAI-P0-04
substage=STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1
package_status=GOVERNANCE_DECISION_ONLY
decision_record_id=PMAI-P0-04-SPR-GOV-DEC-V1-20260812
current_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_EXECUTION_EVIDENCE_V1
proposed_substage=STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1
selected_route=ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2
selected_route_status=APPROVED_GOVERNANCE_ONLY
decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION
next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_REQUIRED
~~~

The selected route does not authorize a V2 implementation, another archive
listing, a target, a runner, a restore, migration 0010, or deployment. Each
requires its own later gate.

## 2. Published baseline

~~~text
evidence_commit=992976b033f115f6872e53f9144c56387c4c4ecf
evidence_commit_parent=7e5e4008ed3613b566aebcf1fc0d12e527ac816c
local_main_at_decision_entry=992976b033f115f6872e53f9144c56387c4c4ecf
origin_main_at_decision_entry=992976b033f115f6872e53f9144c56387c4c4ecf
github_ci_gate_number=196
github_ci_gate_status=PASS
github_ci_gate_commit=992976b033f115f6872e53f9144c56387c4c4ecf
prior_ci_sha256=80bd7f4e5186a33c3420fe4804a636c90e954d2d9349330803d0bb90bebc0870
final_ci_sha256=4b50f28b230853bd57a983a7034aff170e11531bd276964a8c4b93769803c80c
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
inert_investigator_v1_sha256=2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab
sanitized_investigation_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
active_0010_migration_file_count=0
user_direction_source=EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260812
~~~

GitHub CI Gate 196 proves the published execution-evidence repository commit.
It does not prove the backup root contract and does not grant external access.

## 3. Controlling evidence facts

~~~text
investigation_execution_performed=true
investigation_exit_code=0
archive_listing_attempt_budget=1
archive_listing_attempts_consumed=1
archive_listing_attempts_remaining=0
approved_archive_sha256_match=true
archive_member_count=29
archive_uncompressed_size_bytes=196874
regular_file_count=26
directory_entry_count=3
unsafe_or_special_member_count=0
normalized_path_violation_count=29
duplicate_normalized_member_count=0
case_collision_count=0
top_level_component_count=0
toc_dat_candidate_count=0
member_name_set_sha256=e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
root_contract_resolved=false
restore_input_kind_classification=AMBIGUOUS_OR_UNSUPPORTED
stop_code=STRUCTURAL_PREDICATE_MISMATCH
evidence_decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
~~~

Process exit code zero means that the sanitized result was emitted. It does not
mean that the structural predicate passed. The HOLD result remains controlling.

## 4. Static review of the V1 predicate

The reviewed V1 source is an inert `.py.txt` repository artifact. This decision
uses source inspection and synthetic path examples only; it does not import,
execute, modify, or replace the investigator.

The V1 `normalized_parts` logic splits the raw member name on `/` and rejects
every component equal to `.` or `..`. It contains no rule that canonicalizes a
single conventional leading `./` prefix. The V1 success predicate also requires
all accepted members to share one wrapper component and requires `toc.dat` to
be the immediate child of that wrapper.

~~~text
v1_static_source_review_performed=true
v1_investigator_executed_during_review=false
v1_predicate_coverage_gap_confirmed=true
v1_rejects_any_dot_component=true
v1_rejects_parent_component=true
v1_single_leading_dot_prefix_normalization_present=false
v1_unwrapped_pg_directory_root_classification_present=false
v1_requires_single_common_wrapper_root=true
v1_requires_toc_dat_under_wrapper=true
v1_sanitized_rejection_reason_counters_present=false
~~~

The confirmed coverage gap means V1 cannot classify a safe candidate merely
because its logical root is represented with a conventional leading `./`, and
it cannot classify an otherwise valid unwrapped logical directory root. This
is a statement about V1 coverage, not a statement about the approved backup.

## 5. Evidence and inference boundary

If every raw member name began with a leading `./`, the V1 predicate would
reject every member before computing top-level components or `toc.dat`
candidates. That conditional behavior is consistent with the aggregate result
of 29 violations, zero top-level components, zero `toc.dat` candidates, and an
empty normalized-name-set digest. Raw names were deliberately not emitted, so
the actual cause remains unknown.

~~~text
aggregate_result_causal_attribution_possible=false
leading_dot_prefix_hypothesis_status=PLAUSIBLE_BUT_UNVERIFIED
unwrapped_pg_directory_root_hypothesis_status=PLAUSIBLE_BUT_UNVERIFIED
observed_archive_leading_dot_prefix_confirmed=false
observed_archive_unwrapped_pg_directory_root_confirmed=false
toc_dat_absence_established=false
backup_corruption_established=false
backup_safety_established=false
backup_restoreability_established=false
structural_predicate_mismatch_cause_resolved=false
~~~

No route may reinterpret the aggregate counts as proof that `toc.dat` is
missing, that the backup is corrupt, or that the backup is safe to restore.

## 6. Route review

### Route A: stop and replace the approved backup

~~~text
route_a=ROUTE_A_STOP_AND_REPLACE_APPROVED_BACKUP
route_a_status=REJECTED_AT_THIS_GATE
~~~

The evidence does not establish corruption. Replacing the artifact now would
discard an unresolved but potentially usable backup without first correcting a
confirmed predicate coverage gap.

### Route B: rebuild a corrected metadata investigation chain V2

~~~text
route_b=ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2
route_b_status=APPROVED_GOVERNANCE_ONLY
~~~

Route B starts with a separate repository-only preparation. That later stage
may specify an inert V2 design and synthetic fixtures, but it may not execute
against the backup without a new review, a new implementation hash, a new
one-time authorization record, and an exact attempt budget.

### Route C: proceed directly to runner or restore

~~~text
route_c=ROUTE_C_DIRECT_RUNNER_OR_RESTORE
route_c_status=REJECTED
~~~

The root contract is unresolved, backup restoreability is unverified, and no
target or restore execution is authorized.

### Route D: rerun V1

~~~text
route_d=ROUTE_D_REUSE_V1_AUTHORIZATION_OR_RETRY
route_d_status=REJECTED
~~~

The V1 authorization and its single attempt are consumed. Reuse would violate
the evidence chain and would repeat a known coverage limitation.

## 7. Requirements for a future V2 preparation

These are design requirements only. They are not a V2 implementation and do
not authorize creation or execution of one.

~~~text
v2_require_exactly_one_optional_leading_dot_prefix_policy=true
v2_require_explicit_root_marker_policy=true
v2_require_internal_dot_component_rejection=true
v2_require_parent_component_rejection=true
v2_require_absolute_path_rejection=true
v2_require_backslash_rejection=true
v2_require_control_character_rejection=true
v2_require_empty_component_rejection=true
v2_require_drive_prefix_rejection=true
v2_require_special_member_rejection=true
v2_require_wrapped_root_classification=true
v2_require_unwrapped_root_classification=true
v2_require_toc_dat_at_logical_root=true
v2_require_sanitized_reason_counters=true
v2_require_raw_member_names_suppressed=true
v2_require_raw_external_path_suppressed=true
v2_require_member_payload_read_false=true
v2_require_extraction_false=true
v2_require_archive_write_false=true
v2_require_automatic_retry_false=true
v2_require_synthetic_fixture_validation=true
v2_require_separate_implementation_hash_review=true
v2_require_separate_one_time_execution_authorization=true
corrected_predicate_requirements_selected=true
corrected_predicate_implementation_selected=false
~~~

The later preparation must distinguish a logical path normalization rule from
a filesystem extraction rule. It must never use permissive normalization to
erase `..`, internal `.`, absolute paths, backslashes, drive prefixes, empty
components, control characters, or special member types.

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
new_investigator_executed=false
investigator_v2_creation_authorized=false
investigator_v2_execution_authorized=false
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

## 9. Subsequent V2 preparation pointer

The later preparation package starts from this published decision and remains
repository-only. These markers are a forward pointer, not an execution grant.

~~~text
subsequent_v2_preparation_entry_commit=b5eaeb7b1a36b5fcb54734bda5886d93d56576e3
subsequent_v2_preparation_ci_gate=197
subsequent_v2_preparation_ci_status=PASS
subsequent_v2_inert_source_sha256=0d6303b0a5fc63d8231669b8a5d396d67b645120f9ac5421977cb79f3f6e8837
subsequent_v2_investigation_authorized=false
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

Keep HOLD on any attempt to access the backup, list headers, read payloads,
reuse V1, create or execute V2, create a target or runner, connect to a
database, restore, create or execute 0010, deploy, delete, stage, commit, or
push without the corresponding separate authorization.

The only proposed next subject is the repository-only Archive Root Contract
Investigation V2 Preparation. This decision supplies requirements and route
selection only.
