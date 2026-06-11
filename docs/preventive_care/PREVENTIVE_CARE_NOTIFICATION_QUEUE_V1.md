# Preventive Care Reminder Notification Queue V1

## Purpose

This stage adds a manual front-desk notification queue for preventive care reminders.

It is not an automatic messaging system.

## Scope

The queue supports:

```txt
create draft contact item from reminder
list notification queue
manual review
mark manually contacted
cancel queue item
respect client opt-out snapshot
```

## Endpoints

```txt
GET /api/preventive-care/notification-queue
POST /api/preventive-care/notification-queue/draft
POST /api/preventive-care/notification-queue/{notification_id}/review
POST /api/preventive-care/notification-queue/{notification_id}/mark-contacted
POST /api/preventive-care/notification-queue/{notification_id}/cancel
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

This stage does not:

```txt
send SMS
send WeChat
send email
create background worker
auto-contact clients
create Case
update Case
```

## Client opt-out

When a reminder or client preference indicates opt-out, the queue item is created as:

```txt
status=blocked_opt_out
failure_code=client_opt_out
manual_review_required=true
sends_external_message=false
```

## Completion criteria

```txt
1. backend/preventive_care_notification_api.py exists.
2. backend/main.py includes preventive_care_notification_api_router.
3. validator exists and passes.
4. smoke covers draft, review, mark-contacted, cancel, and user isolation.
5. CI static checks include validator.
```
