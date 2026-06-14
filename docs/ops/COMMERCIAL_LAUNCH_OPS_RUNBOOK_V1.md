# Commercial Launch Ops Runbook V1

## Purpose

This runbook defines the operating rhythm for Pet-Med-AI Commercial V1.

The goal is to make the clinic-facing system operationally safe after launch:
daily health checks, weekly operational review, monthly release / backup review,
and P0 incident response are all defined before external commercial use.

This stage does not add product features. It does not open high-risk integrations.
It turns the currently deployable product slice into a service that can be
watched, triaged, paused and recovered.

## Product boundary for this runbook

Commercial V1 operations cover:

```txt
AI consultation
dynamic consultation
consultation sessions
case list / detail / edit
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
preventive care ops dashboard
release / version / feature flag read-only checks
```

Commercial V1 operations do not include:

```txt
automated external reminder delivery
SMS live sending
WeChat live sending
email live sending
provider credentials
background worker based sending
EMR real import execution
EMR case update
device real ingest
DICOM real ingest
lab analyzer real integration
structured prescription writes
billing / invoice real writes
```

## Roles

Suggested owners:

```txt
release_owner       owns deployment, smoke, schema, rollback decision
security_owner      owns feature flags, secrets, cross-user data incidents
clinical_ops_owner  owns clinic workflow, reminders, manual queue and customer impact
frontend_owner      owns frontend availability and UI regressions
backend_owner       owns API health, logs, database connectivity and migrations
```

For a small pilot, the same person may hold multiple roles, but each check must
still record an owner.

## Daily health check

Run once every clinic operating day before active use.

Required commands:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required pass state:

```txt
backend healthz available
frontend static site available
online smoke ALL PASS
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
all_dangerous_features_disabled=true
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
```

If any hard gate fails, stop clinic-facing rollout and follow the incident matrix.

## Daily clinic operations

Clinical workflow checks:

```txt
AI consultation can be submitted
dynamic consultation can continue
AI suggestion human review audit can be recorded before saving cases
case can be saved
case detail can be opened
Clinical Docs Word export can be downloaded
preventive care in-app reminder flow can be reviewed
front-desk manual contact queue can be opened
```

Manual contact queue rule:

```txt
All external client contact remains manual in Commercial V1.
No SMS / WeChat / email provider send is allowed.
```

## Weekly operations review

Run once per week.

Required checks:

```txt
review preventive care notification queue
review overdue manual contact items
review canceled queue items
review client opt-out records
review reminders marked completed / delayed / disabled
review high-risk AI consult cases if any
review case export / Word export failures if any
review GitHub Actions latest main status
review Render backend and frontend deploy history
review feature flags still closed
review backup evidence exists for the week
```

Required output:

```txt
weekly reviewer
date
summary
open issues
P0/P1 incidents
decisions
next actions
```

## Monthly operations review

Run once per month.

Required checks:

```txt
review monthly preventive care queue metrics
review smoke stability
review release records
review changelog
review backup / rollback evidence
review security hardening evidence
review access issues or user isolation complaints
review unresolved incidents
review Commercial Launch Risk Register
```

Required output:

```txt
monthly review owner
review date
release health summary
ops health summary
security findings
backup evidence status
decision: continue / pause / no-go
```

## P0 incident response

P0 examples:

```txt
cross-user data visible
schema_ok=false
database_revision mismatch
database_revision != 0008_auto_delivery
automated external message sent unexpectedly
ENABLE_PREVENTIVE_AUTO_DELIVERY=true unexpectedly
ENABLE_EMR_REAL_IMPORT=true unexpectedly
EMR real import executed unexpectedly
EMR case update executed unexpectedly
secret leaked
database unavailable
online smoke fails during active clinic use
```

Immediate actions:

```txt
1. Stop clinic-facing usage if patient/client data may be affected.
2. Capture current /api/system/version output.
3. Capture current /api/system/feature-flags output.
4. Preserve Render logs and GitHub commit SHA.
5. Confirm whether database writes occurred.
6. If automated external sending is involved, set live-send flags false.
7. If EMR risk is involved, set EMR real import and case update flags false.
8. Notify release_owner, security_owner and clinical_ops_owner.
9. Record the incident in the incident response matrix.
10. Do not resume until smoke is green and owner signs off.
```

## Render incident handling

Backend deploy failed:

```txt
check Render deploy log
check environment variables
check DATABASE_URL availability without exposing value
check latest commit SHA
rollback to last known good deploy if needed
run online smoke after recovery
record incident if clinic-facing impact occurred
```

Frontend deploy failed:

```txt
check static site deploy log
check build errors
check frontend environment values without exposing secrets
rollback to last known good deploy if needed
run frontend live check
run online smoke after recovery
```

## GitHub Actions failure handling

If GitHub Actions fails:

```txt
do not promote launch status
review failed job
run bash scripts/ci_static_checks.sh locally
fix targeted files only
do not use git add .
push fix
confirm latest run green
```

## Database / Alembic incident handling

If database_revision does not equal alembic_head or expected revision:

```txt
NO-GO immediately
capture /api/system/version output
do not run new migrations blindly
check Render shell:
  cd ~/project/src/backend
  python3 -m alembic -c alembic.ini current
  python3 -m alembic -c alembic.ini heads
confirm whether revision should be 0008_auto_delivery
escalate to release_owner before any upgrade
run online smoke after recovery
```

## Feature flag incident handling

Dangerous flags must remain closed:

```txt
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PREVENTIVE_AUTO_DELIVERY=false
ENABLE_PREVENTIVE_SMS_DELIVERY=false
ENABLE_PREVENTIVE_WECHAT_DELIVERY=false
ENABLE_PREVENTIVE_EMAIL_DELIVERY=false
```

If any high-risk flag is enabled unexpectedly:

```txt
NO-GO
disable flag
preserve evidence
verify no unintended writes or sends
run online smoke
record incident
```

## Secrets incident handling

If any secret is exposed:

```txt
NO-GO
remove exposed material from visible surfaces
rotate affected secret
review GitHub / Render logs
confirm no provider credentials were created for Commercial V1
record incident
do not resume until security_owner signs off
```

## Resume criteria after incident

System may resume only when all are true:

```txt
root cause identified
affected users / records identified
schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
dangerous flags closed
online smoke ALL PASS
backup / rollback status known
release_owner signs off
security_owner signs off for data/security incidents
clinical_ops_owner signs off for clinic workflow incidents
```

## Next stage dependency

This runbook does not create RBAC or enforce admin-only routes.

The next required stage remains:

```txt
Commercial Launch User Roles / Access Review V1
```

That stage must turn this operational visibility plan into actual route / API
permission checks for public, clinic staff, clinic admin and internal admin users.
