# EMR Real Import Execution API Risk Review V1

> Stage: documentation / risk review only  
> Status: does **not** implement the real import execution API  
> Scope: review the risks, gates, minimum contract, and approval criteria before any endpoint can write `Case` records from EMR batches.

## 1. Why this stage exists

Pet-Med-AI already has the safer upstream gates for EMR integration:

1. EMR Webhook dry-run receiver.
2. Webhook inbox / receipt persistence.
3. EMR → Case mapping dry-run.
4. Webhook inbox review API / UI.
5. Human review action.
6. EMR real import batch model.
7. Batch planning API / UI.
8. Execution dry-run.
9. Clinical approval API / UI.
10. Final execution runbook.

The next tempting step would be a real execution API that writes to `cases`. That is high risk. This risk review exists to prevent a premature implementation.

## 2. Decision

V1 decision:

```txt
Do not implement real Case write execution yet.
```

This stage only documents:

- required gates
- unacceptable risks
- API design constraints
- rollback requirements
- audit requirements
- smoke / manual testing requirements
- final Go / No-Go decision criteria

## 3. Proposed future endpoint, not implemented in V1

Future candidate endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/execute
```

This endpoint must not be added until this risk review has a signed Go decision.

Expected future behavior:

```txt
Reads one approved batch.
Writes Case records or updates existing Case records.
Writes an audit_log row for every case-level write.
Marks import batch execution state.
Produces an execution result report.
Supports rollback by batch marker / snapshot.
```

## 4. Current safety boundary

The current system is still safe because all completed stages explicitly stop before real Case writes.

Current allowed writes:

```txt
webhook_inbox
audit_log
emr_import_batches
emr_import_batch_receipts
```

Current forbidden writes for EMR real import stages:

```txt
cases
consult_sessions
attachments from external URLs
billing
medication orders
production knowledge-base
```

## 5. Preconditions before any execute API can be implemented

The execute API must not be built unless all items below are true.

| Gate | Required condition | Evidence |
|---|---|---|
| Alembic | Render and local database are at latest head | `python3 -m alembic -c alembic.ini current` |
| Batch status | Batch is `approved` | API detail response |
| Clinical approval | `clinical_signoff_id` is present | Batch detail |
| Rollback | `rollback_snapshot_id` is present and verified | Render snapshot ID / DB backup ID |
| Dry-run | execution dry-run has `quality_gate.passed=true` | dry-run report |
| Blocked rows | blocked_count is `0` | dry-run report |
| Audit | audit_log append-only API is live | smoke |
| Smoke | full local and online smoke pass | `scripts/smoke_petmed.sh` |
| Human owner | named operator and rollback owner assigned | signoff template |
| Case write policy | create/update policy is approved | decision matrix |

## 6. Hard No-Go conditions

Any one of the following blocks real execution:

```txt
No rollback snapshot.
No clinical signoff.
execution dry-run failed.
blocked_count > 0.
Batch status is not approved.
Render PostgreSQL is not at Alembic head.
Online smoke is not ALL PASS.
Unknown case matching policy.
Unknown duplicate handling policy.
Owner phone / owner identity mapping is not approved.
Attachments require download in the same execution path.
The API would write medication orders directly.
No audit-log row per written Case.
No import marker on written Case.
```

## 7. Required design for future real execution

### 7.1 Idempotency

The execute API must be idempotent by `batch_id`.

Future implementation rule:

```txt
Executing the same approved batch twice must not create duplicate cases.
```

At minimum:

- each created or updated Case must carry an import marker in metadata / history
- the result report must include `already_executed=true` if applicable
- repeated execution must return existing result, not write again

### 7.2 Case matching policy

V1 risk decision: do not infer aggressive matches.

Allowed future matching candidates:

```txt
existing webhook_inbox.case_id
external_case_id already linked to a Case through prior import
explicit operator-approved mapping table
```

Forbidden matching candidates:

```txt
pet name alone
owner phone alone
species + pet name only
fuzzy text similarity
```

### 7.3 Case write strategy

The safest first real execution should be:

```txt
create-only
```

Do not do updates in the first real execution API unless a separate update policy is approved.

Recommended first policy:

```txt
If no explicit existing case_id is linked:
  create a new Case.
If an existing case_id is linked:
  block the item and require a separate update approval.
```

### 7.4 Audit requirements

Every Case write must produce an `audit_log` entry.

Minimum audit fields:

```txt
event_type = emr_real_import_case_write
source = pet-med-ai
request_id = emr-real-import-{batch_id}-{receipt_id}
clinician_id = operator_id
suggested_action = import operation summary
action_taken = case_created / case_update_blocked / case_updated
override_reason = clinical approval ID + rollback snapshot ID
metadata.batch_id
metadata.receipt_id
metadata.external_case_id
metadata.case_id
metadata.payload_hash
metadata.rollback_snapshot_id
```

### 7.5 Rollback requirements

The execute API must return:

```txt
rollback_plan
created_case_ids
updated_case_ids
audit_log_ids
batch_id
snapshot_id
```

If rollback cannot be reasonably performed, the execute API must not ship.

## 8. Minimum response contract for future execute API

Future response shape:

```json
{
  "message": "emr_import_execution_completed",
  "mode": "real_execution",
  "batch_id": "emr_batch_xxx",
  "writes_case_database": true,
  "creates_case": true,
  "updates_case": false,
  "downloads_attachments": false,
  "executes_real_import": true,
  "idempotent": true,
  "created_case_ids": [],
  "updated_case_ids": [],
  "blocked_items": [],
  "audit_log_ids": [],
  "rollback_plan": {
    "rollback_snapshot_id": "SNAPSHOT-...",
    "batch_id": "emr_batch_xxx",
    "case_ids_to_restore": []
  }
}
```

## 9. Recommended staged implementation after this risk review

Do not jump directly to full execution. Use this order:

1. `EMR real import execution API design doc V1`
2. `EMR real import execution API create-only V1`
3. `EMR real import execution API idempotency smoke V1`
4. `EMR real import rollback drill V1`
5. `EMR real import limited pilot V1`
6. `EMR real import update-policy review V1`

## 10. V1 outcome

This review recommends:

```txt
Proceed only to an execution API design document.
Do not implement real execution code yet.
```

The next safe stage is:

```txt
EMR real import execution API design doc V1
```
