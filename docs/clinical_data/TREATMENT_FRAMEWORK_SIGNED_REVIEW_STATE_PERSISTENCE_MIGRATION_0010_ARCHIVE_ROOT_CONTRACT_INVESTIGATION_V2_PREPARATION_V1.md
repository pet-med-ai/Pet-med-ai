# Treatment Framework Signed Review State Persistence Migration 0010 Archive Root Contract Investigation V2 Preparation V1

## 1. Purpose and decision

This repository-only package prepares an inert V2 metadata-investigation design
after the published Structural Predicate Review Governance Decision V1. It does
not access the approved backup and does not authorize an investigation attempt.

~~~text
stage_id=PMAI-P0-04
substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_V1
package_status=V2_INERT_DESIGN_PREPARATION_ONLY
preparation_record_id=PMAI-P0-04-ARCI-V2-PREP-V1-20260812
current_substage=STRUCTURAL_PREDICATE_REVIEW_GOVERNANCE_DECISION_V1
proposed_substage=ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_PREPARATION_V1
selected_route=ROUTE_B_REBUILD_CORRECTED_METADATA_INVESTIGATION_CHAIN_V2
selected_route_status=RETAINED
decision=GO_TO_SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW
next_action=SEPARATE_ARCHIVE_ROOT_CONTRACT_INVESTIGATION_V2_AUTHORIZATION_REVIEW_REQUIRED
~~~

The decision authorizes preparation only. The V2 source remains a `.py.txt`
artifact with execution disabled. A future authorization review must separately
approve any implementation change, implementation hash, one-time record, exact
archive, attempt budget, and operator command.

## 2. Published baseline

~~~text
structural_predicate_decision_commit=b5eaeb7b1a36b5fcb54734bda5886d93d56576e3
structural_predicate_decision_parent=992976b033f115f6872e53f9144c56387c4c4ecf
local_main_at_preparation_entry=b5eaeb7b1a36b5fcb54734bda5886d93d56576e3
origin_main_at_preparation_entry=b5eaeb7b1a36b5fcb54734bda5886d93d56576e3
github_ci_gate_number=197
github_ci_gate_status=PASS
github_ci_gate_commit=b5eaeb7b1a36b5fcb54734bda5886d93d56576e3
prior_ci_sha256=39a1f75ecfe5a79dc9293d93b1f562f07146664ad020a03c8cb79a42306ff3bf
final_ci_sha256=d6cae61ff10138ae48be1832291aeefc19442ac68b323d4153939d1fbf19ea2d
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
inert_investigator_v1_sha256=2b99a7446fbd5509e22c9fa5f6cb18eca920711208aa37fb4af568fd21f6faab
inert_investigator_v2_sha256=0d6303b0a5fc63d8231669b8a5d396d67b645120f9ac5421977cb79f3f6e8837
sanitized_v1_result_sha256=c8c68cbe00ebeff2eae75fb6c1b375af8e867b869e68378e43b9188b1a2b6893
active_0010_migration_file_count=0
user_direction_source=EXPLICIT_USER_AUTHORIZATION_IN_CURRENT_CONVERSATION_20260812
~~~

GitHub CI Gate 197 proves the repository governance decision. It does not prove
the archive layout and does not grant a new archive listing attempt.

## 3. Controlling prior facts

~~~text
v1_investigation_execution_performed=true
v1_archive_listing_attempts_consumed=1
v1_archive_listing_attempts_remaining=0
v1_normalized_path_violation_count=29
v1_root_contract_resolved=false
v1_stop_code=STRUCTURAL_PREDICATE_MISMATCH
v1_decision=HOLD_PMAI_P0_04_ARCHIVE_ROOT_CONTRACT_UNRESOLVED
v1_predicate_coverage_gap_confirmed=true
observed_archive_leading_dot_prefix_confirmed=false
observed_archive_unwrapped_pg_directory_root_confirmed=false
toc_dat_absence_established=false
backup_corruption_established=false
structural_predicate_mismatch_cause_resolved=false
~~~

V2 preparation must not treat the plausible leading-`./` explanation as an
observed archive fact. It corrects coverage and diagnostic design without
changing the V1 evidence.

## 4. Inert V2 source contract

~~~text
v2_inert_design_created=true
active_v2_investigator_created=false
v2_source_storage_suffix=.py.txt
v2_source_execution_enabled=false
v2_source_default_mode=CONTRACT_ONLY
v2_source_contains_dormant_archive_access_path=true
v2_source_executed_during_preparation=false
v2_authorization_record_id=PENDING_SEPARATE_V2_AUTHORIZATION_REVIEW
v2_authorization_record_effective=false
v2_execution_requires_explicit_flag=true
v2_member_payload_read_allowed=false
v2_member_extraction_allowed=false
v2_archive_write_allowed=false
v2_automatic_retry_allowed=false
~~~

Even if the text were copied to a `.py` file, `--execute` stops at
`V2_EXECUTION_NOT_ENABLED` before prompting for or opening an archive. The
preparation validator uses AST and source inspection only and never imports or
executes the V2 source.

## 5. V2 logical-path predicate

V2 permits either a canonical relative member path or one conventional leading
`.` component. The leading component is removed only for logical classification.
It is not a general filesystem normalization operation.

An exact directory root marker `./` may be represented as an empty logical
tuple and counted separately. It is not included in the normalized member-name
set. More than one root marker prevents success.

~~~text
v2_allows_one_optional_leading_dot_prefix=true
v2_allows_directory_root_marker=true
v2_rejects_internal_dot_component=true
v2_rejects_parent_component=true
v2_rejects_absolute_path=true
v2_rejects_backslash=true
v2_rejects_control_character=true
v2_rejects_empty_component=true
v2_rejects_drive_prefix=true
v2_rejects_special_member_for_success=true
v2_general_normpath_forbidden=true
v2_path_payload_read_required=false
~~~

Repeated leading-dot components such as `././x` fail because one leading
component may be removed but the remaining internal `.` is still rejected.
Parent components are never removed or collapsed.

## 6. Root-layout classifications

V2 has two success candidates. Both require exactly one regular `toc.dat` at
the logical root, zero unsafe or rejected members, no normalized duplicates or
case collisions, at most one accepted root marker, and the approved member
count.

~~~text
v2_wrapped_root_classification=PG_DIRECTORY_ROOT_WRAPPED
v2_unwrapped_root_classification=PG_DIRECTORY_ROOT_UNWRAPPED
v2_toc_relation_required=IMMEDIATE_CHILD_OF_LOGICAL_ROOT
v2_wrapped_root_toc_shape=wrapper/toc.dat
v2_unwrapped_root_toc_shape=toc.dat
v2_toc_candidate_count_required=1
v2_root_marker_count_maximum=1
v2_duplicate_normalized_member_count_required=0
v2_case_collision_count_required=0
v2_unsafe_or_special_member_count_required=0
v2_normalized_path_violation_count_required=0
~~~

For a wrapped root, every accepted non-marker member must share the wrapper
component. For an unwrapped root, `toc.dat` itself is at the logical root. The
classification emits only a fixed category and a hashed logical-root
fingerprint; it does not emit raw member names.

## 7. Synthetic-only fixtures

The validator models the following invented paths without importing the V2
source and without reading any archive:

~~~text
synthetic_fixture_set_id=PMAI-P0-04-ARCI-V2-PREP-SYNTH-V1
synthetic_fixture_count=13
synthetic_fixtures_are_archive_evidence=false
synthetic_wrapped_canonical_expected=PASS
synthetic_wrapped_leading_dot_expected=PASS
synthetic_unwrapped_canonical_expected=PASS
synthetic_unwrapped_leading_dot_expected=PASS
synthetic_root_marker_expected=PASS_DIRECTORY_ONLY
synthetic_internal_dot_expected=REJECT
synthetic_repeated_leading_dot_expected=REJECT
synthetic_parent_expected=REJECT
synthetic_absolute_expected=REJECT
synthetic_backslash_expected=REJECT
synthetic_empty_component_expected=REJECT
synthetic_drive_prefix_expected=REJECT
synthetic_control_character_expected=REJECT
~~~

Passing synthetic fixtures proves only that the designed rules are internally
consistent. It does not predict the approved archive outcome.

## 8. Sanitized future-result contract

If a later execution is separately approved, V2 may emit only aggregate counts,
fixed classifications, fixed stop codes, and cryptographic digests. The result
must include a fixed-key normalization reason-count map so another aggregate
failure can be diagnosed without raw names.

~~~text
v2_sanitized_reason_counters_required=true
v2_member_name_set_sha256_required=true
v2_logical_root_fingerprint_sha256_required=true
v2_raw_member_names_output_allowed=false
v2_raw_external_path_output_allowed=false
v2_archive_path_echo_allowed=false
v2_member_payload_read_allowed_in_future=false
v2_member_extraction_allowed_in_future=false
v2_archive_modification_allowed_in_future=false
v2_restore_execution_allowed_in_future=false
~~~

## 9. Authorization state

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
v2_investigation_authorized=false
v2_archive_listing_attempt_authorized=false
v2_operator_command_authorized=false
v2_source_activation_authorized=false
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

## 10. Subsequent V2 authorization review handoff

~~~text
subsequent_v2_authorization_review_entry_commit=abeec6d7f1f5a592fc1435b4a370bd6cffb3a4ce
subsequent_v2_authorization_review_ci_gate=198
subsequent_v2_authorization_review_ci_status=PASS
subsequent_v2_authorized_candidate_sha256=ce4b0fc1421624b29309f8eeae750d712601821529102620faf5c1b2b75be4f6
subsequent_current_v2_investigation_authorized=false
~~~

This pointer records only the separately designed authorization-review entry
package. It does not modify this preparation's inert source, consume an attempt,
activate the reviewed candidate, or grant execution authority.

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

Keep HOLD on any proposal to execute or activate the V2 source, access the
backup, reuse V1 authorization, create a target or runner, connect to a
database, restore, create or execute 0010, deploy, delete, stage, commit, or
push without the corresponding separate authorization.

The only proposed next subject is a separate V2 Authorization Review. That
review may accept, reject, or require modification of this inert design; this
preparation does not predetermine execution authorization.
