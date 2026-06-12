# Automated Reminder Delivery Data Model V1

## Purpose

This stage adds the future database model layer for automated preventive care reminder delivery.

It is data model only.

It does not:

```txt
send SMS
send WeChat
send email
create provider credentials
create background workers
create cron jobs
open delivery feature flags
add provider adapters
create delivery API endpoints
change frontend UI
create Case records
update Case records
execute EMR import
```

## New ORM models

```txt
AutomatedReminderDeliveryTemplate
AutomatedReminderDeliveryAttempt
AutomatedReminderDeliveryReceipt
AutomatedReminderDeliverySuppressionRule
```

## New database tables

```txt
automated_reminder_delivery_templates
automated_reminder_delivery_attempts
automated_reminder_delivery_receipts
automated_reminder_delivery_suppression_rules
```

## Migration

```txt
backend/migrations/versions/0008_automated_delivery.py
revision = "0008_auto_delivery"
down_revision = "0007_preventive_care"
```

The revision id is intentionally shorter than 32 characters.

## Safety boundary

```txt
auto_send=false
sends_external_message=false
manual_review_required=true
dry_run=true
creates_case=false
updates_case=false
executes_real_import=false
```

## Design notes

`automated_reminder_delivery_templates` stores future approved message templates. No template in this stage is approved for live external delivery.

`automated_reminder_delivery_attempts` stores dry-run/manual-approval delivery attempts. It must default to:

```txt
dry_run=true
auto_send=false
sends_external_message=false
manual_review_required=true
```

`automated_reminder_delivery_receipts` stores future provider receipt metadata. No provider webhook is implemented in this stage.

`automated_reminder_delivery_suppression_rules` stores future cooldown/quiet/manual suppression rules. It does not send messages.

## Completion criteria

```txt
1. ORM models exist.
2. Alembic 0008 migration exists.
3. validate_automated_reminder_delivery_model.py passes.
4. validate_alembic_setup.py includes 0008 and automated delivery metadata tables.
5. smoke and CI static checks include the validator.
```
