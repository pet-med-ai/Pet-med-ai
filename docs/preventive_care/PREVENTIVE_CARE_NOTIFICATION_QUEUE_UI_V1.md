# Preventive Care Reminder Notification Queue UI V1

## Purpose

This stage adds a frontend page for the preventive care manual notification queue.

It is a front desk workflow page, not an automatic messaging system.

## Route

```txt
/preventive-care/notification-queue
```

## Scope

The UI supports:

```txt
list manual notification queue items
filter by status
filter by channel
create draft queue item from reminder_id
manual review
mark manually contacted
cancel queue item
```

## Safety boundary

```txt
sends_external_message=false
auto_send=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

The UI does not:

```txt
send SMS
send WeChat
send email
create background worker
auto-contact clients
create Case
update Case
```

## Required labels

```txt
预防保健前台待联系队列
创建人工联系草稿
人工审核
标记已人工联系
取消
auto_send=false
sends_external_message=false
```

## Completion criteria

```txt
1. PreventiveCareNotificationQueuePage.jsx exists.
2. App.jsx imports and routes the page.
3. Home page links to the page.
4. Validator exists and passes.
5. Frontend build passes.
6. smoke and CI include validator.
```
