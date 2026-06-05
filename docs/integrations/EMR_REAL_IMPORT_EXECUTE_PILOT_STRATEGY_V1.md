# EMR real import execute pilot strategy V1

## Stage

This document defines the pilot strategy before implementing any real EMR import execution that writes Pet-Med-AI `Case` records.

This stage is documentation and operating strategy only.

## Current prerequisite chain

The following gates must already be complete before any pilot execution implementation is considered:

```txt
EMR Webhook dry-run receiver
Webhook inbox / receipt persistence
EMR -> Case mapping dry-run
Webhook inbox review API / UI / review action
EMR real import batch model
EMR real import batch planning API / UI
EMR execution dry-run
EMR clinical approval API / UI
EMR execution result model
EMR execute API dry-run-protected skeleton
Final execution runbook
Execution API risk review
Execution API design doc
```

## V1 pilot principle

The first real execution pilot must be deliberately small and reversible.

```txt
Pilot batch size: 1-5 receipts
Write policy: create_only
Update policy: disabled
Attachment download: disabled
Medication / prescription structured write: disabled
Billing write: disabled
Case delete: disabled
Rollback rehearsal: mandatory before execution
Clinical spot check: mandatory after execution
```

## Non-negotiable pilot gates

A batch may enter pilot only if all conditions below are true:

```txt
batch.status is approved or clinical_signed
clinical_signoff_id is present
rollback_snapshot_id is present
execution dry-run quality_gate.passed is true
all linked receipts are ready_for_import
all linked receipts have mapped_case_preview
operator signoff completed
rollback owner assigned
pilot window approved
smoke ALL PASS before execution
```

## Hard No-Go conditions

Stop immediately if any item is true:

```txt
No verified database snapshot
No rollback rehearsal
No clinical signoff
Batch contains more than approved pilot limit
Any receipt has blocked reasons in execution dry-run
Any mapped_case_preview missing patient_name/species/chief_complaint
Any receipt has duplicate external_case_id conflict
Any update operation is detected
Any attachment download is required
Any medication/prescription write is requested
Smoke test fails before execution
```

## Pilot import policy

### Create-only

V1 pilot may create new Case records only when:

```txt
existing_case_snapshot is null
operation is case_create_preview
mapped_case_preview has required CaseCreate fields
receipt is ready_for_import
batch link ready_for_import=true
```

### Update disabled

Any operation that would update an existing case must be blocked:

```txt
operation=case_update_preview -> No-Go
existing_case_snapshot exists -> No-Go
```

This avoids overwriting clinical records during the first pilot.

### Attachment disabled

V1 pilot must not download or ingest attachments. It may preserve attachment counts or source references in text summaries only.

### Medication / prescription disabled

V1 pilot must not write medication orders, dose fields, prescription tables, billing rows, or treatment plans as structured medical orders.

Medication text may appear in history/exam summary only when carried from the EMR payload preview.

## Pilot flow

```txt
1. Freeze candidate batch.
2. Run execution dry-run.
3. Confirm quality_gate.passed=true.
4. Confirm rollback_snapshot_id and clinical_signoff_id.
5. Complete pilot Go / No-Go checklist.
6. Execute one small create-only pilot in future implementation stage.
7. Immediately run smoke.
8. Clinically spot-check 100% of created cases.
9. Record audit results.
10. Decide continue / pause / rollback.
```

## Pilot size escalation

Recommended escalation:

```txt
Pilot 0: 1 receipt
Pilot 1: 3 receipts
Pilot 2: 5 receipts
Pilot 3: 10 receipts only after two clean pilots
```

No pilot should exceed 10 receipts until the team has at least two clean production pilot runs.

## Required post-pilot checks

For every created Case:

```txt
patient_name matches EMR pet.name
species normalized correctly
owner_name and owner_phone are correct
chief_complaint is readable
history includes EMR case_id and encounter_id
exam_findings includes vitals summary
no duplicate case created
no update occurred
no attachment downloaded
no medication order created
audit_log exists
execution result exists
rollback marker exists
```

## Rollback rehearsal

Before the first pilot, the team must rehearse rollback on a test batch.

The rehearsal must verify:

```txt
snapshot can be identified
created cases can be identified by import marker
operator can stop execution
rollback owner knows the steps
post-rollback smoke can run
clinical spot check can verify restored state
```

## Required artifacts

```txt
EMR_REAL_IMPORT_PILOT_LIMITS.csv
EMR_REAL_IMPORT_PILOT_SPOT_CHECK_TEMPLATE.csv
EMR_REAL_IMPORT_PILOT_ROLLBACK_REHEARSAL_TEMPLATE.csv
EMR_REAL_IMPORT_PILOT_OPERATOR_RUN_SHEET.csv
EMR_REAL_IMPORT_PILOT_GO_NO_GO_DECISION_TEMPLATE.csv
```

## Completion criteria

```txt
1. Pilot strategy document committed.
2. Pilot limit template committed.
3. Spot check template committed.
4. Rollback rehearsal template committed.
5. Operator run sheet committed.
6. Go / No-Go decision template committed.
```

## Explicit non-goals

This stage does not:

```txt
implement POST /execute real writes
create Case records
update Case records
download attachments
write prescriptions
write billing data
change database schema
change backend runtime
change frontend runtime
```

## Next recommended stage

After this strategy is committed and reviewed:

```txt
EMR real import execute API implementation V1 - create-only pilot
```

That implementation must still be small, audited, and rollback-protected.
