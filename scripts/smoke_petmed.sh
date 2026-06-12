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

python3 scripts/validate_system_version_info.py >/dev/null || fail "system version/build info validation failed"
pass "system version/build info validation"

python3 scripts/validate_release_changelog.py >/dev/null || fail "release changelog validation failed"
pass "release changelog validation"

python3 scripts/validate_ci_gate.py >/dev/null || fail "GitHub Actions CI gate validation failed"
pass "GitHub Actions CI gate validation"

python3 scripts/validate_backup_rollback_runbook.py >/dev/null || fail "backup rollback verification validation failed"
pass "backup rollback verification validation"

python3 scripts/validate_emr_import_pilot0_checklist.py >/dev/null || fail "emr real import pilot0 checklist validation failed"
pass "emr real import pilot0 checklist validation"

python3 scripts/validate_emr_import_pilot0_dry_run_rehearsal.py >/dev/null || fail "emr real import pilot0 dry-run rehearsal validation failed"
pass "emr real import pilot0 dry-run rehearsal validation"

python3 scripts/validate_emr_import_pilot0_rehearsal_report.py >/dev/null || fail "emr real import pilot0 rehearsal report validation failed"
pass "emr real import pilot0 rehearsal report validation"

python3 scripts/validate_emr_import_pilot0_readiness_review.py >/dev/null || fail "emr real import pilot0 readiness review validation failed"
pass "emr real import pilot0 readiness review validation"

python3 scripts/validate_security_hardening.py >/dev/null || fail "render github security hardening validation failed"
pass "render github security hardening validation"

python3 scripts/validate_clinical_docs_export_spec.py >/dev/null || fail "clinical docs export spec validation failed"
pass "clinical docs export spec validation"

python3 scripts/validate_clinical_docs_template_assets.py >/dev/null || fail "clinical docs template assets validation failed"
pass "clinical docs template assets validation"

python3 scripts/validate_clinical_docs_export_api.py >/dev/null || fail "clinical docs export API validation failed"
pass "clinical docs export API validation"

python3 scripts/validate_clinical_docs_export_ui.py >/dev/null || fail "clinical docs export UI validation failed"
pass "clinical docs export UI validation"

python3 scripts/validate_clinical_docs_export_smoke.py >/dev/null || fail "clinical docs export smoke coverage validation failed"
pass "clinical docs export smoke coverage validation"

python3 scripts/validate_clinical_docs_export_ui_online_verification.py >/dev/null || fail "clinical docs export UI online verification validation failed"
pass "clinical docs export UI online verification validation"

python3 scripts/validate_clinical_docs_pdf_conversion_design.py >/dev/null || fail "clinical docs PDF conversion design validation failed"
pass "clinical docs PDF conversion design validation"

python3 scripts/validate_preventive_care_reminder_spec.py >/dev/null || fail "preventive care reminder spec validation failed"
pass "preventive care reminder spec validation"

python3 scripts/validate_preventive_care_reminder_model.py >/dev/null || fail "preventive care reminder data model validation failed"
pass "preventive care reminder data model validation"

python3 scripts/validate_preventive_care_rule_engine_dry_run.py >/dev/null || fail "preventive care reminder rule engine dry-run validation failed"
pass "preventive care reminder rule engine dry-run validation"

python3 scripts/validate_preventive_care_reminder_api.py >/dev/null || fail "preventive care reminder API validation failed"
pass "preventive care reminder API validation"

python3 scripts/validate_preventive_care_notification_queue.py >/dev/null || fail "preventive care notification queue validation failed"
pass "preventive care notification queue validation"

python3 scripts/validate_preventive_care_notification_queue_ui.py >/dev/null || fail "preventive care notification queue UI validation failed"
pass "preventive care notification queue UI validation"

python3 scripts/validate_preventive_care_online_verification.py >/dev/null || fail "preventive care reminder online verification validation failed"
pass "preventive care reminder online verification validation"

python3 scripts/validate_preventive_care_release_record.py >/dev/null || fail "preventive care reminder release record validation failed"
pass "preventive care reminder release record validation"

python3 scripts/validate_preventive_care_ops_dashboard.py >/dev/null || fail "preventive care reminder ops dashboard validation failed"
pass "preventive care reminder ops dashboard validation"

python3 scripts/validate_preventive_care_ops_dashboard_online_verification.py >/dev/null || fail "preventive care ops dashboard online verification validation failed"
pass "preventive care ops dashboard online verification validation"

python3 scripts/validate_preventive_care_weekly_ops_runbook.py >/dev/null || fail "preventive care weekly ops runbook validation failed"
pass "preventive care weekly ops runbook validation"

python3 scripts/validate_preventive_care_notification_queue_monthly_review.py >/dev/null || fail "preventive care notification queue monthly review validation failed"
pass "preventive care notification queue monthly review validation"

python3 scripts/validate_automated_reminder_delivery_risk_review.py >/dev/null || fail "automated reminder delivery risk review validation failed"
pass "automated reminder delivery risk review validation"

python3 scripts/validate_automated_reminder_delivery_design.py >/dev/null || fail "automated reminder delivery design validation failed"
pass "automated reminder delivery design validation"

python3 scripts/validate_automated_reminder_delivery_model.py >/dev/null || fail "automated reminder delivery data model validation failed"
pass "automated reminder delivery data model validation"

python3 scripts/validate_automated_reminder_delivery_eligibility_dry_run.py >/dev/null || fail "automated reminder delivery eligibility dry-run validation failed"
pass "automated reminder delivery eligibility dry-run validation"

python3 scripts/validate_automated_reminder_delivery_template_registry.py >/dev/null || fail "automated reminder delivery template registry validation failed"
pass "automated reminder delivery template registry validation"

python3 scripts/validate_automated_reminder_delivery_api_dry_run.py >/dev/null || fail "automated reminder delivery API dry-run validation failed"
pass "automated reminder delivery API dry-run validation"

python3 scripts/validate_automated_reminder_delivery_manual_approval_ui.py >/dev/null || fail "automated reminder delivery manual approval UI validation failed"
pass "automated reminder delivery manual approval UI validation"

python3 scripts/validate_preventive_care_reminder_ui.py >/dev/null || fail "preventive care reminder UI validation failed"
pass "preventive care reminder UI validation"

python3 scripts/validate_emr_import_pilot0_final_go_no_go.py >/dev/null || fail "emr real import pilot0 final go no-go validation failed"
pass "emr real import pilot0 final go no-go validation"

python3 scripts/validate_emr_import_pilot0_execution_window.py >/dev/null || fail "emr real import pilot0 execution window validation failed"
pass "emr real import pilot0 execution window validation"

python3 scripts/validate_feature_flags.py >/dev/null || fail "feature flags safety gate validation failed"
pass "feature flags safety gate validation"

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

python3 scripts/validate_emr_import_execute_create_only.py >/dev/null || fail "emr real import execute create-only validation failed"
pass "emr real import execute create-only validation"

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

python3 scripts/validate_ops_dashboard.py >/dev/null || fail "ops dashboard frontend validation failed"
pass "ops dashboard frontend validation"

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
http_json GET "/api/system/version"
expect_status 200 "system version"
json_assert_text_contains "$RESPONSE_BODY" "message" "system_version" >/dev/null || fail "system version：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "schema_ok" "True" >/dev/null || fail "system version：schema_ok 应为 true"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "system version：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "exposes_database_url" "False" >/dev/null || fail "system version：不应暴露数据库 URL"

http_json GET "/api/system/feature-flags"
expect_status 200 "system feature flags"
json_assert_text_contains "$RESPONSE_BODY" "message" "system_feature_flags" >/dev/null || fail "system feature flags：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "all_dangerous_features_disabled" "True" >/dev/null || fail "system feature flags：危险功能应默认关闭"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "system feature flags：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "exposes_secret_values" "False" >/dev/null || fail "system feature flags：不应暴露 secret"
json_assert_text_contains "$RESPONSE_BODY" "flags.ENABLE_EMR_REAL_IMPORT.enabled" "False" >/dev/null || fail "system feature flags：EMR real import 默认应关闭"
json_assert_text_contains "$RESPONSE_BODY" "flags.ENABLE_EMR_IMPORT_CASE_UPDATE.enabled" "False" >/dev/null || fail "system feature flags：EMR case update 默认应关闭"
json_assert_text_contains "$RESPONSE_BODY" "flags.ENABLE_EMR_ATTACHMENT_DOWNLOAD.enabled" "False" >/dev/null || fail "system feature flags：附件下载默认应关闭"

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


emr_execute_create_only_blocked_body="$(python3 - "$run_id" <<'PY'
import json
import sys
run_id = sys.argv[1]
body = {
    "operator_id": "SMOKE-CLINICIAN",
    "clinical_signoff_id": f"signoff-smoke-{run_id}",
    "rollback_snapshot_id": f"snapshot-smoke-{run_id}",
    "dry_run_ack": True,
    "create_only_ack": True,
    "execution_confirmation": "I_UNDERSTAND_THIS_WILL_CREATE_CASES",
    "request_id": f"smoke-emr-execute-create-only-blocked-{run_id}",
    "note": "Smoke verifies feature flag blocks real Case writes by default.",
    "metadata": {"test": "emr-real-import-execute-create-only-v1"},
    "max_items": 5,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/emr/import-batches/${emr_batch_id}/execute" "$emr_execute_create_only_blocked_body" "$token_a"
expect_status 403 "emr real import execute feature flag blocked"
json_assert_text_contains "$RESPONSE_BODY" "detail.message" "feature flag disabled" >/dev/null || fail "emr execute create-only：应被 feature flag 阻断"
json_assert_text_contains "$RESPONSE_BODY" "detail.feature_flag" "ENABLE_EMR_REAL_IMPORT" >/dev/null || fail "emr execute create-only：应提示 ENABLE_EMR_REAL_IMPORT"
pass "emr real import execute create-only default block checks"



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


# Clinical Docs Export Smoke Coverage V1: authenticated DOCX render checks.
http_json GET "/api/clinical-docs/templates" "" "$token_a"
expect_status 200 "clinical docs templates"
json_assert_text_contains "$RESPONSE_BODY" "message" "clinical_doc_templates" >/dev/null || fail "clinical docs templates：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "templates" "admission_hospitalization_record_bilingual" >/dev/null || fail "clinical docs templates：缺少 admission 模板"
json_assert_text_contains "$RESPONSE_BODY" "templates" "discharge_summary_bilingual" >/dev/null || fail "clinical docs templates：缺少 discharge 模板"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "clinical docs templates：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "clinical docs templates：不应创建病例"

clinical_doc_preview_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "template_id": "admission_hospitalization_record_bilingual",
    "output": "docx",
    "clinician_name": "Smoke Clinician",
    "clinician_id": "HS-SMOKE-DOCS",
    "generator": "Pet-Med-AI smoke clinical docs",
    "include_preview_context": True,
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/clinical-docs/render-preview" "$clinical_doc_preview_body" "$token_a"
expect_status 200 "clinical docs admission render preview"
clinical_doc_hash="$(json_get "$RESPONSE_BODY" "document_hash")"
[[ -n "$clinical_doc_hash" ]] || fail "clinical docs render preview：没有 document_hash"
json_assert_text_contains "$RESPONSE_BODY" "message" "clinical_doc_render_preview" >/dev/null || fail "clinical docs render preview：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "template_id" "admission_hospitalization_record_bilingual" >/dev/null || fail "clinical docs render preview：template_id 不正确"
json_assert_text_contains "$RESPONSE_BODY" "context.pet.name" "Smoke乐乐" >/dev/null || fail "clinical docs render preview：pet.name 未填充 smoke 病例"
json_assert_text_contains "$RESPONSE_BODY" "context.clinician_id" "HS-SMOKE-DOCS" >/dev/null || fail "clinical docs render preview：clinician_id 未填充"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "clinical docs render preview：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "clinical docs render preview：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "updates_case" "False" >/dev/null || fail "clinical docs render preview：不应更新病例"
json_assert_text_contains "$RESPONSE_BODY" "downloads_attachments" "False" >/dev/null || fail "clinical docs render preview：不应下载附件"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_import" "False" >/dev/null || fail "clinical docs render preview：不应执行真实导入"

http_json POST "/api/clinical-docs/render-preview" "$clinical_doc_preview_body"
expect_status 401 "clinical docs render preview requires auth"

validate_docx_smoke_output() {
  local docx_path="$1"
  local expected_text="$2"
  python3 - "$docx_path" "$expected_text" <<'PY'
import io
import sys
import zipfile
from xml.etree import ElementTree as ET

docx_path, expected_text = sys.argv[1], sys.argv[2]

with zipfile.ZipFile(docx_path, "r") as zf:
    names = set(zf.namelist())
    if "word/document.xml" not in names:
        print("word/document.xml missing")
        sys.exit(2)

    chunks = []
    raw_xml = []
    for name in sorted(n for n in names if n.startswith("word/") and n.endswith(".xml")):
        data = zf.read(name)
        raw_xml.append(data.decode("utf-8", errors="ignore"))
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            continue
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                chunks.append(node.text)

text = "".join(chunks)
raw = "\n".join(raw_xml)
if "{{" in raw or "}}" in raw:
    print("unreplaced placeholders remain")
    sys.exit(3)
if expected_text not in text:
    print(f"expected text not found in DOCX: {expected_text!r}")
    print(text[:1000])
    sys.exit(4)

print("ok")
PY
}

clinical_doc_render() {
  local template_id="$1"
  local label="$2"
  local out_docx="$3"
  local out_headers="$4"
  local body

  body="$(python3 - "$case_id" "$template_id" "$label" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
template_id = sys.argv[2]
label = sys.argv[3]
body = {
    "case_id": case_id,
    "template_id": template_id,
    "output": "docx",
    "clinician_name": "Smoke Clinician",
    "clinician_id": "HS-SMOKE-DOCS",
    "generator": "Pet-Med-AI smoke clinical docs",
}
print(json.dumps(body, ensure_ascii=False))
PY
)"

  RESPONSE_STATUS="$(curl -sS --connect-timeout 15 --max-time 120 \
    -X POST "${BASE_URL}/api/clinical-docs/render" \
    -H "Authorization: Bearer ${token_a}" \
    -H "Content-Type: application/json" \
    --data "$body" \
    -D "$out_headers" \
    -o "$out_docx" \
    -w "%{http_code}")" || {
      RESPONSE_BODY="$out_headers"
      fail "请求失败：POST /api/clinical-docs/render ${label}"
    }
  RESPONSE_BODY="$out_headers"
}

admission_docx="$TMP_DIR/clinical_docs_admission.docx"
admission_headers="$TMP_DIR/clinical_docs_admission.headers"
clinical_doc_render "admission_hospitalization_record_bilingual" "admission" "$admission_docx" "$admission_headers"
expect_status 200 "clinical docs admission DOCX render"
grep -qi "content-type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" "$admission_headers" || fail "clinical docs admission DOCX：Content-Type 不正确"
grep -qi "x-pmai-document-hash:" "$admission_headers" || fail "clinical docs admission DOCX：缺少 X-PMAI-Document-Hash"
grep -qi "x-pmai-writes-database: false" "$admission_headers" || fail "clinical docs admission DOCX：X-PMAI-Writes-Database 应为 false"
grep -qi "x-pmai-creates-case: false" "$admission_headers" || fail "clinical docs admission DOCX：X-PMAI-Creates-Case 应为 false"
validate_docx_smoke_output "$admission_docx" "Smoke乐乐" >/dev/null || fail "clinical docs admission DOCX：内容校验失败"

discharge_docx="$TMP_DIR/clinical_docs_discharge.docx"
discharge_headers="$TMP_DIR/clinical_docs_discharge.headers"
clinical_doc_render "discharge_summary_bilingual" "discharge" "$discharge_docx" "$discharge_headers"
expect_status 200 "clinical docs discharge DOCX render"
grep -qi "content-type: application/vnd.openxmlformats-officedocument.wordprocessingml.document" "$discharge_headers" || fail "clinical docs discharge DOCX：Content-Type 不正确"
grep -qi "x-pmai-document-hash:" "$discharge_headers" || fail "clinical docs discharge DOCX：缺少 X-PMAI-Document-Hash"
grep -qi "x-pmai-writes-database: false" "$discharge_headers" || fail "clinical docs discharge DOCX：X-PMAI-Writes-Database 应为 false"
grep -qi "x-pmai-creates-case: false" "$discharge_headers" || fail "clinical docs discharge DOCX：X-PMAI-Creates-Case 应为 false"
validate_docx_smoke_output "$discharge_docx" "Smoke乐乐" >/dev/null || fail "clinical docs discharge DOCX：内容校验失败"

pass "clinical docs export runtime DOCX checks"


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

# Preventive Care Reminder API V1: in-app reminders only, no external messages.
http_json GET "/api/preventive-care/rules" "" "$token_a"
expect_status 200 "preventive care rules"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_rules" >/dev/null || fail "preventive care rules：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "items" "internal_deworming" >/dev/null || fail "preventive care rules：缺少驱虫规则"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care rules：不应外发消息"

preventive_dry_run_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "as_of_date": "2026-06-11",
    "include_active": True,
    "pet": {
        "pet_name": "Smoke乐乐",
        "species": "dog",
        "life_stage": "adult",
        "last_core_vaccine_date": "2025-06-01",
        "last_rabies_vaccine_date": "2025-06-01",
        "last_deworming_date": "2026-02-01",
        "last_external_parasite_prevention_date": "2026-05-20",
        "last_fecal_exam_date": "2025-12-01",
        "last_preventive_exam_date": "2025-06-01"
    }
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/dry-run" "$preventive_dry_run_body" "$token_a"
expect_status 200 "preventive care dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_rule_engine_dry_run" >/dev/null || fail "preventive care dry-run：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "summary.total" "1" >/dev/null || fail "preventive care dry-run：应返回提醒预览"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "preventive care dry-run：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care dry-run：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "preventive care dry-run：不应创建病例"

preventive_create_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "category": "internal_deworming",
    "rule_id": "adult_deworming_quarterly_if_no_broad_control",
    "source_rule_id": "adult_deworming_quarterly_if_no_broad_control",
    "status": "active",
    "due_date": "2026-06-20T00:00:00Z",
    "due_window_start": "2026-06-10T00:00:00Z",
    "due_window_end": "2026-07-04T00:00:00Z",
    "reminder_lead_days": 10,
    "note": "Smoke in-app preventive care reminder only.",
    "metadata": {"test": "preventive-care-reminder-api-v1"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/reminders" "$preventive_create_body" "$token_a"
expect_status 201 "preventive care reminder create"
preventive_reminder_id="$(json_get "$RESPONSE_BODY" "reminder.reminder_id")"
[[ -n "$preventive_reminder_id" ]] || fail "preventive care reminder create：没有 reminder_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_reminder_created" >/dev/null || fail "preventive care reminder create：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "True" >/dev/null || fail "preventive care reminder create：应写提醒表"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "preventive care reminder create：不应创建病例"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care reminder create：不应外发消息"

http_json GET "/api/preventive-care/reminders?page=1&page_size=10&category=internal_deworming" "" "$token_a"
expect_status 200 "preventive care reminder list"
json_assert_text_contains "$RESPONSE_BODY" "items" "$preventive_reminder_id" >/dev/null || fail "preventive care reminder list：没有找到新提醒"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "preventive care reminder list：不应写数据库"

preventive_complete_body="$(python3 <<'PY'
import json
body = {
    "event_type": "internal_deworming",
    "event_date": "2026-06-11T00:00:00Z",
    "product_name": "Smoke Deworming Product",
    "next_due_date": "2026-09-11T00:00:00Z",
    "clinician_id": "HS-SMOKE",
    "note": "Smoke complete reminder only.",
    "metadata": {"test": "preventive-care-complete"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/reminders/${preventive_reminder_id}/complete" "$preventive_complete_body" "$token_a"
expect_status 200 "preventive care reminder complete"
preventive_event_id="$(json_get "$RESPONSE_BODY" "event.event_id")"
[[ -n "$preventive_event_id" ]] || fail "preventive care reminder complete：没有 event_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_reminder_completed" >/dev/null || fail "preventive care reminder complete：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "reminder.status" "completed" >/dev/null || fail "preventive care reminder complete：status 未 completed"
json_assert_text_contains "$RESPONSE_BODY" "writes_preventive_care_events" "True" >/dev/null || fail "preventive care reminder complete：应写 event"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care reminder complete：不应外发消息"

preventive_create_body_2="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "category": "annual_preventive_exam",
    "status": "active",
    "due_date": "2026-07-01T00:00:00Z",
    "note": "Smoke second reminder for action tests."
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/reminders" "$preventive_create_body_2" "$token_a"
expect_status 201 "preventive care reminder create second"
preventive_reminder_id_2="$(json_get "$RESPONSE_BODY" "reminder.reminder_id")"
[[ -n "$preventive_reminder_id_2" ]] || fail "preventive care second reminder：没有 reminder_id"

http_json POST "/api/preventive-care/reminders/${preventive_reminder_id_2}/snooze" '{"due_date":"2026-07-15T00:00:00Z","reason":"前台电话确认延期","note":"Smoke snooze only."}' "$token_a"
expect_status 200 "preventive care reminder snooze"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_reminder_snoozed" >/dev/null || fail "preventive care reminder snooze：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "reminder.status" "snoozed" >/dev/null || fail "preventive care reminder snooze：status 未 snoozed"

http_json POST "/api/preventive-care/reminders/${preventive_reminder_id_2}/dismiss" '{"reason":"重复提醒","note":"Smoke dismiss only."}' "$token_a"
expect_status 200 "preventive care reminder dismiss"
json_assert_text_contains "$RESPONSE_BODY" "reminder.status" "dismissed" >/dev/null || fail "preventive care reminder dismiss：status 未 dismissed"

http_json POST "/api/preventive-care/reminders/${preventive_reminder_id_2}/disable" '{"reason":"客户暂不接收","note":"Smoke disable only."}' "$token_a"
expect_status 200 "preventive care reminder disable"
json_assert_text_contains "$RESPONSE_BODY" "reminder.status" "disabled" >/dev/null || fail "preventive care reminder disable：status 未 disabled"
json_assert_text_contains "$RESPONSE_BODY" "reminder.client_opt_out" "True" >/dev/null || fail "preventive care reminder disable：client_opt_out 未 true"

http_json GET "/api/preventive-care/client-preferences" "" "$token_a"
expect_status 200 "preventive care client preferences read"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care preferences read：不应外发消息"

http_json PUT "/api/preventive-care/client-preferences" '{"allow_in_app":true,"allow_sms":false,"allow_wechat":false,"allow_email":false,"opt_out_all":true,"preferred_channel":"in_app","updated_by":"HS-SMOKE","note":"Smoke opt-out preference."}' "$token_a"
expect_status 200 "preventive care client preferences save"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_client_preferences_saved" >/dev/null || fail "preventive care preferences save：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "preferences.opt_out_all" "True" >/dev/null || fail "preventive care preferences save：opt_out_all 未 true"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care preferences save：不应外发消息"

http_json GET "/api/preventive-care/reminders" "" "$token_b"
expect_status 200 "preventive care user B reminder list"
json_assert_text_contains "$RESPONSE_BODY" "items" "[]" >/dev/null || fail "preventive care user B：不应看到 user A reminders"

http_json POST "/api/preventive-care/reminders/${preventive_reminder_id}/complete" "$preventive_complete_body" "$token_b"
expect_status 404 "preventive care user B cannot complete user A reminder"
pass "preventive care reminder API checks"

# Preventive Care Reminder Notification Queue V1: manual front-desk queue only, no external send.
preventive_queue_reminder_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "category": "external_parasite_prevention",
    "rule_id": "monthly_broad_spectrum_parasite_control",
    "source_rule_id": "monthly_broad_spectrum_parasite_control",
    "status": "active",
    "due_date": "2026-07-11T00:00:00Z",
    "note": "Smoke notification queue reminder."
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/reminders" "$preventive_queue_reminder_body" "$token_a"
expect_status 201 "preventive care queue reminder create"
preventive_queue_reminder_id="$(json_get "$RESPONSE_BODY" "reminder.reminder_id")"
[[ -n "$preventive_queue_reminder_id" ]] || fail "preventive care queue reminder create：没有 reminder_id"

preventive_queue_draft_body="$(python3 - "$preventive_queue_reminder_id" <<'PY'
import json
import sys
reminder_id = sys.argv[1]
body = {
    "reminder_id": reminder_id,
    "channel": "phone_call",
    "scheduled_for": "2026-07-01T09:00:00Z",
    "message_preview": "【预防保健提醒】Smoke乐乐 需要复核体外驱虫计划。请前台人工电话确认。",
    "reviewed_by": "HS-SMOKE",
    "note": "Smoke draft queue item only.",
    "metadata": {"test": "preventive-care-notification-queue-v1"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/notification-queue/draft" "$preventive_queue_draft_body" "$token_a"
expect_status 201 "preventive care notification queue draft"
preventive_notification_id="$(json_get "$RESPONSE_BODY" "notification.notification_id")"
[[ -n "$preventive_notification_id" ]] || fail "preventive care notification queue draft：没有 notification_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_notification_draft_created" >/dev/null || fail "preventive care notification queue draft：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "manual_review_required" "True" >/dev/null || fail "preventive care notification queue draft：必须人工审核"
json_assert_text_contains "$RESPONSE_BODY" "auto_send" "False" >/dev/null || fail "preventive care notification queue draft：不应自动发送"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care notification queue draft：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "preventive care notification queue draft：不应创建病例"

http_json GET "/api/preventive-care/notification-queue?page=1&page_size=10" "" "$token_a"
expect_status 200 "preventive care notification queue list"
json_assert_text_contains "$RESPONSE_BODY" "items" "$preventive_notification_id" >/dev/null || fail "preventive care notification queue list：没有找到 draft"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "preventive care notification queue list：不应写数据库"

http_json POST "/api/preventive-care/notification-queue/${preventive_notification_id}/review" '{"action":"approve_for_manual_contact","reviewed_by":"HS-SMOKE","note":"Smoke manual review only."}' "$token_a"
expect_status 200 "preventive care notification queue review"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_notification_reviewed" >/dev/null || fail "preventive care notification queue review：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "notification.status" "reviewed" >/dev/null || fail "preventive care notification queue review：status 未 reviewed"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care notification queue review：不应外发消息"

http_json POST "/api/preventive-care/notification-queue/${preventive_notification_id}/mark-contacted" '{"contacted_by":"HS-SMOKE","contact_result":"manual_phone_call_completed","note":"Smoke manually contacted marker only."}' "$token_a"
expect_status 200 "preventive care notification queue mark contacted"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_notification_marked_contacted" >/dev/null || fail "preventive care notification queue contacted：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "notification.status" "contacted_manually" >/dev/null || fail "preventive care notification queue contacted：status 未 contacted_manually"
json_assert_text_contains "$RESPONSE_BODY" "manual_contact_only" "True" >/dev/null || fail "preventive care notification queue contacted：应为人工联系"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care notification queue contacted：系统不应外发消息"

http_json POST "/api/preventive-care/notification-queue/draft" "$preventive_queue_draft_body" "$token_a"
expect_status 201 "preventive care notification queue draft for cancel"
preventive_notification_cancel_id="$(json_get "$RESPONSE_BODY" "notification.notification_id")"
[[ -n "$preventive_notification_cancel_id" ]] || fail "preventive care notification queue cancel draft：没有 notification_id"

http_json POST "/api/preventive-care/notification-queue/${preventive_notification_cancel_id}/cancel" '{"canceled_by":"HS-SMOKE","reason":"Smoke cancel queue item","note":"No external message sent."}' "$token_a"
expect_status 200 "preventive care notification queue cancel"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_notification_canceled" >/dev/null || fail "preventive care notification queue cancel：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "notification.status" "canceled" >/dev/null || fail "preventive care notification queue cancel：status 未 canceled"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care notification queue cancel：不应外发消息"

http_json GET "/api/preventive-care/notification-queue" "" "$token_b"
expect_status 200 "preventive care notification queue user B list"
json_assert_text_contains "$RESPONSE_BODY" "items" "[]" >/dev/null || fail "preventive care notification queue user B：不应看到 user A 队列"

http_json POST "/api/preventive-care/notification-queue/${preventive_notification_id}/review" '{"action":"approve_for_manual_contact","reviewed_by":"HS-SMOKE-B"}' "$token_b"
expect_status 404 "preventive care notification queue user B cannot review user A item"
pass "preventive care notification queue checks"

# Preventive Care Reminder Ops Dashboard V1: read-only operational summary.
http_json GET "/api/preventive-care/ops/summary" "" "$token_a"
expect_status 200 "preventive care ops summary"
json_assert_text_contains "$RESPONSE_BODY" "message" "preventive_care_ops_summary" >/dev/null || fail "preventive care ops summary：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "mode" "preventive_care_reminder_ops_dashboard_v1" >/dev/null || fail "preventive care ops summary：mode 不正确"
json_assert_text_contains "$RESPONSE_BODY" "reminders.total" "1" >/dev/null || fail "preventive care ops summary：应包含 reminders.total"
json_assert_text_contains "$RESPONSE_BODY" "notification_queue.total" "1" >/dev/null || fail "preventive care ops summary：应包含 notification_queue.total"
json_assert_text_contains "$RESPONSE_BODY" "safety.read_only" "True" >/dev/null || fail "preventive care ops summary：read_only 应为 true"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "preventive care ops summary：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "auto_send" "False" >/dev/null || fail "preventive care ops summary：不应自动发送"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care ops summary：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "preventive care ops summary：不应创建病例"

http_json GET "/api/preventive-care/ops/summary" "" "$token_b"
expect_status 200 "preventive care ops summary user B"
json_assert_text_contains "$RESPONSE_BODY" "reminders.total" "0" >/dev/null || fail "preventive care ops summary user B：不应看到 user A reminders"
json_assert_text_contains "$RESPONSE_BODY" "notification_queue.total" "0" >/dev/null || fail "preventive care ops summary user B：不应看到 user A queue"
pass "preventive care ops dashboard checks"

# Automated Reminder Delivery Template Registry V1: templates only, no provider calls.
automated_template_body="$(python3 <<'PY'
import json
from uuid import uuid4
template_key = f"smoke_parasite_review_{uuid4().hex[:12]}"
body = {
    "template_key": template_key,
    "template_version": "v1",
    "channel": "sms",
    "language": "zh-CN",
    "category": "external_parasite_prevention",
    "subject": "预防保健提醒 / Preventive Care Reminder",
    "body": "【预防保健提醒】{{pet_name}} 可能已到 {{reminder_type}} 复核时间。请联系 {{clinic_name}} 确认具体方案。",
    "clinical_safety_text": "此提醒不是诊断或处方。接种/驱虫计划和产品必须由兽医确认；狂犬及受监管疫苗需遵守当地法规和产品标签。",
    "opt_out_text": "如不想接收此类提醒，请联系前台登记退订。",
    "metadata": {"test": "automated-reminder-delivery-template-registry-v1"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/automated-reminder-delivery/templates" "$automated_template_body" "$token_a"
expect_status 201 "automated reminder delivery template create"
automated_template_id="$(json_get "$RESPONSE_BODY" "template.id")"
automated_template_key="$(json_get "$RESPONSE_BODY" "template.template_key")"
[[ -n "$automated_template_id" ]] || fail "automated reminder delivery template create：没有 template.id"
[[ -n "$automated_template_key" ]] || fail "automated reminder delivery template create：没有 template_key"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_template_created" >/dev/null || fail "automated reminder delivery template create：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_template_registry" "True" >/dev/null || fail "automated reminder delivery template create：应写 template registry"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery template create：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "automated reminder delivery template create：不应创建病例"

http_json GET "/api/automated-reminder-delivery/templates?channel=sms&page=1&page_size=20" "" "$token_a"
expect_status 200 "automated reminder delivery template list"
json_assert_text_contains "$RESPONSE_BODY" "items" "$automated_template_key" >/dev/null || fail "automated reminder delivery template list：没有找到新模板"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "automated reminder delivery template list：不应写数据库"

automated_template_preview_body="$(python3 <<'PY'
import json
body = {
    "context": {
        "pet_name": "Smoke乐乐",
        "reminder_type": "体外寄生虫预防",
        "clinic_name": "瀚森宠物医院"
    }
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/automated-reminder-delivery/templates/${automated_template_id}/render-preview" "$automated_template_preview_body" "$token_a"
expect_status 200 "automated reminder delivery template render preview"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_template_render_preview" >/dev/null || fail "automated reminder delivery template preview：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "rendered" "Smoke乐乐" >/dev/null || fail "automated reminder delivery template preview：未渲染 pet_name"
json_assert_text_contains "$RESPONSE_BODY" "dry_run" "True" >/dev/null || fail "automated reminder delivery template preview：必须 dry_run"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery template preview：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "automated reminder delivery template preview：不应写数据库"

http_json POST "/api/automated-reminder-delivery/templates/${automated_template_id}/review" '{"review_status":"approved","reviewed_by":"HS-SMOKE","note":"Smoke template registry approval only; live delivery remains disabled."}' "$token_a"
expect_status 200 "automated reminder delivery template review"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_template_reviewed" >/dev/null || fail "automated reminder delivery template review：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "template.review_status" "approved" >/dev/null || fail "automated reminder delivery template review：status 未 approved"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery template review：不应外发消息"

http_json POST "/api/automated-reminder-delivery/templates/${automated_template_id}/retire" '{"review_status":"retired","reviewed_by":"HS-SMOKE","note":"Smoke retire template."}' "$token_a"
expect_status 200 "automated reminder delivery template retire"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_template_retired" >/dev/null || fail "automated reminder delivery template retire：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "template.review_status" "retired" >/dev/null || fail "automated reminder delivery template retire：status 未 retired"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery template retire：不应外发消息"

http_json GET "/api/automated-reminder-delivery/templates"
expect_status 401 "automated reminder delivery templates require auth"
pass "automated reminder delivery template registry checks"

# Automated Reminder Delivery API Dry-run V1: creates dry-run attempts only, no provider calls.
http_json PUT "/api/preventive-care/client-preferences" '{"allow_in_app":true,"allow_sms":true,"allow_wechat":false,"allow_email":false,"opt_out_all":false,"preferred_channel":"sms","updated_by":"HS-SMOKE","note":"Smoke automated delivery dry-run consent.","metadata":{"consent_source":"smoke-test"}}' "$token_a"
expect_status 200 "automated reminder delivery prepare consent"

automated_delivery_template_body="$(python3 <<'PY'
import json
from uuid import uuid4
template_key = f"smoke_auto_delivery_{uuid4().hex[:12]}"
body = {
    "template_key": template_key,
    "template_version": "v1",
    "channel": "sms",
    "language": "zh-CN",
    "category": "external_parasite_prevention",
    "subject": "预防保健提醒 / Preventive Care Reminder",
    "body": "【预防保健提醒】{{pet_name}} 可能已到 {{reminder_type}} 复核时间。请联系 {{clinic_name}} 确认具体方案。",
    "clinical_safety_text": "此提醒不是诊断或处方。接种/驱虫计划和产品必须由兽医确认；狂犬及受监管疫苗需遵守当地法规和产品标签。",
    "opt_out_text": "如不想接收此类提醒，请联系前台登记退订。",
    "metadata": {"test": "automated-reminder-delivery-api-dry-run-v1"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/automated-reminder-delivery/templates" "$automated_delivery_template_body" "$token_a"
expect_status 201 "automated reminder delivery dry-run template create"
automated_delivery_template_id="$(json_get "$RESPONSE_BODY" "template.id")"
[[ -n "$automated_delivery_template_id" ]] || fail "automated reminder delivery dry-run template：没有 template.id"

http_json POST "/api/automated-reminder-delivery/templates/${automated_delivery_template_id}/review" '{"review_status":"approved","reviewed_by":"HS-SMOKE","note":"Smoke dry-run approval only; live delivery disabled."}' "$token_a"
expect_status 200 "automated reminder delivery dry-run template approve"

automated_delivery_reminder_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "category": "external_parasite_prevention",
    "rule_id": "monthly_broad_spectrum_parasite_control",
    "source_rule_id": "monthly_broad_spectrum_parasite_control",
    "status": "active",
    "due_date": "2026-08-11T00:00:00Z",
    "note": "Smoke automated delivery dry-run reminder."
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/reminders" "$automated_delivery_reminder_body" "$token_a"
expect_status 201 "automated reminder delivery dry-run reminder create"
automated_delivery_reminder_id="$(json_get "$RESPONSE_BODY" "reminder.reminder_id")"
[[ -n "$automated_delivery_reminder_id" ]] || fail "automated reminder delivery dry-run reminder：没有 reminder_id"

automated_delivery_queue_body="$(python3 - "$automated_delivery_reminder_id" <<'PY'
import json
import sys
reminder_id = sys.argv[1]
body = {
    "reminder_id": reminder_id,
    "channel": "phone_call",
    "message_preview": "Smoke dry-run queue item.",
    "reviewed_by": "HS-SMOKE",
    "note": "Queue item for automated delivery dry-run only.",
    "metadata": {"test": "automated-delivery-dry-run"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/preventive-care/notification-queue/draft" "$automated_delivery_queue_body" "$token_a"
expect_status 201 "automated reminder delivery dry-run queue draft"
automated_delivery_notification_id="$(json_get "$RESPONSE_BODY" "notification.notification_id")"
[[ -n "$automated_delivery_notification_id" ]] || fail "automated reminder delivery dry-run queue：没有 notification_id"

http_json POST "/api/preventive-care/notification-queue/${automated_delivery_notification_id}/review" '{"action":"approve_for_manual_contact","reviewed_by":"HS-SMOKE","note":"Smoke manual review for automated delivery dry-run."}' "$token_a"
expect_status 200 "automated reminder delivery dry-run queue review"

automated_delivery_dry_run_body="$(python3 - "$automated_delivery_reminder_id" "$automated_delivery_notification_id" "$automated_delivery_template_id" <<'PY'
import json
import sys
reminder_id, notification_id, template_id = sys.argv[1], sys.argv[2], int(sys.argv[3])
body = {
    "reminder_id": reminder_id,
    "notification_id": notification_id,
    "template_id": template_id,
    "channel": "sms",
    "context": {
        "pet_name": "Smoke乐乐",
        "reminder_type": "体外寄生虫预防",
        "clinic_name": "瀚森宠物医院"
    },
    "destination_exists": True,
    "contact_destination_hash": "sha256:smoke-destination",
    "feature_flags": {
        "ENABLE_PREVENTIVE_AUTO_DELIVERY": False,
        "ENABLE_PREVENTIVE_SMS_DELIVERY": False,
        "ENABLE_PREVENTIVE_DELIVERY_DRY_RUN": True,
        "ENABLE_PREVENTIVE_DELIVERY_MANUAL_APPROVAL": True
    },
    "rate_limits": {
        "owner_daily_sent_count": 0,
        "owner_daily_cap": 1,
        "owner_weekly_sent_count": 0,
        "owner_weekly_cap": 3,
        "global_hourly_sent_count": 0,
        "global_hourly_cap": 100,
        "duplicate_within_cooldown": False
    },
    "quiet_hours": {
        "enabled": True,
        "local_hour": 10,
        "send_window_start_hour": 9,
        "send_window_end_hour": 18
    },
    "provider": {
        "name": "sms_dry_run",
        "credentials_available": True
    },
    "save_attempt": True,
    "metadata": {"test": "automated-reminder-delivery-api-dry-run-v1"}
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/automated-reminder-delivery/dry-run" "$automated_delivery_dry_run_body" "$token_a"
expect_status 201 "automated reminder delivery dry-run create"
automated_delivery_id="$(json_get "$RESPONSE_BODY" "attempt.delivery_id")"
[[ -n "$automated_delivery_id" ]] || fail "automated reminder delivery dry-run：没有 delivery_id"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_dry_run_created" >/dev/null || fail "automated reminder delivery dry-run：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "eligibility.first_blocked_reason" "blocked_kill_switch" >/dev/null || fail "automated reminder delivery dry-run：应被 kill switch 阻断"
json_assert_text_contains "$RESPONSE_BODY" "rendered.body" "Smoke乐乐" >/dev/null || fail "automated reminder delivery dry-run：模板未渲染"
json_assert_text_contains "$RESPONSE_BODY" "attempt.dry_run" "True" >/dev/null || fail "automated reminder delivery dry-run：attempt 必须 dry_run"
json_assert_text_contains "$RESPONSE_BODY" "attempt.auto_send" "False" >/dev/null || fail "automated reminder delivery dry-run：attempt 不应 auto_send"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery dry-run：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "automated reminder delivery dry-run：不应创建病例"

http_json GET "/api/automated-reminder-delivery/attempts?page=1&page_size=20" "" "$token_a"
expect_status 200 "automated reminder delivery attempt list"
json_assert_text_contains "$RESPONSE_BODY" "items" "$automated_delivery_id" >/dev/null || fail "automated reminder delivery attempt list：没有找到 dry-run attempt"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "automated reminder delivery attempt list：不应写数据库"

http_json GET "/api/automated-reminder-delivery/attempts/${automated_delivery_id}" "" "$token_a"
expect_status 200 "automated reminder delivery attempt get"
json_assert_text_contains "$RESPONSE_BODY" "attempt.delivery_id" "$automated_delivery_id" >/dev/null || fail "automated reminder delivery attempt get：ID 不正确"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery attempt get：不应外发消息"

http_json POST "/api/automated-reminder-delivery/attempts/${automated_delivery_id}/cancel" '{"canceled_by":"HS-SMOKE","reason":"Smoke cancel dry-run attempt","note":"No provider was called."}' "$token_a"
expect_status 200 "automated reminder delivery attempt cancel"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_attempt_canceled" >/dev/null || fail "automated reminder delivery attempt cancel：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "attempt.status" "canceled" >/dev/null || fail "automated reminder delivery attempt cancel：status 未 canceled"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery attempt cancel：不应外发消息"

http_json GET "/api/automated-reminder-delivery/attempts/${automated_delivery_id}" "" "$token_b"
expect_status 404 "automated reminder delivery user B cannot see user A attempt"

http_json POST "/api/automated-reminder-delivery/dry-run" "$automated_delivery_dry_run_body"
expect_status 401 "automated reminder delivery dry-run requires auth"
pass "automated reminder delivery API dry-run checks"

# Automated Reminder Delivery Manual Approval UI V1: review dry-run attempts only, no live send.
http_json POST "/api/automated-reminder-delivery/dry-run" "$automated_delivery_dry_run_body" "$token_a"
expect_status 201 "automated reminder delivery dry-run create for manual approval"
manual_approval_delivery_id="$(json_get "$RESPONSE_BODY" "attempt.delivery_id")"
[[ -n "$manual_approval_delivery_id" ]] || fail "automated reminder delivery manual approval：没有 delivery_id"

http_json POST "/api/automated-reminder-delivery/attempts/${manual_approval_delivery_id}/manual-review" '{"decision":"approve_dry_run_only","reviewed_by":"HS-SMOKE","note":"Smoke manual approval for dry-run only; no live delivery.","metadata":{"test":"automated-reminder-delivery-manual-approval-ui-v1"}}' "$token_a"
expect_status 200 "automated reminder delivery manual review"
json_assert_text_contains "$RESPONSE_BODY" "message" "automated_reminder_delivery_attempt_manual_reviewed" >/dev/null || fail "automated reminder delivery manual review：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "attempt.status" "manual_reviewed_dry_run" >/dev/null || fail "automated reminder delivery manual review：status 未 manual_reviewed_dry_run"
json_assert_text_contains "$RESPONSE_BODY" "attempt.approved_by" "HS-SMOKE" >/dev/null || fail "automated reminder delivery manual review：approved_by 不正确"
json_assert_text_contains "$RESPONSE_BODY" "attempt.dry_run" "True" >/dev/null || fail "automated reminder delivery manual review：必须 dry_run"
json_assert_text_contains "$RESPONSE_BODY" "attempt.auto_send" "False" >/dev/null || fail "automated reminder delivery manual review：不应 auto_send"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "automated reminder delivery manual review：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "creates_case" "False" >/dev/null || fail "automated reminder delivery manual review：不应创建病例"

http_json POST "/api/automated-reminder-delivery/attempts/${manual_approval_delivery_id}/manual-review" '{"decision":"reject","reviewed_by":"HS-SMOKE-B","note":"User B should not review user A attempt."}' "$token_b"
expect_status 404 "automated reminder delivery user B cannot review user A attempt"
pass "automated reminder delivery manual approval UI checks"







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
