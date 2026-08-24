# PMAI-P0-04 Fresh Disposable Target Contract Rebind V4

## Controlled repository scope

This record rebinds the active repository governance pointer from the retired V3 disposable target contract to the reviewed V4 contract. It is repository-only evidence. It neither identifies nor creates a provider resource and it grants no external execution authority.

stage_id=PMAI-P0-04
substage=FRESH_DISPOSABLE_TARGET_CONTRACT_REBIND_V4
work_bundle=PMAI-P0-04-DISP-TARGET-REBIND-V4
repository=pet-med-ai/Pet-med-ai
base_branch=main
base_commit=b8d79ff3af32b1452672cdeb766e2e35b72c1213
risk_lane=YELLOW_REPOSITORY_ONLY
repository_only=true
changed_path_scope=EXACT_9_PATHS
maximum_changed_path_count=9

## Trusted V3 retirement input

The prior V3 contract is retained byte-for-byte as historical evidence. Its retirement and absence decision was made from the separately reviewed operator evidence set. This repository package carries the exact decision token and evidence digests; it does not claim to re-perform a provider-side absence check.

prior_v3_target_logical_name=pet-med-ai-db-p0-04-fresh-disposable-restore-v3-ohio
prior_v3_target_contract_identity_sha256=e57fbfce3e490cdf185f83e9e376b20fe0ef665fbe293a512a6298d8a6420744
prior_v3_target_state=RETIRED_ABSENCE_VERIFIED_HISTORICAL
prior_v3_absence_evidence_required=true
prior_v3_absence_evidence_result=PASS_PMAI_P0_04_V3_TARGET_RETIREMENT_AND_ABSENCE_READ_ONLY_EVIDENCE_V1
prior_v3_absence_evidence_source=EXTERNAL_OPERATOR_READ_ONLY_EVIDENCE_DECISION_TOKEN
prior_v3_absence_evidence_reverified_by_repository_validator=false
prior_v3_absence_evidence_raw_artifacts_stored=false
preserve_v3_historical_files_byte_exact=true

## Reviewed V4 contract identity

The V4 identity is reused from the prior approved review record. It is an opaque reviewed identity value. This package checks the exact value and the exact 20-field contract but deliberately makes no canonical hash-recalculation claim.

review_record_id=PMAI-P0-04-FDTP-AUTH-REVIEW-V4-20260823
reviewed_v4_target_logical_name=pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio
reviewed_v4_target_contract_identity_sha256=e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529
reviewed_v4_contract_identity_source=PRIOR_APPROVED_REVIEW_RECORD
reviewed_v4_contract_identity_reused_from_prior_review=true
reviewed_v4_contract_identity_is_opaque=true
reviewed_v4_contract_hash_recalculation_claim=false
reviewed_v4_contract_exact_field_count=20
provider_account_scope=PROJECT_OWNER_EXISTING_RENDER_ACCOUNT

## Exact reviewed contract fields

target_logical_name=pet-med-ai-db-p0-04-fresh-disposable-restore-v4-ohio
target_provider=Render
target_region=Ohio (US East)
target_engine_family=PostgreSQL
target_server_major_version=18
target_instance_type=Basic-256mb
target_storage_gb=1
target_storage_autoscaling=false
target_read_replica_count=0
target_high_availability=false
target_connection_pooling=false
target_application_attachment_count=0
target_network_scope=UNATTACHED_NO_APPLICATION_TRAFFIC
target_external_access_scope=EXECUTION_TIME_SINGLE_OPERATOR_EGRESS_ALLOWLIST_ONLY
target_cost_ceiling_usd=1.00
target_max_lifetime_hours=72
target_delete_within_hours_after_required_evidence=24
target_must_be_new=true
target_must_be_empty=true
target_provisioning_authorized=false

## Repository pointer transition

The active pointer now names V4 only as the active repository contract. The external binding state remains unbound. The locked baseline and active pointer are package members protected by the manifest and validator chain.

target_contract_rebind_recorded=true
active_repository_contract_version=V4
active_repository_contract_identity_sha256=e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529
prior_v3_contract_remains_historical=true
target_selected=false
target_created=false
external_resource_identity_bound=false
raw_provider_resource_identifier_recorded=false
provider_url_recorded=false
credential_material_recorded=false

## Fail-closed execution boundary

Any mismatch in the base commit, exact path set, V3 anchors, evidence token, V4 review record, opaque identity, 20-field contract, package manifest, active pointer, central validator hook, or protected CI entrypoint is a NO-GO. Any external resource action requires a new and separate authorization.

external_target_provisioning_authorized=false
render_control_plane_access_performed=false
render_settings_change=false
database_connection=false
data_read_write_export=false
runner_execution=false
restore_execution=false
migration_execution=false
deployment=false
target_deletion=false
production_staging_v3_resource_operations=false
other_resource_operations=false
manual_retry=false
automatic_retry=false

decision=PASS_REPOSITORY_CONTRACT_REBIND_RECORD_NO_EXTERNAL_AUTHORITY
sole_next_subject=FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V4

## Result

The repository has a reviewable V4 governance contract and an explicit unbound pointer. No provider control-plane access, database connection, target selection, target creation, restore, migration, deployment, deletion, or retry is represented by this record.
