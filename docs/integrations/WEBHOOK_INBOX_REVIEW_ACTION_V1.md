# EMR Webhook inbox review action V1

## Stage boundary

This stage adds a human review action for persisted EMR webhook inbox receipts.

It still does **not** perform real EMR import.

## Safety guarantees

```txt
writes_webhook_inbox = true
writes_audit_log = true
writes_case_database = false
creates_case = false
updates_case = false
downloads_attachments = false
```

## Backend API

```txt
POST /api/webhooks/emr/inbox/{receipt_id}/review-action
```

Authenticated request body:

```json
{
  "action": "ready_for_import",
  "clinician_id": "HS-0001",
  "reason": "映射字段完整，已人工复核",
  "note": "可进入后续真实导入评估，但本阶段不创建病例。",
  "request_id": "optional-review-request-id",
  "metadata": {"ui": "webhook_inbox_detail"}
}
```

Supported actions:

```txt
ready_for_import -> webhook_inbox.status = ready_for_import
needs_fix        -> webhook_inbox.status = needs_fix
rejected         -> webhook_inbox.status = rejected_by_reviewer
```

`needs_fix` and `rejected` require at least 10 characters across reason/note.

## Audit behavior

Every review action appends one `audit_log` row with:

```txt
event_type = webhook_inbox_review
source = pet-med-ai
action_taken = selected action
override_reason = reason
note = note
metadata.receipt_id / status_before / status_after
```

Audit log remains append-only. No update/delete API is introduced.

## Frontend UI

The existing `/webhooks/emr/inbox` page now shows an action panel in the receipt detail section:

```txt
可进入后续真实导入评估
需要 EMR / 数据修复
拒绝导入
```

The UI requires `clinician_id`; for fix/reject actions it also requires a meaningful reason or note.

## Not included

```txt
No Case creation
No Case update
No attachment download
No EMR real ingestion
No queue consumer
No DLQ implementation
```
