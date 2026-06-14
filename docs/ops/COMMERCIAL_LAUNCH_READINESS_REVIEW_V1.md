# Commercial Launch Readiness Review V1

## Purpose

This review is the first commercial launch gate for Pet-Med-AI.

It moves the project from feature-complete development mode into commercial
launch readiness mode. The goal is not to add new product capability. The goal
is to verify that the current system is safe, deployable, observable, recoverable
and operationally controllable before clinic-facing use.

Pet-Med-AI remains a clinical AI assistance system for veterinary hospitals.
This commercial launch gate protects that clinical product direction by ensuring
deployment safety, data isolation, rollback evidence, feature scope control and
high-risk integration controls.

## Scope

This stage verifies:

```txt
GitHub Actions latest run green
Render backend live
Render frontend live
online smoke ALL PASS
/api/system/version schema_ok=true
database_revision == alembic_head
database_revision == 0008_auto_delivery
automated reminder real sending remains disabled
EMR real import remains feature-flag gated
dangerous feature flags remain disabled
customer data isolation has review evidence
audit / backup / rollback evidence exists
commercial launch risk register exists
```

## Explicit non-goals

This stage does not:

```txt
change database schema
create Alembic revisions
add provider credentials
connect SMS providers
connect WeChat providers
connect email providers
create background workers
send external messages
enable automated reminder live sending
enable EMR real import
enable EMR case update
add new clinical product features
```

## Current product context

Commercial V1 should be based on already controlled and operationally useful
capabilities:

```txt
AI consultation
dynamic consultation
consultation session persistence
save consultation to case
case list / detail / edit
case export
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
preventive care ops dashboard
release / version / feature flag visibility
```

The following must remain hidden, paused, or internal-admin-only during this
review:

```txt
EMR real import execution
EMR case update
automated reminder live delivery
SMS provider integration
WeChat provider integration
email provider integration
provider credentials
background worker based sending
high-risk dry-run and approval pages for ordinary users
```

## Hard launch gates

The release is **NO-GO** if any of the following is true:

```txt
GitHub Actions latest run red
Render backend not live
Render frontend not live
online smoke fails
schema_ok=false
database_revision != alembic_head
database_revision != 0008_auto_delivery
automated reminder live-send flag enabled
external message sending enabled unexpectedly
EMR real import enabled unexpectedly
EMR case update enabled unexpectedly
cross-user data access found
backup / rollback evidence missing
secret leak found
```

## Required online commands

Backend health:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
```

System version:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
```

Feature flags:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
```

Online smoke:

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com \
FRONTEND_URL=https://pet-med-ai-frontend-static.onrender.com \
bash scripts/smoke_petmed.sh
```

## Required expected state

```txt
healthz OK
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

## Stage decision

Default decision before evidence is collected:

```txt
NO-GO
```

The decision can become **GO for next launch-planning stage only** when the
checklist evidence is collected and the validator, CI static checks and online
smoke are all green.

Passing this stage does not mean public launch is approved. It only allows the
project to proceed to:

```txt
Commercial Launch Feature Scope Lock V1
Commercial Launch Ops Runbook V1
Commercial Launch User Roles / Access Review V1
Commercial Launch Monitoring / Alerting Plan V1
Commercial Launch Backup / Restore Drill V2
Commercial Launch Legal / Consent Pack V1
Commercial Launch Final Go / No-Go V1
```

## Owner notes

Commercial readiness is an operational safety gate. It must not be used to
justify opening paused high-risk features. In particular, true automated message
sending and true EMR write integrations remain out of Commercial V1 until their
own later controlled pilot gates are completed.
