# EMR real import execution API design doc V1

> Status: design-only gate.
>
> This document defines the proposed API contract and safety requirements for the future real EMR import execution endpoint. It does **not** implement the endpoint and does **not** authorize production Case writes by itself.

## 1. Scope

This design follows the completed EMR dry-run pipeline:

1. EMR webhook dry-run receiver.
2. Webhook inbox / receipt persistence.
3. EMR → Case mapping dry-run.
4. Webhook inbox review API / UI.
5. Webhook inbox review action.
6. EMR real import batch model.
7. EMR real import batch planning API / UI.
8. EMR real import execution dry-run.
9. EMR real import clinical approval API / UI.
10. Final execution runbook and risk review.

The future execution API may only run after all gates above are complete for a specific batch.

## 2. Non-goals in this stage

This stage does not do any of the following:

- Implement `POST /api/emr/import-batches/{batch_id}/execute`.
- Create `Case` rows.
- Update existing `Case` rows.
- Download attachments.
- Add database columns or tables.
- Add Alembic migrations.
- Add frontend execution buttons.
- Modify Render configuration.
- Bypass clinical signoff or rollback snapshot requirements.

## 3. Proposed endpoint

```http
POST /api/emr/import-batches/{batch_id}/execute
Authorization: Bearer <token>
Content-Type: application/json
Idempotency-Key: <stable execution key>
```

### Request body draft

```json
{
  "operator_id": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-20260605-001",
  "rollback_snapshot_id": "SNAPSHOT-20260605-001",
  "execution_dry_run_id": "optional-future-id",
  "execution_dry_run_hash": "sha256-of-final-dry-run-report",
  "mode": "execute_real_import",
  "policy": {
    "case_write_mode": "create_only",
    "allow_case_update": false,
    "allow_attachment_download": false,
    "max_items": 100,
    "stop_on_first_error": true
  },
  "note": "Approved execution window 2026-06-05 23:00-23:30.",
  "metadata": {
    "runbook_id": "EMR-FINAL-RUNBOOK-20260605-001",
    "operator_signoff_id": "OP-SIGNOFF-20260605-001"
  }
}
```

## 4. Proposed response body

```json
{
  "message": "emr_import_execution_started",
  "mode": "real_import_execution",
  "batch_id": "emr_batch_xxx",
  "execution_id": "emr_exec_xxx",
  "status": "accepted",
  "writes_case_database": true,
  "creates_case": true,
  "updates_case": false,
  "downloads_attachments": false,
  "executes_real_import": true,
  "can_rollback": true,
  "rollback_snapshot_id": "SNAPSHOT-20260605-001",
  "audit_log_id": "audit_xxx",
  "accepted_items": 12,
  "blocked_items": 0,
  "next_gate": "monitor execution status and post-execution audit"
}
```

The final implementation must not return `writes_case_database=true` until actual Case writes have occurred or have been enqueued into a clearly audited execution queue.

## 5. Preconditions

The future execution API must reject execution unless all of these are true:

| Gate | Requirement |
|---|---|
| Batch exists | `emr_import_batches.batch_id` exists. |
| Batch status | `status` is `approved` only. |
| Clinical signoff | `clinical_signoff_id` is present and matches the request. |
| Rollback snapshot | `rollback_snapshot_id` is present and matches a verified snapshot record. |
| Execution dry-run | Latest dry-run quality gate passed after the last batch modification. |
| Receipt status | Every linked receipt remains `ready_for_import`. |
| Case preview | Every receipt has `mapped_case_preview`. |
| Duplicate protection | No receipt has already been executed in a previous successful batch. |
| Idempotency | Request `Idempotency-Key` has not been consumed by a different payload. |
| Audit | Audit log append endpoint is healthy before execution starts. |
| Smoke | Latest staging / production smoke is green within the accepted time window. |
| Operator | `operator_id` is present and authorized for EMR import execution. |

## 6. Hard No-Go conditions

The future endpoint must return `409`, `422`, or `423` and not write any Case if any of these occur:

- Batch status is not `approved`.
- Any linked receipt is missing.
- Any linked receipt is no longer `ready_for_import`.
- Any linked receipt lacks `mapped_case_preview`.
- Any required Case field is empty: `patient_name`, `species`, `chief_complaint`.
- No rollback snapshot is verified.
- Clinical signoff is missing or mismatched.
- Existing dry-run report hash is missing or mismatched.
- A duplicate external EMR case is detected without an explicit update policy.
- Attachment download is requested in V1.
- `allow_case_update=true` is requested in V1.
- More than `max_items` rows are requested.
- Audit log write fails.
- Database transaction cannot be opened.
- Production environment lacks required safety environment variables.

## 7. Write policy for V1

The safest V1 execution policy is:

```txt
case_write_mode = create_only
allow_case_update = false
allow_attachment_download = false
stop_on_first_error = true
```

Create-only is recommended because current `Case` records do not yet have a fully stable external EMR identity policy. Updating existing Case records should be a later phase after a dedicated case matching model and conflict review UI are complete.

## 8. Proposed status transitions

```txt
approved
  -> running
  -> completed

approved
  -> running
  -> failed

approved
  -> running
  -> rolled_back
```

The API must not allow:

```txt
draft -> running
frozen -> running
clinical_signed -> running
needs_fix -> running
approval_rejected -> running
completed -> running
rolled_back -> running
```

## 9. Transaction strategy

Recommended implementation:

1. Start database transaction.
2. Lock batch row for update.
3. Re-read linked receipts.
4. Rebuild execution dry-run report inside the transaction.
5. Revalidate every hard gate.
6. Set batch status to `running`.
7. Append audit log row: `emr_import_execution_started`.
8. For each item:
   - Create Case only if policy is `create_only`.
   - Write import marker into Case history / metadata text section.
   - Do not download attachments.
   - Record per-item execution result in a future execution result table or batch receipt metadata.
9. Set batch status to `completed` if all items succeed.
10. Commit transaction.

If any item fails and `stop_on_first_error=true`, rollback the full transaction and set batch to `failed` only if that status update can be performed safely after rollback.

## 10. Audit requirements

The future API must append at least these audit events:

| Event | Timing |
|---|---|
| `emr_import_execution_requested` | Before any Case write. |
| `emr_import_execution_started` | After all gates pass. |
| `emr_import_case_created` | Per created Case. |
| `emr_import_execution_completed` | After success. |
| `emr_import_execution_failed` | On failure. |
| `emr_import_rollback_started` | If rollback begins. |
| `emr_import_rollback_completed` | If rollback succeeds. |

Every audit row should include:

```txt
batch_id
execution_id
receipt_ids
operator_id
clinical_signoff_id
rollback_snapshot_id
dry_run_hash
writes_case_database
creates_case
updates_case
downloads_attachments
executes_real_import
```

## 11. Rollback strategy

A rollback plan must exist before execution. Recommended rollback options:

1. Restore database snapshot for small controlled windows.
2. Reverse only inserted Cases by a clear import marker, if snapshot restore is not acceptable.
3. Never delete manually-created clinical Cases during rollback.
4. Always run smoke after rollback.
5. Always perform clinical spot-check after rollback.

V1 should prefer short execution windows and small batches.

## 12. Minimum implementation prerequisites before coding

Before implementing a real execution API, complete these design/engineering prerequisites:

1. Case import marker policy.
2. Case matching policy V1.
3. EMR import execution result model V1.
4. Rollback API or rollback runbook dry-run.
5. Operator role / permission policy.
6. Production backup verification checklist.
7. Manual approval that real Case writes are allowed.

## 13. Proposed follow-up phases

Recommended next phases:

```txt
1. EMR import execution result model V1
2. EMR real import case matching policy V1
3. EMR real import execution API skeleton V1
4. EMR real import execution API smoke sandbox V1
5. EMR real import rollback dry-run V1
6. EMR real import production pilot V1
```

Do not skip directly to production writes.
