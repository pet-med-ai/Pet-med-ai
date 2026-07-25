# Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1

## Stage identity

stage_id=PMAI-P0-03
stage_name=Treatment Framework Signed Review State Persistence Migration Authenticated Staging Smoke V1
stage_type=authenticated_staging_smoke
PACKAGE_INITIALIZED=true
STAGE_STATUS=IN_PROGRESS
EVIDENCE_COMPLETENESS=PENDING_EXTERNAL_EXECUTION
AUTHENTICATED_STAGING_SMOKE_COMPLETE=false
STAGING_BACKEND_PROVISIONED=false
STAGING_BACKEND_ISOLATED=false
STAGING_DATABASE_REVISION_VERIFIED=false
AUTHENTICATION_VERIFIED=false
OWNER_SCOPE_VERIFIED=false
CROSS_USER_DENIAL_VERIFIED=false
TREATMENT_FRAMEWORK_BUILD_VERIFIED=false
CLINICIAN_REVIEW_VERIFIED=false
APPEND_ONLY_AUDIT_LINK_VERIFIED=false
SIGNED_REVIEW_STATE_PREVIEW_VERIFIED=false
PERSISTENCE_PREPARE_VERIFIED=false
MIGRATION_PATH_PREVIEW_VERIFIED=false
READBACK_VERIFIED=false
IDEMPOTENCY_STRATEGY_VERIFIED=false
FAILURE_NO_PARTIAL_WRITE_VERIFIED=false
STAGING_SYNTHETIC_USERS_WRITE_EXECUTED=false
STAGING_SYNTHETIC_CASE_WRITE_EXECUTED=false
STAGING_APPEND_ONLY_AUDIT_WRITE_EXECUTED=false
SIGNED_REVIEW_0010_STAGING_MIGRATION_EXECUTED=false
PRODUCTION_MIGRATION_EXECUTED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
PRODUCTION_DATABASE_WRITE_PERFORMED=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
CLIENT_FACING_RELEASE_PERFORMED=false
CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false
STAGING_DATABASE_URL_RECORDED=false
STAGING_CREDENTIAL_RECORDED=false
RUNNER_REQUIRES_EXPLICIT_CONFIRMATION=true
PACKAGE_CONNECTS_DATABASE=false
PACKAGE_WRITES_DATABASE=false

PMAI-P0-03 is initialized but not complete. This package prepares a guarded
authenticated staging runner and evidence registers. The repository apply
script and package validator perform no HTTP call and no database write.

## Entry gate

baseline_commit_sha=b37362a2a343b068926edce4862b6f7d7c62a19d
previous_stage_document=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1.md
previous_stage_status=COMPLETE
previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
rollback_restore_evidence_complete=true

## Purpose and clinical value

Use a real authenticated context, an isolated staging backend, two synthetic
users, and a synthetic staging case to verify the full pre-migration chain:

```text
build treatment framework
-> clinician review
-> append-only treatment-framework audit link
-> signed review state preview
-> persistence prepare preview
-> migration path preview
-> owner-scoped readback
```

This stage verifies authorization and dry-run behavior before any signed-review
0010 schema apply. It is not a migration stage and not a controlled signed-state
persistence stage.

## Required isolated staging backend

The future external run requires a dedicated Render web service such as:

```text
service_label=pet-med-ai-backend-staging-ohio
region=Ohio_US_East
database_service=pet-med-ai-db-staging-source-ohio
environment=staging
production_database_attached=false
production_secret_reused=false
```

Required staging-only environment values:

```text
DATABASE_URL=<Render staging internal database URL; never commit>
SECRET_KEY=<unique staging-only secret; never commit>
ENVIRONMENT=staging
PYTHON_VERSION=3.11.9
```

All dangerous feature flags remain false. The runner refuses the production
backend hostname and requires `staging` in the target hostname.

## External runner write scope

The guarded runner is not invoked by CI or cumulative smoke. When explicitly
executed against the isolated staging backend, it is allowed to create only:

```text
two synthetic staging users
one synthetic staging case
exactly one append-only treatment-framework audit row
```

It must not write:

```text
Case.treatment
treatment framework persistence
signed review state persistence
prescription records
medication amount, route, or frequency
client-facing output
production data
```

## Authentication and owner-scope matrix

The external evidence must prove:

- unauthenticated treatment-framework requests return 401;
- user A can access only user A's synthetic case;
- user B receives 404 for user A's case and treatment-framework chain;
- readback audit linkage points only to user A's case;
- no token, email, password, connection URI, or raw case identifier is
  committed as evidence.

## Idempotency strategy

The current append-only audit endpoint does not claim server-side request-ID
uniqueness. PMAI-P0-03 therefore uses a fail-closed interim strategy:

1. run the audit request twice in dry-run mode with a fixed request ID and
   require deterministic output;
2. append the audit row exactly once;
3. never replay the actual append request;
4. repeat all subsequent read-only dry-run chain requests and require
   deterministic preview hashes;
5. require exactly one audit row on owner-scoped readback.

A database uniqueness constraint for future signed-state persistence remains a
P0-04/P0-05 concern. This stage does not create that constraint.

## Failure and partial-write checks

The external evidence must verify that the following fail with no extra audit
row and no Case mutation:

- missing audit reference before signed-review preview;
- missing migration design/readiness acknowledgement;
- forbidden medication amount, route, frequency, or prescription wording;
- cross-user access.

## Production hard gate remains unchanged

database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false

## Dangerous feature flags remain disabled

- ENABLE_EMR_REAL_IMPORT=false
- ENABLE_EMR_IMPORT_CASE_UPDATE=false
- ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
- ENABLE_PREVENTIVE_AUTO_DELIVERY=false
- ENABLE_PREVENTIVE_SMS_DELIVERY=false
- ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
- ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
- ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
- ENABLE_DEVICE_REAL_INGEST=false
- ENABLE_BILLING_REAL_WRITE=false

## Completion contract

PMAI-P0-03 can be marked COMPLETE only after a sanitized external evidence
artifact proves authentication, owner scope, cross-user denial, deterministic
replay, exactly one append-only audit link, complete dry-run chain, and no
partial write on failure.

Until then:

authenticated_staging_smoke_complete=false
staging_0010_apply_authorized=false
production_migration_authorized=false

## Decision

decision=HOLD_PMAI_P0_03_PENDING_AUTHENTICATED_STAGING_SMOKE_EVIDENCE
completion_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_0010_STAGING_MIGRATION_APPLY_V1
