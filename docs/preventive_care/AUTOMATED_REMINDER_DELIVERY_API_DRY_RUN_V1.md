# Automated Reminder Delivery API Dry-run V1

## Purpose

This stage adds a backend API that combines:

```txt
Automated Reminder Delivery Template Registry V1
Automated Reminder Delivery Eligibility Engine Dry-run V1
Automated Reminder Delivery Data Model V1
Preventive Care Reminder Notification Queue V1
```

It can create a saved dry-run delivery attempt.

It does not send any external message.

## Endpoints

```txt
POST /api/automated-reminder-delivery/dry-run
GET /api/automated-reminder-delivery/attempts
GET /api/automated-reminder-delivery/attempts/{delivery_id}
POST /api/automated-reminder-delivery/attempts/{delivery_id}/cancel
```

## What dry-run does

```txt
loads reminder
loads notification queue item if provided
loads template
renders message preview
runs eligibility engine
stores AutomatedReminderDeliveryAttempt if save_attempt=true
returns blocked reasons and safety flags
```

## Safety boundary

```txt
dry_run=true
auto_send=false
sends_external_message=false
creates_case=false
updates_case=false
executes_real_import=false
```

Write endpoints may write:

```txt
automated_reminder_delivery_attempts
```

They must not:

```txt
send SMS
send WeChat
send email
call provider APIs
create provider credentials
create background workers
create Case
update Case
execute EMR import
```

## Completion criteria

```txt
1. backend/automated_reminder_delivery_api.py exists.
2. backend/main.py includes automated_reminder_delivery_api_router.
3. validator exists and passes.
4. smoke covers dry-run create, list, get, cancel, auth, and user isolation.
5. CI static checks include validator.
```
