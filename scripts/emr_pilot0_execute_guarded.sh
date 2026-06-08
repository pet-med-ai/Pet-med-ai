#!/usr/bin/env bash
set -euo pipefail

echo "== Pet-Med-AI EMR pilot_0 guarded execute =="
echo "This script can create exactly one Case if all gates pass."
echo "It does not change Render environment variables."

required_vars=(
  BASE_URL
  TOKEN
  BATCH_ID
  OPERATOR_ID
  CLINICAL_SIGNOFF_ID
  ROLLBACK_SNAPSHOT_ID
  PILOT0_CONFIRM
)

for name in "${required_vars[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "FAIL missing required env var: $name" >&2
    exit 1
  fi
done

if [[ "$PILOT0_CONFIRM" != "I_UNDERSTAND_THIS_WILL_CREATE_EXACTLY_ONE_CASE" ]]; then
  echo "FAIL PILOT0_CONFIRM must equal I_UNDERSTAND_THIS_WILL_CREATE_EXACTLY_ONE_CASE" >&2
  exit 1
fi

if [[ "${MAX_ITEMS:-1}" != "1" ]]; then
  echo "FAIL MAX_ITEMS must be 1 for pilot_0" >&2
  exit 1
fi

RUN_ID="${RUN_ID:-$(date +%Y%m%d%H%M%S)}"
OUT="${OUT:-/tmp/petmed-pilot0-execute-${RUN_ID}.json}"
FLAGS_OUT="${FLAGS_OUT:-/tmp/petmed-pilot0-flags-${RUN_ID}.json}"

echo "Checking feature flags..."
curl -sS "${BASE_URL}/api/system/feature-flags" > "$FLAGS_OUT"

python3 - "$FLAGS_OUT" <<'PY'
import json
import sys
path = sys.argv[1]
data = json.load(open(path))
flags = data.get("flags") or {}

def enabled(name):
    return bool((flags.get(name) or {}).get("enabled"))

errors = []
if not enabled("ENABLE_EMR_REAL_IMPORT"):
    errors.append("ENABLE_EMR_REAL_IMPORT must be true during the approved execution window")

for name in [
    "ENABLE_EMR_IMPORT_CASE_UPDATE",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
    "ENABLE_DEVICE_REAL_INGEST",
    "ENABLE_BILLING_REAL_WRITE",
    "ENABLE_CASE_DELETE_IMPORT",
]:
    if enabled(name):
        errors.append(f"{name} must remain false")

if errors:
    for err in errors:
        print("FAIL " + err)
    sys.exit(1)

print("Feature flag gate OK: real import enabled, all other dangerous flags disabled")
PY

BODY="$(python3 - <<'PY'
import json
import os

body = {
    "operator_id": os.environ["OPERATOR_ID"],
    "clinical_signoff_id": os.environ["CLINICAL_SIGNOFF_ID"],
    "rollback_snapshot_id": os.environ["ROLLBACK_SNAPSHOT_ID"],
    "dry_run_ack": True,
    "create_only_ack": True,
    "execution_confirmation": "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
    "request_id": f"pilot0-controlled-{os.environ.get('RUN_ID', 'manual')}",
    "note": "pilot_0 controlled execution window; exactly one receipt; create-only.",
    "metadata": {
        "pilot_level": "pilot_0",
        "max_receipts": 1,
        "operator_script": "scripts/emr_pilot0_execute_guarded.sh",
    },
    "max_items": 1,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"

echo "Executing pilot_0 batch: ${BATCH_ID}"
HTTP_STATUS="$(curl -sS -w '%{http_code}' -o "$OUT" -X POST "${BASE_URL}/api/emr/import-batches/${BATCH_ID}/execute" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$BODY")"

echo "HTTP status: $HTTP_STATUS"
echo "Response saved: $OUT"

python3 - "$HTTP_STATUS" "$OUT" <<'PY'
import json
import sys

status = sys.argv[1]
path = sys.argv[2]
try:
    data = json.load(open(path))
except Exception as exc:
    print(f"FAIL cannot parse response JSON: {exc}")
    sys.exit(1)

if status != "201":
    print(f"FAIL expected HTTP 201, got {status}")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

summary = data.get("summary") or {}
checks = [
    (data.get("message") == "emr_real_import_execute_create_only_pilot", "message must be emr_real_import_execute_create_only_pilot"),
    (data.get("mode") == "create_only_pilot_v1", "mode must be create_only_pilot_v1"),
    (summary.get("receipt_count") == 1, "summary.receipt_count must be 1"),
    (summary.get("created_count") == 1, "summary.created_count must be 1"),
    (summary.get("updated_count") == 0, "summary.updated_count must be 0"),
    (data.get("updates_case") is False, "updates_case must be false"),
    (data.get("downloads_attachments") is False, "downloads_attachments must be false"),
    (data.get("create_only") is True, "create_only must be true"),
    (data.get("executes_real_import") is True, "executes_real_import must be true"),
]

errors = [msg for ok, msg in checks if not ok]
if errors:
    for err in errors:
        print("FAIL " + err)
    print(json.dumps(data, ensure_ascii=False, indent=2))
    sys.exit(1)

print("PILOT0_EXECUTE_PASS")
print(f"execution_id={data.get('execution_id')}")
print(f"audit_log_id={data.get('audit_log_id')}")
created = data.get("created_cases") or []
print(f"created_cases={created}")
PY

echo
echo "IMPORTANT: immediately disable ENABLE_EMR_REAL_IMPORT=false in Render, wait for deploy live, then run:"
echo "  BASE_URL=${BASE_URL} bash scripts/smoke_petmed.sh"
echo
echo "Do not run a second execution in the same window."
