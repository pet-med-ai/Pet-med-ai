# EMR Real Import Final Execution Runbook V1

> Scope: final operating runbook before any future EMR real import execution.  
> This document defines who may run the import, what must be checked, how rollback is prepared, and when to stop.  
> It is intentionally **not** an implementation of real Case writes.

## 1. Safety boundary

This V1 runbook is a documentation and operations gate only.

It does **not**:

- create Pet-Med-AI `Case` records;
- update existing `Case` records;
- download EMR attachments;
- consume an execution queue;
- bypass `webhook_inbox` review action;
- bypass `audit_log`;
- bypass clinical signoff;
- bypass rollback snapshot requirements.

The current EMR import path before real writes is:

```text
EMR Webhook dry-run
→ webhook_inbox receipt persistence
→ EMR → Case mapping dry-run
→ webhook inbox review API / UI
→ review action: ready_for_import / needs_fix / rejected
→ import batch planning API / UI
→ execution dry-run
→ clinical approval API / UI
→ final execution runbook
→ future real import execution API
```

## 2. Required Go conditions

A batch may be considered for real execution only when all conditions are true.

| Gate | Requirement |
|---|---|
| Batch status | `approved` or `clinical_signed` |
| Receipt review | all included receipts were manually reviewed and batch-linked |
| Execution dry-run | latest execution dry-run has `quality_gate.passed=true` |
| Clinical signoff | valid `clinical_signoff_id` is present |
| Rollback snapshot | valid `rollback_snapshot_id` is present and restorable |
| Operator | operator ID is recorded |
| Smoke status | latest backend smoke is `ALL PASS` |
| UI review | batch detail and mapped_case_preview have been reviewed |
| No-Go list | no active No-Go condition exists |

## 3. No-Go conditions

If any condition below is true, do not execute real import.

| No-Go reason | Action |
|---|---|
| missing rollback snapshot | stop and create snapshot |
| execution dry-run has blocked items | fix receipts or reject batch |
| batch status is not approved / clinical_signed | send to clinical approval |
| smoke is failing | stop and fix system first |
| EMR payload mismatch with clinical records | mark receipt needs_fix |
| duplicate or reused Idempotency-Key with different payload | investigate and do not import |
| mapped_case_preview lacks patient_name / species / chief_complaint | fix mapping |
| operator cannot identify rollback point | stop |
| Render database current revision is not expected head | stop |
| production support owner unavailable | reschedule |

## 4. Pre-execution checklist

1. Confirm current Git commit deployed on Render backend.
2. Confirm Render PostgreSQL `alembic current` is at the expected head.
3. Confirm `BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh` returns `ALL PASS`.
4. Confirm batch status is `approved` or `clinical_signed`.
5. Confirm latest execution dry-run output was reviewed and archived.
6. Confirm `rollback_snapshot_id` exists and restore procedure is known.
7. Confirm clinical approver and technical operator are available during the execution window.
8. Freeze new EMR sends for the selected batch, or record the event sequence boundary.
9. Record the execution start time, operator ID, and support channel.
10. Confirm no unrelated deployment is running.

## 5. Execution window

Recommended first production execution window:

```text
low-traffic period
batch size <= 20 receipts
operator + clinician both online
rollback owner online
support window >= 60 minutes
```

Suggested phases:

```text
T-30 min: smoke, DB current, snapshot verification
T-15 min: batch detail review
T-5 min: final Go / No-Go
T0: execution starts
T+5 min: immediate smoke
T+15 min: clinical spot check
T+30 min: KPI / audit check
T+60 min: close or rollback decision
```

## 6. Real execution guardrails for future implementation

The future real execution API must enforce:

```text
batch.status in {"approved", "clinical_signed"}
execution dry-run has passed
clinical_signoff_id is present
rollback_snapshot_id is present
operator_id is present
all linked receipts ready_for_import
all target Case write operations are idempotent
every created/updated Case is marked with import_batch_id
audit_log row is appended for every run
no direct attachment download unless attachment pipeline is separately approved
```

The future endpoint should return:

```json
{
  "message": "emr_real_import_executed",
  "batch_id": "emr_batch_xxx",
  "created_case_count": 0,
  "updated_case_count": 0,
  "failed_count": 0,
  "rollback_snapshot_id": "SNAPSHOT-...",
  "audit_log_id": "...",
  "can_rollback": true
}
```

## 7. Rollback plan

Rollback priority:

1. Stop further imports.
2. Identify `batch_id`.
3. Identify imported Case IDs by import marker.
4. If small batch and import marker is complete, reverse created records or restore edited fields.
5. If uncertainty exists, restore database snapshot.
6. Run smoke.
7. Clinical spot check affected cases.
8. Record rollback decision and outcome.

Minimum rollback data:

```text
batch_id
rollback_snapshot_id
operator_id
created_case_ids
updated_case_ids
failed_receipts
audit_log_id
rollback_decision_id
```

## 8. Post-execution monitoring

Monitor for at least 24 hours after first production execution.

| Metric | Threshold |
|---|---|
| backend healthz | always OK |
| smoke | ALL PASS |
| created/updated Case count | equals execution report |
| clinical spot check | pass |
| duplicate Case rate | 0 critical duplicates |
| failed receipt count | reviewed within same day |
| audit log coverage | 100% of execution events |

## 9. Required records

Each execution must leave these records:

```text
Go / No-Go checklist
execution window record
batch_id
clinical_signoff_id
rollback_snapshot_id
operator signoff
execution result
post-execution audit checklist
rollback decision if applicable
```

## 10. Stage completion standard

This runbook stage is complete when:

```text
1. runbook document exists;
2. checklist CSV templates exist;
3. commit succeeds;
4. push succeeds.
```

No local smoke or online smoke is required because this stage changes no runtime code.
