# PMAI-P0-04 Fresh Disposable Target Provisioning Execution Evidence V4

## Controlled evidence scope

This package records sanitized evidence for the already completed V4 disposable
target creation and the later successful service-level network lockdown. It
does not recreate the target, change Render, reveal a provider identifier, read
credentials, connect to a database, execute a runner, access a backup, restore,
migrate, deploy, or delete a resource.

```text
stage_id=PMAI-P0-04
substage=FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4
work_bundle=PMAI-P0-04-DISP-TARGET-PROVISION-EVID-V4
stage_status=IN_PROGRESS
package_status=V4_PROVISIONING_AND_NETWORK_LOCKDOWN_EXECUTION_EVIDENCE_RECORD_ONLY
evidence_status=COMPLETE_SANITIZED_TARGET_AVAILABLE_AND_PUBLIC_ACCESS_BLOCKED
evidence_record_id=PMAI-P0-04-FDTP-EXEC-EVID-V4-20260826
authorization_record_id=PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXECUTION_EVIDENCE_V4_REPOSITORY_PATCH_CONTROLLED_EXECUTION_V1
repository=pet-med-ai/Pet-med-ai
base_branch=main
base_commit=8d48f29930d2849de9f03cfeeb050a917dd3f6d5
base_tree_sha=72dee05677050d0004d4a5b955f206c0de1accd2
head_branch=pmai-p0-04-v4-provisioning-execution-evidence
risk_lane=YELLOW_REPOSITORY_PLUS_RENDER_READONLY_EVIDENCE
changed_path_scope=EXACT_9_PATHS
maximum_changed_path_count=9
maximum_commit_count=1
maximum_push_count=1
repository_patch_authorized=true
repository_commit_authorized=true
repository_push_authorized=true
pull_request_creation_authorized=false
merge_authorized=false
```

## Reviewed V4 contract binding

The reviewed contract identity remains an opaque approved value. It is not
recomputed and is not used as a substitute for the separately hashed provider
resource identity.

```text
review_record_id=PMAI-P0-04-FDTP-AUTH-REVIEW-V4-20260823
target_contract_identity_sha256=e1cba6bc207fa4654d3155ef4abd8d818d8fd4323ce990446bc680fd15522529
target_contract_identity_is_opaque=true
target_contract_hash_recalculation_claim=false
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
target_cost_projection_usd_max=0.63
target_max_lifetime_hours=72
target_delete_within_hours_after_required_evidence=24
target_must_be_new=true
target_must_be_empty=true
target_provisioning_authorized=false
```

The empty-at-creation value above is the reviewed contract requirement, not a
database readback. No database connection was made and current database
emptiness remains unverified.

## One-time external execution history

The first authorization stopped before target creation because the initial
network default did not match the reviewed envelope. The second authorization
created exactly one target and attempted the initial network save. That save
did not persist. A later separate user instruction and action-time confirmation
authorized one new save; its confirmation flow completed and the empty rule set
persisted after refresh.

```text
prior_v1_authorization_id=PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_EXTERNAL_EXECUTION_AUTHORIZATION_V4_CONTROLLED_EXECUTION_V1
prior_v1_final_state=STOPPED_NOT_EXECUTED_NETWORK_DEFAULT_CONTRACT_MISMATCH
prior_v1_target_creation_count=0
provisioning_authorization_id=PMAI_P0_04_FRESH_DISPOSABLE_TARGET_PROVISIONING_AND_NETWORK_LOCKDOWN_V4_CONTROLLED_EXECUTION_V2
provisioning_authorization_final_state=STOPPED_PARTIAL_EXECUTION_NETWORK_LOCKDOWN_SAVE_NOT_PERSISTED
target_created_under_v2=true
target_creation_count=1
first_network_save_persisted=false
network_lockdown_resave_authorization_source=EXPLICIT_USER_INSTRUCTION_AND_ACTION_TIME_CONFIRMATION_20260826
network_lockdown_resave_persisted=true
unapproved_retry_performed=false
network_lockdown_automatic_retry=false
authorization_reuse_allowed=false
```

## Sanitized provider identity and observations

The provider resource identifier was hashed in memory. The raw identifier,
dashboard address, connection values, username, password, environment values,
and provider response are not admitted to this package.

```text
target_service_identifier_sha256=3f0ed4e1cb1bbef10babb4d3ba7fa9ec03e048d7d30595389f30d0871bcdb4fe
external_resource_binding_state=BOUND_SANITIZED_HASH_ONLY
raw_target_service_identifier_recorded=false
target_dashboard_url_recorded=false
target_connection_url_recorded=false
target_credential_material_recorded=false
raw_provider_response_recorded=false
render_readonly_metadata_revalidation_performed=true
render_readonly_scope=EXACT_V4_TARGET_INFO_APPS_AND_NETWORK_ONLY
render_service_identifier_hash_only_binding=true
target_created=true
target_status=AVAILABLE
target_open_connection_count=0
target_open_connection_evidence_source=PRIOR_AND_POST_NETWORK_LOCKDOWN_RENDER_INFO_READBACK_20260826
target_database_connectivity_verified=false
target_database_empty_state_readback_verified=false
backup_restoreability_verified=false
```

The Render Apps page showed only optional deployment actions and no attached
application. The connection count was observed as zero in the surrounding
pre-lockdown and immediate post-lockdown Info readbacks. A later revalidation
did not render that table, but no non-zero connection observation exists.

## Final service-level network state

The empty service-level rule set is the dormant, stricter state. It does not
grant a future execution-time allowlist. A temporary single-operator `/32`
rule requires a separate authorization.

```text
initial_service_inbound_ip_rule_set=[0.0.0.0/0]
required_final_service_inbound_ip_rule_set=[]
observed_final_service_inbound_ip_rule_set=[]
final_public_external_access_blocked=true
network_lockdown_persisted_after_refresh=true
post_refresh_network_lockdown_verification=PASS
workspace_network_rules_modified=false
future_single_operator_allowlist_authorized=false
render_settings_change_performed_by_repository_package=false
```

Render explicitly reported both that external traffic was not allowed and
that all internet traffic was blocked by the PostgreSQL inbound rules.

## Hash-bound sanitized evidence

Each digest binds a canonical JSON object containing only public configuration,
booleans, bounded numbers, and non-secret decision tokens. Raw screenshots are
kept out of the repository.

```text
sanitized_configuration_evidence_sha256=d2ee629ebbb8e515bd13a67bf1fe5b7cb4ab31912714fd7188769d7b9dc4e434
sanitized_availability_evidence_sha256=20ba1c1d42e198da706d99774110e6d92816453fa9dc7fec4dd5163345f45f62
sanitized_network_lockdown_evidence_sha256=882c28ea6cf259cd64bf2c61020685d2f36862dae62dde54f6b8384df77cc1e2
sanitized_lifecycle_evidence_sha256=b27e47dded2440ac216f76e62d3efa2219cafd4789aaea833ba6a09507dfa083
sanitized_execution_history_evidence_sha256=af8268416eeb00924893707c66154b7bbb57b31f50258f8f94df8e158006bc58
sanitized_external_evidence_count=5
external_evidence_storage=HASH_ONLY_REPOSITORY_BINDING
raw_screenshot_repository_value=FORBIDDEN
```

## Current fail-closed boundary

```text
render_control_plane_write=false
render_settings_change=false
credential_or_connection_value_access=false
database_connection=false
database_read_write_export=false
runner_import_or_execution=false
backup_access=false
restore_execution=false
pg_restore_or_psql_execution=false
migration_creation_or_execution=false
deployment=false
target_deletion=false
production_staging_v3_resource_operations=false
library_master_directory_update=false
manual_retry=false
automatic_retry=false
```

The existing V3 activation authorization and SRBE baseline remain immutable
historical records and still name the retired V3 contract. They cannot be used
for V4. The next gate must create a successor repository-only rebind package
before any temporary allowlist, credential access, database connection, or
runtime evidence collection.

```text
decision=PASS_V4_PROVISIONING_AND_NETWORK_LOCKDOWN_EXECUTION_EVIDENCE_RECORDED
sole_next_subject=ACTIVE_RESTORE_RUNNER_V3_ACTIVATION_AND_SRBE_CONTRACT_REBIND_V4_PREPARATION
```

## Result

The V4 target is bound to the repository by a sanitized provider-identity hash,
its reviewed public configuration, its Available state, and its persistent
block-all service-level network state. This package grants no runtime authority.
