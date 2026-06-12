# Automated Reminder Delivery Risk Review V1

## Purpose

This stage reviews the risks, requirements, and hard gates before Pet-Med-AI considers automated delivery of preventive care reminders.

Automated delivery means any system-initiated outbound message such as:

```txt
SMS
WeChat
email
push notification outside the app
automated phone call
third-party messaging provider callback
```

This stage is risk review only.

It does not:

```txt
send SMS
send WeChat
send email
create provider credentials
create background workers
create cron jobs
open delivery feature flags
change backend code
change frontend code
change database schema
run Alembic
auto-contact clients
create Case records
update Case records
execute EMR import
```

## Default decision

Default state:

```txt
NO-GO
```

Automated reminder delivery must stay blocked until a future implementation stage explicitly passes all gates.

## Current approved scope

The currently approved Preventive Care Reminder V1 scope is:

```txt
in-app reminders
manual front-desk queue
manual review
manual contact marker
manual cancel
client opt-out recording
weekly ops review
monthly ops review
ops dashboard summary
```

Current safety boundary:

```txt
auto_send=false
sends_external_message=false
manual_review_required=true
creates_case=false
updates_case=false
executes_real_import=false
```

## Why automated delivery is higher risk

Automated delivery adds risks that are not present in manual queue V1:

```txt
wrong client receives message
client opt-out ignored
message frequency too high
message appears to be medical diagnosis or prescription
rabies/local-law vaccine timing wrong
product-specific vaccine/deworming interval wrong
owner phone/email stale
message sent outside allowed hours
third-party provider credential leak
provider outage / duplicate sends
untracked delivery failure
client privacy complaint
```

## Required future controls before implementation

No automated delivery implementation may start unless all are designed and reviewed:

```txt
client consent model
opt-out enforcement
message template approval
clinician review policy
channel preference model
quiet hours / send window
rate limiting
deduplication
delivery log
failure log
provider credential storage
kill switch
dry-run mode
manual approval mode
P0 incident response
rollback plan
```

## Required feature flags

Future implementation must be feature-flag protected.

Proposed flags:

```txt
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true
```

Required default:

```txt
all delivery flags false
```

Exception:

```txt
dry-run flag may be true only if it sends no external message
```

## Required delivery states

Future delivery records must support:

```txt
draft
manual_review_required
approved_for_send
dry_run_only
queued
sent
delivered
failed
canceled
blocked_opt_out
blocked_quiet_hours
blocked_rate_limit
blocked_missing_consent
blocked_missing_channel
```

## Consent and opt-out gates

Automated delivery requires:

```txt
client consent recorded
channel-specific permission recorded
opt-out registry enforced before every send
opt-out snapshot stored on each delivery attempt
unsubscribe / opt-out instructions in message where applicable
no send if opt_out_all=true
no send if channel disabled
```

## Message content gate

All automated message templates must avoid diagnosis or prescription wording.

Required wording:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

Do not include:

```txt
confirmed diagnosis
prescription order
dose instruction
guaranteed due date without clinical review
fear-based urgency language
private diagnosis details unnecessary for reminder
```

## Send frequency gate

Minimum requirements:

```txt
no duplicate reminder for same pet/category within configured cooldown
daily send cap per owner
weekly send cap per owner
global provider send cap
quiet hours
manual suppression list
```

## Provider / credential gate

Before any provider integration:

```txt
credentials stored only in Render environment or provider secret store
no credentials in repo
no credentials in logs
provider webhook signing verified
provider delivery receipts verified
provider failure modes documented
```

## Audit / log gate

Future delivery must log:

```txt
delivery_id
owner_id
reminder_id
notification_id
channel
template_id
template_version
consent_snapshot
opt_out_snapshot
message_hash
provider_message_id
status
attempt_count
last_error
created_at
sent_at
delivered_at
canceled_at
```

## Pilot gate

First automated delivery pilot, if ever approved, must be:

```txt
single channel
small batch
manual approval before send
limited to non-regulated reminders first
no rabies reminders in first automated pilot
no medication/dose language
kill switch available
operator watching live
post-pilot review required
```

## Hard No-Go

Any one means no automated delivery:

```txt
monthly review not completed
weekly ops completion rate < 75%
online smoke not 100%
schema_ok=false
database_revision != alembic_head
client opt-out incident exists
external message was previously sent unexpectedly
secret leak exists
no kill switch
no provider credential plan
no delivery log model
no template approval process
no quiet hours
no rate limit
no duplicate suppression
no rollback owner
```

## Required next stage if this review passes

Do not jump directly to implementation.

Next stage must be:

```txt
Automated Reminder Delivery Design V1
```

not:

```txt
Automated Reminder Delivery Implementation V1
```

## Completion criteria

This risk review stage is complete when:

```txt
1. Risk review runbook exists.
2. Risk register exists.
3. Go / No-Go checklist exists.
4. Channel matrix exists.
5. Provider credential checklist exists.
6. Incident playbook exists.
7. Release addendum exists.
8. Validator exists and is included in smoke.
9. CI static checks include validator.

```
