# Preventive Care Reminder Data Model V1

## Purpose

This stage adds the database model layer for vaccine, deworming, parasite prevention, fecal exam, wellness exam, consent preference, and manual notification queue records.

This is data model only.

It does not:

```txt
add API endpoints
add frontend UI
send SMS / WeChat / email
create notification workers
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
```

## New ORM models

```txt
PreventiveCareRuleSet
PreventiveCareReminder
PreventiveCareEvent
PreventiveCareClientPreference
PreventiveCareNotificationQueue
```

## New database tables

```txt
preventive_care_rule_sets
preventive_care_reminders
preventive_care_events
preventive_care_client_preferences
preventive_care_notification_queue
```

## Migration

```txt
backend/migrations/versions/0007_preventive_care.py
revision = "0007_preventive_care"
down_revision = "0006_emr_import_results"
```

The revision id is intentionally shorter than 32 characters.

## Safety boundary

```txt
sends_external_message=false
allow_auto_send=false
manual_review_required=true
writes_case_database=false
executes_real_import=false
```

## Design notes

`preventive_care_reminders` is linked to:

```txt
owner_id
case_id
future pet_id
```

Short-term V1 can attach reminders to a Case. Long-term, a Pet Profile model can own reminders across visits.

`preventive_care_notification_queue` is draft/manual-review only. It exists to prepare a future front-desk queue; it does not send messages.

## Completion criteria

```txt
1. ORM models exist.
2. Alembic 0007 migration exists.
3. validate_preventive_care_reminder_model.py passes.
4. validate_alembic_setup.py includes 0007 and metadata tables.
5. smoke and CI static checks include the validator.
```
