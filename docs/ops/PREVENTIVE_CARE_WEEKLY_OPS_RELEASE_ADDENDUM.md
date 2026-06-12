# Release record addendum: Preventive Care Reminder Weekly Ops Runbook

Copy this section into the current release record after the first weekly ops run.

## Weekly ops evidence

```txt
week_id:
week_start:
week_end:
operator_id:
online_smoke_result:
schema_ok:
database_revision:
alembic_head:
preventive_attention:
reminders_open:
due_today:
due_soon:
overdue:
queue_needs_review:
manual_contacted:
blocked_opt_out:
recent_events_30d:
```

## Safety checks

```txt
[ ] auto_send=false
[ ] sends_external_message=false
[ ] manual_review_required=true
[ ] read_only=true for ops summary
[ ] no Case created
[ ] no Case updated
[ ] no EMR import executed
[ ] no secret leak found
[ ] opt-out items not contacted
```

## Weekly decision

```txt
PASS / PAUSE / ESCALATE:
Reason:
Operator:
Date:
```
