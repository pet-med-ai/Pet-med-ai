# Automated Reminder Delivery Manual Approval UI V1

## Purpose

This stage adds a manual approval UI for automated reminder delivery dry-run attempts.

It supports:

```txt
list dry-run delivery attempts
filter by status
filter by channel
manual review dry-run attempt
mark changes requested
reject dry-run attempt
cancel dry-run attempt
```

This stage does not send any external message.

It does not:

```txt
send SMS
send WeChat
send email
call provider APIs
create provider credentials
create background workers
create cron jobs
create Case records
update Case records
execute EMR import
```

## Frontend route

```txt
/automated-reminder-delivery/manual-approval
```

## Backend addition

This stage adds a dry-run review endpoint:

```txt
POST /api/automated-reminder-delivery/attempts/{delivery_id}/manual-review
```

The endpoint writes review metadata to the dry-run attempt only.

It must keep:

```txt
dry_run=true
auto_send=false
sends_external_message=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

## UI labels

```txt
自动提醒发送人工审批（Dry-run）
审核通过 dry-run
要求修改
拒绝
取消
auto_send=false
sends_external_message=false
```

## Important safety rule

Approving a dry-run attempt means:

```txt
approved for dry-run review evidence only
```

It does not mean:

```txt
approved for live SMS / WeChat / email delivery
```

## Completion criteria

```txt
1. Manual approval UI page exists.
2. App.jsx imports and routes the page.
3. backend automated delivery API has manual-review endpoint.
4. validator exists and passes.
5. smoke covers manual-review endpoint and user isolation.
6. CI static checks include validator.
```
