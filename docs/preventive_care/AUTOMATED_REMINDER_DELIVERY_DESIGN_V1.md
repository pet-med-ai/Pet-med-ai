# Automated Reminder Delivery Design V1

## Purpose

This stage defines the future architecture for automated preventive care reminder delivery.

Automated delivery means any system-initiated outbound message:

```txt
SMS
WeChat
email
push notification outside the app
automated phone call
third-party provider message
```

This is a design-only stage.

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

## Default deployment state

```txt
NO-GO for real delivery
auto_send=false
sends_external_message=false
manual_review_required=true
```

Automated delivery must remain disabled until later implementation stages pass all safety gates.

## Design principles

```txt
1. In-app/manual queue remains the source of truth.
2. Automated delivery must be opt-in per client and per channel.
3. Every send attempt must be logged before provider call.
4. Every send must check opt-out immediately before send.
5. Every message must be template-approved.
6. Every provider credential must be stored outside the repository.
7. Every channel must have a kill switch.
8. First pilot must be dry-run or manual-approval only.
```

## Proposed architecture

```txt
PreventiveCareReminder
  -> PreventiveCareNotificationQueue
  -> DeliveryEligibilityCheck
  -> TemplateRenderer
  -> DeliveryDryRun / ManualApproval
  -> ProviderAdapter
  -> DeliveryAttemptLog
  -> ProviderReceipt
```

## Required components

Future implementation should add these components in separate stages:

```txt
Automated Reminder Delivery Data Model V1
Automated Reminder Delivery Eligibility Engine Dry-run V1
Automated Reminder Delivery Template Registry V1
Automated Reminder Delivery Provider Adapter Sandbox V1
Automated Reminder Delivery API Dry-run V1
Automated Reminder Delivery Manual Approval UI V1
Automated Reminder Delivery Pilot Runbook V1
```

Do not combine these into one large implementation stage.

## Delivery eligibility

A delivery is eligible only when all are true:

```txt
feature flag enabled for dry-run or approved pilot
client consent exists
channel preference allows selected channel
client is not opted out
reminder belongs to current owner
queue item has manual review approval
message template is approved
rate limit allows send
quiet hours allow send
deduplication check passes
provider credentials available in secure store
kill switch is not active
```

## Hard block conditions

```txt
opt_out_all=true
channel permission false
client_opt_out_snapshot=true
missing consent
missing owner contact
manual_review_required=true and not reviewed
unapproved template
duplicate within cooldown window
outside quiet hours
rate limit exceeded
provider credentials missing
kill switch active
```

## Feature flags

Required defaults:

```txt
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true
ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL=true
```

Important:

```txt
DRY_RUN may generate logs and previews only.
DRY_RUN must not send external messages.
MANUAL_APPROVAL means a human must approve a specific delivery attempt.
```

## Delivery log model

Future delivery attempt records must be append-only or correction-by-new-event.

Required fields:

```txt
delivery_id
owner_id
reminder_id
notification_id
channel
template_id
template_version
eligibility_result
blocked_reason
consent_snapshot
opt_out_snapshot
message_hash
provider_message_id
status
attempt_count
created_at
approved_at
sent_at
delivered_at
failed_at
canceled_at
```

## Provider abstraction

Provider code must be isolated behind an adapter interface.

Proposed methods:

```txt
validate_config()
render_provider_payload()
send()
parse_delivery_receipt()
parse_failure()
```

Provider adapter must not:

```txt
read database directly
mutate Case
bypass opt-out
log credentials
retry forever
```

## Message templates

Message templates must be approved and versioned.

Every template must include:

```txt
template_id
template_version
channel
language
approved_by
approved_at
clinical_safety_text
opt_out_text where applicable
```

## Safety wording

Every automated message must avoid diagnosis/prescription language and include or imply:

```txt
This is a preventive care reminder, not a diagnosis or prescription.
Schedule and products must be confirmed by a veterinarian.
Rabies and regulated vaccines must follow local law and product label.
```

## Pilot design

First pilot must be:

```txt
single channel
small batch
manual approval before each send
dry-run evidence before live send
no rabies reminders
no medication or dose wording
single operator watching live
kill switch tested before start
post-pilot review required
```

## Security design

```txt
provider credentials stored only in Render environment or provider secret store
no provider secrets in repo
no provider secrets in logs
provider webhooks must be signed
provider callbacks must be idempotent
delivery logs must redact contact details where possible
```

## Rate limiting and deduplication

Minimum design:

```txt
owner daily cap
owner weekly cap
global hourly cap
same pet/category cooldown
idempotency key per delivery_id
provider retry cap
quiet hours by clinic timezone
```

## Rollback / kill switch

Required:

```txt
one flag disables all automated delivery
channel-specific flags disable individual channels
provider credentials can be revoked
queue can remain visible in manual-only mode
delivery attempts remain auditable
```

## Non-goals in this design stage

```txt
no real provider chosen
no provider credential created
no real messages sent
no delivery worker
no database migration
no UI implementation
```

## Completion criteria

```txt
1. Automated delivery design document exists.
2. Feature flag design exists.
3. Eligibility state machine exists.
4. Consent / opt-out design exists.
5. Template policy exists.
6. Delivery log model design exists.
7. Pilot plan exists.
8. Dry-run test matrix exists.
9. Release addendum exists.
10. Validator exists and is included in smoke.
11. CI static checks include validator.
```
