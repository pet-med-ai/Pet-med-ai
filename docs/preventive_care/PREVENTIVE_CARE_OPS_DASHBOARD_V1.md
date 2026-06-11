# Preventive Care Reminder Ops Dashboard V1

## Purpose

This stage adds an operational dashboard summary for Preventive Care Reminder V1.

It helps the clinic see:

```txt
total reminders
open reminders
due today
due soon
overdue reminders
notification queue needs review
manual contacted count
blocked opt-out count
recent 30-day preventive events
```

## Backend endpoint

```txt
GET /api/preventive-care/ops/summary
```

## Frontend placement

The existing Ops Dashboard page is extended:

```txt
/ops
```

The dashboard remains an operational read-only view.

## Safety boundary

```txt
read_only=true
writes_database=false
creates_case=false
updates_case=false
auto_send=false
sends_external_message=false
executes_real_import=false
manual_review_required=true
```

This stage does not:

```txt
send SMS
send WeChat
send email
create reminder records
create queue records
create Case
update Case
execute EMR import
```

## Display cards

Expected UI cards:

```txt
Preventive attention
Reminders open
Due today
Queue needs review
Manual contacted
Blocked opt-out
Recent events 30d
```

## Completion criteria

```txt
1. backend/preventive_care_ops_api.py exists.
2. backend/main.py includes preventive_care_ops_api_router.
3. OpsDashboard.jsx displays Preventive Care Reminder Ops Dashboard V1.
4. smoke covers /api/preventive-care/ops/summary.
5. validator exists and is included in smoke and CI static checks.
```
