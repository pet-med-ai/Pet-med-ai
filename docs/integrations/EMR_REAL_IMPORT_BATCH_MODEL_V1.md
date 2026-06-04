# EMR real import batch model V1

## Stage boundary

This stage creates database models for planning and freezing a future real EMR import batch.

It does **not** perform real import.

```txt
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
runs_real_import=false
```

## Why this model exists

Before Pet-Med-AI allows any EMR receipt to become a real `Case`, the clinic needs a frozen import batch with:

```txt
batch_id
source_system
receipt_count
ready_for_import_count
clinical_signoff_id
rollback_snapshot_id
status
created_by
approved_by
timestamps
```

This prevents ad-hoc real imports and makes every future import batch reviewable, signable, and rollback-aware.

## New tables

### emr_import_batches

Purpose: one row per planned real import batch.

Key fields:

```txt
batch_id
source_system
status
receipt_count
ready_for_import_count
rejected_count
review_action_count
clinical_signoff_id
rollback_snapshot_id
frozen_at
approved_at
started_at
completed_at
created_by
approved_by
note
metadata
created_at
updated_at
```

Recommended status values:

```txt
draft
frozen
clinical_signed
approved
running
completed
failed
rolled_back
cancelled
```

### emr_import_batch_receipts

Purpose: selected webhook receipts in a batch.

Key fields:

```txt
batch_id
receipt_id
review_status
ready_for_import
external_case_id
external_encounter_id
note
metadata
created_at
```

This is a selection and review snapshot table. It does not execute the import.

## Required gates before any future real import

A future real import implementation must verify:

```txt
1. All selected receipts exist in webhook_inbox.
2. Every receipt has passed EMR Webhook inbox review action.
3. The batch is frozen.
4. clinical_signoff_id is present.
5. rollback_snapshot_id is present.
6. audit_log records exist for review and approval.
7. The batch status is approved.
8. A separate real-import API / worker exists and has its own smoke tests.
```

## Explicit non-goals

This stage does not:

```txt
create Case
update Case
download attachments
write audit_log
consume queue
implement retry / DLQ
expose real import API
```

## Local migration

```bash
cd ~/Documents/Pet-med-ai/backend
python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

Expected head:

```txt
0005_emr_import_batches (head)
```

## Render migration

After deploy:

```bash
cd ~/project/src/backend
python3 -m alembic -c alembic.ini current
python3 -m alembic -c alembic.ini upgrade head
python3 -m alembic -c alembic.ini current
```

Expected head:

```txt
0005_emr_import_batches (head)
```

## Next stage

Recommended next stage:

```txt
EMR real import batch planning API V1
```

That stage should create and freeze batches from already reviewed webhook receipts, but still should not create Case records.
