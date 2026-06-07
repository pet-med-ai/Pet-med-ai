# EMR real import pilot_0 dry-run rehearsal V1

## Stage

This runbook defines a full pilot_0 rehearsal that uses the production-like EMR import chain but intentionally stops before real Case creation.

Pilot level:

```txt
pilot_0 dry-run rehearsal
```

Rehearsal policy:

```txt
no real import
no Case creation
no Case update
no attachment download
no prescription write
no billing write
ENABLE_EMR_REAL_IMPORT=false throughout
```

## Purpose

The goal is to rehearse the complete operational chain before the first true pilot_0 create-only execution.

The rehearsal walks through:

```txt
EMR webhook signed dry-run
webhook_inbox receipt persistence
human review action = ready_for_import
batch planning with exactly one receipt
execution dry-run
clinical approval
feature flag verification
online smoke before and after
evidence recording
Go / No-Go decision
```

It does not call `/execute` with real import enabled.

## Absolute stop line

This rehearsal must never enable:

```txt
ENABLE_EMR_REAL_IMPORT=true
```

Expected feature flag state throughout rehearsal:

```txt
ENABLE_EMR_REAL_IMPORT=false
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

## Required previous stages

```txt
EMR real import pilot_0 execution checklist V1
Backup / Rollback Verification V1
GitHub Actions CI Gate V1
Release Status / Admin Ops Dashboard V1
Feature Flag / Safety Gate V1
EMR real import create-only implementation V1
```

## Go conditions for rehearsal

All must be true:

```txt
GitHub Actions CI Gate latest run is green
online smoke ALL PASS
/api/system/version schema_ok=true
database_revision == alembic_head
/api/system/feature-flags all_dangerous_features_disabled=true
rollback_snapshot_id selected for rehearsal
clinical_signoff_id selected for rehearsal
operator and clinical reviewer available
```

## Rehearsal exact sequence

### 1. Static preflight

```bash
cd ~/Documents/Pet-med-ai

git pull origin main
python3 scripts/validate_emr_import_pilot0_dry_run_rehearsal.py
python3 scripts/validate_emr_import_pilot0_checklist.py
python3 scripts/validate_backup_rollback_runbook.py
bash scripts/ci_static_checks.sh
```

### 2. Online health and version

```bash
curl -sS https://pet-med-ai-backend.onrender.com/healthz
curl -sS https://pet-med-ai-backend.onrender.com/api/system/version | python3 -m json.tool
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Required:

```txt
healthz ok
schema_ok=true
database_revision == alembic_head
all_dangerous_features_disabled=true
online smoke ALL PASS
```

### 3. Create one signed EMR dry-run receipt

Use the cURL template:

```txt
docs/integrations/EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_API_CURL_TEMPLATE.md
```

Expected:

```txt
message=emr_case_mapping_dry_run or emr_webhook_dry_run
receipt_persisted=true
writes_webhook_inbox=true
writes_case_database=false
creates_case=false
mapped_case_preview present
```

### 4. Review one receipt

Open:

```txt
/webhooks/emr/inbox
```

Apply review action:

```txt
ready_for_import
```

Expected:

```txt
writes_webhook_inbox=true
writes_audit_log=true
writes_case_database=false
creates_case=false
updates_case=false
```

### 5. Create one-receipt batch

Open:

```txt
/emr/import-batches
```

Create or select a batch with:

```txt
receipt_count=1
status=frozen
clinical_signoff_id=SIGNOFF-DRYRUN-...
rollback_snapshot_id=SNAPSHOT-DRYRUN-...
```

Expected:

```txt
writes_emr_import_batches=true
writes_emr_import_batch_receipts=true
writes_audit_log=true
writes_case_database=false
creates_case=false
```

### 6. Run execution dry-run

Use the execution dry-run endpoint.

Expected:

```txt
quality_gate.passed=true
would_create_count=1
would_update_count=0
blocked_count=0
writes_database=false
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
executes_real_import=false
can_execute_import=false
rollback_plan present
```

### 7. Clinical approval rehearsal

Submit clinical approval for the frozen batch.

Expected:

```txt
status_after=approved or clinical_signed
audit_log_id present
writes_emr_import_batches=true
writes_audit_log=true
writes_case_database=false
creates_case=false
executes_real_import=false
can_execute_import=false
```

### 8. Prove /execute is still blocked

Because `ENABLE_EMR_REAL_IMPORT=false`, calling `/execute` should return:

```txt
HTTP 403
feature flag disabled
ENABLE_EMR_REAL_IMPORT
```

This is a safety proof. Do not enable the flag during this rehearsal.

### 9. Post rehearsal smoke

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Required:

```txt
ALL PASS
```

### 10. Record decision

Complete:

```txt
docs/integrations/EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_EVIDENCE_TEMPLATE.csv
docs/integrations/EMR_REAL_IMPORT_PILOT0_DRY_RUN_REHEARSAL_GO_NO_GO_TEMPLATE.csv
```

## Completion criteria

```txt
1 signed receipt persisted
1 receipt reviewed ready_for_import
1 frozen batch created with exactly 1 receipt
execution dry-run passed
clinical approval rehearsal completed
/execute remained blocked by feature flag
online smoke after rehearsal ALL PASS
evidence template completed
Go / No-Go decision recorded
ENABLE_EMR_REAL_IMPORT remained false throughout
```

## Explicit non-goals

This rehearsal does not:

```txt
open ENABLE_EMR_REAL_IMPORT
create Case
update Case
download attachments
write prescriptions
write billing
run Render Shell
run Alembic upgrade
change database schema
```
