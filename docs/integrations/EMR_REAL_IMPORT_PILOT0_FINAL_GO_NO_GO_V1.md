# EMR real import pilot_0 final Go / No-Go V1

## Stage

This is the final Go / No-Go gate before scheduling the first controlled `pilot_0` real EMR import execution window.

This stage is decision documentation and validation only.

It does not:

```txt
enable ENABLE_EMR_REAL_IMPORT
execute POST /api/emr/import-batches/{batch_id}/execute
create Case records
update Case records
download attachments
write prescriptions
write billing rows
run Alembic
change database schema
```

## Decision question

This gate answers one question:

```txt
May Pet-Med-AI schedule a short, supervised pilot_0 execution window that temporarily enables ENABLE_EMR_REAL_IMPORT=true and imports exactly one ready_for_import receipt as create-only?
```

Default decision:

```txt
NO-GO
```

Decision can become `GO` only if every evidence field is complete and every safety gate is green.

## Required completed stages

All must be complete and referenced in the evidence packet:

```txt
Release / Upgrade Framework V1
Version / Build Info V1
Feature Flag / Safety Gate V1
Release Status / Admin Ops Dashboard V1
Release Tag / Changelog V1
GitHub Actions CI Gate V1
Backup / Rollback Verification V1
Render / GitHub Security Hardening V1
EMR real import pilot_0 execution checklist V1
EMR real import pilot_0 dry-run rehearsal V1
EMR real import pilot_0 rehearsal execution report V1
EMR real import pilot_0 controlled execution readiness review V1
```

## Final required evidence

### 1. Release and CI evidence

Required:

```txt
release_id present
git_commit present
GitHub Actions CI Gate latest run green
local ci_static_checks.sh PASS
frontend build PASS
online smoke before pilot ALL PASS
```

### 2. Version and schema evidence

Required from:

```txt
GET /api/system/version
```

Expected:

```txt
schema_ok=true
database_revision == alembic_head
writes_database=false
```

### 3. Feature flag evidence

Before any execution window:

```txt
all_dangerous_features_disabled=true
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

The Go decision may approve only this temporary future window state:

```txt
ENABLE_EMR_REAL_IMPORT=true
```

All other dangerous flags must remain false.

### 4. Security hardening evidence

Required:

```txt
Render / GitHub Security Hardening V1 complete
security_check.sh reviewed
GitHub token/PAT review complete
Render environment variable review complete
Render log leak review complete
DB backup / restore drill evidence reviewed
```

### 5. Backup and rollback evidence

Required:

```txt
Render PostgreSQL backup verified
backup_id present
rollback_snapshot_id present
restore path known
rollback owner online during planned window
post-rollback smoke command known
```

### 6. Batch and receipt evidence

Required:

```txt
receipt_id present
batch_id present
batch.status in approved / clinical_signed
batch.receipt_count == 1
linked receipt status ready_for_import
mapped_case_preview present
clinical_signoff_id present
rollback_snapshot_id matches verified backup
```

### 7. Execution dry-run evidence

Required:

```txt
quality_gate.passed=true
would_create_count=1
would_update_count=0
blocked_count=0
writes_database=false
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

### 8. Clinical evidence

Required:

```txt
clinical owner final GO or NO-GO decision recorded
clinical reviewer assigned for 100% post-execution spot-check
doctor understands exactly one Case may be created
doctor understands updates/deletes/attachments/prescriptions/billing are forbidden
```

### 9. Operator evidence

Required:

```txt
operator_id present
operator signoff present
operator has exact execute command or UI action ready
operator has feature flag close procedure ready
operator has online smoke command ready
operator has rollback owner contact ready
operator has release record open
```

## Final Hard No-Go

Any one condition below means final decision must be `NO-GO`:

```txt
GitHub Actions not green
ci_static_checks fails
frontend build fails
online smoke before pilot fails
schema_ok=false
database_revision != alembic_head
security_check has unreviewed real secret finding
Render logs expose secret values
backup_id missing
rollback_snapshot_id missing
restore path unknown
rollback owner unavailable
clinical_signoff_id missing
clinical reviewer unavailable
batch receipt_count != 1
receipt not ready_for_import
mapped_case_preview missing
execution dry-run quality_gate.passed=false
would_update_count > 0
blocked_count > 0
dangerous feature flag unexpectedly enabled
operator cannot immediately disable ENABLE_EMR_REAL_IMPORT after execution
```

## Decision options

```txt
GO
PAUSE
NO-GO
ROLLBACK-REVIEW
```

Definitions:

```txt
GO: all evidence complete; schedule the controlled pilot_0 execution window.
PAUSE: evidence incomplete or minor fix needed; do not schedule execution yet.
NO-GO: hard safety issue; repeat rehearsal or readiness review.
ROLLBACK-REVIEW: unexpected mutation happened during rehearsal; inspect rollback path.
```

## If final decision is GO

The next stage may be scheduled:

```txt
EMR real import pilot_0 controlled execution window V1
```

That future stage must still:

```txt
temporarily enable ENABLE_EMR_REAL_IMPORT=true
execute exactly one receipt
disable ENABLE_EMR_REAL_IMPORT=false immediately after execution
run online smoke immediately
perform 100% clinical spot-check
record created_case_id / execution_id / audit_log_id
record Go / Pause / Rollback post-decision
```

## Completion criteria

This final Go / No-Go V1 stage is complete when:

```txt
1. Final Go/No-Go runbook committed.
2. Final evidence packet template committed.
3. Final decision checklist committed.
4. Final approver signoff template committed.
5. Final execution window handoff template committed.
6. Release record addendum committed.
7. Validator committed and included in smoke.
8. CI static checks include the validator.
```
