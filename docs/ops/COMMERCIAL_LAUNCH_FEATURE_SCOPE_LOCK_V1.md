# Commercial Launch Feature Scope Lock V1

## Purpose

This document locks the Commercial V1 feature boundary for Pet-Med-AI.

The goal is to prevent scope creep and accidental exposure of high-risk internal
features during commercial launch preparation. This stage does not add clinical
features, does not enable live integrations, and does not grant new permissions.

Pet-Med-AI's long-term product direction remains:

```txt
structured consultation
species knowledge base
case record
diagnostic data model
lab / imaging / device data
AI abnormality summary
diagnostic assistance
treatment suggestions
medication safety
clinical documentation
hospital operations loop
```

Commercial V1 is only the safe deployable slice of that larger clinical system.

## Scope states

Every feature must have exactly one Commercial V1 state:

```txt
public_clinic
clinic_staff
clinic_admin
internal_admin
internal_dry_run
hidden_paused
future_not_in_v1
```

Definitions:

```txt
public_clinic      usable by logged-in clinic users in normal workflow
clinic_staff       usable by front desk / clinic staff for operations
clinic_admin       visible to clinic owner/admin or trusted operator
internal_admin     internal operations only; not clinic-facing by default
internal_dry_run   internal validation only; no live external effect
hidden_paused      not visible and not part of Commercial V1
future_not_in_v1   legitimate roadmap item, but not promised for V1 launch
```

## Commercial V1 allowed scope

Commercial V1 may expose:

```txt
AI consultation
dynamic consultation
consultation session persistence
history / restore consultation
save consultation as case
update bound case after follow-up
case list / case detail / case edit
case filtering / pagination
case CSV export
case print
Clinical Docs Word export
dog / cat structured intake templates
exotic structured intake templates
save-before-case history merge preview
AI suggestion human review audit before saving cases
preventive care in-app reminders
preventive care notification queue
front-desk manual contact workflow
preventive care ops dashboard
system version read-only view
feature flag read-only safety view
```

## Commercial V1 admin or internal-only scope

The following are not ordinary clinic-user features:

```txt
KPI dashboard
Ops dashboard
Release dashboard
Feature flags
Audit logs
Webhook inbox
EMR mapping dry-run
EMR import batch planning
EMR clinical approval
EMR execution dry-run
Automated Reminder Delivery dry-run
Automated Reminder Delivery manual approval
```

These may exist in the codebase, but Commercial V1 treats them as admin or
internal-only surfaces until the Access Review stage enforces route and API
authorization.

## Commercial V1 hidden / paused scope

The following are explicitly outside Commercial V1:

```txt
EMR real import execution
EMR case update
EMR attachment download
automated reminder live delivery
true SMS provider
true WeChat provider
true email provider
provider credentials
background worker based sending
cron-based automatic sends
unreviewed external client communication
device real ingest
DICOM real ingest
lab analyzer real integration
structured prescription writes
billing / invoice real writes
```

## UI navigation lock

Commercial V1 must not expose high-risk internal-dry-run pages in the normal
clinic-facing navigation.

For this V1 scope lock:

```txt
Remove default navigation link to /automated-reminder-delivery/manual-approval.
Keep direct route handling unchanged until Access Review V1.
Do not treat UI hiding as a security boundary.
Route and API authorization must be enforced in Commercial Launch User Roles / Access Review V1.
```

## Non-goals

This stage does not:

```txt
create RBAC
create admin roles
create route guards
change database schema
add migrations
remove dry-run code
send external messages
enable provider APIs
enable background workers
enable EMR real import
enable EMR case update
ship device gateway
ship DICOM ingestion
ship PDF conversion
ship medication dose knowledge base
```

## Required next stage

After this scope lock, the project must proceed to:

```txt
Commercial Launch Ops Runbook V1
Commercial Launch User Roles / Access Review V1
Commercial Launch Monitoring / Alerting Plan V1
Commercial Launch Backup / Restore Drill V2
Commercial Launch Legal / Consent Pack V1
Commercial Launch Final Go / No-Go V1
```

## Hard rules

Commercial V1 is **NO-GO** if any of the following is true:

```txt
Automated Reminder Delivery manual approval is shown in default clinic navigation.
EMR real import execution is shown to ordinary users.
Automated live sending is described as available.
SMS / WeChat / email live delivery is described as available.
Provider credentials are required for launch.
Device / DICOM / lab real ingest is promised in Commercial V1.
High-risk surfaces have no owner or access plan.
```

## Decision

Default decision before validation:

```txt
NO-GO
```

Decision can become:

```txt
GO to Ops Runbook and Access Review
```

only when:

```txt
feature matrix exists
route visibility matrix exists
default navigation hides automated reminder manual approval
validator passes
CI static checks include the validator
smoke includes the validator
```
