# EMR real import execution dry-run V1

## Stage positioning

This stage adds a dry-run execution gate for previously planned EMR real-import candidate batches.

It reads:

- `emr_import_batches`
- `emr_import_batch_receipts`
- linked `webhook_inbox` receipts
- optional existing `cases` referenced by `webhook_inbox.case_id`

It generates:

- import diff
- would-create / would-update counts
- blocked item list
- rollback plan
- safety gate

It does not execute the import.

## Endpoint

```txt
POST /api/emr/import-batches/{batch_id}/execution-dry-run
```

Authentication is required.

Example request:

```json
{
  "operator_id": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-20260604-001",
  "rollback_snapshot_id": "SNAPSHOT-20260604-001",
  "include_payload_preview": false,
  "max_items": 100
}
```

## Safety boundary

This endpoint returns:

```txt
writes_database=false
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
```

It does not:

- create `Case`
- update `Case`
- download attachments
- change batch status
- enqueue import jobs
- write audit_log

## Why no writes in V1?

The execution dry-run must be repeatable and safe. It is intended to be run many times before a real import execution API exists.

The next stage must still be a separate audited implementation.

## Import diff

For each batch receipt, V1 emits:

```txt
receipt_id
external_case_id
external_encounter_id
operation
case_id
case_create_preview
existing_case_snapshot
field_diff
blocked_reasons
```

Operation is:

```txt
case_create_preview
case_update_preview
```

`case_update_preview` is only used when the receipt already references an internal `case_id`.

## Rollback plan

The endpoint returns a rollback plan that requires:

```txt
rollback_snapshot_id
database backup / snapshot before real import
batch_id
receipt_ids
manual signoff
```

This stage only drafts the rollback plan. It does not create a snapshot by itself.

## Go / No-Go

A real import implementation should not be built unless:

```txt
execution dry-run returns blocked_count = 0
clinical signoff is present
rollback snapshot ID is present
source receipts are frozen into a batch
batch has been reviewed by a clinician/admin
```

## Validation

```bash
python3 scripts/validate_emr_import_execution_dry_run.py
```

## Smoke

```bash
BASE_URL=http://127.0.0.1:8000 bash scripts/smoke_petmed.sh
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```
