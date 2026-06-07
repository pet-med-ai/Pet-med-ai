# EMR real import pilot_0 dry-run rehearsal API cURL template

## Purpose

Use this template to create exactly one signed EMR dry-run receipt for pilot_0 rehearsal.

This template does not create Case records.

## Variables

```bash
BASE_URL="https://pet-med-ai-backend.onrender.com"
SECRET="petmed-emr-webhook-dry-run-secret-v1"
IDEM="pilot0-dryrun-$(date +%Y%m%d%H%M%S)"
```

## Payload

```bash
BODY='{
  "case_id": "PILOT0-DRYRUN-CASE-001",
  "pet": {
    "name": "Pilot0DryRunPet",
    "species": "cat",
    "dob": "2023-01-01",
    "weight_kg": 3.2
  },
  "owner": {
    "name": "Pilot0DryRunOwner",
    "phone": "13800000000"
  },
  "encounter": {
    "encounter_id": "PILOT0-DRYRUN-ENC-001",
    "status": "updated",
    "chief_complaint": "pilot_0 dry-run rehearsal only",
    "vitals": {
      "temp_c": 38.6,
      "hr": 120,
      "rr": 28,
      "weight_kg": 3.2
    },
    "diagnosis_codes": [],
    "procedures": [],
    "meds": []
  },
  "attachments": [],
  "clinician": {
    "id": "HS-0001",
    "name": "Pilot Operator"
  },
  "timestamps": {
    "created_at": "2026-06-07T00:00:00Z",
    "updated_at": "2026-06-07T00:00:00Z"
  }
}'
```

## Sign and send

```bash
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
SIG="sha256=$(printf "%s.%s" "$TS" "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -binary | xxd -p -c 256)"

curl -sS -X POST "${BASE_URL}/api/webhooks/emr/case-mapping/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${TS}" \
  -H "X-PMAI-Signature: ${SIG}" \
  -H "Idempotency-Key: ${IDEM}" \
  --data "$BODY" | python3 -m json.tool
```

## Expected response

```txt
message=emr_case_mapping_dry_run
receipt_persisted=true
writes_webhook_inbox=true
writes_case_database=false
creates_case=false
updates_case=false
downloads_attachments=false
mapped_case_preview present
```

## Execute block proof

During rehearsal, `/execute` must remain blocked because:

```txt
ENABLE_EMR_REAL_IMPORT=false
```

Expected:

```txt
HTTP 403
feature flag disabled
ENABLE_EMR_REAL_IMPORT
```
