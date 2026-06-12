# Automated Reminder Delivery Pilot Runbook V1

## Purpose

This runbook defines the controlled pilot procedure for any future automated preventive care reminder delivery.

This stage is pilot documentation and validation only.

It does not:

```txt
send SMS
send WeChat
send email
call provider APIs
create provider credentials
create background workers
create cron jobs
enable live delivery feature flags
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

```txt
NO-GO
```

A live automated delivery pilot must not start from this stage.

This runbook only defines the required evidence and controlled-window process for a later pilot.

## Pilot scope

Allowed first pilot shape:

```txt
single clinic
single channel
small batch
manual approval before each send
dry-run evidence before each send
operator watching live
kill switch tested before start
provider sandbox tested before live
post-pilot review required
```

Suggested first pilot limits:

```txt
max_owners=5
max_reminders=5
max_channel=1
max_duration=1 controlled window
```

## Explicit exclusions

The first pilot must not include:

```txt
rabies reminders
regulated vaccine reminders
medication dose reminders
diagnosis-specific messages
multi-channel campaigns
fully automatic sends
night-time sending
clients with opt-out
unreviewed templates
unreviewed delivery attempts
```

## Required previous stages

All must be complete and green:

```txt
Automated Reminder Delivery Risk Review V1
Automated Reminder Delivery Design V1
Automated Reminder Delivery Data Model V1
Automated Reminder Delivery Eligibility Engine Dry-run V1
Automated Reminder Delivery Template Registry V1
Automated Reminder Delivery API Dry-run V1
Automated Reminder Delivery Manual Approval UI V1
```

## Required pre-pilot gates

A pilot cannot start unless all are true:

```txt
GitHub Actions latest run green
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
ENABLE_PREVENTIVE_AUTO_DELIVERY=false before controlled enable
dry-run attempts created for every candidate
manual approval recorded for every candidate
template approved for dry-run evidence
client consent verified
opt_out_all=false
channel permission true
quiet hours configured
rate limits configured
duplicate cooldown configured
kill switch tested
rollback owner online
security owner reachable
clinical_ops_owner approves candidate list
```

## Required feature flag plan

Initial state before pilot:

```txt
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
ENABLE_PREVENTIVE_DELIVERY_DRY_RUN=true
ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL=true
```

Controlled pilot can only enable the chosen channel in a later implementation stage after all checks pass.

This runbook itself does not enable any flag.

## Candidate selection

For each candidate owner/reminder:

```txt
owner belongs to pilot clinic
contact destination verified
client consent recorded
opt-out not active
reminder category low-risk
template approved
queue item reviewed
dry-run attempt exists
manual approval exists
eligibility result reviewed
```

Disallow:

```txt
client_opt_out_snapshot=true
opt_out_all=true
blocked_missing_consent
blocked_missing_channel
blocked_unapproved_template
manual_review_required without review
blocked_rate_limit
blocked_quiet_hours
blocked_kill_switch unless only dry-run evidence
```

## Controlled window procedure

### T minus 30 minutes

```txt
confirm owner list
confirm reminder list
confirm channel
confirm provider sandbox result
confirm no secret leak in logs
confirm online smoke ALL PASS
confirm rollback owner online
confirm kill switch tested
```

### T minus 10 minutes

```txt
run final dry-run
export candidate evidence
confirm no opt-out changed
confirm quiet hours allow sending
confirm rate limits
```

### During window

```txt
one operator performs send action
one clinical_ops_owner watches output
one rollback_owner watches logs
stop after each candidate if any warning appears
do not batch blindly
```

### After each candidate

Record:

```txt
delivery_id
provider_message_id if future provider exists
status
timestamp
operator
client response if known
error if any
```

### After window

```txt
disable live delivery flag
run online smoke
check logs for secrets
confirm no duplicate sends
complete pilot report
schedule post-pilot review
```

## Stop conditions

Stop immediately if any occurs:

```txt
wrong recipient
client opt-out discovered
duplicate delivery
provider error spike
unexpected external message
unapproved template used
send outside quiet hours
rate limit exceeded
secret appears in logs
API 500
online smoke fails
Case created or updated unexpectedly
EMR import executed unexpectedly
```

## Incident response

For any P0:

```txt
1. Set ENABLE_PREVENTIVE_AUTO_DELIVERY=false.
2. Set all channel flags false.
3. Revoke provider credentials if credential misuse is suspected.
4. Preserve logs and delivery records.
5. Notify release_owner, security_owner, clinical_ops_owner.
6. Record incident in pilot evidence.
7. Do not resume pilot without written approval.
```

## Post-pilot review

Review within 24 hours:

```txt
send count
success count
failure count
duplicate count
opt-out incident count
wrong recipient count
client complaint count
secret leak count
case mutation incident count
EMR import incident count
```

Decision options:

```txt
PASS
PAUSE
FAIL
ROLLBACK-REVIEW
```

## Hard No-Go

Any one means no pilot:

```txt
online smoke fails
GitHub Actions red
schema_ok=false
database_revision != alembic_head
database_revision != 0008_auto_delivery
dry-run API fails
manual approval UI fails
no rollback owner
no security owner
no clinical_ops_owner approval
client opt-out not verified
template not approved
rate limits not configured
quiet hours not configured
kill switch not tested
provider credential plan missing
secret leak exists
previous unresolved P0 exists
```

## Completion criteria

This pilot runbook stage is complete when:

```txt
1. Pilot runbook exists.
2. Candidate checklist exists.
3. Controlled window checklist exists.
4. Pilot evidence template exists.
5. Stop condition / incident matrix exists.
6. Post-pilot review template exists.
7. Release addendum exists.
8. Validator exists and is included in smoke.
9. CI static checks include validator.
```
