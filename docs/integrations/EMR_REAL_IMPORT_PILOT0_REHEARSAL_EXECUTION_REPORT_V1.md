# EMR real import pilot_0 rehearsal execution report V1

## Stage

This report records the result of the `EMR real import pilot_0 dry-run rehearsal V1`.

It is evidence-only.

It does not:

```txt
enable ENABLE_EMR_REAL_IMPORT
create Case records
update Case records
download attachments
write prescriptions
write billing rows
run Alembic
change database schema
```

## Report purpose

This report confirms whether the pilot_0 dry-run rehearsal is strong enough to proceed toward a future controlled real pilot.

The rehearsal must prove:

```txt
1 signed EMR dry-run receipt persisted
1 receipt reviewed as ready_for_import
1 frozen batch created with exactly 1 receipt
execution dry-run quality gate passed
clinical approval rehearsal completed
/execute remained blocked by feature flag
online smoke passed before and after rehearsal
ENABLE_EMR_REAL_IMPORT remained false throughout
```

## Required evidence

Fill the evidence values below from the actual rehearsal.

```txt
rehearsal_id:
date:
operator_id:
clinical_owner:
rollback_owner:

receipt_id:
batch_id:
execution_dry_run_request_id:
clinical_approval_audit_log_id:
clinical_signoff_id:
rollback_snapshot_id:

database_revision:
alembic_head:
schema_ok:
git_commit:
git_tag:

online_smoke_before:
online_smoke_after:
feature_flags_before:
feature_flags_after:

execute_blocked_status:
execute_blocked_reason:
```

## Required API / UI checkpoints

### 1. System version

Endpoint:

```txt
GET /api/system/version
```

Required result:

```txt
schema_ok=true
database_revision == alembic_head
writes_database=false
```

### 2. Feature flags before rehearsal

Endpoint:

```txt
GET /api/system/feature-flags
```

Required result:

```txt
all_dangerous_features_disabled=true
ENABLE_EMR_REAL_IMPORT=false
```

### 3. EMR dry-run receipt

Endpoint:

```txt
POST /api/webhooks/emr/case-mapping/dry-run
```

Required result:

```txt
receipt_persisted=true
writes_webhook_inbox=true
writes_case_database=false
creates_case=false
mapped_case_preview present
```

### 4. Webhook inbox review action

Endpoint:

```txt
POST /api/webhooks/emr/inbox/{receipt_id}/review-action
```

Required result:

```txt
status_after=ready_for_import
writes_webhook_inbox=true
writes_audit_log=true
writes_case_database=false
creates_case=false
```

### 5. Batch planning

Endpoint:

```txt
POST /api/emr/import-batches/plan
```

Required result:

```txt
receipt_count=1
status=frozen
writes_emr_import_batches=true
writes_emr_import_batch_receipts=true
writes_case_database=false
creates_case=false
```

### 6. Execution dry-run

Endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/execution-dry-run
```

Required result:

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

### 7. Clinical approval rehearsal

Endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/clinical-approval
```

Required result:

```txt
status_after=approved or clinical_signed
audit_log_id present
writes_emr_import_batches=true
writes_audit_log=true
writes_case_database=false
creates_case=false
executes_real_import=false
can_execute_import=false
```

### 8. Execute remains blocked

Endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/execute
```

Required result while `ENABLE_EMR_REAL_IMPORT=false`:

```txt
HTTP 403
feature flag disabled
ENABLE_EMR_REAL_IMPORT
```

This is a required safety proof.

## No-Go findings

Record any item below as No-Go:

```txt
schema_ok=false
database_revision != alembic_head
online smoke failed
feature flag unexpectedly enabled
receipt_count != 1
quality_gate.passed=false
would_update_count > 0
blocked_count > 0
/execute did not return 403 while flag disabled
clinical approval missing
rollback_snapshot_id missing
clinical_signoff_id missing
```

## Decision

Choose one:

```txt
GO: rehearsal passed; allowed to plan controlled pilot_0 real execution window.
PAUSE: minor issue; fix and repeat dry-run rehearsal.
NO-GO: major safety issue; do not proceed to real import.
ROLLBACK-REVIEW: rehearsal changed unexpected state; review rollback decision.
```

## Recommended default decision

Unless every required field is recorded and every required result is green:

```txt
NO-GO
```

## Completion criteria

This report stage is complete when:

```txt
1. Execution report template committed.
2. Evidence summary CSV committed.
3. API evidence template committed.
4. Go/No-Go report template committed.
5. Validator committed.
6. smoke and CI static checks include the validator.
```
