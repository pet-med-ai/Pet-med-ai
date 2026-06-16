# Commercial V1 First Clinic Pilot Operations V1

## Purpose

This document defines the operating plan for the first clinic pilot after
Commercial V1 launch approval.

The first clinic pilot is a controlled real-world operations window, not a new
feature build. It confirms that Pet-Med-AI can support clinic workflows safely
under daily observation.

## Pilot scope

Allowed:

```txt
one clinic
named pilot users
AI-assisted consultation
structured intake
case management
Clinical Docs Word export
preventive care in-app reminders
front-desk manual contact queue
ops/read-only support checks
```

Not allowed:

```txt
SMS live sending
WeChat live sending
email live sending
provider credentials
automated external reminder delivery
EMR real import
EMR case update
device ingest
DICOM ingest
lab analyzer ingest
structured prescription write
billing write
```

## Pilot roles

```txt
pilot_clinic_owner
pilot_clinical_lead
pilot_front_desk_lead
release_owner
security_owner
clinical_ops_owner
support_contact
```

## Pre-pilot staff briefing

Before active use, staff should understand:

```txt
AI is assistive only
veterinarian/clinician final judgment remains required
AI review audit is required before saving AI-assisted cases
preventive reminders are not diagnosis or prescription
external client contact remains manual
client opt-out must be respected
do not paste secrets or unnecessary personal data into free text
report access issues immediately
report wrong output or unsafe AI suggestions immediately
```

## Day 0 launch day flow

```txt
run daily health check
confirm named pilot users
confirm clinic workflow scope
confirm no high-risk flags enabled
perform one supervised AI consultation
save one supervised case
open case detail
perform one Word export
review preventive care reminder flow
review manual contact queue
record Day 0 evidence
```

## Days 1-7 operating flow

```txt
run daily health check before active use
record workflow pass/fail
review support issues
review manual contact queue
review opt-out events
review AI audit issues
review Word export issues
record incident log even if zero incidents
```

## Pilot success criteria

```txt
daily checks completed
no P0 incident
no unresolved P1 blocker
clinic staff can complete core workflow
manual contact queue usable
AI review audit understood
no automated external sending
no EMR real write
no cross-user access failure
no secret / PHI leak
pilot metrics recorded
```

## Pilot failure criteria

```txt
cross-user data visible
schema mismatch
online smoke repeatedly fails
staff cannot safely operate core workflow
client contacted after opt-out
unexpected external message sent
EMR real write occurs
secret leaked
unresolved P1 blocks clinic workflow
```

## Pilot evidence

Record daily:

```txt
date
reviewer
backend health
frontend health
system version state
feature flag state
online smoke result
core workflow status
queue status
incidents
open actions
decision
```

## Post-pilot review

At end of D7:

```txt
review daily checklists
review incident log
review pilot metrics
review staff feedback
review support burden
decide: continue / extend stabilization / pause / rollback
```
