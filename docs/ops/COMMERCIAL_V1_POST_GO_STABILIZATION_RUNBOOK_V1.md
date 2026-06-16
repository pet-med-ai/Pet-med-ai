# Commercial V1 Post-Go Stabilization Runbook V1

## Purpose

This runbook defines the first post-GO stabilization period for Pet-Med-AI
Commercial V1.

Commercial V1 is launch-approved, but the first clinic pilot must be operated as
a controlled stabilization window. The goal is to confirm that clinic-facing use
is stable, safe, manually supervised and recoverable before expanding to more
clinics or higher-risk integrations.

## Stabilization window

Initial stabilization window:

```txt
D0 through D7 after Commercial V1 GO
```

Optional extension:

```txt
D8 through D14 if any P1 issue occurs
```

Expansion to additional clinics is not allowed until the stabilization exit
criteria are met.

## Commercial V1 allowed scope

Allowed during post-GO stabilization:

```txt
AI consultation
dynamic consultation
structured intake
case creation / list / detail / edit
AI suggestion human review audit
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
ops / release / system read-only checks
manual clinic staff operations
```

Still not allowed:

```txt
automated SMS sending
automated WeChat sending
automated email sending
provider credentials
background worker sending
EMR real import
EMR case update
device real ingest
DICOM real ingest
lab analyzer real integration
structured prescription writes
billing/invoice real writes
```

## First clinic pilot limits

Suggested limits for the first clinic:

```txt
one clinic
named pilot users only
front-desk manual contact only
no automated external messaging
no EMR real writes
no case update import
no provider credentials
daily smoke before active use
daily incident review
daily backup/restore status awareness
```

Suggested first-week volume:

```txt
AI consults: controlled normal clinic use
case saves: controlled normal clinic use
preventive reminders: reviewed manually
manual contact queue: front-desk reviewed only
clinical document export: Word export only
```

## Daily post-GO checks

Run every pilot operating day:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz

curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool

curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool

BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

Required state:

```txt
healthz OK
frontend live
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

## Daily workflow observation

Each pilot day, record whether these workflows are usable:

```txt
login
AI consultation
dynamic consultation follow-up
AI review audit before save
save consult as case
case list/filter/page
case detail
case edit
case print
Clinical Docs Word export
preventive care reminder review
front-desk manual contact queue
opt-out handling
ops dashboard read-only review
```

## Incident thresholds

Immediate P0 pause conditions:

```txt
schema_ok=false
database_revision mismatch
database_revision != 0008_auto_delivery
cross-user data visible
secret leaked
PHI/client data leaked in repo or evidence
automated external message sent unexpectedly
EMR real write executed unexpectedly
dangerous feature flag enabled
online smoke fails during clinic use
```

P1 stabilization extension conditions:

```txt
backend or frontend unavailable
online smoke fails outside active clinic use
Word export repeatedly fails
manual contact queue unavailable
GitHub Actions red after launch fix
Render deploy failed
```

P2 weekly review conditions:

```txt
manual contact backlog grows
opt-out workflow confusion
staff training gap
feature scope drift
documentation gap
minor UI issue without clinical risk
```

## Pause and resume

If P0 occurs:

```txt
pause clinic-facing use
preserve evidence
capture /api/system/version
capture /api/system/feature-flags
confirm no real external sending
confirm no EMR real write
identify affected users/records
notify release_owner security_owner clinical_ops_owner
resume only after root cause fixed and online smoke ALL PASS
```

## Daily owner signoff

Each operating day should record:

```txt
release_owner daily check
security_owner flag/access check
clinical_ops_owner workflow check
front_desk queue check
```

## Stabilization exit criteria

Exit Commercial V1 post-GO stabilization only when all are true:

```txt
D0-D7 daily checks complete
no open P0
no unresolved P1
online smoke stable
schema_ok remained true
database_revision remained 0008_auto_delivery
dangerous flags remained disabled
no cross-user access issue
no secret / PHI leak
no unexpected external message
no EMR real write
manual contact queue workflow reviewed
opt-out workflow understood
Clinical Docs Word export acceptable
pilot metrics recorded
release_owner signoff
security_owner signoff
clinical_ops_owner signoff
```

## Expansion rule

Do not expand to additional clinics until exit criteria are met.

If any P0 occurs, expansion is blocked until incident review is complete and a
new stabilization window is approved.

## Next recommended stages after stabilization

After successful stabilization, choose one controlled roadmap branch:

```txt
Commercial V1 Clinic Onboarding Pack V1
Commercial V1 Support / Ticket SOP V1
Clinical Core Roadmap Restart: DiagnosticReport / Observation / ImagingStudy
Clinical Docs PDF Conversion Implementation V1
Multi-clinic / Tenant Model Design V1
```

Do not jump directly into live automated messaging or EMR real writes.
