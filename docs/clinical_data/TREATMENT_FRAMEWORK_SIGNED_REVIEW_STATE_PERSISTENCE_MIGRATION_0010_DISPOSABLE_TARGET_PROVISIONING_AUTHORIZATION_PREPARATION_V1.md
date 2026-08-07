# Treatment Framework Signed Review State Persistence Migration 0010
## Disposable Target Provisioning Authorization Preparation V1

```text
stage_id=PMAI-P0-04
substage=DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1
stage_status=IN_PROGRESS
package_status=PREPARATION_ONLY
repository_only=true
evidence_completeness=PENDING_DRY_RUN_REVIEW_VALIDATION_AND_SEPARATE_AUTHORIZATION
decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW
```

## 1. Purpose and clinical value

This package defines the authorization boundary, target requirements,
validation gates, CI hook, and fail-closed stop conditions for a future
disposable restore target. It does not create or authorize that target.

The clinical value is indirect but necessary: the signed-review-state
persistence chain cannot proceed until backup restoreability is proven on
an isolated disposable target without changing production, staging source,
or the signed-review migration state.

## 2. Trusted entry baseline

```text
local_main=3124087025522892d9e9a887af977ab03e244c73
origin_main=3124087025522892d9e9a887af977ab03e244c73
main_parent=d659aefbdec6f4d212f6804dd1e600199ddd065b
isolated_branch=pmai-p0-04-staging-0010
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
production_runtime=d659aefb
staging_runtime=8d1dc881
production_database_revision=0009_diag_data
production_alembic_head=0009_diag_data
staging_database_revision=0009_diag_data
staging_alembic_head=0009_diag_data
approved_revision_contract=0010_signed_review_states
active_0010_migration_file_created=false
candidate_migration_deployed=false
baseline_source=operator_handoff_not_network_reverified_by_this_package
```

The runtime and database values above are the accepted entry baseline.
Because this package is repository-only and network-disabled, it does not
claim fresh Render or database verification.

## 3. Completed prerequisites retained by reference

```text
p0_03_authenticated_staging_smoke=COMPLETE
p0_03_evidence_sha256=da52b46466a65316331d420c809bc406e49dfa722b1b5875667e30db50eef213
deployment_isolation_verified=true
deployment_isolation_evidence_sha256=67fe12a4dc32e8edf91217693bf5ad85a7ab17fee107111aeafde66fabd4525b
fresh_post_p0_03_staging_backup_verified=true
backup_artifact_sha256=ea7b5a69231f50e54bd0a9da5b8eab4dde04d763853bef824564c4c66d2fa8a7
external_sanitized_evidence_sha256=a7af6ca2c0cba862bb7f6073f0866ef6dafcb20364ae64db6c9693fe622798e1
pg_restore_toc_sha256=6a1b20417a90fe9a5d954c4451e6fd3ebc7072407bc031e68b44c2b824e1ee1c
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
```

Raw backup bytes and external evidence JSON remain outside the repository.
This package must not read, copy, print, stage, commit, or upload them.

## 4. Scope

In scope:

- one consolidated governance document;
- a provisioning authorization checklist;
- a Go / No-Go record fixed at HOLD;
- a static test matrix;
- a repository validator and fail-closed CI hook;
- explicit requirements for a later, separately authorized disposable target;
- explicit deletion ownership and evidence requirements for that later target.

Out of scope:

- creating, restoring, connecting to, inspecting, or deleting any database;
- opening Render, clicking Restore Database, Manual Deploy, Redeploy, or Rollback;
- obtaining or copying a database connection string;
- invoking restore, SQL, migration, or locked-runner commands;
- creating an active 0010 migration;
- changing either environment revision;
- writing Case.treatment, prescription, dose, route, or frequency data;
- enabling real integrations, client-facing diagnosis, or outbound messaging.

## 5. Execution boundary

```text
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
active_0010_migration_file_created=false
```

## 6. Authorization state

```text
disposable_restore_governance_preparation_complete=true
disposable_target_provisioning_governance_ready=true
disposable_target_provisioning_authorization_preparation_complete=true
disposable_restore_target_provisioning_authorized=false
disposable_restore_execution_authorized=false
disposable_restore_database_created=false
disposable_restore_database_write_authorized=false
restore_runner_created=false
restore_runner_execution_enabled=false
restore_runner_executed_by_ci=false
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
corrected_migration_implementation_authorized=false
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
staging_0010_migration_executed=false
production_migration_authorized=false
production_migration_executed=false
```

No sentence, checkbox, CI pass, or dry-run result in this package may be
interpreted as authorization to provision or restore a target.

## 7. Future disposable target requirements

A later authorization review may consider provisioning only when every
item below is known and recorded in sanitized evidence:

1. Target purpose is limited to one restore rehearsal for PMAI-P0-04.
2. Target is a new disposable database, never production and never the
   staging source database.
3. Target identity, provider, region, engine family, server major version,
   plan, and owner are explicitly recorded without credentials.
4. Source and target version compatibility is reviewed before restore.
5. Network boundary and access principals are explicitly limited.
6. The target is empty and has no application traffic before restore.
7. A hard expiry or deletion deadline, deletion owner, and cleanup evidence
   format are approved before provisioning.
8. Cost ceiling and billing owner are known before provisioning.
9. Credentials are supplied only through the approved operator channel and
   are never printed, committed, or copied into evidence.
10. The exact backup is referenced only by its approved SHA-256 and external
    custody location; raw backup bytes remain outside the repository.
11. Restore execution is a later gate with a separate command review,
    operator authorization, stop conditions, and evidence capture plan.
12. Production and staging source remain read-only and unchanged throughout.

## 8. Required sanitized authorization evidence

The later authorization decision must record:

```text
authorization_record_id
target_logical_name
target_service_identifier_sanitized
provider
region
engine_family
target_server_major_version
source_server_major_version
restore_client_version
version_compatibility_review
target_is_disposable
production_target_excluded
staging_source_target_excluded
application_traffic_disabled
target_empty_before_restore
network_scope_reviewed
credential_handling_reviewed
cost_ceiling
expiry_at
deletion_owner
cleanup_evidence_required
backup_sha256
approver_role
operator_role
reviewed_at
decision
```

Forbidden evidence fields include connection URLs, passwords, secret keys,
raw environment dumps, raw backup contents, and unsanitized external JSON.

## 9. Production and clinical safety hard gates

```text
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
```

This repository-only package records these as unchanged hard gates. Runtime
verification remains a separate read-only activity and is not performed here.

## 10. Locked runner integrity

```text
locked_runner=scripts/run_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
EXECUTION_ENABLED=false
runner_execution_enabled=false
runner_executed_by_ci=false
```

The apply generator and validator may hash the runner read-only. They must
not edit, stage, execute, import, or otherwise activate it.

## 11. Fail-closed stop conditions

Stop immediately if any of the following is observed:

- repository branch, local main, origin/main, parent, or cleanliness differs
  from the trusted entry baseline before applying this package;
- either isolated-branch local or remote-tracking reference differs from the
  trusted entry baseline;
- the locked runner hash differs or its execution flag is not false;
- any active backend 0010 migration file exists;
- any target package file already exists or any unrelated file is changed;
- CI cannot be patched unambiguously or the validator is not fail-closed;
- any proposed artifact contains a credential, connection URL, or raw evidence;
- any authorization flag becomes true;
- any database, restore, migration, deploy, staging-data cleanup, external
  messaging, real integration, prescription, or dose action is requested;
- production or staging runtime/schema drift is later observed;
- a fourth manual deployment deviation is proposed or observed;
- dry-run bundle SHA-256 is missing, stale, or not explicitly reviewed.

On any stop, retain decision=HOLD and perform no compensating deployment,
database write, migration, or manual revision change.

## 12. Validation and exit gate

This preparation package passes only when:

- repository preflight is exact and clean;
- dry-run reports zero writes and a deterministic bundle SHA-256;
- the same reviewed bundle is applied without unrelated changes;
- the package validator passes;
- shell syntax, git diff checks, and the existing static CI gate pass;
- all provisioning, restore, migration, production, and clinical write
  authorizations remain false.

Passing these checks means only:

```text
ready_for_separate_disposable_target_provisioning_authorization_review=true
disposable_restore_target_provisioning_authorized=false
```

## 13. Next decision

```text
CURRENT=DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_PREPARATION_V1
NEXT=SEPARATE_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW
DECISION=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW
```

The next review must not be conflated with target creation. Target creation
remains a later operator action after explicit authorization.

## 14. Protected-hash compatibility rollover

The first repository-only apply correctly changed `scripts/ci_static_checks.sh`,
but the preceding PMAI-P0-04 validator still protected the prior CI hash and
required a single-validator target scope. Full static CI therefore stopped with
`NO-GO: protected hash scripts/ci_static_checks.sh` before this package could be
admitted to the existing protection chain.

This rollover is a compatibility correction inside the same preparation
package. It is not a provisioning, restore, migration, deployment, or clinical
write authorization.

```text
protected_hash_rollover_required=true
protected_hash_rollover_scope=CI_TARGETS_PRIOR_VALIDATOR_TARGETS_HASHES_AND_APPROVED_VALIDATOR_LIST_ONLY
prior_ci_sha256=27579b1d054a50223f76590c15bf310c4cc950341d1018e89c54a4849f62d0c2
pre_rollover_ci_sha256=9d07238bc0831d43c1b4ee7dfea73d2a92016eca68af4f5bdb210032ab071d50
post_rollover_ci_sha256=8068312d6aa24e667f344b3eea9082f0a9b3688bc664dee0984d3e3dd251f25c
prior_validator_path=scripts/validate_treatment_framework_signed_review_state_persistence_migration_0010_staging_migration_apply.py
prior_validator_target_scope_extended=true
prior_validator_hash_scope_extended=true
ci_target_scope_extended=true
approved_ci_validator_count=2
protected_hash_rollover_complete=true
repository_only=true
network_access=false
database_connection=false
database_write=false
restore_execution=false
migration_created=false
migration_executed=false
disposable_restore_target_provisioning_authorized=false
disposable_restore_execution_authorized=false
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
decision=HOLD_PMAI_P0_04_PENDING_DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW
```

Fail closed if either CI hash differs, any unapproved target is added, more than
the two named validators become executable, any protected package hash differs,
or any database/restore/migration authorization becomes true.
