# Automated Reminder Delivery Eligibility Engine Dry-run V1

## Purpose

This stage adds an offline dry-run eligibility engine for future automated preventive care reminder delivery.

It answers:

```txt
Would this reminder be eligible for automated delivery if delivery were allowed?
Why is it blocked?
Which safety gate blocked it first?
```

This stage does not send messages.

It does not:

```txt
send SMS
send WeChat
send email
call provider APIs
create provider credentials
create background workers
create cron jobs
change database
create delivery attempts
create Case records
update Case records
execute EMR import
```

## New files

```txt
backend/automated_reminder_delivery_eligibility.py
scripts/automated_reminder_delivery_eligibility_dry_run.py
docs/preventive_care/AUTOMATED_REMINDER_DELIVERY_ELIGIBILITY_DRY_RUN_V1.md
docs/preventive_care/AUTOMATED_REMINDER_DELIVERY_ELIGIBILITY_SAMPLE_INPUT.json
scripts/validate_automated_reminder_delivery_eligibility_dry_run.py
```

## Evaluated gates

```txt
global kill switch
channel feature flag
client opt-out
channel consent
consent source
contact destination
manual review
template approval
rate limit
duplicate cooldown
quiet hours
suppression rule
provider credentials
```

## Output safety markers

Every dry-run output must include:

```txt
dry_run=true
auto_send=false
sends_external_message=false
manual_review_required=true
writes_database=false
creates_case=false
updates_case=false
executes_real_import=false
```

## Typical blocked states

```txt
blocked_opt_out
blocked_missing_consent
manual_review_required
blocked_unapproved_template
blocked_rate_limit
blocked_quiet_hours
blocked_suppression
blocked_kill_switch
blocked_channel_disabled
blocked_provider_credentials
```

## Command

```bash
python3 scripts/automated_reminder_delivery_eligibility_dry_run.py \
  --input docs/preventive_care/AUTOMATED_REMINDER_DELIVERY_ELIGIBILITY_SAMPLE_INPUT.json
```

## Completion criteria

```txt
1. Eligibility engine exists.
2. CLI dry-run script exists.
3. Sample input exists.
4. Validator exists and runs scenario tests.
5. smoke and CI include validator.
```
