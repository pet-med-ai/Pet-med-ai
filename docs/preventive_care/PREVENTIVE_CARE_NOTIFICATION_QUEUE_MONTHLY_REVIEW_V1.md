# Preventive Care Reminder Notification Queue Monthly Review V1

## Purpose

This runbook defines the monthly review routine for the Preventive Care Reminder notification queue.

It is intended for clinic owner / clinical ops / front desk lead monthly review.

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

## Monthly owner

Primary owner:

```txt
clinical_ops_owner
```

Required participants:

```txt
front_desk_owner
release_owner
security_owner if any P0/P1 safety issue
```

Optional participants:

```txt
clinic_owner
developer
rollback_owner
```

## Recommended schedule

```txt
First business day of each month
```

Recommended duration:

```txt
30 to 45 minutes
```

## Inputs

Required inputs:

```txt
last 4 weekly ops logs
latest online smoke result
latest GitHub Actions status
latest /api/system/version evidence
latest /ops screenshot or values
latest /preventive-care/notification-queue review
client opt-out issue list
manual contact outcome notes
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

## Monthly workflow

### 1. Preflight

Confirm:

```txt
GitHub Actions CI Gate latest run green
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
database_revision == 0007_preventive_care
```

If any fail:

```txt
monthly review can continue as incident review
but do not expand preventive care operations
do not enable any automated notification
```

### 2. Review weekly logs

Review the last 4 weekly logs:

```txt
PREVENTIVE_CARE_WEEKLY_OPS_LOG_TEMPLATE.csv entries
```

Aggregate:

```txt
total preventive attention
total reminders open
total due today
total overdue
total queue needs review
total manual contacted
total blocked opt-out
total recent events 30d
escalations count
```

### 3. Review queue throughput

From `/ops` and `/preventive-care/notification-queue`, assess:

```txt
new queue drafts
reviewed queue items
contacted_manually count
canceled count
blocked_opt_out count
backlog count
```

Monthly questions:

```txt
Are draft queue items being reviewed within 2 business days?
Are overdue reminders increasing?
Are blocked opt-outs respected?
Are manual contacted records complete?
Are front desk notes usable for follow-up?
```

### 4. Review clinical quality

Sample review:

```txt
5 to 10 completed preventive reminders
5 to 10 notification queue items
all blocked_opt_out items
any P0/P1 triage items
```

Check:

```txt
reminder category is appropriate
manual contact note is clinically reasonable
no client opt-out was bypassed
no external message was automatically sent
no Case was created or updated unexpectedly
```

### 5. Review safety gates

Required every month:

```txt
auto_send=false
sends_external_message=false
manual_review_required=true
read_only=true for ops summary
creates_case=false
updates_case=false
executes_real_import=false
```

### 6. Review client opt-out

Review all:

```txt
client_opt_out_snapshot=true
blocked_opt_out
opt_out_all=true
```

Required conclusion:

```txt
Do not contact blocked opt-out clients.
Do not override opt-out without explicit clinical_ops_owner approval and documented reason.
```

### 7. Decide monthly status

Decision options:

```txt
PASS
PAUSE
ESCALATE
IMPROVE
```

Definitions:

```txt
PASS: operations are safe and under control.
PAUSE: process incomplete or evidence missing; no expansion.
ESCALATE: P0/P1 safety/compliance/reliability issue exists.
IMPROVE: safe but operational improvements are needed next month.
```

## Monthly KPIs

Minimum monthly metrics:

```txt
online_smoke_pass_rate
weekly_ops_completion_rate
preventive_attention_total
overdue_reminders_total
queue_needs_review_total
manual_contacted_total
blocked_opt_out_total
queue_cancel_rate
opt_out_incident_count
external_message_sent_count
secret_leak_count
```

## Expansion gate

Do not proceed to any automated delivery stage unless all are true for at least one monthly review:

```txt
online smoke pass rate = 100%
weekly ops completion rate >= 75%
external_message_sent_count = 0
opt_out_incident_count = 0
secret_leak_count = 0
queue backlog is stable or decreasing
manual review process is consistently followed
```

Even if all are true, next stage should still be:

```txt
Automated Reminder Delivery Risk Review V1
```

not direct implementation.

## Hard Stop

Any one means stop expansion and escalate:

```txt
external SMS / WeChat / email sent unexpectedly
auto_send=true
sends_external_message=true
manual_review_required=false
client opt-out ignored
Case created or updated unexpectedly
EMR import executed unexpectedly
secret appears in console or Render logs
online smoke fails repeatedly
schema mismatch
```

## Completion criteria

This monthly review stage is complete when:

```txt
1. Monthly review runbook exists.
2. Monthly checklist exists.
3. Monthly report template exists.
4. Monthly KPI scorecard exists.
5. Monthly triage matrix exists.
6. Release addendum exists.
7. Validator exists and is included in smoke.
8. CI static checks include validator.
```
