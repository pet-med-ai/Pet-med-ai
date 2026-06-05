# EMR real import execute API dry-run-protected skeleton V1

## Stage

This stage adds the future real execution endpoint shell:

```txt
POST /api/emr/import-batches/{batch_id}/execute
```

The endpoint is intentionally blocked in V1. It is a contract and safety-gate skeleton only.

## Why this exists

Pet-Med-AI already has:

```txt
EMR webhook receipt persistence
EMR -> Case mapping dry-run
Webhook inbox review action
EMR real import batch planning
EMR execution dry-run
Clinical approval API / UI
Execution result model
```

The next engineering risk is accidentally crossing from planning into real Case writes. This V1 skeleton proves that the route can exist while remaining hard-disabled.

## Request draft

```json
{
  "operator_id": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-20260605-001",
  "rollback_snapshot_id": "SNAPSHOT-20260605-001",
  "dry_run_ack": true,
  "execution_confirmation": "I_UNDERSTAND_THIS_ENDPOINT_IS_DISABLED",
  "request_id": "execute-skeleton-20260605-001",
  "note": "Contract inspection only. Real execution remains disabled.",
  "metadata": {
    "ui": "emr_import_batch_planning"
  },
  "max_items": 100
}
```

## Response behavior

The endpoint returns HTTP 409 by design.

Required response markers:

```txt
message=emr_real_import_execute_blocked
mode=execute_api_skeleton
blocked_by_design=true
execution_enabled=false
writes_database=false
writes_case_database=false
writes_audit_log=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

## What it may read

The endpoint may read:

```txt
emr_import_batches
emr_import_batch_receipts
webhook_inbox
cases for diff comparison only
```

It may also call the existing execution dry-run report builder.

## What it must not do

```txt
No Case creation
No Case update
No attachment download
No audit_log write
No execution result write
No batch status mutation
No queue enqueue
No real import
```

## Gate before a future implementation

A future real execution implementation must be a separate stage and must require:

```txt
approved / clinical_signed batch
clinical_signoff_id
rollback_snapshot_id
latest execution dry-run hash
operator signoff
database backup verified
rollback rehearsal passed
small pilot batch only
smoke ALL PASS before and after
post-execution audit checklist
```

## Completion criteria

```txt
1. POST /api/emr/import-batches/{batch_id}/execute exists.
2. It returns HTTP 409 with blocked_by_design=true.
3. It returns the current execution dry-run quality gate and import diff summary.
4. It never writes Case.
5. It never mutates emr_import_batches.
6. It never writes audit_log.
7. Smoke verifies the block.
```
