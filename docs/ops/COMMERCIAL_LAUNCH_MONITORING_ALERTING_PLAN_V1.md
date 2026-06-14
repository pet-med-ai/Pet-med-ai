# Commercial Launch Monitoring / Alerting Plan V1

## Purpose

This plan defines what Pet-Med-AI Commercial V1 must monitor before and after
clinic-facing use.

The goal is to detect availability issues, schema drift, dangerous feature flag
changes, smoke failures, access/security incidents and operational degradation
early enough to stop clinic-facing usage before harm spreads.

This stage is a monitoring and alerting plan only. It does not create third-party
alerting credentials, does not configure SMS/WeChat/email alert providers, does
not create background workers and does not enable any high-risk feature.

## Product boundary

Commercial V1 monitoring covers:

```txt
Render backend availability
Render frontend availability
/api/system/version
/api/system/feature-flags
online smoke
GitHub Actions
database revision safety
dangerous feature flags
manual preventive care queue health
clinical document export smoke
access / IDOR incident signals
secret exposure signals
P0/P1 incident review
```

Commercial V1 monitoring explicitly does not enable:

```txt
automated reminder live delivery
SMS provider sends
WeChat provider sends
email provider sends
provider credentials
background worker sending
EMR real import
EMR case update
device real ingest
DICOM real ingest
lab analyzer real integration
```

## Monitoring modes

Commercial V1 uses three monitoring modes:

```txt
manual_daily_check       performed by release_owner / clinical_ops_owner
release_gate_check       performed before deploy / after deploy / before Go decision
future_external_alerting optional later integration with an uptime or log alerting provider
```

The V1 plan may mention future external alerting, but it does not require or
create any provider account or credential.

## Hard monitored gates

These conditions are hard gates:

```txt
/healthz unavailable
frontend unavailable
online smoke fails
schema_ok=false
database_revision != alembic_head
database_revision != 0008_auto_delivery
all_dangerous_features_disabled=false
ENABLE_EMR_REAL_IMPORT=true
ENABLE_EMR_IMPORT_CASE_UPDATE=true
ENABLE_EMR_ATTACHMENT_DOWNLOAD=true
ENABLE_PREVENTIVE_AUTO_DELIVERY=true
ENABLE_PREVENTIVE_SMS_DELIVERY=true
ENABLE_PREVENTIVE_WECHAT_DELIVERY=true
ENABLE_PREVENTIVE_EMAIL_DELIVERY=true
secret appears in logs/UI
cross-user data access suspected
```

If any hard gate triggers, Commercial V1 is **NO-GO** until the incident is
triaged, fixed and smoke is green.

## Required daily checks

Run once per clinic operating day:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Expected:

```txt
healthz OK
frontend live
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
all_dangerous_features_disabled=true
dangerous EMR flags false
automated live delivery flags false
```

## Required release checks

Run before and after deploy:

```txt
GitHub Actions latest main run green
bash scripts/ci_static_checks.sh PASS
online smoke PASS
Render backend live
Render frontend live
/api/system/version safe
/api/system/feature-flags safe
```

## Alert severity

Use these severities:

```txt
P0  immediate stop; data/security/schema/live-send/EMR-write risk
P1  service degraded or launch gate failed; release blocked
P2  operational backlog or repeated warning; review within weekly ops
P3  informational trend; review monthly
```

## P0 examples

```txt
cross-user data visible
secret leaked
schema_ok=false
database_revision mismatch
database_revision != 0008_auto_delivery
automated external message sent unexpectedly
ENABLE_PREVENTIVE_AUTO_DELIVERY=true unexpectedly
ENABLE_EMR_REAL_IMPORT=true unexpectedly
EMR real import executed unexpectedly
EMR case update executed unexpectedly
database unavailable during clinic use
```

## P1 examples

```txt
backend /healthz unavailable
frontend unavailable
online smoke fails
GitHub Actions red
Render deploy failed
Clinical Docs Word export repeatedly failing
manual contact queue unavailable
```

## P2 examples

```txt
manual contact queue backlog grows
preventive care opt-out workflow error
repeated login failures without confirmed breach
feature scope drift in UI
weekly backup evidence missing
```

## P3 examples

```txt
monthly trend review
slow response trend without outage
documentation update needed
roadmap item drift
```

## Escalation rules

```txt
P0: notify release_owner + security_owner + clinical_ops_owner immediately.
P1: notify release_owner and owning component owner the same business day.
P2: record in weekly ops review and assign an owner.
P3: record in monthly ops review.
```

## Stop conditions

Stop clinic-facing use when:

```txt
P0 incident is open
schema_ok=false
database_revision mismatch
database_revision != 0008_auto_delivery
dangerous flags unexpectedly enabled
secret leak suspected
cross-user access suspected
automated external send happened unexpectedly
EMR real write happened unexpectedly
```

## Recovery requirements

Resume only when all are true:

```txt
root cause identified
affected users/data identified if applicable
dangerous flags closed
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
online smoke ALL PASS
CI static checks PASS
release_owner signs off
security_owner signs off for data/security/flag incidents
clinical_ops_owner signs off for clinic workflow incidents
incident evidence recorded
```

## Evidence collection

For every P0/P1 alert, capture:

```txt
date/time
environment
git_commit
BASE_URL
FRONTEND_URL
healthz output
/api/system/version output
/api/system/feature-flags output
smoke result
Render deploy/log reference
GitHub Actions reference if applicable
owner
decision
next action
```

## Future external alerting candidates

Future implementation may connect:

```txt
uptime check for /healthz
uptime check for frontend URL
scheduled smoke runner
Render deploy failed notifications
GitHub Actions failed notifications
log-based 500-rate alerts
schema_ok=false alert
database_revision mismatch alert
dangerous feature flag changed alert
secret pattern detection alert
```

This V1 plan does not create these integrations. It only defines what must be
monitored and what should alert when implementation is approved.

## Next stage dependency

After this plan, proceed to:

```txt
Commercial Launch Backup / Restore Drill V2
Commercial Launch Legal / Consent Pack V1
Commercial Launch Final Go / No-Go V1
```

Final Go cannot pass unless monitoring/alerting expectations are present and
incident response ownership is clear.
