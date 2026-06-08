# EMR real import pilot_0 controlled execution window V1

## Stage

This stage defines the controlled execution window for the first real EMR import pilot.

Pilot level:

```txt
pilot_0
```

Execution scope:

```txt
exactly one ready_for_import receipt
exactly one approved / clinical_signed batch
create_only
maximum one Case creation
```

This package includes a guarded operator script, runbook, evidence templates, and validators.

## Critical safety boundary

This stage does not automatically:

```txt
change Render environment variables
enable ENABLE_EMR_REAL_IMPORT
run the execute endpoint
create Case records
update Case records
download attachments
write prescriptions
write billing rows
run Alembic
change database schema
```

The provided script only executes if the operator manually sets explicit environment variables and confirmation text.

## Required preconditions

Do not enter the execution window unless all are true:

```txt
Final Go / No-Go decision is GO
GitHub Actions CI Gate latest run green
online smoke before window ALL PASS
schema_ok=true
database_revision == alembic_head
Render / GitHub Security Hardening V1 complete
backup_id recorded
rollback_snapshot_id recorded
clinical_signoff_id recorded
receipt_id recorded
batch_id recorded
batch.receipt_count == 1
batch.status is approved or clinical_signed
execution dry-run quality_gate.passed=true
would_create_count=1
would_update_count=0
blocked_count=0
clinical reviewer ready
rollback owner ready
operator ready
```

## Feature flag window

Before window:

```txt
ENABLE_EMR_REAL_IMPORT=false
```

During window, and only during the approved short window:

```txt
ENABLE_EMR_REAL_IMPORT=true
```

All other dangerous flags must remain false:

```txt
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

Immediately after the single execution response is recorded:

```txt
ENABLE_EMR_REAL_IMPORT=false
```

## Execution command

Use the guarded script:

```bash
scripts/emr_pilot0_execute_guarded.sh
```

The script requires:

```txt
BASE_URL
TOKEN
BATCH_ID
OPERATOR_ID
CLINICAL_SIGNOFF_ID
ROLLBACK_SNAPSHOT_ID
PILOT0_CONFIRM=I_UNDERSTAND_THIS_WILL_CREATE_EXACTLY_ONE_CASE
```

The script refuses to run if required variables are missing.

## Expected successful response

```txt
message=emr_real_import_execute_create_only_pilot
mode=create_only_pilot_v1
summary.receipt_count=1
summary.created_count=1
summary.updated_count=0
updates_case=false
downloads_attachments=false
create_only=true
executes_real_import=true
```

## Immediate post execution

After the response is captured:

```txt
1. Disable ENABLE_EMR_REAL_IMPORT=false in Render.
2. Wait for backend deploy to be live.
3. Verify /api/system/feature-flags shows all dangerous flags disabled.
4. Run online smoke.
5. Perform 100% clinical spot-check of created_case_id.
6. Record execution_id, audit_log_id, created_case_id.
7. Record Go / Pause / Rollback post-decision.
```

## Hard stop after execution

Stop and call rollback owner if any is true:

```txt
created_count > 1
updated_count > 0
downloads_attachments=true
updates_case=true
creates_case=false with unexpected failure
online smoke after execution fails
clinical spot-check fails
duplicate Case detected
feature flag cannot be disabled after execution
```

## Completion criteria

This controlled execution window stage is complete when:

```txt
1. Controlled execution runbook committed.
2. Guarded execute script committed.
3. Window checklist committed.
4. Execution result record template committed.
5. Feature flag closeout template committed.
6. Post-execution checklist committed.
7. Validator committed and included in smoke.
8. CI static checks include the validator.
```
