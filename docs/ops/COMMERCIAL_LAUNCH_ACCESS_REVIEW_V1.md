# Commercial Launch User Roles / Access Review V1

## Purpose

This review defines the Commercial V1 access boundary for Pet-Med-AI.

The goal is to prove that clinic-facing users cannot access other users' clinical
data, and to identify which routes and APIs require administrator or internal
guards before final launch.

This stage does not create a full RBAC system. It documents the target role
model, maps existing routes and APIs, records IDOR test cases, validates existing
owner-scoped controls, and identifies any remaining access gaps.

## Current access model

Current Commercial V1 code should be treated as:

```txt
authenticated owner-scoped user model
```

Known current strengths:

```txt
case list filters by owner_id
case detail/update/delete use owned-case lookup
consult sessions use owner access checks
preventive care reminders check owner_id
automated reminder delivery attempts check owner_id
feature flags/system version endpoints are read-only
```

Known current limitation:

```txt
full RBAC is not yet implemented
clinic_staff / clinic_admin / internal_admin are target roles, not guaranteed database roles
UI hiding is not an authorization boundary
admin/internal routes need route/API guard review before final Go
```

## Target Commercial V1 roles

Commercial V1 should use the following target roles:

```txt
anonymous
clinic_user
clinician
front_desk
clinic_admin
internal_admin
release_owner
security_owner
clinical_ops_owner
```

Operational owner roles may be the same real person in a pilot, but application
permissions must still be reasoned about separately.

## Hard data isolation rule

The most important launch rule:

```txt
User B must not be able to read, list, edit, delete, restore, export, update, review,
or otherwise mutate User A's clinical data by guessing IDs.
```

This applies to:

```txt
cases
consultation sessions
case save preview / save-case / update-case
preventive care reminders
preventive care notification queue items
preventive care client preferences
automated reminder delivery attempts
manual approval actions
clinical document exports
audit evidence
```

## Commercial V1 route policy

Public clinic workflow:

```txt
/
 /cases/new/edit
 /cases/:id/edit
 /cases/:id
 /preventive-care/notification-queue
```

Admin or internal-only workflow:

```txt
/kpi
/ops
/webhooks/emr/inbox
/emr/import-batches
/automated-reminder-delivery/manual-approval
```

Commercial V1 scope lock already removed the default navigation link to:

```txt
/automated-reminder-delivery/manual-approval
```

This is necessary but not sufficient. Access Review V1 requires that final launch
does not rely on UI hiding alone.

## API access policy

Public clinic user APIs must be authenticated and owner-scoped:

```txt
/api/cases*
/api/ai/consult/session*
/api/preventive-care*
/api/clinical-docs*
/api/audit*
```

Internal/admin APIs must not be ordinary clinic-user public surfaces:

```txt
/api/system/feature-flags
/api/system/version
/api/ops*
/api/emr*
/api/automated-reminder-delivery*
```

Read-only system status endpoints may be used for support and smoke, but they
must not expose secrets or mutate data.

## IDOR testing requirement

Commercial launch must include IDOR checks:

```txt
create user A
create user B
create data as user A
attempt read/list/edit/delete/export/review as user B
expect 401/403/404 and no data leakage
```

Use 404 for owner-scoped clinical records when possible to avoid confirming that
another user's resource exists.

## High-risk pages

These pages are high-risk until route and API guards exist:

```txt
/ops
/webhooks/emr/inbox
/emr/import-batches
/automated-reminder-delivery/manual-approval
```

Commercial V1 treats Automated Reminder Delivery manual approval as an internal
dry-run surface only. It must not be exposed to ordinary clinic users and must
not enable live external sending.

Commercial Final Go is **NO-GO** if these are available to ordinary clinic users
without an explicit admin/internal authorization decision.

## Explicit non-goals

This stage does not:

```txt
create RBAC tables
create Alembic migrations
create admin roles
change JWT claims
rewrite frontend routing
enable real message sending
enable EMR real import
enable EMR case update
connect providers
create provider credentials
```

## Required evidence

Before this stage can pass, the repo must contain:

```txt
access matrix
route access matrix
IDOR test plan
evidence template
validator
CI static hook
smoke hook
existing owner-scoped backend checks
```

## Findings for next stage / follow-up

The following must be tracked before Final Go:

```txt
Decide whether clinic_admin/internal_admin are implemented as JWT claims, database roles, or deployment-only operator accounts.
Add route/API guards for internal admin surfaces if ordinary clinic users can reach them.
Confirm clinical document export cannot export another user's case.
Confirm automated delivery manual approval cannot review another user's attempt.
Confirm EMR integration routes remain internal/admin only.
Confirm ops dashboards do not expose cross-user data in multi-user deployment.
```

## Decision

This stage can be marked complete when access review evidence and validator pass.

Completion means:

```txt
access boundaries are documented
existing owner-scoped controls are validated statically
IDOR test plan is ready
known RBAC gaps are explicit
```

Completion does not mean:

```txt
Final commercial launch is approved
full RBAC exists
admin routes are safe for ordinary users
```
