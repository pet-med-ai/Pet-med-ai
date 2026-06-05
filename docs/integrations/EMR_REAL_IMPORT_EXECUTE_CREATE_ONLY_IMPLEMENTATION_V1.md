# EMR real import execute API implementation V1 - create-only pilot

## Stage

This stage implements the first real EMR import execution path, but only as a feature-flag-protected create-only pilot.

Endpoint:

```txt
POST /api/emr/import-batches/{batch_id}/execute
```

## Default behavior

By default this endpoint must be blocked because:

```txt
ENABLE_EMR_REAL_IMPORT=false
```

Smoke must verify the default block.

## Required flags for execution

Before any Case write:

```txt
ENABLE_EMR_REAL_IMPORT=true
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

## Create-only constraints

The implementation may:

```txt
read approved / clinical_signed batches
read linked receipts
read mapped_case_preview
create new Case records
write emr_import_execution_runs
write emr_import_execution_item_results
write audit_log
```

The implementation must not:

```txt
update Case records
delete Case records
download attachments
write structured prescriptions
write billing rows
write device records
```

## Request payload

```json
{
  "operator_id": "HS-0001",
  "clinical_signoff_id": "SIGNOFF-20260605-001",
  "rollback_snapshot_id": "SNAPSHOT-20260605-001",
  "dry_run_ack": true,
  "create_only_ack": true,
  "execution_confirmation": "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
  "request_id": "execute-create-only-20260605-001",
  "note": "Create-only pilot after clinical approval.",
  "metadata": {
    "pilot_level": "pilot_0"
  },
  "max_items": 5
}
```

## Safety response markers

A successful flagged pilot response includes:

```txt
message=emr_real_import_execute_create_only_pilot
mode=create_only_pilot_v1
writes_database=true
writes_case_database=true
writes_audit_log=true
writes_execution_results=true
creates_case=true
updates_case=false
downloads_attachments=false
executes_real_import=true
create_only=true
```

## Pilot limit

Static validation marker: pilot limit

```txt
CREATE_ONLY_PILOT_MAX_RECEIPTS=5
```

The recommended first production run is still pilot_0 = 1 receipt.

## Post-execution requirements

Immediately after execution:

```txt
run smoke
100% clinical spot-check
record execution result
record created_case_id per receipt
record Go / pause / rollback decision
```

## Completion criteria

```txt
1. Endpoint contains feature flag gate.
2. Default smoke verifies feature flag disabled.
3. Code contains create-only Case creation path.
4. Code writes execution run and item result tables.
5. Code writes audit_log.
6. Code blocks updates, deletes, attachments, prescriptions, billing.
7. No production real import should be run until operator intentionally enables ENABLE_EMR_REAL_IMPORT.
```
