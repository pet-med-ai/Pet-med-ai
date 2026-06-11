# Preventive Care Reminder API V1

## Purpose

This stage adds authenticated backend APIs for in-app preventive care reminders.

It supports:

```txt
list seed rules
dry-run reminder calculation
list reminders
create reminder
complete reminder
snooze reminder
dismiss reminder
disable reminder
read/save client preferences
```

It does not:

```txt
send SMS / WeChat / email
create background jobs
auto-send notification queue items
create Case records
update Case records
execute EMR import
```

## Endpoints

```txt
GET /api/preventive-care/rules
POST /api/preventive-care/dry-run
GET /api/preventive-care/reminders
POST /api/preventive-care/reminders
POST /api/preventive-care/reminders/{reminder_id}/complete
POST /api/preventive-care/reminders/{reminder_id}/snooze
POST /api/preventive-care/reminders/{reminder_id}/dismiss
POST /api/preventive-care/reminders/{reminder_id}/disable
GET /api/preventive-care/client-preferences
PUT /api/preventive-care/client-preferences
```

## Security model

All endpoints require login.

Rules:

```txt
current user can access only their own reminders
case_id is checked against current user owner_id
external messaging is disabled
client opt-out can be recorded
```

## Safety markers

Read-only endpoints return:

```txt
writes_database=false
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```

Write endpoints may return:

```txt
writes_database=true
```

but must still return:

```txt
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```

## Completion criteria

```txt
1. backend/preventive_care_api.py exists.
2. backend/main.py includes preventive_care_api_router.
3. validator exists and passes.
4. smoke and CI include validator.
5. smoke covers dry-run, create, complete, snooze, dismiss, disable, client preferences.
```
