# EMR real import clinical approval API V1

## Stage

This stage adds a clinical Go / No-Go approval gate for a planned EMR import batch.

It is intentionally **not** a real import execution step.

## Endpoint

```txt
POST /api/emr/import-batches/{batch_id}/clinical-approval
```

Requires authentication.

## Request

```json
{
  "operator_id": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-20260604-001",
  "rollback_snapshot_id": "SNAPSHOT-20260604-001",
  "approval_action": "approve",
  "note": "Clinical signoff completed after execution dry-run review.",
  "request_id": "approval-20260604-001",
  "metadata": {
    "ui": "emr_import_batch_planning"
  }
}
```

Supported `approval_action` values:

```txt
approve
clinical_signed
needs_fix
reject
rejected
```

## Writes

This endpoint may write:

```txt
emr_import_batches.status
emr_import_batches.clinical_signoff_id
emr_import_batches.rollback_snapshot_id
emr_import_batches.approved_at
emr_import_batches.approved_by
audit_log
```

## Does not write

```txt
Case
ConsultSession
attachments
real import queue
```

Response safety fields must stay explicit:

```txt
writes_emr_import_batches=true
writes_audit_log=true
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

## Quality gate

Before `approve` / `clinical_signed`, the endpoint runs the existing execution dry-run report and requires:

```txt
quality_gate.passed=true
batch status in frozen / clinical_signed / approved
clinical_signoff_id present
rollback_snapshot_id present
no blocked dry-run items
```

If the gate fails, the endpoint returns 422 and does not approve the batch.

## Acceptance

- Static validator passes.
- Smoke test creates a planned batch, runs execution dry-run, then clinical approval.
- Response includes `audit_log_id`.
- Response keeps `can_execute_import=false`.
- No real Case is created or updated.
