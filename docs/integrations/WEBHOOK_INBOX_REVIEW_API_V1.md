# EMR Webhook inbox review API V1

## Stage

`EMR Webhook inbox review API V1`

## Goal

Expose authenticated, read-only review endpoints for `webhook_inbox` receipts.

This stage supports operational review of signed EMR dry-run receipts and Case mapping previews without creating Pet-Med-AI cases.

## Safety boundary

This stage does:

```txt
Read webhook_inbox receipts
Return paginated receipt summaries
Return a single receipt detail
Omit raw payload by default
Require login token
```

This stage does not:

```txt
Create Case
Update Case
Create ConsultSession
Download attachments
Write audit_log
Mutate webhook_inbox
Expose POST/PUT/PATCH/DELETE review routes
```

## Endpoints

### List receipts

```txt
GET /api/webhooks/emr/inbox?page=1&page_size=20
GET /api/webhooks/emr/inbox?status=accepted
GET /api/webhooks/emr/inbox?external_case_id=CASE-2026-000123
GET /api/webhooks/emr/inbox?idempotency_key=...
```

Response shape:

```json
{
  "message": "webhook_inbox_receipts",
  "mode": "review_api",
  "review_only": true,
  "writes_database": false,
  "creates_case": false,
  "downloads_attachments": false,
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

### Read one receipt

```txt
GET /api/webhooks/emr/inbox/{receipt_id}
```

Raw payload is omitted by default:

```json
{
  "message": "webhook_inbox_receipt",
  "receipt": {
    "receipt_id": "rcpt_xxx",
    "payload_omitted": true,
    "mapped_case_preview": {}
  }
}
```

Controlled troubleshooting can request:

```txt
GET /api/webhooks/emr/inbox/{receipt_id}?include_payload=true
```

## Review fields

Receipt summary includes:

```txt
receipt_id
source
event_type
idempotency_key
payload_hash
signature_hash
external_case_id
external_encounter_id
case_id
status
dry_run
validation_error_count
validation_warning_count
has_mapped_case_preview
error_code
received_at
processed_at
created_at
updated_at
```

Detail includes:

```txt
validation_errors
validation_warnings
mapped_case_preview
error_message
payload_omitted
payload when include_payload=true
```

## Validation

Run:

```bash
python3 scripts/validate_webhook_inbox_review_api.py
```

Smoke covers:

```txt
GET /api/webhooks/emr/inbox returns 200 for logged-in user
GET /api/webhooks/emr/inbox/{receipt_id} returns mapped preview
unauthenticated inbox request returns 401
missing receipt returns 404
API remains read-only
```

## Next gate

After this stage, the next safe stage is:

```txt
EMR Webhook inbox detail UI V1
```

or:

```txt
EMR Webhook import approval dry-run V1
```

Real Case ingestion must remain a separate audited implementation with rollback and clinical sign-off.
