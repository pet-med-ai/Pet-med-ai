# Preventive Care Reminder Release Record V1

## Release identity

```txt
release_name: preventive-care-reminder-v1
risk_class: clinical_workflow_in_app
owner: HS-0001
stage: release_record
```

## Purpose

This release record captures the full evidence package for the Preventive Care Reminder V1 feature set.

The feature set includes:

```txt
Preventive Care Reminder Spec V1
Preventive Care Reminder Data Model V1
Preventive Care Reminder Rule Engine Dry-run V1
Preventive Care Reminder API V1
Preventive Care Reminder UI V1
Preventive Care Reminder Notification Queue V1
Preventive Care Reminder Notification Queue UI V1
Preventive Care Reminder Online Verification V1
```

This stage is release documentation only.

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
create Case records
update Case records
open ENABLE_EMR_REAL_IMPORT
execute EMR import
```

## Release scope

Preventive Care Reminder V1 supports:

```txt
vaccine reminder rules
deworming reminder rules
parasite prevention reminders
fecal exam reminder placeholders
annual / semiannual preventive exam reminders
dry-run reminder calculation
in-app reminder creation
reminder complete / snooze / dismiss / disable
client preference / opt-out recording
manual front-desk notification queue
manual queue review
manual contact marker
queue cancellation
```

## Explicit non-goals

This release does not support:

```txt
automated SMS
automated WeChat
automated email
background notification worker
external message delivery
medical order automation
prescription generation
Case creation
Case update
EMR import execution
```

## Safety boundary

The release must preserve:

```txt
sends_external_message=false
auto_send=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

## Database evidence

Required:

```txt
alembic_head=0007_preventive_care
database_revision=0007_preventive_care
schema_ok=true
```

The `0007_preventive_care` revision id is intentionally short enough for PostgreSQL `alembic_version.version_num VARCHAR(32)`.

## Feature evidence

Required completed validations:

```txt
python3 scripts/validate_preventive_care_reminder_spec.py
python3 scripts/validate_preventive_care_reminder_model.py
python3 scripts/validate_preventive_care_rule_engine_dry_run.py
python3 scripts/validate_preventive_care_reminder_api.py
python3 scripts/validate_preventive_care_reminder_ui.py
python3 scripts/validate_preventive_care_notification_queue.py
python3 scripts/validate_preventive_care_notification_queue_ui.py
python3 scripts/validate_preventive_care_online_verification.py
```

Required platform validations:

```txt
bash scripts/ci_static_checks.sh
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
GitHub Actions CI Gate latest run green
```

## Clinical safety statement

Preventive Care Reminder V1 is a clinic workflow helper.

It must be described as:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

## Client communication statement

The system does not send external messages.

Allowed:

```txt
in-app reminder
manual front-desk contact queue
manual review
manual contact marker
```

Not allowed in V1:

```txt
automatic SMS
automatic WeChat
automatic email
automatic phone call
```

## Go / Pause / No-Go criteria

### GO

All are true:

```txt
CI static checks PASS
GitHub Actions latest run green
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head == 0007_preventive_care
preventive care online verification completed
no external message sent by system
client opt-out behavior verified
user isolation verified
```

### PAUSE

Any minor evidence missing:

```txt
manual browser verification incomplete
release addendum not copied into release record
non-blocking UI copy issue
```

### NO-GO

Any one condition below:

```txt
online smoke fails
GitHub Actions red
schema_ok=false
database_revision != alembic_head
preventive API creates or updates Case
notification queue sends external message
client opt-out ignored
secret appears in frontend console or backend logs
```

## Final decision

Default:

```txt
NO-GO until all evidence is filled.
```

Final decision options:

```txt
GO
PAUSE
NO-GO
ROLLBACK-REVIEW
```

## Completion criteria

This release record stage is complete when:

```txt
1. Release record exists.
2. Release checklist exists.
3. Release evidence CSV exists.
4. Rollback notes exist.
5. Triage matrix exists.
6. Validator exists and is included in smoke.
7. CI static checks include validator.
```
