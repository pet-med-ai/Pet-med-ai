# Treatment Framework Signed Review State Persistence Migration 0010
## Disposable Target Provisioning Authorization Review V1

This is one consolidated, provisioning-only authorization record for
PMAI-P0-04.  It does not create a target and it does not authorize or
execute restore, database access, schema migration, deployment, or any
clinical write.

## 1. Canonical authorization record

```text
stage_id=PMAI-P0-04
substage=DISPOSABLE_TARGET_PROVISIONING_AUTHORIZATION_REVIEW_V1
stage_status=IN_PROGRESS
package_status=AUTHORIZATION_RECORD_ONLY
review_status=APPROVED_PROVISIONING_ONLY
authorization_record_id=PMAI-P0-04-DTPA-AUTH-20260808-001
authorization_recorded_date=2026-08-08
approval_statement=批准以上参数，仅授权 disposable target provisioning，不授权 restore execution。
approval_statement_sha256=2afe7b8c5a9701b972fd81c15c67759a16c84d9658f7613583e5a7162a06d92b
approver_role=PROJECT_OWNER_OPERATOR
operator_role=PROJECT_OWNER_OPERATOR
authorization_scope=ONE_NEW_EMPTY_ISOLATED_POSTGRES_SERVICE_ONLY
authorization_effective_gate=PACKAGE_COMMITTED_PUSHED_AND_CI_GATE_PASS
disposable_restore_target_provisioning_authorized=true
disposable_restore_execution_authorized=false
decision=GO_TO_DISPOSABLE_TARGET_PROVISIONING_ONLY
next_action=OPERATOR_PROVISION_NEW_EMPTY_TARGET_AND_CAPTURE_SANITIZED_EVIDENCE
evidence_completeness=PENDING_TARGET_PROVISIONING_AND_SANITIZED_PROVISIONING_EVIDENCE
```

The approval statement is preserved verbatim and identified by SHA-256.
No broader authority may be inferred from it.  In particular, provisioning
authority becomes operational only after this exact repository package is
committed, pushed, and its CI gate passes.

## 2. Trusted repository and environment baseline

```text
local_main=b47d455aeeecb7dac9654d9e1dbf3df399573d5b
origin_main=b47d455aeeecb7dac9654d9e1dbf3df399573d5b
main_parent=3124087025522892d9e9a887af977ab03e244c73
isolated_branch=pmai-p0-04-staging-0010
local_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
remote_isolated_branch=8d1dc8814ed8f80d8bc965b494c1c320fc08f228
production_runtime=d659aefb
staging_runtime=8d1dc881
production_database_revision=0009_diag_data
production_alembic_head=0009_diag_data
staging_database_revision=0009_diag_data
staging_alembic_head=0009_diag_data
candidate_migration_deployed=false
production_auto_deploy_verified=false
baseline_source=TRUSTED_HANDOFF_AND_SANITIZED_OPERATOR_SCREENSHOTS_NOT_NETWORK_REVERIFIED_BY_PACKAGE
final_ci_sha256=f224dd3ed069a198613ad3ddbace564245586528acddab54e1eb835921ffea2f
```

CI Gate #186 passed for commit b47d455.  The observed production deploy
remains the earlier manually triggered d659aef event and is not promoted
as Auto-Deploy evidence.  No manual deploy is part of this authorization.

## 3. Approved source compatibility facts

```text
source_database_service=pet-med-ai-db-staging-source-ohio
source_database_status=Available
source_region=Ohio (US East)
source_postgresql_major_version=18
source_instance_type=Basic-256mb
source_memory_mb=256
source_cpu=0.1
source_storage_gb=1
source_storage_used_percent=10.33
restore_client_version=18.4
version_compatibility_review=PASS_POSTGRESQL_18_SOURCE_TARGET_AND_CLIENT
```

These values are sanitized operator evidence.  They contain no connection
string, credential, environment dump, raw backup bytes, or external JSON.

## 4. Approved disposable target parameters

```text
target_logical_name=pet-med-ai-db-p0-04-disposable-restore-ohio
target_provider=Render
target_region=Ohio (US East)
target_engine_family=PostgreSQL
target_postgresql_major_version=18
target_instance_type=Basic-256mb
target_memory_mb=256
target_cpu=0.1
target_storage_gb=1
target_storage_autoscaling=false
target_read_replica_count=0
target_high_availability=false
target_connection_pooling=false
target_application_attachment_count=0
target_is_disposable=true
target_must_be_new=true
target_must_be_empty=true
target_purpose=PMAI_P0_04_ONE_TIME_BACKUP_RESTOREABILITY_REHEARSAL
provisioning_method=NEW_EMPTY_POSTGRES_SERVICE_NOT_RESTORE_DATABASE
production_target_excluded=true
staging_source_target_excluded=true
application_traffic_disabled=true
network_scope=UNATTACHED_NO_APPLICATION_TRAFFIC
credential_handling=DO_NOT_COPY_PRINT_COMMIT_OR_CAPTURE_CONNECTION_VALUES
```

Provision exactly one new empty service with these parameters.  Do not
reuse production, the staging source, a previous target, or any service
with application traffic.  Do not click Restore Database as part of the
provisioning-only action.

## 5. Cost and lifecycle boundary

```text
target_compute_monthly_usd=6.00
target_storage_monthly_usd_per_gb=0.30
target_planning_month_hours=720
target_max_lifetime_hours=72
target_delete_within_hours_after_evidence=24
target_expiry_at=DERIVE_FROM_CREATED_AT_PLUS_72_HOURS
target_estimated_max_cost_usd=0.63
target_cost_ceiling_usd=1.00
billing_owner=PROJECT_OWNER_OPERATOR
deletion_owner=PROJECT_OWNER_OPERATOR
cleanup_evidence_required=true
render_pricing_reference=https://render.com/pricing
render_postgresql_reference=https://render.com/docs/postgresql-refresh
render_blueprint_reference=https://render.com/docs/blueprint-spec
```

The planning estimate uses 72 of 720 monthly hours: compute USD 0.60 plus
one GB storage USD 0.03, for at most USD 0.63.  Stop before provisioning
if current provider pricing or required storage would exceed USD 1.00.

## 6. Package execution boundary

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
restore_runner_execution_enabled=false
restore_runner_executed_by_ci=false
disposable_restore_database_created=false
disposable_restore_database_write_authorized=false
backup_restoreability_verified=false
disposable_restore_rehearsal_complete=false
corrected_migration_implementation_authorized=false
active_0010_migration_file_created=false
staging_0010_migration_executed=false
p0_04_execution_authorized=false
staging_0010_apply_authorized=false
production_migration_authorized=false
production_migration_executed=false
provisioning_execution_performed=false
target_created_by_package=false
locked_runner_sha256=c50002898763c0b7e6aa618d2728f8595496c5c4bb57e300aedbc4d59bbde23f
```

The provisioning authorization is a narrow control-plane permission to
create one empty isolated service.  It is not database-write authority for
restored or clinical data and it supplies no permission to connect.

## 7. Production and clinical hard gates retained

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

## 8. Permitted later operator action

Only after the repository gate is effective, the operator may:

1. Create one new empty Render PostgreSQL service using the exact approved
   name, region, major version, instance type, and one-GB storage value.
2. Leave it unattached to all applications and without application traffic.
3. Record only sanitized provisioning evidence: authorization record ID,
   service name or sanitized service identifier, creation time, Available
   status, region, engine major, instance type, storage, attachment count,
   calculated expiry, deletion owner, and current cost projection.
4. Stop.  Do not retrieve a connection value and do not begin restore.

A successful empty-target creation will later change only the external
provisioning evidence state.  It does not make restoreability verified.

## 9. Mandatory stop conditions

Stop before creating anything if:

- the repository package is not committed, pushed, and CI-passing;
- main or either isolated ref differs from the trusted baseline;
- the approved service name already exists or a different name is required;
- provider, region, PostgreSQL major, plan, or explicit one-GB storage differs;
- storage autoscaling, a replica, HA, pooling, or an app attachment is required;
- the estimated total cost can exceed the approved USD 1.00 ceiling;
- a connection value, secret, restore action, SQL action, migration action,
  deployment, application attachment, or staging-source change is proposed;
- the target would be production, staging source, non-empty, reused, or shared;
- the 72-hour expiry, deletion owner, or cleanup evidence cannot be recorded;
- the locked runner hash differs or an active backend 0010 file exists;
- a fourth manual deployment deviation is proposed or observed.

On any stop, create nothing, retain restore authorization as false, and
return to a separate review.  Do not compensate with a manual deploy,
revision edit, schema stamp, connection, or restore attempt.

## 10. Next gate

After sanitized evidence proves that the exact empty disposable target is
Available and isolated, prepare a separate restore-execution authorization
review.  This document cannot satisfy that later gate and cannot be used as
a restore command approval.
