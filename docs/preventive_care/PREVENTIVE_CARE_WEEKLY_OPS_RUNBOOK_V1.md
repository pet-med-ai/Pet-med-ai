# Preventive Care Reminder Weekly Ops Runbook V1

## Purpose

This runbook defines the weekly operating routine for Pet-Med-AI Preventive Care Reminder V1.

It turns the vaccine / deworming / preventive-care feature set into a repeatable clinic operations workflow.

This stage is operations documentation and validation only.

It does not:

```txt
change backend code
change frontend code
change database schema
run Alembic
send SMS
send WeChat
send email
create background worker
auto-contact clients
create reminders automatically
create queue items automatically
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
execute EMR import
```

## Weekly owner

Recommended weekly owner:

```txt
front_desk_owner
```

Backup owners:

```txt
clinical_ops_owner
rollback_owner
release_owner
```

## Recommended schedule

```txt
Every Monday morning before outpatient peak
or every Friday afternoon before weekend follow-up
```

Recommended duration:

```txt
10 to 20 minutes
```

## Required pages

Frontend:

```txt
https://pet-med-ai-frontend-static.onrender.com/ops
https://pet-med-ai-frontend-static.onrender.com/preventive-care/notification-queue
```

Backend smoke command:

```bash
cd ~/Documents/Pet-med-ai
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

## Weekly workflow

### 1. Preflight

Run or confirm:

```txt
GitHub Actions CI Gate latest run green
online smoke ALL PASS
/api/system/version schema_ok=true
database_revision == alembic_head
database_revision == 0007_preventive_care
```

If any fail:

```txt
stop weekly reminder operations
do not create new queue items
escalate to release_owner / developer
```

### 2. Open Ops Dashboard

Open:

```txt
/ops
```

Confirm:

```txt
Preventive Care Reminder Ops Dashboard V1 visible
read_only=true
writes_database=false
auto_send=false
sends_external_message=false
manual_review_required=true
```

Record:

```txt
Preventive attention
Reminders open
Due today
Queue needs review
Manual contacted
Blocked opt-out
Recent events 30d
```

### 3. Review overdue / due reminders

Prioritize:

```txt
overdue reminders
due today reminders
due soon reminders
blocked opt-out items
queue needs review
```

Clinical rule:

```txt
All vaccine / deworming reminders are suggestions, not medical orders.
Schedule and product must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

### 4. Process queue items

Open:

```txt
/preventive-care/notification-queue
```

For each queue item:

```txt
draft -> manual review -> manual contact -> mark contacted
or draft -> cancel
or blocked_opt_out -> do not contact
```

Allowed actions:

```txt
manual review
manual phone call
manual WeChat handled outside system
manual SMS handled outside system
cancel
```

System must not:

```txt
send SMS
send WeChat
send email
auto-contact clients
```

### 5. Respect client opt-out

If item shows:

```txt
client_opt_out_snapshot=true
blocked_opt_out
```

Then:

```txt
do not contact
do not manually override without clinical_ops_owner approval
record blocked opt-out count
```

### 6. Complete weekly log

Record:

```txt
week_start
week_end
operator_id
online_smoke_result
schema_ok
database_revision
alembic_head
preventive_attention
reminders_open
due_today
overdue
queue_needs_review
manual_contacted
blocked_opt_out
actions_taken
escalations
final_status
```

## Weekly decision states

```txt
PASS
PAUSE
ESCALATE
```

### PASS

```txt
online smoke passed
safety gates OK
queue reviewed
no P0/P1 issue
```

### PAUSE

```txt
minor evidence missing
operator cannot complete queue review
unclear reminder data
```

### ESCALATE

```txt
smoke fails
schema mismatch
secret leak
external message sent unexpectedly
opt-out ignored
API 500 on queue or ops dashboard
```

## Safety gates

Required every week:

```txt
read_only=true for ops summary
writes_database=false for ops summary
auto_send=false
sends_external_message=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

## Hard Stop

Any one means stop weekly operations and escalate:

```txt
online smoke fails
GitHub Actions red
schema_ok=false
database_revision != alembic_head
database_revision != 0007_preventive_care
Ops Dashboard missing Preventive Care section
Notification Queue page fails to load
auto_send=true
sends_external_message=true
manual_review_required=false
client opt-out ignored
Case created or updated unexpectedly
secret appears in console or Render logs
```

## Completion criteria

This weekly ops runbook stage is complete when:

```txt
1. Weekly runbook exists.
2. Weekly checklist exists.
3. Weekly log template exists.
4. KPI threshold table exists.
5. Escalation / triage matrix exists.
6. Release addendum exists.
7. Validator exists and is included in smoke.
8. CI static checks include validator.
```
