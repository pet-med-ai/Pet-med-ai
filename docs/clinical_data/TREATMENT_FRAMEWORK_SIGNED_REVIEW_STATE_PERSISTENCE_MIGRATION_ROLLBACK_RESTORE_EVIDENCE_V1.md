# Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1

## Stage identity

stage_id=PMAI-P0-02
stage_name=Treatment Framework Signed Review State Persistence Migration Rollback Restore Evidence V1
stage_type=rollback_restore_evidence_collection
PACKAGE_INITIALIZED=true
STAGE_STATUS=IN_PROGRESS
EVIDENCE_COMPLETENESS=PENDING_EXTERNAL_EXECUTION
ROLLBACK_RESTORE_EVIDENCE_COMPLETE=false
BACKUP_EVIDENCE_COMPLETE=false
RESTORE_EVIDENCE_COMPLETE=false
ROLLBACK_DRY_RUN_EVIDENCE_COMPLETE=false
DATA_VERIFICATION_COMPLETE=false
CLINICAL_CASE_READBACK_COMPLETE=false
FAILURE_PATH_OWNER_RECORDED=false
STAGING_MIGRATION_EXECUTED=false
PRODUCTION_MIGRATION_EXECUTED=false
ACTIVE_0010_MIGRATION_FILE_CREATED=false
SCHEMA_CHANGE_APPLIED=false
APPLICATION_DATABASE_WRITE_PERFORMED=false
PRODUCTION_DATABASE_WRITE_PERFORMED=false
CASE_TREATMENT_WRITE_PERFORMED=false
PRESCRIPTION_WRITE_PERFORMED=false
CLIENT_FACING_RELEASE_PERFORMED=false
CLIENT_FACING_MEDICATION_DETAIL_OUTPUT=false
STAGING_DATABASE_URL_RECORDED=false
STAGING_CREDENTIAL_RECORDED=false
STAMP_HEAD_USED=false
MANUAL_ALEMBIC_REVISION_EDIT_USED=false

This package enters PMAI-P0-02 without claiming completion. It initializes a
sanitized evidence register for a real backup/restore drill on an isolated,
disposable staging restore target. The repository apply script itself performs
no backup, restore, migration, schema change, or database connection.

## Production hard gate remains unchanged

database_revision=0009_diag_data
alembic_head=0009_diag_data
schema_ok=true
migration_errors=[]
writes_database=false
exposes_database_url=false

## Reproducible baseline

baseline_commit_sha=8d118180ced24b4df9af987790d47ab049346786
baseline_remote_ref=origin/main
previous_evidence_document=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_STAGING_REHEARSAL_EVIDENCE_V1.md
previous_evidence_document_sha256=0f91dd34b0489fc66b378628520955a6b3d9bf2108918b4ed3fa6819e3ee38d3
inactive_0010_draft_path=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_IMPLEMENTATION_ALEMBIC_0010_DRAFT.py.txt
inactive_0010_draft_sha256=bfab1107e54d888854d685fcab62e4367871acd44c12d2c2bad0a63946a8995d
inactive_0010_reference_only=true
active_0010_migration_file_must_not_exist=true

## Evidence files

- checklist=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_CHECKLIST_V1.csv
- evidence_register=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_REGISTER_V1.csv
- verification_matrix=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_VERIFICATION_V1.csv
- go_no_go=docs/clinical_data/TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_GO_NO_GO_V1.csv
- validator=scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py

## Required external evidence

The operator must collect the following outside this apply script, using the
provider console or approved secure operations channel:

1. A non-secret staging service label and database engine.
2. Proof that the source staging service and disposable restore target are
   isolated from production.
3. A provider backup identifier and provider timestamp.
4. A disposable restore target identifier.
5. Restore start and finish timestamps plus calculated duration.
6. Read-only revision verification before and after restore; both must remain
   at 0009_diag_data for this pre-0010 drill.
7. Read-only row-count comparisons for cases, consult sessions, diagnostic
   reports, observations, imaging studies, and append-only audit records.
8. A pseudonymized sample-case readback that excludes owner names, phone
   numbers, email addresses, free-text secrets, and database connection data.
9. Sanitized backup/restore command or provider-operation output with SHA-256.
10. A named operational role and incident owner for failure handling.

Do not commit a database URL, password, access token, provider secret, raw
backup archive, unredacted patient data, owner contact data, or private service
credential. Evidence artifacts referenced by SHA-256 must be sanitized before
being placed in the repository.

## Rollback and restore runbook boundary

- The source must be staging, never production.
- The restore target must be disposable and isolated from production services.
- No active backend/migrations/versions/0010*.py file may be created.
- No Alembic upgrade or downgrade is executed in this stage package.
- The current drill proves the 0009 backup/restore path before P0-04.
- `alembic stamp head` and manual edits to Alembic revision state are forbidden.
- Any revision mismatch, row-count mismatch, unreadable sample case, missing
  evidence hash, or secret leakage returns NO-GO.
- Destroying the disposable target occurs only after evidence review and
  according to the provider retention policy.

## Completion contract

PMAI-P0-02 can be marked COMPLETE only after every blocking row in the
checklist, evidence register, verification matrix, and Go/No-Go file is backed
by sanitized source evidence. At completion, run:

```text
python3 scripts/validate_treatment_framework_signed_review_state_persistence_migration_rollback_restore_evidence.py --require-complete
```

Until then:

rollback_restore_evidence_complete=false
staging_apply_authorized=false
authenticated_staging_smoke_authorized=false

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

## Explicit non-goals

- no real staging migration apply
- no production migration
- no active Alembic 0010 migration
- no schema change
- no application database write
- no Case.treatment write
- no prescription write
- no medication amount, route, or frequency output
- no client-facing AI diagnosis
- no real EMR, LIS, DICOM, PACS, device, or gateway ingest
- no automatic SMS, WeChat, or email delivery
- no invoice real write

## Decision

previous_stage_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_ROLLBACK_RESTORE_EVIDENCE_V1
decision=HOLD_PMAI_P0_02_PENDING_EXTERNAL_ROLLBACK_RESTORE_EVIDENCE
completion_decision=GO_TO_TREATMENT_FRAMEWORK_SIGNED_REVIEW_STATE_PERSISTENCE_MIGRATION_AUTHENTICATED_STAGING_SMOKE_V1
