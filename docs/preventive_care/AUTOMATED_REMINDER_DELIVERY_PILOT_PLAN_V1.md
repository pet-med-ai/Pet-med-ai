# Automated Reminder Delivery Pilot Plan V1

## Purpose

Defines the only acceptable first automated reminder delivery pilot shape.

## Pilot default

```txt
NO-GO until design, data model, dry-run, provider sandbox, and manual approval stages are complete.
```

## Required pilot constraints

```txt
single channel
single clinic
small batch
manual approval before every send
dry-run evidence before every send
operator watching live
kill switch tested before start
provider sandbox tested first
post-pilot review required
```

## Excluded from first pilot

```txt
rabies reminders
regulated vaccine reminders
medication/dose reminders
diagnosis-specific messaging
multi-channel campaigns
fully automatic sends
```

## Pilot batch limits

Suggested first pilot:

```txt
max owners: 5
max reminders: 5
max channel: one
max duration: one controlled window
```

## Required evidence

```txt
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
delivery dry-run report
provider sandbox report
template approval
manual approval list
operator log
post-pilot result
```

## Stop conditions

```txt
any wrong recipient
any opt-out issue
any provider duplicate
any secret leak
any unapproved template
any API 500 during controlled window
```
