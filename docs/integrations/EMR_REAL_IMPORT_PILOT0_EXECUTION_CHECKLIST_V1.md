# EMR real import pilot_0 execution checklist V1

## Stage

This runbook defines the first controlled production pilot for EMR real import execution.

Pilot level:

```txt
pilot_0
```

Pilot limit:

```txt
exactly 1 ready_for_import receipt
```

Execution policy:

```txt
create_only
```

This stage is documentation, checklist, and validation only. It does not execute the pilot and does not enable feature flags.

## Absolute safety rule

Do not enable real import until every gate below is complete and recorded.

```txt
ENABLE_EMR_REAL_IMPORT=false by default
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

During the pilot window, only `ENABLE_EMR_REAL_IMPORT` may be intentionally set to `true`.

All other dangerous flags must remain false.

## Required previous stages

Pilot_0 requires these completed stages:

```txt
Release / Upgrade Framework V1
Version / Build Info V1
Feature Flag / Safety Gate V1
Release Status / Admin Ops Dashboard V1
Release Tag / Changelog V1
GitHub Actions CI Gate V1
Backup / Rollback Verification V1
EMR real import create-only implementation V1
```

## Pilot_0 Go conditions

All must be true:

```txt
GitHub Actions CI Gate latest run is green
Online smoke ALL PASS before pilot
Ops Dashboard overall state is safe
/api/system/version schema_ok=true
database_revision == alembic_head
/api/system/feature-flags all_dangerous_features_disabled=true before pilot window
Render PostgreSQL backup exists
rollback_snapshot_id is recorded
clinical_signoff_id is recorded
batch.status is approved or clinical_signed
batch.receipt_count == 1
execution dry-run quality_gate.passed=true
batch contains only case_create_preview operation
100% clinical spot-check reviewer is assigned
rollback owner is online during execution window
```

## Pilot_0 No-Go conditions

Any one means stop:

```txt
No backup evidence
No rollback_snapshot_id
No clinical_signoff_id
schema_ok=false
database_revision != alembic_head
GitHub Actions red
online smoke fails
dangerous feature flags already enabled unexpectedly
batch has more than 1 receipt
execution dry-run has blocked_items
operation includes case_update_preview
receipt lacks mapped_case_preview
operator cannot identify rollback owner
clinical reviewer unavailable
```

## Pilot_0 exact sequence

### 1. Preflight

```bash
cd ~/Documents/Pet-med-ai

git pull origin main
python3 scripts/validate_backup_rollback_runbook.py
python3 scripts/validate_emr_import_execute_create_only.py
python3 scripts/validate_emr_import_pilot0_checklist.py
bash scripts/ci_static_checks.sh
```

### 2. Confirm online health

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

### 3. Prepare exactly one receipt

Use:

```txt
/webhooks/emr/inbox
```

Select exactly one receipt and mark it:

```txt
ready_for_import
```

### 4. Create or identify pilot_0 batch

Use:

```txt
/emr/import-batches
```

Required batch state:

```txt
receipt_count == 1
status=frozen initially
clinical approval later changes status to approved or clinical_signed
clinical_signoff_id present
rollback_snapshot_id present
```

### 5. Run execution dry-run

Use existing execution dry-run API and record:

```txt
quality_gate.passed=true
would_create_count=1
would_update_count=0
blocked_count=0
rollback_plan present
```

### 6. Clinical approval

Clinical owner must approve:

```txt
approval_action=approve or clinical_signed
clinical_signoff_id matches batch
rollback_snapshot_id matches verified backup
```

### 7. Feature flag pilot window

In Render backend service environment, intentionally set:

```txt
ENABLE_EMR_REAL_IMPORT=true
```

Keep all others false:

```txt
ENABLE_EMR_IMPORT_CASE_UPDATE=false
ENABLE_EMR_ATTACHMENT_DOWNLOAD=false
ENABLE_PRESCRIPTION_STRUCTURED_WRITE=false
ENABLE_DEVICE_REAL_INGEST=false
ENABLE_BILLING_REAL_WRITE=false
ENABLE_CASE_DELETE_IMPORT=false
```

Wait for backend deploy to become live.

Immediately verify feature flags:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
```

Expected only during pilot window:

```txt
real_import_enabled=true
case_update_import_enabled=false
attachment_download_enabled=false
device_real_ingest_enabled=false
```

### 8. Execute pilot_0

Use the cURL template in:

```txt
docs/integrations/EMR_REAL_IMPORT_PILOT0_API_CURL_TEMPLATE.md
```

Expected successful response:

```txt
message=emr_real_import_execute_create_only_pilot
mode=create_only_pilot_v1
summary.receipt_count=1
summary.created_count=1
summary.updated_count=0
updates_case=false
downloads_attachments=false
create_only=true
```

### 9. Immediately close feature flag window

After response is recorded, set Render backend:

```txt
ENABLE_EMR_REAL_IMPORT=false
```

Redeploy / wait until live.

Verify:

```bash
curl -sS https://pet-med-ai-backend.onrender.com/api/system/feature-flags | python3 -m json.tool
```

Required:

```txt
all_dangerous_features_disabled=true
```

### 10. Post-check

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Then complete:

```txt
100% clinical spot-check
created_case_id recorded
execution_id recorded
audit_log_id recorded
Go/Pause/Rollback decision recorded
```

## Completion criteria

Pilot_0 is complete only when:

```txt
1 receipt executed
1 Case created
0 Case updates
0 attachment downloads
0 prescription writes
0 billing writes
online smoke after execution ALL PASS
clinical spot-check passed
feature flag returned to disabled
rollback decision recorded
release record updated
```
