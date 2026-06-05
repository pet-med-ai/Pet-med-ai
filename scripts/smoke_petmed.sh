#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"
PASSWORD="${PASSWORD:-123456}"
KEEP_TMP="${KEEP_TMP:-0}"

TMP_DIR="$(mktemp -d -t petmed-smoke.XXXXXX)"
RESPONSE_BODY=""
RESPONSE_STATUS=""

if [[ "$KEEP_TMP" != "1" ]]; then
  trap 'rm -rf "$TMP_DIR"' EXIT
else
  echo "KEEP_TMP=1，临时文件保留在：$TMP_DIR"
fi

pass() {
  printf "PASS %-48s\n" "$1"
}

fail() {
  local msg="$1"
  echo
  echo "FAIL $msg" >&2
  if [[ -n "${RESPONSE_BODY:-}" && -f "$RESPONSE_BODY" ]]; then
    echo "---- last response status: ${RESPONSE_STATUS:-unknown} ----" >&2
    cat "$RESPONSE_BODY" >&2 || true
    echo >&2
  fi
  echo "BASE_URL=$BASE_URL" >&2
  echo "TMP_DIR=$TMP_DIR" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "缺少命令：$1"
}

require_cmd curl
require_cmd python3

python3 scripts/validate_legacy_cases_csv.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv --errors-out "$TMP_DIR/legacy_migration_errors.csv" >/dev/null || fail "legacy cases CSV validation failed"
pass "legacy cases CSV validation"

python3 scripts/legacy_cases_to_case_payloads.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv \
  --jsonl-out "$TMP_DIR/legacy_case_payloads.jsonl" \
  --errors-out "$TMP_DIR/legacy_case_payload_errors.csv" \
  --report-out "$TMP_DIR/legacy_case_payload_report.json" >/dev/null || fail "legacy case payload dry-run failed"
python3 - "$TMP_DIR/legacy_case_payloads.jsonl" "$TMP_DIR/legacy_case_payload_report.json" <<'PY' || fail "legacy case payload dry-run output invalid"
import json
import sys
jsonl_path, report_path = sys.argv[1], sys.argv[2]
with open(jsonl_path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]
if len(records) != 1:
    print(f"expected 1 JSONL record, got {len(records)}")
    sys.exit(2)
record = records[0]
payload = record.get("case_create") or {}
assert record.get("operation") == "case_create"
assert record.get("dry_run") is True
assert record.get("idempotency_key")
assert payload.get("patient_name") == "咪咪"
assert payload.get("species") == "cat"
assert payload.get("weight") == "3.20kg"
assert "Acute gastroenteritis" in (payload.get("chief_complaint") or "")
assert "旧系统迁移记录" in (payload.get("history") or "")
assert "影像数量：2" in (payload.get("exam_findings") or "")
with open(report_path, "r", encoding="utf-8") as f:
    report = json.load(f)
assert report.get("status") == "PASS"
assert report.get("writes_database") is False
assert report.get("calls_api") is False
assert report.get("payload_rows") == 1
print("ok")
PY
pass "legacy case payload dry-run"

python3 scripts/validate_alembic_setup.py >/dev/null || fail "alembic migration setup validation failed"
pass "alembic migration setup validation"

python3 scripts/validate_release_readiness.py >/dev/null || fail "release readiness validation failed"
pass "release readiness validation"

python3 scripts/validate_kpi_api.py >/dev/null || fail "kpi aggregation API validation failed"
pass "kpi aggregation API validation"

python3 scripts/validate_kpi_dashboard_frontend.py >/dev/null || fail "kpi dashboard frontend validation failed"
pass "kpi dashboard frontend validation"

python3 scripts/validate_kpi_data_models.py >/dev/null || fail "kpi data model validation failed"
pass "kpi data model validation"

python3 scripts/validate_audit_log_model.py >/dev/null || fail "audit log model validation failed"
pass "audit log model validation"

python3 scripts/validate_webhook_inbox_model.py >/dev/null || fail "webhook inbox model validation failed"
pass "webhook inbox model validation"

python3 scripts/validate_emr_import_batch_model.py >/dev/null || fail "emr real import batch model validation failed"
pass "emr real import batch model validation"

python3 scripts/validate_emr_import_batch_planning_api.py >/dev/null || fail "emr real import batch planning API validation failed"
pass "emr real import batch planning API validation"

python3 scripts/validate_emr_import_execution_dry_run.py >/dev/null || fail "emr real import execution dry-run validation failed"
pass "emr real import execution dry-run validation"

python3 scripts/validate_emr_import_execution_result_model.py >/dev/null || fail "emr import execution result model validation failed"
pass "emr import execution result model validation"

python3 scripts/validate_emr_import_clinical_approval_api.py >/dev/null || fail "emr real import clinical approval API validation failed"
pass "emr real import clinical approval API validation"

python3 scripts/validate_emr_import_execute_skeleton.py >/dev/null || fail "emr real import execute skeleton validation failed"
pass "emr real import execute skeleton validation"

python3 scripts/validate_emr_import_clinical_approval_ui.py >/dev/null || fail "emr real import clinical approval UI validation failed"
pass "emr real import clinical approval UI validation"


python3 scripts/validate_audit_log_api.py >/dev/null || fail "audit log append-only API validation failed"
pass "audit log append-only API validation"

python3 scripts/validate_emr_webhook_dry_run.py >/dev/null || fail "emr webhook dry-run validation failed"
pass "emr webhook dry-run validation"

python3 scripts/validate_emr_webhook_receipt_persistence.py >/dev/null || fail "emr webhook receipt persistence validation failed"
pass "emr webhook receipt persistence validation"

python3 scripts/validate_webhook_inbox_review_api.py >/dev/null || fail "webhook inbox review API validation failed"
pass "webhook inbox review API validation"

python3 scripts/validate_webhook_inbox_ui.py >/dev/null || fail "webhook inbox detail UI validation failed"
pass "webhook inbox detail UI validation"

python3 scripts/validate_emr_import_batch_planning_ui.py >/dev/null || fail "emr import batch planning UI validation failed"
pass "emr import batch planning UI validation"

python3 scripts/validate_emr_case_mapping_dry_run.py >/dev/null || fail "emr to case mapping dry-run validation failed"
pass "emr to case mapping dry-run validation"

python3 scripts/validate_webhook_inbox_review_action.py >/dev/null || fail "webhook inbox review action validation failed"
pass "webhook inbox review action validation"

python3 scripts/validate_ai_review_audit_ui.py >/dev/null || fail "AI review audit UI validation failed"
pass "AI review audit UI validation"

python3 scripts/validate_alembic_runtime.py >/dev/null || fail "alembic runtime validation failed"
pass "alembic runtime validation"


python3 scripts/validate_exotic_kb.py >/dev/null || fail "exotic knowledge JSON validation failed"
pass "exotic knowledge JSON validation"
python3 scripts/validate_companion_kb.py >/dev/null || fail "companion animal knowledge JSON validation failed"
pass "companion animal knowledge JSON validation"
python3 scripts/validate_exotic_intake_templates.py >/dev/null || fail "exotic structured intake validation failed"
pass "exotic structured intake validation"

http_json() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  local token="${4:-}"
  local out
  out="$TMP_DIR/resp_$(date +%s%N).json"

  local args=(
    -sS
    --connect-timeout 15
    --max-time 120
    -X "$method"
    "${BASE_URL}${path}"
    -o "$out"
    -w "%{http_code}"
  )

  if [[ -n "$body" ]]; then
    args+=(-H "Content-Type: application/json" -d "$body")
  fi

  if [[ -n "$token" ]]; then
    args+=(-H "Authorization: Bearer ${token}")
  fi

  RESPONSE_STATUS="$(curl "${args[@]}")" || {
    RESPONSE_BODY="$out"
    fail "请求失败：$method $path"
  }
  RESPONSE_BODY="$out"
}

http_form() {
  local path="$1"
  local form="$2"
  local token="${3:-}"
  local out
  out="$TMP_DIR/resp_$(date +%s%N).json"

  local args=(
    -sS
    --connect-timeout 15
    --max-time 120
    -X POST
    "${BASE_URL}${path}"
    -H "Content-Type: application/x-www-form-urlencoded"
    -d "$form"
    -o "$out"
    -w "%{http_code}"
  )

  if [[ -n "$token" ]]; then
    args+=(-H "Authorization: Bearer ${token}")
  fi

  RESPONSE_STATUS="$(curl "${args[@]}")" || {
    RESPONSE_BODY="$out"
    fail "请求失败：POST $path"
  }
  RESPONSE_BODY="$out"
}

expect_status() {
  local expected="$1"
  local label="$2"
  if [[ "$RESPONSE_STATUS" != "$expected" ]]; then
    fail "$label：期望 HTTP $expected，实际 HTTP $RESPONSE_STATUS"
  fi
  pass "$label"
}

json_get() {
  local file="$1"
  local path="$2"
  python3 - "$file" "$path" <<'PY'
import json
import sys

file_path, dotted = sys.argv[1], sys.argv[2]
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cur = data
for part in dotted.split("."):
    if part == "":
        continue
    if isinstance(cur, list):
        cur = cur[int(part)]
    elif isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
    if cur is None:
        break

if cur is None:
    print("")
elif isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
else:
    print(cur)
PY
}

json_assert_session_case() {
  local file="$1"
  local session_id="$2"
  local expected_case_id="$3"
  python3 - "$file" "$session_id" "$expected_case_id" <<'PY'
import json
import sys

file_path, session_id, expected_case_id = sys.argv[1], sys.argv[2], str(sys.argv[3])
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items") or []
for item in items:
    if item.get("session_id") == session_id:
        actual = item.get("case_id")
        if str(actual) == expected_case_id:
            print("ok")
            sys.exit(0)
        print(f"session found but case_id mismatch: actual={actual!r}, expected={expected_case_id!r}")
        sys.exit(2)

print("session not found in history")
sys.exit(3)
PY
}

json_assert_not_contains_session() {
  local file="$1"
  local session_id="$2"
  python3 - "$file" "$session_id" <<'PY'
import json
import sys

file_path, session_id = sys.argv[1], sys.argv[2]
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items") or []
for item in items:
    if item.get("session_id") == session_id:
        print("forbidden session is visible")
        sys.exit(2)
print("ok")
PY
}

json_assert_session_present() {
  local file="$1"
  local session_id="$2"
  python3 - "$file" "$session_id" <<'PY'
import json
import sys

file_path, session_id = sys.argv[1], sys.argv[2]
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items") or []
for item in items:
    if item.get("session_id") == session_id:
        print("ok")
        sys.exit(0)

print("session not found")
sys.exit(3)
PY
}

json_assert_text_contains() {
  local file="$1"
  local path="$2"
  local needle="$3"
  python3 - "$file" "$path" "$needle" <<'PY'
import json
import sys

file_path, dotted, needle = sys.argv[1], sys.argv[2], sys.argv[3]
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cur = data
for part in dotted.split("."):
    if isinstance(cur, list):
        cur = cur[int(part)]
    elif isinstance(cur, dict):
        cur = cur.get(part)
    else:
        cur = None
    if cur is None:
        break

text = "" if cur is None else str(cur)
if needle not in text:
    print(f"field {dotted!r} does not contain {needle!r}; actual={text[:500]!r}")
    sys.exit(2)

print("ok")
PY
}

run_id="$(date +%s)$RANDOM"
email_a="smokea${run_id}@gmail.com"
email_b="smokeb${run_id}@gmail.com"

echo "Pet-Med-AI smoke test"
echo "BASE_URL=$BASE_URL"
echo "USER_A=$email_a"
echo "USER_B=$email_b"
echo

# 1. healthz
http_json GET "/healthz"
expect_status 200 "healthz"

# EMR Webhook dry-run V1: signed handshake without DB writes.
emr_body_file="$TMP_DIR/emr_webhook_body.json"
emr_headers_file="$TMP_DIR/emr_webhook_headers.json"
python3 - "$run_id" "$emr_body_file" "$emr_headers_file" <<'PY'
import hashlib
import hmac
import json
import sys
from datetime import datetime, timezone

run_id, body_path, headers_path = sys.argv[1], sys.argv[2], sys.argv[3]
secret = "petmed-emr-webhook-dry-run-secret-v1"
body = {
    "case_id": f"CASE-SMOKE-{run_id}",
    "pet": {
        "name": "咪咪",
        "species": "cat",
        "dob": "2023-09-01",
        "weight_kg": 3.2,
    },
    "owner": {
        "name": "王小花",
        "phone": "+86-13900000000",
        "id": "OWNER-SMOKE",
    },
    "encounter": {
        "encounter_id": f"ENC-SMOKE-{run_id}",
        "status": "updated",
        "chief_complaint": "呕吐、腹泻、食欲差",
        "vitals": {
            "temp_c": 39.2,
            "hr": 160,
            "rr": 32,
            "weight_kg": 3.1,
            "bcs": 4,
        },
        "diagnosis_codes": ["K52.9", "R11"],
        "procedures": ["US-ABDOMEN", "CBC", "BIOCHEM"],
        "meds": [
            {"name": "奥美拉唑", "dose": "1 mg/kg", "route": "PO", "freq": "q24h"},
        ],
    },
    "attachments": [
        {"presigned_url": "https://files.example.com/presigned/smoke.jpg"},
    ],
    "clinician": {"id": "CLN-SMOKE", "name": "Smoke Clinician"},
    "timestamps": {
        "created_at": "2026-05-25T09:12:33Z",
        "updated_at": "2026-05-25T10:05:11Z",
    },
}
raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
sig = "sha256=" + hmac.new(secret.encode("utf-8"), (ts + "." + raw).encode("utf-8"), hashlib.sha256).hexdigest()
headers = {
    "timestamp": ts,
    "signature": sig,
    "idempotency_key": f"smoke-emr-{run_id}",
}
with open(body_path, "w", encoding="utf-8") as f:
    f.write(raw)
with open(headers_path, "w", encoding="utf-8") as f:
    json.dump(headers, f, ensure_ascii=False)
PY

emr_ts="$(json_get "$emr_headers_file" "timestamp")"
emr_sig="$(json_get "$emr_headers_file" "signature")"
emr_idem="$(json_get "$emr_headers_file" "idempotency_key")"
emr_resp="$TMP_DIR/emr_webhook_resp.json"

RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
  -X POST "${BASE_URL}/api/webhooks/emr/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${emr_ts}" \
  -H "X-PMAI-Signature: ${emr_sig}" \
  -H "Idempotency-Key: ${emr_idem}" \
  --data-binary "@${emr_body_file}" \
  -o "$emr_resp" \
  -w "%{http_code}")" || {
    RESPONSE_BODY="$emr_resp"
    fail "请求失败：POST /api/webhooks/emr/dry-run"
  }
RESPONSE_BODY="$emr_resp"
expect_status 202 "emr webhook dry-run accepted"
emr_receipt_id="$(json_get "$RESPONSE_BODY" "receipt_id")"
[[ -n "$emr_receipt_id" ]] || fail "emr webhook dry-run：没有 receipt_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_webhook_dry_run" >/dev/null || fail "emr webhook dry-run：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "status" "accepted" >/dev/null || fail "emr webhook dry-run：status 未 accepted"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "True" >/dev/null || fail "emr webhook dry-run：应写入 webhook_inbox receipt"
json_assert_text_contains "$RESPONSE_BODY" "writes_webhook_inbox" "True" >/dev/null || fail "emr webhook dry-run：应写入 webhook_inbox"
json_assert_text_contains "$RESPONSE_BODY" "writes_case_database" "False" >/dev/null || fail "emr webhook dry-run：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "emr webhook dry-run：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "downloads_attachments" "False" >/dev/null || fail "emr webhook dry-run：不应下载附件"
json_assert_text_contains "$RESPONSE_BODY" "receipt_persisted" "True" >/dev/null || fail "emr webhook dry-run：receipt 未持久化"
json_assert_text_contains "$RESPONSE_BODY" "mapped_case_preview.patient_name" "咪咪" >/dev/null || fail "emr webhook dry-run：patient_name 映射错误"
json_assert_text_contains "$RESPONSE_BODY" "mapped_case_preview.species" "cat" >/dev/null || fail "emr webhook dry-run：species 映射错误"

RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
  -X POST "${BASE_URL}/api/webhooks/emr/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${emr_ts}" \
  -H "X-PMAI-Signature: ${emr_sig}" \
  -H "Idempotency-Key: ${emr_idem}" \
  --data-binary "@${emr_body_file}" \
  -o "$emr_resp" \
  -w "%{http_code}")" || {
    RESPONSE_BODY="$emr_resp"
    fail "请求失败：POST /api/webhooks/emr/dry-run duplicate"
  }
RESPONSE_BODY="$emr_resp"
expect_status 202 "emr webhook dry-run duplicate"
json_assert_text_contains "$RESPONSE_BODY" "status" "duplicate" >/dev/null || fail "emr webhook dry-run：重复幂等键未返回 duplicate"
json_assert_text_contains "$RESPONSE_BODY" "receipt_persisted" "True" >/dev/null || fail "emr webhook dry-run：duplicate receipt 未持久化"

RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
  -X POST "${BASE_URL}/api/webhooks/emr/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${emr_ts}" \
  -H "X-PMAI-Signature: sha256=bad" \
  -H "Idempotency-Key: smoke-emr-bad-${run_id}" \
  --data-binary "@${emr_body_file}" \
  -o "$emr_resp" \
  -w "%{http_code}")" || {
    RESPONSE_BODY="$emr_resp"
    fail "请求失败：POST /api/webhooks/emr/dry-run bad signature"
  }
RESPONSE_BODY="$emr_resp"
expect_status 401 "emr webhook dry-run rejects bad signature"
pass "emr webhook dry-run checks"

# EMR -> Case mapping dry-run V1: richer CaseCreate preview, still no Case writes.
emr_map_idem="smoke-emr-map-${run_id}"
map_resp="$TMP_DIR/emr_case_mapping_resp.json"
RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
  -X POST "${BASE_URL}/api/webhooks/emr/case-mapping/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${emr_ts}" \
  -H "X-PMAI-Signature: ${emr_sig}" \
  -H "Idempotency-Key: ${emr_map_idem}" \
  --data-binary "@${emr_body_file}" \
  -o "$map_resp" \
  -w "%{http_code}")" || {
    RESPONSE_BODY="$map_resp"
    fail "请求失败：POST /api/webhooks/emr/case-mapping/dry-run"
  }
RESPONSE_BODY="$map_resp"
expect_status 202 "emr to case mapping dry-run accepted"
emr_map_receipt_id="$(json_get "$RESPONSE_BODY" "receipt_id")"
[[ -n "$emr_map_receipt_id" ]] || fail "emr to case mapping dry-run：没有 receipt_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_case_mapping_dry_run" >/dev/null || fail "emr to case mapping dry-run：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "mode" "case_mapping_dry_run" >/dev/null || fail "emr to case mapping dry-run：mode 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_webhook_inbox" "True" >/dev/null || fail "emr to case mapping dry-run：应写入 webhook_inbox receipt"
json_assert_text_contains "$RESPONSE_BODY" "writes_case_database" "False" >/dev/null || fail "emr to case mapping dry-run：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "emr to case mapping dry-run：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "mapping.case_create.patient_name" "咪咪" >/dev/null || fail "emr to case mapping dry-run：patient_name 映射错误"
json_assert_text_contains "$RESPONSE_BODY" "mapping.case_create.species" "cat" >/dev/null || fail "emr to case mapping dry-run：species 映射错误"
json_assert_text_contains "$RESPONSE_BODY" "mapping.case_create.chief_complaint" "呕吐" >/dev/null || fail "emr to case mapping dry-run：主诉映射错误"
json_assert_text_contains "$RESPONSE_BODY" "import_plan.can_promote_to_real_import" "False" >/dev/null || fail "emr to case mapping dry-run：不应允许直接提升为真实入库"

RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
  -X POST "${BASE_URL}/api/webhooks/emr/case-mapping/dry-run" \
  -H "Content-Type: application/json" \
  -H "X-PMAI-Timestamp: ${emr_ts}" \
  -H "X-PMAI-Signature: ${emr_sig}" \
  -H "Idempotency-Key: ${emr_map_idem}" \
  --data-binary "@${emr_body_file}" \
  -o "$map_resp" \
  -w "%{http_code}")" || {
    RESPONSE_BODY="$map_resp"
    fail "请求失败：POST /api/webhooks/emr/case-mapping/dry-run duplicate"
  }
RESPONSE_BODY="$map_resp"
expect_status 202 "emr to case mapping dry-run duplicate"
json_assert_text_contains "$RESPONSE_BODY" "status" "duplicate" >/dev/null || fail "emr to case mapping dry-run：重复幂等键未返回 duplicate"
json_assert_text_contains "$RESPONSE_BODY" "receipt_persisted" "True" >/dev/null || fail "emr to case mapping dry-run：duplicate 应保留 receipt_persisted"
pass "emr to case mapping dry-run checks"




# 2. signup/login user A
http_json POST "/auth/signup" "{\"email\":\"${email_a}\",\"password\":\"${PASSWORD}\",\"full_name\":\"Smoke A\"}"
expect_status 200 "signup user A"

http_form "/auth/login" "username=${email_a}&password=${PASSWORD}"
expect_status 200 "login user A"
token_a="$(json_get "$RESPONSE_BODY" "access_token")"
[[ -n "$token_a" ]] || fail "login user A：没有 access_token"


http_json GET "/api/webhooks/emr/inbox?page=1&page_size=5&status=accepted" "" "$token_a"
expect_status 200 "webhook inbox review list"
json_assert_text_contains "$RESPONSE_BODY" "message" "webhook_inbox_receipts" >/dev/null || fail "webhook inbox review list：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "review_only" "True" >/dev/null || fail "webhook inbox review list：应为 review_only"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "webhook inbox review list：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "items" "$emr_receipt_id" >/dev/null || fail "webhook inbox review list：没有找到 EMR receipt"

http_json GET "/api/webhooks/emr/inbox/${emr_receipt_id}" "" "$token_a"
expect_status 200 "webhook inbox review detail"
json_assert_text_contains "$RESPONSE_BODY" "message" "webhook_inbox_receipt" >/dev/null || fail "webhook inbox review detail：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "receipt.receipt_id" "$emr_receipt_id" >/dev/null || fail "webhook inbox review detail：receipt_id 不正确"
json_assert_text_contains "$RESPONSE_BODY" "receipt.payload_omitted" "True" >/dev/null || fail "webhook inbox review detail：payload 默认应省略"
json_assert_text_contains "$RESPONSE_BODY" "receipt.mapped_case_preview.patient_name" "咪咪" >/dev/null || fail "webhook inbox review detail：patient_name 映射错误"

http_json GET "/api/webhooks/emr/inbox/${emr_receipt_id}?include_payload=true" "" "$token_a"
expect_status 200 "webhook inbox review detail with payload"
json_assert_text_contains "$RESPONSE_BODY" "receipt.payload_omitted" "False" >/dev/null || fail "webhook inbox review detail：include_payload 未生效"
json_assert_text_contains "$RESPONSE_BODY" "receipt.payload.case_id" "CASE-SMOKE" >/dev/null || fail "webhook inbox review detail：payload.case_id 未返回"

http_json GET "/api/webhooks/emr/inbox?page=1&page_size=5"
expect_status 401 "webhook inbox review requires auth"

http_json GET "/api/webhooks/emr/inbox/rcpt_missing_${run_id}" "" "$token_a"
expect_status 404 "webhook inbox review missing receipt"
pass "webhook inbox review API checks"


audit_log_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "request_id": f"smoke-audit-{run_id}",
    "patient_token": f"tok-smoke-{run_id}",
    "clinician_id": "SMOKE-CLINICIAN",
    "model_version": "pet-med-ai@smoke",
    "confidence": 0.82,
    "suggested_action": "建议：根据问诊风险提示完善检查计划。",
    "action_taken": "accepted",
    "override_reason": "与临床体征一致",
    "note": "Smoke test append-only audit log entry.",
    "event_type": "ai_review",
    "source": "smoke",
    "metadata": {"test": "audit-log-api-v1"},
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/audit-log" "$audit_log_body" "$token_a"
expect_status 201 "audit log append create"
audit_log_id="$(json_get "$RESPONSE_BODY" "log_id")"
[[ -n "$audit_log_id" ]] || fail "audit log append create：没有 log_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "created" >/dev/null || fail "audit log append create：message 未返回 created"
json_assert_text_contains "$RESPONSE_BODY" "append_only" "True" >/dev/null || fail "audit log append create：append_only 未返回 true"
json_assert_text_contains "$RESPONSE_BODY" "can_update" "False" >/dev/null || fail "audit log append create：can_update 应为 false"
json_assert_text_contains "$RESPONSE_BODY" "can_delete" "False" >/dev/null || fail "audit log append create：can_delete 应为 false"

audit_log_bad_confidence="$(python3 <<'PY'
import json
print(json.dumps({
    "request_id": "smoke-audit-bad-confidence",
    "clinician_id": "SMOKE-CLINICIAN",
    "confidence": 1.5,
    "suggested_action": "bad",
    "action_taken": "accepted",
}, ensure_ascii=False))
PY
)"
http_json POST "/api/audit-log" "$audit_log_bad_confidence" "$token_a"
expect_status 422 "audit log rejects invalid confidence"

http_json POST "/api/audit-log" "$audit_log_body"
expect_status 401 "audit log requires auth"

http_json PUT "/api/audit-log" "$audit_log_body" "$token_a"
expect_status 405 "audit log has no update route"

http_json DELETE "/api/audit-log" "" "$token_a"
expect_status 405 "audit log has no delete route"
pass "audit log append-only API checks"

webhook_review_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "action": "ready_for_import",
    "clinician_id": "SMOKE-CLINICIAN",
    "reason": "映射字段完整，已人工复核",
    "note": "Smoke review action only marks the webhook receipt; it does not create a Case.",
    "request_id": f"smoke-webhook-review-{run_id}",
    "metadata": {"test": "webhook-inbox-review-action-v1"},
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/webhooks/emr/inbox/${emr_receipt_id}/review-action" "$webhook_review_body" "$token_a"
expect_status 200 "webhook inbox review action"
webhook_review_audit_id="$(json_get "$RESPONSE_BODY" "audit_log_id")"
[[ -n "$webhook_review_audit_id" ]] || fail "webhook inbox review action：没有 audit_log_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "webhook_inbox_review_action" >/dev/null || fail "webhook inbox review action：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "status_after" "ready_for_import" >/dev/null || fail "webhook inbox review action：status_after 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_webhook_inbox" "True" >/dev/null || fail "webhook inbox review action：应写 webhook_inbox"
json_assert_text_contains "$RESPONSE_BODY" "writes_audit_log" "True" >/dev/null || fail "webhook inbox review action：应写 audit_log"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "webhook inbox review action：不应创建病例"

http_json GET "/api/webhooks/emr/inbox/${emr_receipt_id}" "" "$token_a"
expect_status 200 "webhook inbox detail after review action"
json_assert_text_contains "$RESPONSE_BODY" "receipt.status" "ready_for_import" >/dev/null || fail "webhook inbox detail：status 未更新为 ready_for_import"
pass "webhook inbox review action checks"


emr_batch_plan_body="$(python3 - "$run_id" "$emr_receipt_id" <<'PY'
import json
import sys
run_id, receipt_id = sys.argv[1], sys.argv[2]
body = {
    "batch_id": f"emr_batch_smoke_{run_id}",
    "source_system": "emr",
    "receipt_ids": [receipt_id],
    "freeze": True,
    "created_by": "SMOKE-CLINICIAN",
    "clinical_signoff_id": f"signoff-smoke-{run_id}",
    "rollback_snapshot_id": f"snapshot-smoke-{run_id}",
    "note": "Smoke planned batch only; no real import execution.",
    "metadata": {"test": "emr-import-batch-planning-api-v1"},
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/emr/import-batches/plan" "$emr_batch_plan_body" "$token_a"
expect_status 201 "emr import batch planning"
emr_batch_id="$(json_get "$RESPONSE_BODY" "batch.batch_id")"
[[ -n "$emr_batch_id" ]] || fail "emr import batch planning：没有 batch_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_import_batch_planned" >/dev/null || fail "emr import batch planning：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_case_database" "False" >/dev/null || fail "emr import batch planning：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "emr import batch planning：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "can_execute_import" "False" >/dev/null || fail "emr import batch planning：不应允许执行真实导入"

emr_execution_dry_run_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "operator_id": "SMOKE-CLINICIAN",
    "clinical_signoff_id": f"signoff-smoke-{run_id}",
    "rollback_snapshot_id": f"snapshot-smoke-{run_id}",
    "include_payload_preview": False,
    "max_items": 20,
    "note": "Smoke execution dry-run only; no Case writes.",
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/emr/import-batches/${emr_batch_id}/execution-dry-run" "$emr_execution_dry_run_body" "$token_a"
expect_status 200 "emr real import execution dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_import_execution_dry_run" >/dev/null || fail "emr execution dry-run：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "mode" "execution_dry_run" >/dev/null || fail "emr execution dry-run：mode 不正确"
json_assert_text_contains "$RESPONSE_BODY" "safety.writes_database" "False" >/dev/null || fail "emr execution dry-run：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "safety.writes_case_database" "False" >/dev/null || fail "emr execution dry-run：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "safety.creates_case" "False" >/dev/null || fail "emr execution dry-run：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "safety.executes_real_import" "False" >/dev/null || fail "emr execution dry-run：不应执行真实导入"
json_assert_text_contains "$RESPONSE_BODY" "import_diff.summary.receipt_count" "1" >/dev/null || fail "emr execution dry-run：receipt_count 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "import_diff.summary.would_create_count" "1" >/dev/null || fail "emr execution dry-run：would_create_count 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "rollback_plan.snapshot_required" "True" >/dev/null || fail "emr execution dry-run：必须要求回滚快照"
json_assert_text_contains "$RESPONSE_BODY" "can_execute_import" "False" >/dev/null || fail "emr execution dry-run：不应允许直接执行真实导入"
pass "emr real import execution dry-run checks"


emr_clinical_approval_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "operator_id": "SMOKE-CLINICIAN",
    "clinical_signoff_id": f"signoff-smoke-{run_id}",
    "rollback_snapshot_id": f"snapshot-smoke-{run_id}",
    "approval_action": "approve",
    "note": "Smoke clinical approval only; this does not execute real import or create Case records.",
    "request_id": f"smoke-emr-clinical-approval-{run_id}",
    "metadata": {"test": "emr-import-clinical-approval-api-v1"},
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/emr/import-batches/${emr_batch_id}/clinical-approval" "$emr_clinical_approval_body" "$token_a"
expect_status 200 "emr real import clinical approval"
emr_clinical_approval_audit_id="$(json_get "$RESPONSE_BODY" "audit_log_id")"
[[ -n "$emr_clinical_approval_audit_id" ]] || fail "emr clinical approval：没有 audit_log_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_import_clinical_approval" >/dev/null || fail "emr clinical approval：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "status_after" "approved" >/dev/null || fail "emr clinical approval：status_after 应为 approved"
json_assert_text_contains "$RESPONSE_BODY" "quality_gate.passed" "True" >/dev/null || fail "emr clinical approval：quality_gate 应通过"
json_assert_text_contains "$RESPONSE_BODY" "writes_emr_import_batches" "True" >/dev/null || fail "emr clinical approval：应写 emr_import_batches"
json_assert_text_contains "$RESPONSE_BODY" "writes_audit_log" "True" >/dev/null || fail "emr clinical approval：应写 audit_log"
json_assert_text_contains "$RESPONSE_BODY" "writes_case_database" "False" >/dev/null || fail "emr clinical approval：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "emr clinical approval：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_import" "False" >/dev/null || fail "emr clinical approval：不应执行真实导入"
json_assert_text_contains "$RESPONSE_BODY" "can_execute_import" "False" >/dev/null || fail "emr clinical approval：仍不应允许直接执行真实导入"

http_json GET "/api/emr/import-batches/${emr_batch_id}" "" "$token_a"
expect_status 200 "emr import batch detail after clinical approval"
json_assert_text_contains "$RESPONSE_BODY" "batch.status" "approved" >/dev/null || fail "emr batch detail：status 未更新为 approved"
pass "emr real import clinical approval checks"


emr_execute_skeleton_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "operator_id": "SMOKE-CLINICIAN",
    "clinical_signoff_id": f"signoff-smoke-{run_id}",
    "rollback_snapshot_id": f"snapshot-smoke-{run_id}",
    "dry_run_ack": True,
    "execution_confirmation": "I_UNDERSTAND_THIS_ENDPOINT_IS_DISABLED",
    "request_id": f"smoke-emr-execute-skeleton-{run_id}",
    "note": "Smoke execute skeleton must remain blocked and must not write Case records.",
    "metadata": {"test": "emr-real-import-execute-skeleton-v1"},
    "max_items": 20,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/emr/import-batches/${emr_batch_id}/execute" "$emr_execute_skeleton_body" "$token_a"
expect_status 409 "emr real import execute skeleton blocked"
json_assert_text_contains "$RESPONSE_BODY" "message" "emr_real_import_execute_blocked" >/dev/null || fail "emr execute skeleton：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "mode" "execute_api_skeleton" >/dev/null || fail "emr execute skeleton：mode 不正确"
json_assert_text_contains "$RESPONSE_BODY" "blocked_by_design" "True" >/dev/null || fail "emr execute skeleton：必须 blocked_by_design"
json_assert_text_contains "$RESPONSE_BODY" "execution_enabled" "False" >/dev/null || fail "emr execute skeleton：execution_enabled 应为 false"
json_assert_text_contains "$RESPONSE_BODY" "writes_case_database" "False" >/dev/null || fail "emr execute skeleton：不应写病例库"
json_assert_text_contains "$RESPONSE_BODY" "writes_audit_log" "False" >/dev/null || fail "emr execute skeleton：不应写 audit_log"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "emr execute skeleton：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "updates_case" "False" >/dev/null || fail "emr execute skeleton：不应更新病例"
json_assert_text_contains "$RESPONSE_BODY" "downloads_attachments" "False" >/dev/null || fail "emr execute skeleton：不应下载附件"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_import" "False" >/dev/null || fail "emr execute skeleton：不应执行真实导入"
json_assert_text_contains "$RESPONSE_BODY" "can_execute_import" "False" >/dev/null || fail "emr execute skeleton：不应允许执行真实导入"
pass "emr real import execute skeleton checks"


legacy_mock_body="$(python3 - "$TMP_DIR/legacy_case_payloads.jsonl" <<'PY'
import json
import sys
jsonl_path = sys.argv[1]
with open(jsonl_path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]
body = {
    "batch_id": "smoke-legacy-api-mock",
    "records": records,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/migrations/legacy-cases/mock" "$legacy_mock_body" "$token_a"
expect_status 200 "legacy case API mock"
json_assert_text_contains "$RESPONSE_BODY" "message" "mocked" >/dev/null || fail "legacy case API mock：message 未返回 mocked"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "legacy case API mock：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "calls_case_create_api" "False" >/dev/null || fail "legacy case API mock：不应调用 case_create API"
json_assert_text_contains "$RESPONSE_BODY" "accepted" "1" >/dev/null || fail "legacy case API mock：accepted 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "rejected" "0" >/dev/null || fail "legacy case API mock：rejected 应为 0"
json_assert_text_contains "$RESPONSE_BODY" "items.0.case_create_preview.patient_name" "咪咪" >/dev/null || fail "legacy case API mock：patient_name 预览不正确"
pass "legacy case API mock"

# Legacy case API dry-run V2: richer batch report, still no DB writes.
legacy_dry_run_body="$(python3 - "$TMP_DIR/legacy_case_payloads.jsonl" <<'PY'
import json
import sys
jsonl_path = sys.argv[1]
with open(jsonl_path, "r", encoding="utf-8") as f:
    records = [json.loads(line) for line in f if line.strip()]
body = {
    "batch_id": "smoke-legacy-api-dry-run-v2",
    "records": records,
    "options": {
        "chunk_size": 1000,
        "sample_limit": 2,
        "include_items": True,
    },
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/migrations/legacy-cases/dry-run" "$legacy_dry_run_body" "$token_a"
expect_status 200 "legacy case API dry-run V2"
json_assert_text_contains "$RESPONSE_BODY" "message" "dry_run_report" >/dev/null || fail "legacy API dry-run V2：message 未返回 dry_run_report"
json_assert_text_contains "$RESPONSE_BODY" "mode" "api_dry_run" >/dev/null || fail "legacy API dry-run V2：mode 未返回 api_dry_run"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "legacy API dry-run V2：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "calls_case_create_api" "False" >/dev/null || fail "legacy API dry-run V2：不应调用 case_create API"
json_assert_text_contains "$RESPONSE_BODY" "accepted" "1" >/dev/null || fail "legacy API dry-run V2：accepted 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "rejected" "0" >/dev/null || fail "legacy API dry-run V2：rejected 应为 0"
json_assert_text_contains "$RESPONSE_BODY" "ready_for_import" "True" >/dev/null || fail "legacy API dry-run V2：ready_for_import 应为 true"
json_assert_text_contains "$RESPONSE_BODY" "summary.species_counts.cat" "1" >/dev/null || fail "legacy API dry-run V2：species_counts.cat 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "quality.field_coverage.patient_name.ratio" "1.0" >/dev/null || fail "legacy API dry-run V2：patient_name 覆盖率异常"
json_assert_text_contains "$RESPONSE_BODY" "import_plan.chunks" "1" >/dev/null || fail "legacy API dry-run V2：chunks 应为 1"
json_assert_text_contains "$RESPONSE_BODY" "sample_payloads.0.case_create.patient_name" "咪咪" >/dev/null || fail "legacy API dry-run V2：sample payload patient_name 不正确"
pass "legacy case API dry-run V2"

python3 scripts/run_legacy_pilot_batch.py docs/migrations/LEGACY_CASES_IMPORT_TEMPLATE.csv \
  --work-dir "$TMP_DIR/legacy_pilot" \
  --base-url "$BASE_URL" \
  --token "$token_a" \
  --batch-id "smoke-legacy-pilot-v1" \
  --sample-size 1 \
  --include-items >/dev/null || fail "legacy pilot batch V1 failed"
python3 - "$TMP_DIR/legacy_pilot/pilot_report.json" "$TMP_DIR/legacy_pilot/pilot_review_checklist.csv" <<'PY' || fail "legacy pilot batch V1 output invalid"
import csv
import json
import sys
report_path, checklist_path = sys.argv[1], sys.argv[2]
with open(report_path, "r", encoding="utf-8") as f:
    report = json.load(f)
assert report.get("status") == "PASS"
assert report.get("mode") == "legacy_pilot_batch_v1"
assert report.get("writes_database") is False
assert report.get("calls_case_create_api") is False
assert report.get("api_dry_run_called") is True
assert report.get("payload_rows") == 1
assert report.get("review_rows") == 1
assert report.get("quality_gate", {}).get("passed") is True
with open(checklist_path, "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 1
assert rows[0].get("pet_name") == "咪咪"
assert rows[0].get("species") == "cat"
assert rows[0].get("api_status") == "accepted"
print("ok")
PY
pass "legacy pilot batch V1"




# 3. create owned consult session
consult_text="小狗频繁呕吐，精神差，腹部胀"
http_json POST "/api/ai/consult/session" "{\"text\":\"${consult_text}\"}" "$token_a"
expect_status 200 "create owned consult session"
session_id="$(json_get "$RESPONSE_BODY" "session_id")"
[[ -n "$session_id" ]] || fail "create consult：没有 session_id"

# 4. answer consult
answer_1="突然出现，已经持续4小时，期间有干呕，肚子越来越胀"
question_1="目前是否有腹胀、干呕或精神沉郁？"
http_json POST "/api/ai/consult/session/${session_id}/answer" "{\"question\":\"${question_1}\",\"answer\":\"${answer_1}\"}" "$token_a"
expect_status 200 "answer consult"
answered_count="$(json_get "$RESPONSE_BODY" "result.dynamic.answered_count")"
[[ "$answered_count" == "1" ]] || fail "answer consult：answered_count 应为 1，实际 $answered_count"

# 5. save consult as case
http_json POST "/api/ai/consult/session/${session_id}/save-case" '{"patient_name":"Smoke乐乐","species":"dog","sex":"M","age_info":"4y","breed":"贵宾","weight":"5.2kg","coat_color":"白色","owner_name":"张三","owner_phone":"13800000000"}' "$token_a"
expect_status 200 "save consult as case"
case_id="$(json_get "$RESPONSE_BODY" "case_id")"
message="$(json_get "$RESPONSE_BODY" "message")"
[[ -n "$case_id" ]] || fail "save consult as case：没有 case_id"
[[ "$message" == "saved" || "$message" == "already_saved" ]] || fail "save consult as case：message 异常：$message"

# 6. history contains case_id
http_json GET "/api/ai/consult/sessions?page=1&page_size=20" "" "$token_a"
expect_status 200 "history list user A"
history_total="$(json_get "$RESPONSE_BODY" "total")"
[[ "${history_total:-0}" -ge 1 ]] || fail "history list user A：total 应大于等于 1，实际 ${history_total:-}"
json_assert_session_case "$RESPONSE_BODY" "$session_id" "$case_id" >/dev/null || fail "history list user A：没有找到带 case_id 的 session"
pass "history contains case_id"

http_json GET "/api/ai/consult/sessions?page=1&page_size=20&saved=saved" "" "$token_a"
expect_status 200 "history saved filter user A"
json_assert_session_case "$RESPONSE_BODY" "$session_id" "$case_id" >/dev/null || fail "history saved filter：没有找到已保存 session"
pass "history saved filter contains case_id"

# 7. repeat save returns already_saved
http_json POST "/api/ai/consult/session/${session_id}/save-case" '{"patient_name":"Smoke乐乐","species":"dog","sex":"M","age_info":"4y","breed":"贵宾","weight":"5.2kg","coat_color":"白色","owner_name":"张三","owner_phone":"13800000000"}' "$token_a"
expect_status 200 "repeat save consult"
repeat_msg="$(json_get "$RESPONSE_BODY" "message")"
repeat_case_id="$(json_get "$RESPONSE_BODY" "case_id")"
[[ "$repeat_msg" == "already_saved" ]] || fail "repeat save：期望 already_saved，实际 $repeat_msg"
[[ "$repeat_case_id" == "$case_id" ]] || fail "repeat save：case_id 不一致"
pass "repeat save returns already_saved"

# KPI aggregation API V1 checks. Read-only; does not write KPI records.
http_json GET "/api/kpi/cases" "" "$token_a"
expect_status 200 "kpi cases"
json_assert_text_contains "$RESPONSE_BODY" "message" "kpi_cases" >/dev/null || fail "kpi cases：message 异常"
json_assert_text_contains "$RESPONSE_BODY" "metrics.case_completeness.total_cases" "1" >/dev/null || fail "kpi cases：total_cases 应包含当前 smoke 病例"

http_json GET "/api/kpi/imaging" "" "$token_a"
expect_status 200 "kpi imaging"
json_assert_text_contains "$RESPONSE_BODY" "message" "kpi_imaging" >/dev/null || fail "kpi imaging：message 异常"
json_assert_text_contains "$RESPONSE_BODY" "metrics.repeat_imaging.rate" "0.0" >/dev/null || fail "kpi imaging：空影像复拍率应为 0"

http_json GET "/api/kpi/followups" "" "$token_a"
expect_status 200 "kpi followups"
json_assert_text_contains "$RESPONSE_BODY" "message" "kpi_followups" >/dev/null || fail "kpi followups：message 异常"
json_assert_text_contains "$RESPONSE_BODY" "metrics.followup_compliance.due_total" "0" >/dev/null || fail "kpi followups：空随访 due_total 应为 0"

http_json GET "/api/kpi/qa" "" "$token_a"
expect_status 200 "kpi qa"
json_assert_text_contains "$RESPONSE_BODY" "message" "kpi_qa" >/dev/null || fail "kpi qa：message 异常"
json_assert_text_contains "$RESPONSE_BODY" "metrics.qa_audit_coverage.total_cases" "1" >/dev/null || fail "kpi qa：total_cases 应包含当前 smoke 病例"

http_json GET "/api/kpi/dashboard" "" "$token_a"
expect_status 200 "kpi dashboard"
json_assert_text_contains "$RESPONSE_BODY" "message" "kpi_dashboard" >/dev/null || fail "kpi dashboard：message 异常"
json_assert_text_contains "$RESPONSE_BODY" "cards.case_completeness.label" "病例字段完整度率" >/dev/null || fail "kpi dashboard：缺少病例完整度卡片"
json_assert_text_contains "$RESPONSE_BODY" "sections.cases.message" "kpi_cases" >/dev/null || fail "kpi dashboard：缺少 cases section"
pass "kpi aggregation API checks"


# 8. unsaved consult can be deleted, saved consult cannot be deleted
http_json POST "/api/ai/consult/session" '{"text":"Smoke未保存问诊，准备删除"}' "$token_a"
expect_status 200 "create unsaved consult for delete"
unsaved_session_id="$(json_get "$RESPONSE_BODY" "session_id")"
[[ -n "$unsaved_session_id" ]] || fail "create unsaved consult：没有 session_id"

http_json GET "/api/ai/consult/sessions?page=1&page_size=20&saved=unsaved" "" "$token_a"
expect_status 200 "history unsaved filter user A"
json_assert_session_present "$RESPONSE_BODY" "$unsaved_session_id" >/dev/null || fail "history unsaved filter：没有找到未保存 session"
pass "history unsaved filter contains unsaved session"

http_json DELETE "/api/ai/consult/session/${unsaved_session_id}" "" "$token_a"
expect_status 200 "delete unsaved consult"

http_json GET "/api/ai/consult/session/${unsaved_session_id}" "" "$token_a"
expect_status 404 "deleted unsaved consult cannot be read"

http_json DELETE "/api/ai/consult/session/${session_id}" "" "$token_a"
expect_status 400 "saved consult cannot be deleted"

# 9. continue consult and update bound case
answer_2="今天仍有干呕，腹部紧张，精神比昨天更差"
question_2="今天症状是否缓解？腹部触诊和精神状态如何？"
http_json POST "/api/ai/consult/session/${session_id}/answer" "{\"question\":\"${question_2}\",\"answer\":\"${answer_2}\"}" "$token_a"
expect_status 200 "continue consult"

http_json POST "/api/ai/consult/session/${session_id}/update-case" "" "$token_a"
expect_status 200 "update bound case"
update_msg="$(json_get "$RESPONSE_BODY" "message")"
[[ "$update_msg" == "updated" ]] || fail "update bound case：message 应为 updated，实际 $update_msg"

# 10. read case detail and confirm updated history
http_json GET "/api/cases/${case_id}" "" "$token_a"
expect_status 200 "read user A case"
json_assert_text_contains "$RESPONSE_BODY" "history" "$answer_2" >/dev/null || fail "case detail：history 未包含继续追问内容"
json_assert_text_contains "$RESPONSE_BODY" "analysis" "风险" >/dev/null || fail "case detail：analysis 未包含风险信息"
json_assert_text_contains "$RESPONSE_BODY" "breed" "贵宾" >/dev/null || fail "case detail：breed 未保存"
json_assert_text_contains "$RESPONSE_BODY" "weight" "5.2kg" >/dev/null || fail "case detail：weight 未保存"
json_assert_text_contains "$RESPONSE_BODY" "coat_color" "白色" >/dev/null || fail "case detail：coat_color 未保存"
json_assert_text_contains "$RESPONSE_BODY" "owner_name" "张三" >/dev/null || fail "case detail：owner_name 未保存"
json_assert_text_contains "$RESPONSE_BODY" "owner_phone" "13800000000" >/dev/null || fail "case detail：owner_phone 未保存"
pass "case detail contains updated consult and basic info"

# 11. signup/login user B
http_json POST "/auth/signup" "{\"email\":\"${email_b}\",\"password\":\"${PASSWORD}\",\"full_name\":\"Smoke B\"}"
expect_status 200 "signup user B"

http_form "/auth/login" "username=${email_b}&password=${PASSWORD}"
expect_status 200 "login user B"
token_b="$(json_get "$RESPONSE_BODY" "access_token")"
[[ -n "$token_b" ]] || fail "login user B：没有 access_token"

# 12. user B cannot see/read user A session
http_json GET "/api/ai/consult/sessions?page=1&page_size=20&saved=all" "" "$token_b"
expect_status 200 "history list user B"
json_assert_not_contains_session "$RESPONSE_BODY" "$session_id" >/dev/null || fail "user B history：看到了 user A session"
pass "user B cannot see user A session"

http_json GET "/api/ai/consult/session/${session_id}" "" "$token_b"
expect_status 404 "user B cannot read user A session"

# 13. user B cannot read/update/delete/reanalyze user A case
http_json GET "/api/cases/${case_id}" "" "$token_b"
expect_status 404 "user B cannot read user A case"

http_json PUT "/api/cases/${case_id}" '{"patient_name":"非法修改"}' "$token_b"
expect_status 404 "user B cannot update user A case"

http_json POST "/api/cases/${case_id}/analyze" '{"chief_complaint":"非法重分析"}' "$token_b"
expect_status 404 "user B cannot reanalyze user A case"

http_json DELETE "/api/cases/${case_id}" "" "$token_b"
expect_status 404 "user B cannot delete user A case"


# 14. exotic knowledge base V1 smoke checks
exotic_cases=(
  'rabbit|兔子24小时不吃东西，粪便明显减少，精神差，腹胀|高|兔|消化'
  'bird|鹦鹉张口呼吸，尾巴上下摆，蓬毛闭眼|高|鸟|呼吸'
  'lizard|鬃狮蜥拒食一周，UVB灯坏了，腿软，活动少|中|蜥蜴|饲养环境'
  'ferret|雪貂突然虚弱，流口水，后肢无力，发呆|高|雪貂|低血糖'
  'guinea_pig|豚鼠不吃东西，流口水，粪便减少，精神差|高|豚鼠|牙科'
)

for row in "${exotic_cases[@]}"; do
  IFS='|' read -r species_value text_value expected_risk expected_label expected_path <<< "$row"
  http_json POST "/api/ai/consult/session" "{\"species\":\"${species_value}\",\"text\":\"${text_value}\"}" "$token_a"
  expect_status 200 "exotic consult ${species_value}"
  json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "$expected_risk" >/dev/null || fail "exotic consult ${species_value}：risk_level 未命中 $expected_risk"
  json_assert_text_contains "$RESPONSE_BODY" "result.tree_path" "$expected_label" >/dev/null || fail "exotic consult ${species_value}：tree_path 未包含 $expected_label"
  json_assert_text_contains "$RESPONSE_BODY" "result.tree_path" "$expected_path" >/dev/null || fail "exotic consult ${species_value}：tree_path 未包含 $expected_path"
done
pass "exotic knowledge base consult checks"

# 15. exotic structured intake template checks
http_json POST "/api/ai/consult/session" '{"species":"rabbit","text":"兔子24小时不吃东西，粪便明显减少，精神差，腹胀"}' "$token_a"
expect_status 200 "structured intake rabbit"
json_assert_text_contains "$RESPONSE_BODY" "result.structured_intake.template_key" "rabbit" >/dev/null || fail "structured intake rabbit：template_key 未命中 rabbit"
json_assert_text_contains "$RESPONSE_BODY" "result.structured_intake.sections.0.title" "基础" >/dev/null || fail "structured intake rabbit：缺少基础信息 section"
json_assert_text_contains "$RESPONSE_BODY" "result.structured_intake.sections.1.title" "采食" >/dev/null || fail "structured intake rabbit：缺少采食/粪便 section"

structured_rabbit_session_id="$(json_get "$RESPONSE_BODY" "session_id")"
structured_rabbit_question="$(json_get "$RESPONSE_BODY" "result.next_questions.questions.0")"
[[ -n "$structured_rabbit_session_id" ]] || fail "structured intake rabbit：没有 session_id"
[[ -n "$structured_rabbit_question" ]] || structured_rabbit_question="请继续补充兔子的采食、粪便和腹部状态。"
structured_rabbit_body="$(python3 - "$structured_rabbit_question" <<'PY'
import json
import sys
question = sys.argv[1]
body = {
    "question": question,
    "answer": "补充：精神差，腹部胀，愿意少量饮水。",
    "structured_intake_answers": {
        "version": "exotic-structured-intake-v1",
        "template_key": "rabbit",
        "label": "兔结构化问诊模板",
        "sections": [
            {
                "key": "food_feces_urine",
                "title": "采食 / 粪便 / 排尿",
                "answers": [
                    {"key": "last_eating_time", "label": "最后一次主动吃草/粮/蔬菜是什么时候？", "answer": "约24小时前", "required": True, "triggered": True},
                    {"key": "feces_change", "label": "粪便是变少、变小、变软，还是完全没有？最后一次排便时间？", "answer": "粪便明显减少且变小，最后一次少量排便约12小时前", "required": True, "triggered": True},
                ],
            },
            {
                "key": "pain_abdomen",
                "title": "腹痛 / 胃肠淤滞红旗",
                "answers": [
                    {"key": "abdomen_pain", "label": "是否腹胀、弓背、磨牙、拒绝活动或触碰腹部疼痛？", "answer": "腹胀，趴着不愿动，触碰腹部躲避", "required": True, "triggered": True},
                ],
            },
        ],
    },
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/ai/consult/session/${structured_rabbit_session_id}/answer" "$structured_rabbit_body" "$token_a"
expect_status 200 "structured intake answer submission"
json_assert_text_contains "$RESPONSE_BODY" "result.dynamic.structured_intake_context" "True" >/dev/null || fail "structured intake answer submission：未标记 structured_intake_context"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "structured intake answer submission：兔急症风险未保持高风险"

http_json POST "/api/ai/consult/session" '{"species":"bird","text":"鹦鹉张口呼吸，尾巴上下摆，蓬毛闭眼"}' "$token_a"
expect_status 200 "structured intake bird"
json_assert_text_contains "$RESPONSE_BODY" "result.structured_intake.template_key" "bird" >/dev/null || fail "structured intake bird：template_key 未命中 bird"
json_assert_text_contains "$RESPONSE_BODY" "result.structured_intake.sections.1.title" "呼吸" >/dev/null || fail "structured intake bird：缺少呼吸 section"
pass "exotic structured intake consult checks"


# 15. dog/cat companion knowledge base V1 checks
http_json POST "/api/ai/consult/session" '{"species":"dog","text":"犬反复干呕吐不出来，腹部胀大，坐立不安，流口水"}' "$token_a"
expect_status 200 "companion dog GDV"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion dog GDV：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "GDV" >/dev/null || fail "companion dog GDV：tree_path 未命中 GDV"

http_json POST "/api/ai/consult/session" '{"species":"dog","text":"狗误食巧克力后呕吐、烦躁、心跳快"}' "$token_a"
expect_status 200 "companion dog toxin"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion dog toxin：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "毒理" >/dev/null || fail "companion dog toxin：tree_path 未命中毒理"

http_json POST "/api/ai/consult/session" '{"species":"dog","text":"狗连续抽搐两次，意识不清，流口水"}' "$token_a"
expect_status 200 "companion dog seizure"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion dog seizure：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "神经" >/dev/null || fail "companion dog seizure：tree_path 未命中神经"

http_json POST "/api/ai/consult/session" '{"species":"cat","text":"公猫频繁蹲猫砂盆，尿不出来，叫唤，精神差"}' "$token_a"
expect_status 200 "companion cat urinary obstruction"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion cat urinary obstruction：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "尿闭" >/dev/null || fail "companion cat urinary obstruction：tree_path 未命中尿闭"

http_json POST "/api/ai/consult/session" '{"species":"cat","text":"猫三天不吃东西，精神差，体重下降"}' "$token_a"
expect_status 200 "companion cat anorexia"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion cat anorexia：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "不吃" >/dev/null || fail "companion cat anorexia：tree_path 未命中不吃"

http_json POST "/api/ai/consult/session" '{"species":"cat","text":"猫张口呼吸，呼吸急促，趴着不动"}' "$token_a"
expect_status 200 "companion cat respiratory"
json_assert_text_contains "$RESPONSE_BODY" "result.risk_level" "高" >/dev/null || fail "companion cat respiratory：risk_level 未判高"
json_assert_text_contains "$RESPONSE_BODY" "result.tree_path.2" "呼吸" >/dev/null || fail "companion cat respiratory：tree_path 未命中呼吸"
pass "companion dog/cat knowledge checks"


# Companion structured intake V3: preview/save payload is written into case history.
http_json POST "/api/ai/consult/session" '{"species":"dog","text":"犬反复干呕吐不出来，腹部胀大，坐立不安，流口水"}' "$token_a"
expect_status 200 "companion intake v3 dog session"
companion_dog_session_id="$(json_get "$RESPONSE_BODY" "session_id")"
companion_dog_question="$(json_get "$RESPONSE_BODY" "result.next_questions.questions.0")"
[[ -n "$companion_dog_session_id" ]] || fail "companion intake v3 dog session：没有 session_id"
[[ -n "$companion_dog_question" ]] || companion_dog_question="请继续补充犬的干呕、腹胀和精神状态。"

companion_dog_answer_body="$(python3 - "$companion_dog_question" <<'PY'
import json
import sys
question = sys.argv[1]
structured = {
    "version": "companion-structured-intake-v2",
    "template_key": "dog",
    "category": "companion",
    "label": "犬结构化问诊模板",
    "sections": [
        {
            "key": "gi_gdv_toxin",
            "title": "消化道 / GDV / 中毒与异物",
            "answers": [
                {"key": "unproductive_retching", "label": "是否反复干呕但吐不出来？", "answer": "反复干呕但吐不出来", "required": True, "triggered": True},
                {"key": "abdomen_distension", "label": "腹部是否胀大、紧张或触碰疼痛？", "answer": "腹部胀大，坐立不安，触碰紧张", "required": True, "triggered": True},
            ],
        },
        {
            "key": "timeline",
            "title": "基础信息 / 发病时间线",
            "answers": [
                {"key": "onset", "label": "症状什么时候开始？", "answer": "约2小时前突然开始", "required": True, "triggered": False},
            ],
        },
    ],
}
body = {
    "question": question,
    "answer": "补充：反复干呕，腹胀明显，精神焦躁。",
    "structured_intake_answers": structured,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/ai/consult/session/${companion_dog_session_id}/answer" "$companion_dog_answer_body" "$token_a"
expect_status 200 "companion intake v3 answer context"
json_assert_text_contains "$RESPONSE_BODY" "result.dynamic.structured_intake_context" "True" >/dev/null || fail "companion intake v3 answer：未标记 structured_intake_context"

companion_dog_save_body="$(python3 <<'PY'
import json
structured = {
    "version": "companion-structured-intake-v2",
    "template_key": "dog",
    "category": "companion",
    "label": "犬结构化问诊模板",
    "sections": [
        {
            "key": "gi_gdv_toxin",
            "title": "消化道 / GDV / 中毒与异物",
            "answers": [
                {"key": "unproductive_retching", "label": "是否反复干呕但吐不出来？", "answer": "反复干呕但吐不出来", "required": True, "triggered": True},
                {"key": "abdomen_distension", "label": "腹部是否胀大、紧张或触碰疼痛？", "answer": "腹部胀大，坐立不安，触碰紧张", "required": True, "triggered": True},
            ],
        },
        {
            "key": "timeline",
            "title": "基础信息 / 发病时间线",
            "answers": [
                {"key": "onset", "label": "症状什么时候开始？", "answer": "约2小时前突然开始", "required": True, "triggered": False},
            ],
        },
    ],
}
body = {
    "patient_name": "Smoke犬猫结构化",
    "species": "dog",
    "sex": "M",
    "age_info": "5y",
    "breed": "大型犬",
    "weight": "32kg",
    "structured_intake_answers": structured,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/ai/consult/session/${companion_dog_session_id}/preview-case" "$companion_dog_save_body" "$token_a"
expect_status 200 "case save preview companion dog"
json_assert_text_contains "$RESPONSE_BODY" "message" "preview" >/dev/null || fail "case save preview：message 未返回 preview"
json_assert_text_contains "$RESPONSE_BODY" "history" "犬猫结构化问诊记录" >/dev/null || fail "case save preview：history 未包含犬猫结构化问诊记录"
json_assert_text_contains "$RESPONSE_BODY" "history" "反复干呕但吐不出来" >/dev/null || fail "case save preview：history 未包含干呕结构化答案"

http_json POST "/api/ai/consult/session/${companion_dog_session_id}/save-case" "$companion_dog_save_body" "$token_a"
expect_status 200 "companion intake v3 save case"
companion_dog_case_id="$(json_get "$RESPONSE_BODY" "case_id")"
[[ -n "$companion_dog_case_id" ]] || fail "companion intake v3 save case：没有 case_id"

http_json GET "/api/cases/${companion_dog_case_id}" "" "$token_a"
expect_status 200 "companion intake v3 read case"
json_assert_text_contains "$RESPONSE_BODY" "history" "犬猫结构化问诊记录" >/dev/null || fail "companion intake v3 case：history 未包含犬猫结构化问诊记录"
json_assert_text_contains "$RESPONSE_BODY" "history" "反复干呕但吐不出来" >/dev/null || fail "companion intake v3 case：history 未包含干呕结构化答案"
json_assert_text_contains "$RESPONSE_BODY" "history" "腹部胀大" >/dev/null || fail "companion intake v3 case：history 未包含腹胀结构化答案"
pass "companion structured intake v3 history export"

echo
echo "ALL PASS"
echo "Created smoke artifacts:"
echo "  user A: $email_a"
echo "  user B: $email_b"
echo "  session_id: $session_id"
echo "  case_id: $case_id"
