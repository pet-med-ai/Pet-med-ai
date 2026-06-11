# Preventive Care Reminder Spec V1

## Purpose

This stage defines the Pet-Med-AI preventive care reminder specification for:

```txt
vaccine reminders
deworming reminders
parasite prevention reminders
annual / semiannual preventive exam reminders
```

This is a specification-only stage.

It does not:

```txt
create database tables
add Alembic migrations
send SMS / WeChat / email
create notification jobs
change backend APIs
change frontend UI
write Case records
change EMR import state
```

## Product goal

Pet-Med-AI should help the clinic remember preventive care tasks for pets over time.

V1 focuses on:

```txt
dogs
cats
vaccines
internal deworming
external parasite prevention
fecal exam reminders
heartworm / vector-borne testing reminder placeholders
```

The system must treat all generated dates as:

```txt
clinical reminder suggestions
```

not as automatic medical orders.

## Medical safety boundary

Preventive reminders must never replace clinician judgment.

Required wording:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

## Why V1 is spec-only

Automatic reminder delivery touches:

```txt
owner phone / contact information
client consent
opt-out
medical liability
local vaccine law
product-specific interval
species / age / reproductive status
travel / boarding / exposure risks
```

So V1 must not send external messages.

## Default reminder categories

```txt
canine_core_vaccine
canine_rabies
canine_leptospirosis
canine_noncore_lifestyle_vaccine
feline_core_vaccine
feline_rabies
feline_felv_risk_based
internal_deworming
external_parasite_prevention
fecal_exam
heartworm_test_placeholder
annual_preventive_exam
```

## Suggested MVP product behavior

The future app should support:

```txt
create reminder
view reminder
complete reminder
snooze reminder
dismiss reminder
disable reminder for this pet
record clinician override
record client opt-out
```

## Reminder status values

```txt
draft
active
due_soon
due
overdue
completed
snoozed
dismissed
disabled
opted_out
```

## Reminder timing model

Every reminder should have:

```txt
due_date
due_window_start
due_window_end
reminder_lead_days
last_completed_at
next_due_date
source_rule_id
clinician_override
client_opt_out
```

## Scope of V1 rules

Rules are seed rules only. They are intentionally conservative and must be editable before clinical use.

Examples:

```txt
puppy_kitten_deworming_early
adult_quarterly_deworming_if_no_year_round_control
monthly_broad_spectrum_parasite_control_placeholder
canine_core_vaccine_adult_review
feline_core_vaccine_adult_review
rabies_local_law_review
annual_wellness_exam
semiannual_senior_wellness_exam
```

## Data placement strategy

Short-term:

```txt
link reminders to owner_id and case_id
copy pet display fields from Case
```

Long-term:

```txt
introduce Pet Profile / pet_id
link reminders to pet_id
merge reminders across cases
```

V1 should not force a Pet Profile migration yet.

## Required future entities

Future data model should likely include:

```txt
preventive_care_reminders
preventive_care_events
preventive_care_rule_sets
preventive_care_notification_queue
preventive_care_client_preferences
```

## Consent / opt-out

Before external messaging, the system must support:

```txt
client consent recorded
client opt-out recorded
channel preference
message frequency limit
manual review before first send
```

V1 does not send messages.

## Notification roadmap

### Stage 1

```txt
in-app reminder only
```

### Stage 2

```txt
manual call list / front desk queue
```

### Stage 3

```txt
approved outbound WeChat/SMS/email with opt-out and logs
```

## Safety markers

```txt
writes_database=false
creates_case=false
updates_case=false
sends_external_message=false
executes_real_import=false
```

## Completion criteria

```txt
1. Preventive care reminder spec exists.
2. Vaccine/deworming seed rules CSV exists.
3. Field model JSON exists.
4. Client communication safety SOP exists.
5. Validator exists and is included in smoke.
6. CI static checks include the validator.
```
