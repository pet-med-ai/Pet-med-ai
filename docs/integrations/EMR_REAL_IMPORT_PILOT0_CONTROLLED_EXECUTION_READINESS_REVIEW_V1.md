# EMR real import pilot_0 controlled execution readiness review V1

## Stage

This is the final readiness review before deciding whether Pet-Med-AI may enter a short, controlled pilot_0 execution window.

Pilot level:

```txt
pilot_0 controlled execution readiness review
```

This stage is review and documentation only.

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

## Purpose

The purpose is to answer one question:

```txt
Are we ready to schedule a short feature-flag window for exactly one create-only EMR import pilot?
```

The default decision is:

```txt
NO-GO
```

Decision may become `GO` only when every required gate is complete and evidence is recorded.

## Required completed stages

All must be complete:

```txt
Release / Upgrade Framework V1
Version / Build Info V1
Feature Flag / Safety Gate V1
Release Status / Admin Ops Dashboard V1
Release Tag / Changelog V1
GitHub Actions CI Gate V1
Backup / Rollback Verification V1
EMR real import pilot_0 execution checklist V1
EMR real import pilot_0 dry-run rehearsal V1
EMR real import pilot_0 rehearsal execution report V1
```

## Non-negotiable readiness gates

### 1. CI and release gates

Required:

```txt
GitHub Actions CI Gate latest run is green
local ci_static_checks.sh PASS
frontend build passes
online smoke ALL PASS
release record exists or is prepared
```

### 2. Version and schema gates

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

### 3. Feature flag gates

Before the controlled window:

```txt
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

Only during the approved window may this temporarily become:

```txt
ENABLE_EMR_REAL_IMPORT=true
```

All other dangerous flags must remain false.

### 4. Backup and rollback gates

Required:

```txt
Render PostgreSQL backup verified
rollback_snapshot_id recorded
rollback owner available during the full pilot window
restore path known
post-rollback smoke command known
rollback decision matrix reviewed
```

### 5. EMR batch gates

Required:

```txt
batch.status in approved / clinical_signed
batch.receipt_count == 1
clinical_signoff_id present
rollback_snapshot_id present
linked receipt status ready_for_import
mapped_case_preview present
```

### 6. Dry-run gates

Required:

```txt
execution dry-run quality_gate.passed=true
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

### 7. Clinical gates

Required:

```txt
clinical owner signs GO for pilot_0
100% post-execution spot-check reviewer assigned
owner understands one Case may be created
owner understands update/delete/attachments/prescription/billing are forbidden
```

### 8. Operator gates

Required:

```txt
operator knows exact command / UI action
operator knows how to disable ENABLE_EMR_REAL_IMPORT immediately after execution
operator has terminal ready for online smoke after execution
operator has release record open for evidence
operator has rollback owner contact open
```

## Hard No-Go

Any one condition below means stop:

```txt
GitHub Actions not green
ci_static_checks fails
frontend build fails
online smoke fails before pilot
schema_ok=false
database_revision != alembic_head
Render backup not verified
rollback_snapshot_id missing
clinical_signoff_id missing
batch has more than 1 receipt
dry-run blocked_count > 0
dry-run would_update_count > 0
receipt not ready_for_import
mapped_case_preview missing
clinical reviewer unavailable
rollback owner unavailable
feature flag state unclear
ENABLE_EMR_IMPORT_CASE_UPDATE=true
ENABLE_EMR_ATTACHMENT_DOWNLOAD=true
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=true
ENABLE_BILLING_REAL_WRITE=true
ENABLE_CASE_DELETE_IMPORT=true
```

## Approved window constraints

If readiness is GO, the future controlled execution window must be:

```txt
one operator
one clinical reviewer
one rollback owner
one receipt
one batch
one Case creation maximum
no updates
no attachments
no prescriptions
no billing
feature flag open only for execution window
feature flag closed immediately after execution
online smoke immediately after execution
100% clinical spot-check immediately after smoke
```

## Required evidence before GO

Record:

```txt
release_id
git_commit
GitHub Actions run URL
database_revision
alembic_head
schema_ok
feature flags before
backup_id
rollback_snapshot_id
receipt_id
batch_id
clinical_signoff_id
execution dry-run evidence
clinical approval evidence
online smoke before
operator_id
clinical_owner
rollback_owner
```

## Decision options

```txt
GO: schedule controlled pilot_0 execution window.
PAUSE: fix missing evidence and repeat readiness review.
NO-GO: do not proceed; repeat dry-run rehearsal or rollback planning.
ROLLBACK-REVIEW: unexpected mutation occurred; inspect rollback path.
```

## Default decision

```txt
NO-GO until every required evidence field is complete.
```

## Completion criteria

This readiness review stage is complete when:

```txt
1. readiness review runbook committed
2. readiness checklist committed
3. feature flag window approval template committed
4. operator signoff template committed
5. Go/No-Go decision template committed
6. validator committed and included in smoke
7. CI static checks include the validator
```
