# EMR real import pilot_0 API cURL template

## Purpose

Use this template only during an approved pilot_0 feature flag window.

Do not run this while:

```txt
ENABLE_EMR_REAL_IMPORT=false
rollback_snapshot_id missing
clinical_signoff_id missing
execution dry-run not passed
online smoke not passed
```

## Required variables

```bash
BASE_URL="https://pet-med-ai-backend.onrender.com"
TOKEN="<paste-auth-token>"
BATCH_ID="<approved-batch-id>"
CLINICAL_SIGNOFF_ID="<clinical-signoff-id>"
ROLLBACK_SNAPSHOT_ID="<rollback-snapshot-id>"
RUN_ID="$(date +%Y%m%d%H%M%S)"
```

## Execute pilot_0

```bash
curl -sS -X POST "${BASE_URL}/api/emr/import-batches/${BATCH_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"operator_id\": \"HS-0001\",
    \"clinical_signoff_id\": \"${CLINICAL_SIGNOFF_ID}\",
    \"rollback_snapshot_id\": \"${ROLLBACK_SNAPSHOT_ID}\",
    \"dry_run_ack\": true,
    \"create_only_ack\": true,
    \"execution_confirmation\": \"I_UNDERSTAND_THIS_WILL_CREATE_CASES\",
    \"request_id\": \"pilot0-${RUN_ID}\",
    \"note\": \"pilot_0 create-only execution; exactly one receipt; rollback snapshot verified.\",
    \"metadata\": {
      \"pilot_level\": \"pilot_0\",
      \"max_receipts\": 1
    },
    \"max_items\": 1
  }" | python3 -m json.tool
```

## Expected response markers

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

## Immediate after-action

```bash
BASE_URL=https://pet-med-ai-backend.onrender.com bash scripts/smoke_petmed.sh
```

Then disable:

```txt
ENABLE_EMR_REAL_IMPORT=false
```
