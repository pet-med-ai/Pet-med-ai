# EMR real import create-only implementation risk gate V1

## Stage

This is a pre-implementation risk gate before building any real EMR import code that creates Pet-Med-AI `Case` records.

This stage is documentation and approval-gate only.

It does not:

```txt
implement POST /execute real writes
create Case records
update Case records
download attachments
write prescriptions
write billing records
change database schema
change backend runtime
change frontend runtime
```

## Current state before this gate

Pet-Med-AI already has:

```txt
EMR webhook dry-run receiver
webhook_inbox receipt persistence
EMR -> Case mapping dry-run
Webhook inbox review API / UI / review action
EMR real import batch model
EMR real import batch planning API / UI
EMR execution dry-run
EMR clinical approval API / UI
EMR execution result model
EMR execute API dry-run-protected skeleton
EMR execute pilot strategy
Feature flags / safety gates
Release / upgrade framework
Version / build info endpoint
```

## Why this gate exists

Real EMR import is the first stage that may write clinical data from an external system into Pet-Med-AI.

The first implementation must therefore be:

```txt
create-only
small batch
feature-flag protected
rollback protected
fully audited
smoke tested before and after
100% clinically spot-checked
```

## Proposed next implementation

Future stage name:

```txt
EMR real import execute API implementation V1 - create-only pilot
```

Future endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/execute
```

This endpoint is currently blocked by skeleton V1. It may only be converted to real create-only execution after this risk gate is approved.

## Mandatory implementation boundaries

### Allowed

The first implementation may:

```txt
read approved / clinical_signed batches
read linked emr_import_batch_receipts
read linked webhook_inbox receipts
read mapped_case_preview
create new Case records only
write emr_import_execution_runs
write emr_import_execution_item_results
write audit_log
write import markers in result tables
return created_case_id per item
```

### Forbidden

The first implementation must not:

```txt
update existing Case records
delete Case records
download attachments
create prescriptions or structured medication orders
write billing / invoice rows
create device records
silently skip audit_log
run without feature flag
run without rollback_snapshot_id
run without clinical_signoff_id
run if execution dry-run quality gate fails
run batch size above pilot limit
```

## Required feature flags

The following flags must be checked before any real write:

```txt
ENABLE_EMR_REAL_IMPORT=true
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

If `ENABLE_EMR_REAL_IMPORT` is not explicitly true, the future endpoint must return HTTP 403 before any database write.

## Required batch state

A batch can be executed only if:

```txt
batch.status in approved / clinical_signed
batch.clinical_signoff_id is present
batch.rollback_snapshot_id is present
batch.receipt_count <= approved pilot limit
execution dry-run quality_gate.passed=true
all items operation=case_create_preview
all items existing_case_snapshot=null
all linked receipts status=ready_for_import
all linked receipts have mapped_case_preview
```

## Required fields for Case creation

Each `mapped_case_preview` must contain:

```txt
patient_name
species
chief_complaint
```

Recommended fields:

```txt
owner_name
owner_phone
weight
history
exam_findings
```

Optional fields:

```txt
sex
age_info
breed
coat_color
```

## Duplicate protection

Before creating a Case, implementation must check for likely duplicates.

Minimum duplicate checks:

```txt
external_case_id already created in execution results
receipt_id already executed successfully
idempotency_key already executed successfully
same patient_name + owner_phone + chief_complaint + external_case_id
```

If duplicate risk is detected, the item must be blocked and recorded as skipped / failed in execution result tables.

## Case write policy

### Create-only

Allowed:

```txt
Case(owner_id=operator/import service user, patient_name=..., species=..., chief_complaint=..., history=..., exam_findings=...)
```

Required import marker should be recorded in execution result tables, not necessarily in Case fields.

### Update disabled

If a receipt points to an existing Case or dry-run identifies `case_update_preview`, implementation must not write that item.

### Owner policy

V1 should not assign imported cases to arbitrary external owner IDs.

Acceptable V1 options:

```txt
use current authenticated operator user_id
use a dedicated import service user if explicitly configured
```

This must be decided before implementation.

## Audit policy

Each execution must append audit records.

Minimum audit events:

```txt
emr_import_execute_started
emr_import_case_created
emr_import_item_failed
emr_import_execute_completed
emr_import_execute_aborted
```

Audit must include:

```txt
batch_id
execution_id
receipt_id
created_case_id if any
operator_id
clinical_signoff_id
rollback_snapshot_id
feature flag snapshot
execution dry-run summary
```

## Rollback policy

Before pilot execution:

```txt
rollback_snapshot_id must be verified
rollback rehearsal must pass
created cases must be identifiable by execution_id / receipt_id
operator must know stop procedure
post-rollback smoke must be defined
```

Rollback strategy for create-only pilot:

```txt
preferred: restore database snapshot for production pilot failure
secondary: soft-delete or reverse created cases only if explicitly approved and traceable
```

## Pilot levels

```txt
pilot_0: 1 receipt
pilot_1: 3 receipts
pilot_2: 5 receipts
pilot_3: 10 receipts only after two clean pilots
```

No pilot should exceed 10 receipts before repeated clean runs.

## Go conditions

All must be true:

```txt
Feature flag framework deployed
Version endpoint schema_ok=true
Release readiness validation passes
Online smoke ALL PASS
Batch approved or clinical_signed
Rollback snapshot verified
Execution dry-run quality gate passed
Clinical approval completed
Pilot size within approved limit
Create-only contract approved
Operator run sheet complete
Spot-check reviewer assigned
```

## No-Go conditions

Any one stops implementation:

```txt
ENABLE_EMR_REAL_IMPORT not explicitly controlled
Any update path exists
Any attachment download path exists
Any prescription write path exists
Any billing write path exists
No rollback snapshot
No clinical signoff
No audit_log plan
No execution result write plan
No duplicate protection
No post-execution smoke plan
No 100% pilot spot-check plan
```

## Required review signatures

Before implementing create-only pilot code, collect:

```txt
technical owner
clinical owner
rollback owner
operator
data compliance owner
```

## Decision

Default decision for this gate:

```txt
Do not implement real Case writes until this risk gate is reviewed and signed.
```

Recommended next stage after this document is approved:

```txt
EMR real import execute API implementation V1 - create-only pilot
```

## Completion criteria

This stage is complete when:

```txt
1. Risk gate document is committed.
2. Risk register CSV is committed.
3. Allowed field matrix is committed.
4. No-Go checklist is committed.
5. Implementation contract draft is committed.
6. Operator approval template is committed.
```
