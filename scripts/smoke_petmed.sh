#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
BASE_URL="${BASE_URL%/}"
FRONTEND_URL="${FRONTEND_URL:-}"
FRONTEND_URL="${FRONTEND_URL%/}"
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

python3 scripts/validate_automated_reminder_delivery_pilot_runbook.py >/dev/null || fail "automated reminder delivery pilot runbook validation failed"
pass "automated reminder delivery pilot runbook validation"

python3 scripts/validate_commercial_launch_readiness.py >/dev/null || fail "commercial launch readiness validation failed"
pass "commercial launch readiness validation"

python3 scripts/validate_commercial_launch_feature_scope_lock.py >/dev/null || fail "commercial launch feature scope lock validation failed"
pass "commercial launch feature scope lock validation"

python3 scripts/validate_commercial_launch_ops_runbook.py >/dev/null || fail "commercial launch ops runbook validation failed"
pass "commercial launch ops runbook validation"

python3 scripts/validate_commercial_launch_access_review.py >/dev/null || fail "commercial launch access review validation failed"
pass "commercial launch access review validation"

python3 scripts/validate_commercial_launch_monitoring_alerting_plan.py >/dev/null || fail "commercial launch monitoring alerting plan validation failed"
pass "commercial launch monitoring alerting plan validation"

python3 scripts/validate_commercial_launch_backup_restore_drill_v2.py >/dev/null || fail "commercial launch backup restore drill v2 validation failed"
pass "commercial launch backup restore drill v2 validation"

python3 scripts/validate_commercial_launch_legal_consent_pack.py >/dev/null || fail "commercial launch legal consent pack validation failed"
pass "commercial launch legal consent pack validation"

python3 scripts/validate_commercial_launch_final_go_no_go.py >/dev/null || fail "commercial launch final go no-go validation failed"
pass "commercial launch final go no-go validation"

python3 scripts/validate_commercial_v1_post_go_stabilization.py >/dev/null || fail "commercial v1 post-go stabilization validation failed"
pass "commercial v1 post-go stabilization validation"

python3 scripts/validate_preventive_care_reminder_ui.py >/dev/null || fail "preventive care reminder UI validation failed"
pass "preventive care reminder UI validation"

python3 scripts/validate_case_detail_diagnostic_data_display.py >/dev/null || fail "case detail diagnostic data display validation failed"
pass "case detail diagnostic data display validation"

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
    fail "${label}: expected HTTP ${expected}, actual HTTP ${RESPONSE_STATUS:-unknown}"
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
database_revision="$(json_get "$RESPONSE_BODY" "database_revision")"
alembic_head="$(json_get "$RESPONSE_BODY" "alembic_head")"
if [[ -z "$database_revision" ]]; then
  fail "system version：database_revision 不能为空"
fi
if [[ -z "$alembic_head" || "$database_revision" != "$alembic_head" ]]; then
  fail "system version：database_revision 必须等于 alembic_head，database_revision=${database_revision:-empty}, alembic_head=${alembic_head:-empty}"
fi
pass "system version database revision schema alignment gate"
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

if [[ -n "$FRONTEND_URL" ]]; then
  FRONTEND_STATUS="$(curl -sS --connect-timeout 15 --max-time 60 -o /dev/null -w "%{http_code}" "$FRONTEND_URL")" || fail "frontend live check failed"
  if [[ "$FRONTEND_STATUS" != "200" && "$FRONTEND_STATUS" != "304" ]]; then
    fail "frontend live：期望 HTTP 200/304，实际 HTTP $FRONTEND_STATUS"
  fi
  pass "frontend live"
fi

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
json_assert_text_contains "$RESPONSE_BODY" "writes_webhook_inbox" "True" >/dev/null || fail "emr webhook dry-run：应写入 webhook_inbox receipt"
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

# Diagnostic Data Read-only API / Dry-run Fixtures V1.
http_json GET "/api/diagnostic-data/cases/${case_id}/summary" "" "$token_a"
expect_status 200 "diagnostic data case summary"
json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_data_case_summary" >/dev/null || fail "diagnostic data summary：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "case.case_id" "$case_id" >/dev/null || fail "diagnostic data summary：case_id 不正确"
json_assert_text_contains "$RESPONSE_BODY" "counts.reports" "0" >/dev/null || fail "diagnostic data summary：新 smoke 病例不应已有 diagnostic reports"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic data summary：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "diagnostic data summary：不应外发消息"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_import" "False" >/dev/null || fail "diagnostic data summary：不应执行真实导入"

http_json GET "/api/diagnostic-data/cases/${case_id}/reports?page=1&page_size=10" "" "$token_a"
expect_status 200 "diagnostic data reports read-only"
json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_reports" >/dev/null || fail "diagnostic reports：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "total" "0" >/dev/null || fail "diagnostic reports：新 smoke 病例不应已有报告"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic reports：不应写数据库"

http_json GET "/api/diagnostic-data/cases/${case_id}/observations?page=1&page_size=10" "" "$token_a"
expect_status 200 "diagnostic data observations read-only"
json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_observations" >/dev/null || fail "diagnostic observations：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic observations：不应写数据库"

http_json GET "/api/diagnostic-data/cases/${case_id}/imaging-studies?page=1&page_size=10" "" "$token_a"
expect_status 200 "diagnostic data imaging studies read-only"
json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_imaging_studies" >/dev/null || fail "diagnostic imaging studies：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic imaging studies：不应写数据库"

http_json GET "/api/diagnostic-data/dry-run/fixtures" "" "$token_a"
expect_status 200 "diagnostic data dry-run fixture list"
json_assert_text_contains "$RESPONSE_BODY" "fixture_ids" "diagnostic_data_dry_run_fixture_v1" >/dev/null || fail "diagnostic fixtures：缺少 dry-run fixture"
json_assert_text_contains "$RESPONSE_BODY" "dry_run" "True" >/dev/null || fail "diagnostic fixtures：应为 dry_run"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic fixtures：不应写数据库"

http_json GET "/api/diagnostic-data/dry-run/fixtures/diagnostic_data_dry_run_fixture_v1" "" "$token_a"
expect_status 200 "diagnostic data dry-run fixture get"
json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_data_dry_run_fixture" >/dev/null || fail "diagnostic fixture：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.diagnostic_reports" "CBC + Chemistry Dry-run Fixture" >/dev/null || fail "diagnostic fixture：报告 fixture 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.observations" "WBC" >/dev/null || fail "diagnostic fixture：observation fixture 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.imaging_studies" "DRYRUN-STUDY-0001" >/dev/null || fail "diagnostic fixture：imaging fixture 不正确"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_lab_ingest" "False" >/dev/null || fail "diagnostic fixture：不应执行真实检验接入"

http_json GET "/api/diagnostic-data/dry-run/fixtures/diagnostic_data_dry_run_fixture_v1"
expect_status 401 "diagnostic data fixture requires auth"


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
python3 -c 'import json,sys; data=json.load(open(sys.argv[1], encoding="utf-8")); value=data.get("context", {}).get("pet.name"); sys.exit(0 if "Smoke乐乐" in str(value or "") else 1)' "$RESPONSE_BODY" >/dev/null || fail "clinical docs render preview：pet.name 未填充 smoke 病例"
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

http_json GET "/api/diagnostic-data/cases/${case_id}/summary" "" "$token_b"
expect_status 404 "user B cannot read user A diagnostic data"
pass "diagnostic data read-only API checks"


# Lab Result Dry-run Fixture Parser V1: parses synthetic lab results into report/observation previews only.
http_json GET "/api/diagnostic-data/dry-run/lab-results/fixtures" "" "$token_a"
expect_status 200 "lab result dry-run fixture list"
json_assert_text_contains "$RESPONSE_BODY" "message" "lab_result_dry_run_fixtures" >/dev/null || fail "lab result fixture list：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture_ids" "lab_result_dry_run_fixture_v1" >/dev/null || fail "lab result fixture list：缺少 fixture"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "lab result fixture list：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_lab_ingest" "False" >/dev/null || fail "lab result fixture list：不应接真实检验"

http_json GET "/api/diagnostic-data/dry-run/lab-results/fixtures/lab_result_dry_run_fixture_v1" "" "$token_a"
expect_status 200 "lab result dry-run fixture get"
json_assert_text_contains "$RESPONSE_BODY" "message" "lab_result_dry_run_fixture" >/dev/null || fail "lab result fixture get：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.results" "WBC" >/dev/null || fail "lab result fixture get：缺少 WBC"
json_assert_text_contains "$RESPONSE_BODY" "fixture.results" "ALT" >/dev/null || fail "lab result fixture get：缺少 ALT"

lab_result_parse_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "fixture_id": "lab_result_dry_run_fixture_v1",
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/lab-results/parse" "$lab_result_parse_body" "$token_a"
expect_status 200 "lab result dry-run fixture parse"
json_assert_text_contains "$RESPONSE_BODY" "message" "lab_result_dry_run_parsed" >/dev/null || fail "lab result parser：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "quality_gate.status" "PASS" >/dev/null || fail "lab result parser：quality gate 未 PASS"
json_assert_text_contains "$RESPONSE_BODY" "report_preview.report_type" "lab_panel" >/dev/null || fail "lab result parser：report_type 不正确"
json_assert_text_contains "$RESPONSE_BODY" "observations_preview" "WBC" >/dev/null || fail "lab result parser：缺少 WBC observation"
json_assert_text_contains "$RESPONSE_BODY" "abnormal_observations" "ALT" >/dev/null || fail "lab result parser：缺少 ALT abnormal"
json_assert_text_contains "$RESPONSE_BODY" "abnormal_observations" "GLU" >/dev/null || fail "lab result parser：缺少 GLU abnormal"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "lab result parser：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "creates_diagnostic_report" "False" >/dev/null || fail "lab result parser：不应创建 DiagnosticReport"
json_assert_text_contains "$RESPONSE_BODY" "creates_observation" "False" >/dev/null || fail "lab result parser：不应创建 Observation"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_lab_ingest" "False" >/dev/null || fail "lab result parser：不应接真实检验"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "lab result parser：不应外发消息"

http_json POST "/api/diagnostic-data/dry-run/lab-results/parse" "$lab_result_parse_body"
expect_status 401 "lab result dry-run parser requires auth"

http_json POST "/api/diagnostic-data/dry-run/lab-results/parse" "$lab_result_parse_body" "$token_b"
expect_status 404 "user B cannot parse user A lab dry-run fixture"
pass "lab result dry-run fixture parser checks"

lab_abnormal_summary_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "fixture_id": "lab_result_dry_run_fixture_v1",
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/lab-results/abnormal-summary" "$lab_abnormal_summary_body" "$token_a"
expect_status 200 "AI lab abnormal summary dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "ai_lab_abnormal_summary_dry_run" >/dev/null || fail "AI lab abnormal summary：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "summary.human_review_required" "True" >/dev/null || fail "AI lab abnormal summary：必须人工复核"
json_assert_text_contains "$RESPONSE_BODY" "summary.not_a_diagnosis" "True" >/dev/null || fail "AI lab abnormal summary：不得作为诊断"
json_assert_text_contains "$RESPONSE_BODY" "summary.not_a_treatment_plan" "True" >/dev/null || fail "AI lab abnormal summary：不得作为治疗方案"
json_assert_text_contains "$RESPONSE_BODY" "abnormal_findings" "WBC" >/dev/null || fail "AI lab abnormal summary：缺少 WBC"
json_assert_text_contains "$RESPONSE_BODY" "abnormal_findings" "ALT" >/dev/null || fail "AI lab abnormal summary：缺少 ALT"
json_assert_text_contains "$RESPONSE_BODY" "abnormal_findings" "GLU" >/dev/null || fail "AI lab abnormal summary：缺少 GLU"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "AI lab abnormal summary：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "calls_external_ai" "False" >/dev/null || fail "AI lab abnormal summary：不应调用外部 AI"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_lab_ingest" "False" >/dev/null || fail "AI lab abnormal summary：不应接真实检验"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "AI lab abnormal summary：不应给剂量建议"

http_json POST "/api/diagnostic-data/dry-run/lab-results/abnormal-summary" "$lab_abnormal_summary_body"
expect_status 401 "AI lab abnormal summary requires auth"

http_json POST "/api/diagnostic-data/dry-run/lab-results/abnormal-summary" "$lab_abnormal_summary_body" "$token_b"
expect_status 404 "user B cannot summarize user A lab abnormal summary"
pass "AI lab abnormal summary checks"

# Imaging Metadata Dry-run Fixture Parser V1: synthetic metadata only, no PACS/DICOM/device ingest.
http_json GET "/api/diagnostic-data/dry-run/imaging-metadata/fixtures" "" "$token_a"
expect_status 200 "imaging metadata dry-run fixture list"
json_assert_text_contains "$RESPONSE_BODY" "message" "imaging_metadata_dry_run_fixtures" >/dev/null || fail "imaging metadata fixture list：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture_ids" "imaging_metadata_dry_run_fixture_v1" >/dev/null || fail "imaging metadata fixture list：缺少 fixture"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "imaging metadata fixture list：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_dicom_ingest" "False" >/dev/null || fail "imaging metadata fixture list：不应真实 DICOM ingest"

http_json GET "/api/diagnostic-data/dry-run/imaging-metadata/fixtures/imaging_metadata_dry_run_fixture_v1" "" "$token_a"
expect_status 200 "imaging metadata dry-run fixture get"
json_assert_text_contains "$RESPONSE_BODY" "message" "imaging_metadata_dry_run_fixture" >/dev/null || fail "imaging metadata fixture get：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.imaging_study.modality" "XR" >/dev/null || fail "imaging metadata fixture get：modality 不正确"
json_assert_text_contains "$RESPONSE_BODY" "fixture.safety.writes_database" "False" >/dev/null || fail "imaging metadata fixture get：不应写数据库"

imaging_parse_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "fixture_id": "imaging_metadata_dry_run_fixture_v1"
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/imaging-metadata/parse" "$imaging_parse_body" "$token_a"
expect_status 200 "imaging metadata dry-run fixture parse"
json_assert_text_contains "$RESPONSE_BODY" "message" "imaging_metadata_dry_run_parse" >/dev/null || fail "imaging metadata parse：message 不正确"
json_assert_text_contains "$RESPONSE_BODY" "quality_gate.status" "PASS" >/dev/null || fail "imaging metadata parse：quality_gate 未 PASS"
json_assert_text_contains "$RESPONSE_BODY" "study_preview.modality" "XR" >/dev/null || fail "imaging metadata parse：modality 不正确"
json_assert_text_contains "$RESPONSE_BODY" "study_preview.body_part" "abdomen" >/dev/null || fail "imaging metadata parse：body_part 不正确"
json_assert_text_contains "$RESPONSE_BODY" "study_preview.abnormal_flag" "abnormal" >/dev/null || fail "imaging metadata parse：abnormal_flag 不正确"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "imaging metadata parse：不应写数据库"
json_assert_text_contains "$RESPONSE_BODY" "creates_imaging_study" "False" >/dev/null || fail "imaging metadata parse：不应创建 imaging study"
json_assert_text_contains "$RESPONSE_BODY" "queries_pacs" "False" >/dev/null || fail "imaging metadata parse：不应查询 PACS"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_dicom_ingest" "False" >/dev/null || fail "imaging metadata parse：不应真实 DICOM ingest"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_device_ingest" "False" >/dev/null || fail "imaging metadata parse：不应真实设备 ingest"

http_json GET "/api/diagnostic-data/dry-run/imaging-metadata/fixtures"
expect_status 401 "imaging metadata dry-run parser requires auth"

http_json POST "/api/diagnostic-data/dry-run/imaging-metadata/parse" "$imaging_parse_body" "$token_b"
expect_status 404 "user B cannot parse user A imaging metadata fixture"
pass "imaging metadata dry-run fixture parser checks"


# AI Imaging Report Summary V1: deterministic dry-run summary only; no PACS/DICOM/device/external AI.
ai_imaging_summary_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "fixture_id": "imaging_metadata_dry_run_fixture_v1"
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/imaging-metadata/report-summary" "$ai_imaging_summary_body" "$token_a"
expect_status 200 "AI imaging report summary dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "ai_imaging_report_summary_dry_run" >/dev/null || fail "AI imaging report summary: bad message"
json_assert_text_contains "$RESPONSE_BODY" "summary.human_review_required" "True" >/dev/null || fail "AI imaging report summary: human review required"
json_assert_text_contains "$RESPONSE_BODY" "summary.not_a_diagnosis" "True" >/dev/null || fail "AI imaging report summary: must not be diagnosis"
json_assert_text_contains "$RESPONSE_BODY" "summary.not_a_treatment_plan" "True" >/dev/null || fail "AI imaging report summary: must not be treatment plan"
json_assert_text_contains "$RESPONSE_BODY" "summary.not_a_radiologist_report" "True" >/dev/null || fail "AI imaging report summary: must not be radiologist report"
json_assert_text_contains "$RESPONSE_BODY" "imaging_findings" "gastric" >/dev/null || fail "AI imaging report summary: missing gastric finding"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "AI imaging report summary: must not write database"
json_assert_text_contains "$RESPONSE_BODY" "creates_imaging_study" "False" >/dev/null || fail "AI imaging report summary: must not create ImagingStudy"
json_assert_text_contains "$RESPONSE_BODY" "queries_pacs" "False" >/dev/null || fail "AI imaging report summary: must not query PACS"
json_assert_text_contains "$RESPONSE_BODY" "reads_raw_dicom" "False" >/dev/null || fail "AI imaging report summary: must not read raw DICOM"
json_assert_text_contains "$RESPONSE_BODY" "calls_external_ai" "False" >/dev/null || fail "AI imaging report summary: must not call external AI"
json_assert_text_contains "$RESPONSE_BODY" "executes_real_dicom_ingest" "False" >/dev/null || fail "AI imaging report summary: must not execute real DICOM ingest"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "AI imaging report summary: must not give drug dose recommendation"

http_json POST "/api/diagnostic-data/dry-run/imaging-metadata/report-summary" "$ai_imaging_summary_body"
expect_status 401 "AI imaging report summary requires auth"

http_json POST "/api/diagnostic-data/dry-run/imaging-metadata/report-summary" "$ai_imaging_summary_body" "$token_b"
expect_status 404 "user B cannot summarize user A imaging report"
pass "AI imaging report summary checks"


# Treatment Recommendation Boundary V1: boundary-only review guard; no treatment plan or drug dose.
treatment_boundary_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "source_summary": "Dry-run lab and imaging summaries require clinician review before any treatment decision.",
    "candidate_recommendation": "Clinician should review hydration status, abdominal imaging, and lab abnormalities before deciding any treatment."
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/treatment-boundary/check" "$treatment_boundary_body" "$token_a"
expect_status 200 "Treatment recommendation boundary dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "treatment_recommendation_boundary_checked" >/dev/null || fail "Treatment boundary: bad message"
json_assert_text_contains "$RESPONSE_BODY" "boundary.decision" "review_only" >/dev/null || fail "Treatment boundary: expected review_only"
json_assert_text_contains "$RESPONSE_BODY" "boundary.human_review_required" "True" >/dev/null || fail "Treatment boundary: human review required"
json_assert_text_contains "$RESPONSE_BODY" "boundary.not_a_treatment_plan" "True" >/dev/null || fail "Treatment boundary: must not be treatment plan"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "Treatment boundary: must not write database"
json_assert_text_contains "$RESPONSE_BODY" "creates_treatment_plan" "False" >/dev/null || fail "Treatment boundary: must not create treatment plan"
json_assert_text_contains "$RESPONSE_BODY" "treatment_recommendation" "False" >/dev/null || fail "Treatment boundary: treatment recommendation disabled"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "Treatment boundary: drug dose recommendation disabled"
json_assert_text_contains "$RESPONSE_BODY" "calls_external_ai" "False" >/dev/null || fail "Treatment boundary: must not call external AI"

treatment_boundary_blocked_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "candidate_recommendation": "Give maropitant 1 mg/kg PO q24h."
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/treatment-boundary/check" "$treatment_boundary_blocked_body" "$token_a"
expect_status 200 "Treatment recommendation boundary blocks dose"
json_assert_text_contains "$RESPONSE_BODY" "boundary.decision" "blocked_drug_or_dose" >/dev/null || fail "Treatment boundary: expected blocked drug/dose"
json_assert_text_contains "$RESPONSE_BODY" "prohibited_items" "mg/kg" >/dev/null || fail "Treatment boundary: missing dose blocker"
json_assert_text_contains "$RESPONSE_BODY" "prohibited_items" "maropitant" >/dev/null || fail "Treatment boundary: missing drug blocker"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "Treatment boundary: still must not recommend dose"

http_json POST "/api/diagnostic-data/dry-run/treatment-boundary/check" "$treatment_boundary_body"
expect_status 401 "Treatment recommendation boundary requires auth"

http_json POST "/api/diagnostic-data/dry-run/treatment-boundary/check" "$treatment_boundary_body" "$token_b"
expect_status 404 "user B cannot check user A treatment boundary"
pass "Treatment recommendation boundary checks"


# Drug Dose Safety Framework V1: safety boundary only; no dose calculation or prescription output.
drug_dose_safety_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "species": "dog",
    "weight_kg": 5.2,
    "drug_name": "maropitant",
    "dose_expression": "mg/kg PO q24h",
    "clinical_context": "Dry-run safety boundary test only. Do not calculate or return a dose."
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/drug-dose-safety/check" "$drug_dose_safety_body" "$token_a"
expect_status 200 "Drug dose safety framework dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "drug_dose_safety_framework_checked" >/dev/null || fail "Drug dose safety framework: bad message"
json_assert_text_contains "$RESPONSE_BODY" "framework.decision" "blocked_dose_calculation_disabled" >/dev/null || fail "Drug dose safety framework: must block dose calculation"
json_assert_text_contains "$RESPONSE_BODY" "framework.dose_calculation_enabled" "False" >/dev/null || fail "Drug dose safety framework: dose calculation must be disabled"
json_assert_text_contains "$RESPONSE_BODY" "framework.returns_numeric_dose" "False" >/dev/null || fail "Drug dose safety framework: must not return numeric dose"
json_assert_text_contains "$RESPONSE_BODY" "framework.human_review_required" "True" >/dev/null || fail "Drug dose safety framework: human review required"
json_assert_text_contains "$RESPONSE_BODY" "prohibited_items" "maropitant" >/dev/null || fail "Drug dose safety framework: should identify drug name"
json_assert_text_contains "$RESPONSE_BODY" "prohibited_items" "q24h" >/dev/null || fail "Drug dose safety framework: should identify frequency token"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "Drug dose safety framework: must not write database"
json_assert_text_contains "$RESPONSE_BODY" "creates_prescription" "False" >/dev/null || fail "Drug dose safety framework: must not create prescription"
json_assert_text_contains "$RESPONSE_BODY" "writes_prescription" "False" >/dev/null || fail "Drug dose safety framework: must not write prescription"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "Drug dose safety framework: must not recommend dose"
json_assert_text_contains "$RESPONSE_BODY" "calls_external_ai" "False" >/dev/null || fail "Drug dose safety framework: must not call external AI"
pass "Drug dose safety framework blocks dose"

http_json POST "/api/diagnostic-data/dry-run/drug-dose-safety/check" "$drug_dose_safety_body"
expect_status 401 "Drug dose safety framework requires auth"

http_json POST "/api/diagnostic-data/dry-run/drug-dose-safety/check" "$drug_dose_safety_body" "$token_b"
expect_status 404 "user B cannot check user A drug dose safety"
pass "Drug dose safety framework checks"


# Drug Dose Knowledge Base V1: gated monograph shell only; no numeric dose output or prescription.
drug_dose_kb_review_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "drug_key": "maropitant",
    "species": "dog",
    "weight_kg": 5.2,
    "age_info": "adult",
    "current_medications": [],
    "renal_risk": False,
    "hepatic_risk": False,
    "pregnant_or_lactating": False,
    "known_allergies": []
}, ensure_ascii=False))
PY
)"
http_json GET "/api/diagnostic-data/dry-run/drug-dose-kb/monographs" "" "$token_a"
expect_status 200 "Drug dose knowledge base list"
json_assert_text_contains "$RESPONSE_BODY" "message" "drug_dose_knowledge_base_monographs" >/dev/null || fail "Drug dose KB list: bad message"
json_assert_text_contains "$RESPONSE_BODY" "items" "maropitant" >/dev/null || fail "Drug dose KB list: missing maropitant"
json_assert_text_contains "$RESPONSE_BODY" "numeric_dose_values_redacted" "True" >/dev/null || fail "Drug dose KB list: numeric dose values must be redacted"
json_assert_text_contains "$RESPONSE_BODY" "returns_numeric_dose" "False" >/dev/null || fail "Drug dose KB list: must not return numeric dose"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "Drug dose KB list: must not write database"

http_json GET "/api/diagnostic-data/dry-run/drug-dose-kb/monographs/maropitant" "" "$token_a"
expect_status 200 "Drug dose knowledge base monograph get"
json_assert_text_contains "$RESPONSE_BODY" "message" "drug_dose_knowledge_base_monograph" >/dev/null || fail "Drug dose KB get: bad message"
json_assert_text_contains "$RESPONSE_BODY" "monograph.drug_key" "maropitant" >/dev/null || fail "Drug dose KB get: wrong drug"
json_assert_text_contains "$RESPONSE_BODY" "monograph.dose_policy.numeric_dose_values_redacted" "True" >/dev/null || fail "Drug dose KB get: dose values must be redacted"
json_assert_text_contains "$RESPONSE_BODY" "monograph.dose_policy.dose_calculation_enabled" "False" >/dev/null || fail "Drug dose KB get: dose calculation must be disabled"
json_assert_text_contains "$RESPONSE_BODY" "drug_dose_recommendation" "False" >/dev/null || fail "Drug dose KB get: must not recommend dose"

http_json POST "/api/diagnostic-data/dry-run/drug-dose-kb/review" "$drug_dose_kb_review_body" "$token_a"
expect_status 200 "Drug dose knowledge base review"
json_assert_text_contains "$RESPONSE_BODY" "message" "drug_dose_knowledge_base_reviewed" >/dev/null || fail "Drug dose KB review: bad message"
json_assert_text_contains "$RESPONSE_BODY" "knowledge_base_review.decision" "kb_review_only_no_dose_output" >/dev/null || fail "Drug dose KB review: expected review-only decision"
json_assert_text_contains "$RESPONSE_BODY" "knowledge_base_review.numeric_dose_values_redacted" "True" >/dev/null || fail "Drug dose KB review: dose values must be redacted"
json_assert_text_contains "$RESPONSE_BODY" "knowledge_base_review.returns_numeric_dose" "False" >/dev/null || fail "Drug dose KB review: must not return numeric dose"
json_assert_text_contains "$RESPONSE_BODY" "knowledge_base_review.human_review_required" "True" >/dev/null || fail "Drug dose KB review: human review required"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "Drug dose KB review: must not write database"
json_assert_text_contains "$RESPONSE_BODY" "writes_prescription" "False" >/dev/null || fail "Drug dose KB review: must not write prescription"
json_assert_text_contains "$RESPONSE_BODY" "dose_calculation_enabled" "False" >/dev/null || fail "Drug dose KB review: dose calculation disabled"
json_assert_text_contains "$RESPONSE_BODY" "calls_external_ai" "False" >/dev/null || fail "Drug dose KB review: must not call external AI"

http_json POST "/api/diagnostic-data/dry-run/drug-dose-kb/review" "$drug_dose_kb_review_body"
expect_status 401 "Drug dose knowledge base requires auth"

http_json POST "/api/diagnostic-data/dry-run/drug-dose-kb/review" "$drug_dose_kb_review_body" "$token_b"
expect_status 404 "user B cannot review user A drug dose knowledge base"
pass "Drug dose knowledge base checks"


# Clinician Review Workflow for Diagnostic Summaries V1: review workflow preview only; no persistence or signoff.
clinician_review_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
print(json.dumps({
    "case_id": case_id,
    "requested_action": "review_and_signoff_preview",
    "lab_summary": {
        "headline": "Dry-run abnormal lab summary: WBC high, ALT high, GLU low",
        "human_review_required": True
    },
    "imaging_summary": {
        "headline": "Dry-run imaging summary: gastric abnormality requires clinician review",
        "human_review_required": True
    },
    "treatment_boundary": {
        "boundary": {
            "decision": "review_only",
            "not_a_treatment_plan": True
        }
    },
    "drug_dose_safety": {
        "framework": {
            "decision": "blocked_dose_calculation_disabled",
            "returns_numeric_dose": False
        }
    },
    "drug_dose_kb_review": {
        "knowledge_base_review": {
            "decision": "kb_review_only_no_dose_output",
            "numeric_dose_values_redacted": True
        }
    }
}, ensure_ascii=False))
PY
)"
http_json POST "/api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check" "$clinician_review_body" "$token_a"
expect_status 200 "Clinician review diagnostic summaries dry-run"
json_assert_text_contains "$RESPONSE_BODY" "message" "clinician_review_workflow_checked" >/dev/null || fail "Clinician review workflow: bad message"
json_assert_text_contains "$RESPONSE_BODY" "review_workflow.decision" "clinician_review_required" >/dev/null || fail "Clinician review workflow: expected clinician_review_required"
json_assert_text_contains "$RESPONSE_BODY" "review_workflow.human_review_required" "True" >/dev/null || fail "Clinician review workflow: human review required"
json_assert_text_contains "$RESPONSE_BODY" "review_workflow.final_signoff_persisted" "False" >/dev/null || fail "Clinician review workflow: final signoff must not persist"
json_assert_text_contains "$RESPONSE_BODY" "review_items" "ai_lab_abnormal_summary" >/dev/null || fail "Clinician review workflow: missing lab review item"
json_assert_text_contains "$RESPONSE_BODY" "review_items" "ai_imaging_report_summary" >/dev/null || fail "Clinician review workflow: missing imaging review item"
json_assert_text_contains "$RESPONSE_BODY" "blocked_actions" "write_ai_summary_to_diagnostic_report" >/dev/null || fail "Clinician review workflow: missing blocked write"
json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "Clinician review workflow: must not write database"
json_assert_text_contains "$RESPONSE_BODY" "writes_ai_summary" "False" >/dev/null || fail "Clinician review workflow: must not write AI summary"
json_assert_text_contains "$RESPONSE_BODY" "creates_audit_log" "False" >/dev/null || fail "Clinician review workflow: must not create audit log"
json_assert_text_contains "$RESPONSE_BODY" "signs_report" "False" >/dev/null || fail "Clinician review workflow: must not sign report"
json_assert_text_contains "$RESPONSE_BODY" "releases_to_client" "False" >/dev/null || fail "Clinician review workflow: must not release to client"
json_assert_text_contains "$RESPONSE_BODY" "writes_prescription" "False" >/dev/null || fail "Clinician review workflow: must not write prescription"

http_json POST "/api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check" "$clinician_review_body"
expect_status 401 "Clinician review workflow requires auth"

http_json POST "/api/diagnostic-data/dry-run/clinician-review/diagnostic-summaries/check" "$clinician_review_body" "$token_b"
expect_status 404 "user B cannot check user A clinician review workflow"
pass "Clinician review diagnostic summaries checks"



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
preventive_dry_run_total="$(json_get "$RESPONSE_BODY" "summary.total")"
[[ "${preventive_dry_run_total:-}" =~ ^[0-9]+$ ]] || fail "preventive care dry-run：summary.total 非数字：${preventive_dry_run_total:-empty}"
[[ "$preventive_dry_run_total" -ge 1 ]] || fail "preventive care dry-run：应返回至少 1 条提醒预览，实际 ${preventive_dry_run_total}"
json_assert_text_contains "$RESPONSE_BODY" "items" "preventive_care_reminder_preview" >/dev/null || fail "preventive care dry-run：items 未包含提醒预览"
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

# Reset opt-out before notification queue approval-path smoke.
# The opt-out save above validates the preference endpoint; queue review below tests
# the normal manual-contact approval path and must not inherit opt_out_all=true.
http_json PUT "/api/preventive-care/client-preferences" '{"allow_in_app":true,"allow_sms":false,"allow_wechat":false,"allow_email":false,"opt_out_all":false,"preferred_channel":"in_app","updated_by":"HS-SMOKE","note":"Smoke reset opt-out before notification queue tests."}' "$token_a"
expect_status 200 "preventive care client preferences reset"
json_assert_text_contains "$RESPONSE_BODY" "preferences.opt_out_all" "False" >/dev/null || fail "preventive care preferences reset：opt_out_all 未 false"
json_assert_text_contains "$RESPONSE_BODY" "sends_external_message" "False" >/dev/null || fail "preventive care preferences reset：不应外发消息"

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
json_assert_text_contains "$RESPONSE_BODY" "reminders.total" "3" >/dev/null || fail "preventive care ops summary：reminders.total 应为 3"
json_assert_text_contains "$RESPONSE_BODY" "notification_queue.total" "2" >/dev/null || fail "preventive care ops summary：notification_queue.total 应为 2"
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
# --- Diagnostic Assistance Problem List V1 smoke: start ---
if [ -f scripts/validate_diagnostic_assistance_problem_list.py ]; then
  echo "[smoke] Diagnostic Assistance Problem List V1 validator"
  python3 scripts/validate_diagnostic_assistance_problem_list.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_problem_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_problem_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_problem_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_problem_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_problem_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_problem_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_problem_auth_header}" ]; then
    _petmed_problem_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/dry-run/problem-list/build" \
      -H "${_petmed_problem_auth_header}" \
      -H "Content-Type: application/json" \
      --data '{"chief_complaint":"dry-run vomiting preview","history":{"duration":"2 days"},"lab_summary":{"abnormal_findings":[{"display_name":"ALT","abnormal_flag":"high","interpretation":"review required"}]},"clinician_review_workflow":{"review_workflow":{"status":"pending_clinician_review"}}}' \
      > "${_petmed_problem_json}"
    python3 - "${_petmed_problem_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

if data.get("message") != "diagnostic_assistance_problem_list_built":
    print("[smoke] Diagnostic Assistance Problem List V1 unexpected response:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    raise AssertionError("unexpected diagnostic assistance problem-list endpoint response")
assert data.get("mode") == "diagnostic_assistance_problem_list_v1"
assert data.get("writes_database") is False
assert data.get("requires_human_review") is True
assert data.get("not_a_diagnosis") is True
assert data.get("not_a_treatment_plan") is True
assert data.get("not_a_prescription") is True
assert data.get("not_client_facing") is True
assert isinstance(data.get("problem_list_preview"), list)
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] Diagnostic Assistance Problem List V1 endpoint PASS")
PY
    rm -f "${_petmed_problem_json}"
  else
    echo "[smoke] Diagnostic Assistance Problem List V1 endpoint skipped: no auth token exported"
  fi
fi
# --- Diagnostic Assistance Problem List V1 smoke: end ---
# --- Differential Diagnosis Candidates V1 smoke: start ---
if [ -f scripts/validate_differential_diagnosis_candidates.py ]; then
  echo "[smoke] Differential Diagnosis Candidates V1 validator"
  python3 scripts/validate_differential_diagnosis_candidates.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_ddx_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_ddx_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_ddx_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_ddx_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_ddx_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_ddx_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_ddx_auth_header}" ]; then
    _petmed_ddx_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/dry-run/differential-diagnosis/candidates/build" \
      -H "${_petmed_ddx_auth_header}" \
      -H "Content-Type: application/json" \
      --data '{"problem_list_preview":[{"problem_id":"problem-001","category":"presenting_complaint","title":"Vomiting requires clinician review","severity_hint":"medium","evidence_sources":[{"source_type":"case","field":"chief_complaint","snippet":"Vomiting for 2 days"}]},{"problem_id":"problem-002","category":"lab_abnormality","title":"Laboratory abnormality requires clinician review: ALT","severity_hint":"medium","evidence_sources":[{"source_type":"lab_abnormal_summary","field":"interpretation","snippet":"ALT high; liver enzyme pattern requires review"}]}]}' \
      > "${_petmed_ddx_json}"
    python3 - "${_petmed_ddx_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "differential_diagnosis_candidates_built"
assert data.get("mode") == "differential_diagnosis_candidates_v1"
assert data.get("writes_database") is False
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_a_diagnosis") is True
assert data.get("not_a_treatment_plan") is True
assert data.get("not_a_prescription") is True
assert data.get("not_client_facing") is True
assert data.get("returns_drug_dose") is False
assert data.get("returns_drug_route") is False
assert data.get("returns_drug_frequency") is False
assert data.get("returns_probability") is False
assert isinstance(data.get("differential_diagnosis_candidates_preview"), list)
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] Differential Diagnosis Candidates V1 endpoint PASS")
PY
    rm -f "${_petmed_ddx_json}"
  else
    echo "[smoke] Differential Diagnosis Candidates V1 endpoint skipped: no auth token exported"
  fi
fi
# --- Differential Diagnosis Candidates V1 smoke: end ---
# --- Diagnostic Reasoning Evidence Trace V1 smoke: start ---
if [ -f scripts/validate_diagnostic_reasoning_evidence_trace.py ]; then
  echo "[smoke] Diagnostic Reasoning Evidence Trace V1 validator"
  python3 scripts/validate_diagnostic_reasoning_evidence_trace.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_trace_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_trace_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_trace_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_trace_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_trace_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_trace_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_trace_auth_header}" ]; then
    _petmed_trace_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/dry-run/diagnostic-reasoning/evidence-trace/build" \
      -H "${_petmed_trace_auth_header}" \
      -H "Content-Type: application/json" \
      --data '{"problem_list_preview":[{"problem_id":"problem-001","category":"presenting_complaint","title":"Vomiting requires clinician review","severity_hint":"medium","evidence_sources":[{"source_type":"case","field":"chief_complaint","snippet":"Vomiting for 2 days"}]},{"problem_id":"problem-002","category":"lab_abnormality","title":"ALT abnormality requires clinician review","severity_hint":"medium","evidence_sources":[{"source_type":"lab_abnormal_summary","field":"ALT","snippet":"ALT high; hepatobiliary involvement requires review"}]}],"differential_diagnosis_candidates_preview":[{"candidate_key":"gastrointestinal_process_candidate","candidate_label":"Gastrointestinal process candidate","system_category":"gastrointestinal","severity_hint":"medium","supporting_evidence_sources":[{"source_type":"problem_list_preview","field":"chief_complaint","snippet":"Vomiting and appetite change"}],"contradicting_or_missing_evidence":["hydration status not supplied"],"evidence_fit_hint":"moderate_signal_for_review"}]}' \
      > "${_petmed_trace_json}"
    python3 - "${_petmed_trace_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "diagnostic_reasoning_evidence_trace_built"
assert data.get("mode") == "diagnostic_reasoning_evidence_trace_v1"
assert data.get("writes_database") is False
assert data.get("persists_reasoning_trace") is False
assert data.get("writes_audit_log") is False
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_a_diagnosis") is True
assert data.get("not_a_treatment_plan") is True
assert data.get("not_a_prescription") is True
assert data.get("not_client_facing") is True
assert data.get("returns_probability") is False
assert data.get("returns_numeric_confidence") is False
assert data.get("returns_drug_dose") is False
assert data.get("returns_drug_route") is False
assert data.get("returns_drug_frequency") is False
assert isinstance(data.get("diagnostic_reasoning_evidence_trace_preview"), list)
assert data.get("diagnostic_reasoning_evidence_trace_preview")
assert isinstance(data.get("evidence_source_index"), list)
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] Diagnostic Reasoning Evidence Trace V1 endpoint PASS")
PY
    rm -f "${_petmed_trace_json}"
  else
    echo "[smoke] Diagnostic Reasoning Evidence Trace V1 endpoint skipped: no auth token exported"
  fi
fi
# --- Diagnostic Reasoning Evidence Trace V1 smoke: end ---
# --- Diagnostic Assistance Case Detail UI V1 smoke: start ---
echo "[smoke] Diagnostic Assistance Case Detail UI V1 validator"
python3 scripts/validate_diagnostic_assistance_case_detail_ui.py >/dev/null || fail "diagnostic assistance case detail UI validation failed"
pass "diagnostic assistance case detail UI validator"
# --- Diagnostic Assistance Case Detail UI V1 smoke: end ---
# --- Clinician Review Persistence V1 smoke: start ---
if [ -f scripts/validate_clinician_review_persistence.py ]; then
  echo "[smoke] Clinician Review Persistence V1 validator"
  python3 scripts/validate_clinician_review_persistence.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_review_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_review_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_review_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_review_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_review_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_review_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  _petmed_review_case_id="${PETMED_REVIEW_CASE_ID:-}"
  if [ -z "${_petmed_review_case_id}" ] && [ -n "${case_id:-}" ]; then
    _petmed_review_case_id="${case_id}"
  fi

  if [ -n "${_petmed_review_auth_header}" ] && [ -n "${_petmed_review_case_id}" ]; then
    _petmed_review_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/clinician-review/persistence/apply" \
      -H "${_petmed_review_auth_header}" \
      -H "Content-Type: application/json" \
      --data "{\"case_id\":${_petmed_review_case_id},\"dry_run\":true,\"reviewed_by\":\"SMOKE-CLINICIAN\",\"review_items\":[]}" \
      > "${_petmed_review_json}"
    python3 - "${_petmed_review_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "clinician_review_persistence_applied"
assert data.get("mode") == "clinician_review_persistence_v1"
assert data.get("writes_database") is False
assert data.get("writes_audit_log") is False
assert data.get("persists_reasoning_trace") is False
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_client_facing") is True
assert data.get("quality_gate", {}).get("status") == "PASS"
assert data.get("persistence_result", {}).get("review_status_persistence_only") is True
print("[smoke] Clinician Review Persistence V1 endpoint PASS")
PY
    rm -f "${_petmed_review_json}"
  else
    echo "[smoke] Clinician Review Persistence V1 endpoint skipped: export PETMED_AUTH_TOKEN; PETMED_REVIEW_CASE_ID is optional when smoke creates case_id"
  fi
fi
# --- Clinician Review Persistence V1 smoke: end ---

# --- Diagnostic Summary Audit Log V1 smoke: start ---
if [ -f scripts/validate_diagnostic_summary_audit_log.py ]; then
  echo "[smoke] Diagnostic Summary Audit Log V1 validator"
  python3 scripts/validate_diagnostic_summary_audit_log.py
fi

if [ -n "${token_a:-}" ] && [ -n "${case_id:-}" ]; then
  diagnostic_summary_audit_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "dry_run": True,
    "clinician_id": "SMOKE-CLINICIAN",
    "action_taken": "summary_reviewed",
    "review_status": "reviewed",
    "target_type": "case_diagnostic_assistance",
    "source_modes": [
        "diagnostic_assistance_problem_list_v1",
        "differential_diagnosis_candidates_v1",
        "diagnostic_reasoning_evidence_trace_v1",
        "clinician_review_persistence_v1"
    ],
    "source_preview_ids": ["smoke-problem-list", "smoke-ddx", "smoke-trace"],
    "note": "Smoke dry-run audit event only; no clinical conclusion, no treatment plan, no prescription.",
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
  http_json POST "/api/diagnostic-data/diagnostic-summary/audit-log/append" "$diagnostic_summary_audit_body" "$token_a"
  expect_status 200 "diagnostic summary audit log dry-run"
  json_assert_text_contains "$RESPONSE_BODY" "message" "diagnostic_summary_audit_log_appended" >/dev/null || fail "diagnostic summary audit log：message 不正确"
  json_assert_text_contains "$RESPONSE_BODY" "mode" "diagnostic_summary_audit_log_v1" >/dev/null || fail "diagnostic summary audit log：mode 不正确"
  json_assert_text_contains "$RESPONSE_BODY" "dry_run" "True" >/dev/null || fail "diagnostic summary audit log：dry_run 应为 true"
  json_assert_text_contains "$RESPONSE_BODY" "writes_database" "False" >/dev/null || fail "diagnostic summary audit log dry-run：不应写数据库"
  json_assert_text_contains "$RESPONSE_BODY" "writes_audit_log" "False" >/dev/null || fail "diagnostic summary audit log dry-run：不应写 audit log"
  json_assert_text_contains "$RESPONSE_BODY" "creates_audit_log" "False" >/dev/null || fail "diagnostic summary audit log dry-run：不应创建 audit log"
  json_assert_text_contains "$RESPONSE_BODY" "updates_case" "False" >/dev/null || fail "diagnostic summary audit log：不应更新 Case"
  json_assert_text_contains "$RESPONSE_BODY" "updates_diagnostic_report" "False" >/dev/null || fail "diagnostic summary audit log：不应更新 DiagnosticReport"
  json_assert_text_contains "$RESPONSE_BODY" "writes_ai_summary" "False" >/dev/null || fail "diagnostic summary audit log：不应写 ai_summary"
  json_assert_text_contains "$RESPONSE_BODY" "persists_reasoning_trace" "False" >/dev/null || fail "diagnostic summary audit log：不应持久化 reasoning trace"
  json_assert_text_contains "$RESPONSE_BODY" "generates_final_diagnosis" "False" >/dev/null || fail "diagnostic summary audit log：不应生成 final diagnosis"
  json_assert_text_contains "$RESPONSE_BODY" "creates_treatment_plan" "False" >/dev/null || fail "diagnostic summary audit log：不应生成 treatment plan"
  json_assert_text_contains "$RESPONSE_BODY" "writes_prescription" "False" >/dev/null || fail "diagnostic summary audit log：不应写 prescription"
  json_assert_text_contains "$RESPONSE_BODY" "returns_drug_dose" "False" >/dev/null || fail "diagnostic summary audit log：不应返回 drug dose"
  json_assert_text_contains "$RESPONSE_BODY" "returns_probability" "False" >/dev/null || fail "diagnostic summary audit log：不应返回 probability"
  json_assert_text_contains "$RESPONSE_BODY" "requires_human_review" "True" >/dev/null || fail "diagnostic summary audit log：必须人工复核"
  json_assert_text_contains "$RESPONSE_BODY" "clinician_signoff_required" "True" >/dev/null || fail "diagnostic summary audit log：必须 clinician signoff"
  json_assert_text_contains "$RESPONSE_BODY" "not_client_facing" "True" >/dev/null || fail "diagnostic summary audit log：不应 client-facing"

  http_json POST "/api/diagnostic-data/diagnostic-summary/audit-log/append" "$diagnostic_summary_audit_body"
  expect_status 401 "diagnostic summary audit log requires auth"

  if [ -n "${token_b:-}" ]; then
    http_json POST "/api/diagnostic-data/diagnostic-summary/audit-log/append" "$diagnostic_summary_audit_body" "$token_b"
    expect_status 404 "user B cannot append user A diagnostic summary audit log"
  fi

  if [ "${PETMED_DIAGNOSTIC_SUMMARY_AUDIT_WRITE_SMOKE:-0}" = "1" ]; then
    diagnostic_summary_audit_write_body="$(python3 - "$case_id" <<'PY'
import json
import sys
case_id = int(sys.argv[1])
body = {
    "case_id": case_id,
    "dry_run": False,
    "clinician_id": "SMOKE-CLINICIAN",
    "action_taken": "summary_reviewed",
    "review_status": "reviewed",
    "target_type": "case_diagnostic_assistance",
    "source_preview_ids": ["smoke-controlled-audit-write"],
    "note": "Controlled smoke audit append only; no diagnosis, no treatment plan, no prescription.",
    "audit_log_confirmation": "I_UNDERSTAND_THIS_APPENDS_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ONLY"
}
print(json.dumps(body, ensure_ascii=False))
PY
)"
    http_json POST "/api/diagnostic-data/diagnostic-summary/audit-log/append" "$diagnostic_summary_audit_write_body" "$token_a"
    expect_status 200 "diagnostic summary audit log controlled append"
    json_assert_text_contains "$RESPONSE_BODY" "writes_audit_log" "True" >/dev/null || fail "diagnostic summary audit controlled append：应写 audit log"
    json_assert_text_contains "$RESPONSE_BODY" "audit_log_result.persisted" "True" >/dev/null || fail "diagnostic summary audit controlled append：persisted 应为 true"
  fi

  pass "Diagnostic Summary Audit Log V1 checks"
else
  echo "[smoke] Diagnostic Summary Audit Log V1 endpoint skipped: smoke token_a/case_id unavailable"
fi
# --- Diagnostic Summary Audit Log V1 smoke: end ---
# --- DiagnosticReport AI Summary Persistence V1 smoke: start ---
if [ -f scripts/validate_diagnosticreport_ai_summary_persistence.py ]; then
  echo "[smoke] DiagnosticReport AI Summary Persistence V1 validator"
  python3 scripts/validate_diagnosticreport_ai_summary_persistence.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_ai_summary_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_ai_summary_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_ai_summary_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_ai_summary_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_ai_summary_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_ai_summary_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_ai_summary_auth_header}" ] && [ -n "${PETMED_DIAGNOSTIC_REPORT_ID:-}" ]; then
    _petmed_ai_summary_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/diagnostic-reports/${PETMED_DIAGNOSTIC_REPORT_ID}/ai-summary/persistence/apply" \
      -H "${_petmed_ai_summary_auth_header}" \
      -H "Content-Type: application/json" \
      --data '{"dry_run":true,"reviewed_by":"SMOKE-CLINICIAN","ai_summary":"Clinician-reviewed summary: diagnostic abnormalities require continued professional review and are not client-facing conclusions.","source_preview_ids":["smoke-diagnostic-assistance-case-detail-ui-v1"]}' \
      > "${_petmed_ai_summary_json}"
    python3 - "${_petmed_ai_summary_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "diagnosticreport_ai_summary_persistence_applied"
assert data.get("mode") == "diagnosticreport_ai_summary_persistence_v1"
assert data.get("dry_run") is True
assert data.get("writes_database") is False
assert data.get("writes_ai_summary") is False
assert data.get("writes_audit_log") is False
assert data.get("persists_reasoning_trace") is False
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_client_facing") is True
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] DiagnosticReport AI Summary Persistence V1 dry-run endpoint PASS")
PY
    rm -f "${_petmed_ai_summary_json}"

    if [ "${PETMED_AI_SUMMARY_WRITE_SMOKE:-0}" = "1" ]; then
      if [ -z "${PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID:-}" ]; then
        echo "[smoke] DiagnosticReport AI Summary Persistence V1 controlled write skipped: missing PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID"
      else
        _petmed_ai_summary_write_json="$(mktemp)"
        curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/diagnostic-reports/${PETMED_DIAGNOSTIC_REPORT_ID}/ai-summary/persistence/apply" \
          -H "${_petmed_ai_summary_auth_header}" \
          -H "Content-Type: application/json" \
          --data "{\"dry_run\":false,\"reviewed_by\":\"SMOKE-CLINICIAN\",\"audit_log_id\":\"${PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID}\",\"persistence_confirmation\":\"I_UNDERSTAND_THIS_WRITES_DIAGNOSTICREPORT_AI_SUMMARY_ONLY\",\"ai_summary\":\"Clinician-reviewed summary: diagnostic abnormalities require continued professional review and are not client-facing conclusions.\"}" \
          > "${_petmed_ai_summary_write_json}"
        python3 - "${_petmed_ai_summary_write_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "diagnosticreport_ai_summary_persistence_applied"
assert data.get("mode") == "diagnosticreport_ai_summary_persistence_v1"
assert data.get("dry_run") is False
assert data.get("writes_database") is True
assert data.get("updates_diagnostic_report") is True
assert data.get("writes_ai_summary") is True
assert data.get("writes_ai_summary_status") is True
assert data.get("writes_audit_log") is False
assert data.get("updates_case") is False
assert data.get("updates_observation") is False
assert data.get("updates_imaging_study") is False
assert data.get("persists_reasoning_trace") is False
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert data.get("persistence_result", {}).get("persisted") is True
assert data.get("persistence_result", {}).get("audit_log_verified") is True
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] DiagnosticReport AI Summary Persistence V1 controlled write PASS")
PY
        rm -f "${_petmed_ai_summary_write_json}"
      fi
    fi
  else
    echo "[smoke] DiagnosticReport AI Summary Persistence V1 endpoint skipped: requires auth token and PETMED_DIAGNOSTIC_REPORT_ID"
  fi
fi
# --- DiagnosticReport AI Summary Persistence V1 smoke: end ---
# --- Observation Abnormal Flag Review V1 smoke: start ---
if [ -f scripts/validate_observation_abnormal_flag_review.py ]; then
  echo "[smoke] Observation Abnormal Flag Review V1 validator"
  python3 scripts/validate_observation_abnormal_flag_review.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_obs_flag_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_obs_flag_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_obs_flag_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_obs_flag_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_obs_flag_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_obs_flag_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_obs_flag_auth_header}" ] && [ -n "${PETMED_OBSERVATION_ID:-}" ]; then
    _petmed_obs_flag_json="$(mktemp)"
    _petmed_obs_flag_payload="$(python3 - <<'PY'
import json
import os

write_smoke = os.environ.get("PETMED_OBSERVATION_ABNORMAL_FLAG_WRITE_SMOKE") == "1"
body = {
    "dry_run": not write_smoke,
    "reviewed_by": "SMOKE-CLINICIAN",
    "abnormal_flag": os.environ.get("PETMED_OBSERVATION_ABNORMAL_FLAG", "abnormal"),
    "review_status": "reviewed",
    "note": "Observation Abnormal Flag Review V1 smoke; not a diagnosis, not a treatment plan, not a prescription.",
}
case_id = os.environ.get("PETMED_OBSERVATION_CASE_ID")
if case_id:
    body["case_id"] = int(case_id)
if write_smoke:
    body["audit_log_id"] = os.environ.get("PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID", "")
    body["abnormal_flag_review_confirmation"] = "I_UNDERSTAND_THIS_WRITES_OBSERVATION_ABNORMAL_FLAG_REVIEW_ONLY"
print(json.dumps(body, ensure_ascii=False))
PY
)"
    _petmed_obs_flag_status="$(curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/observations/${PETMED_OBSERVATION_ID}/abnormal-flag/review/apply" \
      -H "${_petmed_obs_flag_auth_header}" \
      -H "Content-Type: application/json" \
      --data "${_petmed_obs_flag_payload}" \
      -o "${_petmed_obs_flag_json}" \
      -w "%{http_code}")"
    python3 - "${_petmed_obs_flag_json}" "${_petmed_obs_flag_status}" <<'PY'
import json
import sys

path, status = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

if status != "200":
    print(json.dumps(data, indent=2, ensure_ascii=False))
    raise SystemExit("Observation Abnormal Flag Review V1 endpoint returned HTTP %s" % status)

assert data.get("message") == "observation_abnormal_flag_review_applied"
assert data.get("mode") == "observation_abnormal_flag_review_v1"
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_a_diagnosis") is True
assert data.get("not_a_treatment_plan") is True
assert data.get("not_a_prescription") is True
assert data.get("not_client_facing") is True
assert data.get("updates_case") is False
assert data.get("updates_diagnostic_report") is False
assert data.get("updates_imaging_study") is False
assert data.get("writes_ai_summary") is False
assert data.get("writes_audit_log") is False
assert data.get("persists_reasoning_trace") is False
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert data.get("quality_gate", {}).get("status") == "PASS"
if data.get("dry_run") is True:
    assert data.get("writes_database") is False
    assert data.get("updates_observation") is False
else:
    assert data.get("writes_database") is True
    assert data.get("updates_observation") is True
    assert data.get("writes_observation_abnormal_flag_only") is True
print("[smoke] Observation Abnormal Flag Review V1 endpoint PASS")
PY
    rm -f "${_petmed_obs_flag_json}"
  else
    echo "[smoke] Observation Abnormal Flag Review V1 endpoint skipped: set PETMED_OBSERVATION_ID for live endpoint smoke"
  fi
fi
# --- Observation Abnormal Flag Review V1 smoke: end ---
# --- ImagingStudy Review Workflow V1 smoke: start ---
if [ -f scripts/validate_imagingstudy_review_workflow.py ]; then
  echo "[smoke] ImagingStudy Review Workflow V1 validator"
  python3 scripts/validate_imagingstudy_review_workflow.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_imaging_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_imaging_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_imaging_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_imaging_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_imaging_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_imaging_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_imaging_auth_header}" ] && [ -n "${PETMED_IMAGING_STUDY_ID:-}" ]; then
    _petmed_imaging_json="$(mktemp)"
    _petmed_imaging_status_file="$(mktemp)"
    _petmed_imaging_dry_run="true"
    if [ "${PETMED_IMAGINGSTUDY_REVIEW_WRITE_SMOKE:-0}" = "1" ]; then
      _petmed_imaging_dry_run="false"
    fi
    _petmed_imaging_body="$(python3 - "${_petmed_imaging_dry_run}" "${PETMED_DIAGNOSTIC_SUMMARY_AUDIT_LOG_ID:-}" <<'PY'
import json
import sys

dry_run = sys.argv[1].lower() == "true"
audit_log_id = sys.argv[2]
body = {
    "dry_run": dry_run,
    "reviewed_by": "SMOKE-CLINICIAN",
    "review_status": "reviewed",
    "abnormal_flag": "abnormal",
    "note": "ImagingStudy Review Workflow V1 smoke; not a diagnosis, not a treatment plan, not a prescription.",
}
if not dry_run:
    body["audit_log_id"] = audit_log_id
    body["imagingstudy_review_confirmation"] = "I_UNDERSTAND_THIS_WRITES_IMAGINGSTUDY_REVIEW_WORKFLOW_ONLY"
print(json.dumps(body, ensure_ascii=False))
PY
)"
    _petmed_imaging_http_status="$(curl -sS -X POST "${BASE_URL%/}/api/diagnostic-data/imaging-studies/${PETMED_IMAGING_STUDY_ID}/review-workflow/apply" \
      -H "${_petmed_imaging_auth_header}" \
      -H "Content-Type: application/json" \
      --data "${_petmed_imaging_body}" \
      -o "${_petmed_imaging_json}" \
      -w "%{http_code}")"
    printf "%s" "${_petmed_imaging_http_status}" > "${_petmed_imaging_status_file}"
    python3 - "${_petmed_imaging_json}" "${_petmed_imaging_status_file}" <<'PY'
import json
import sys

body_path, status_path = sys.argv[1], sys.argv[2]
status = open(status_path, "r", encoding="utf-8").read().strip()
with open(body_path, "r", encoding="utf-8") as handle:
    data = json.load(handle)
if status != "200":
    print(json.dumps(data, indent=2, ensure_ascii=False))
    raise SystemExit("ImagingStudy Review Workflow V1 endpoint returned HTTP %s" % status)

assert data.get("message") == "imagingstudy_review_workflow_applied"
assert data.get("mode") == "imagingstudy_review_workflow_v1"
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_client_facing") is True
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert data.get("writes_audit_log") is False
assert data.get("updates_observation") is False
assert data.get("updates_diagnostic_report") is False
assert data.get("writes_ai_summary") is False
assert data.get("quality_gate", {}).get("status") == "PASS"
if data.get("dry_run") is True:
    assert data.get("writes_database") is False
    assert data.get("updates_imaging_study") is False
else:
    assert data.get("writes_database") is True
    assert data.get("updates_imaging_study") is True
    assert data.get("writes_imaging_study_review_status") is True
    assert data.get("writes_imaging_study_reviewed_by") is True
    assert data.get("writes_imaging_study_reviewed_at") is True
print("[smoke] ImagingStudy Review Workflow V1 endpoint PASS")
PY
    rm -f "${_petmed_imaging_json}" "${_petmed_imaging_status_file}"
  else
    echo "[smoke] ImagingStudy Review Workflow V1 endpoint skipped: set PETMED_IMAGING_STUDY_ID for live endpoint smoke"
  fi
fi
# --- ImagingStudy Review Workflow V1 smoke: end ---

# --- Clinical Docs Diagnostic Data Merge V1 smoke: start ---
if [ -f scripts/validate_clinical_docs_diagnostic_data_merge.py ]; then
  echo "[smoke] Clinical Docs Diagnostic Data Merge V1 validator"
  python3 scripts/validate_clinical_docs_diagnostic_data_merge.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_clinical_docs_diag_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_clinical_docs_diag_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_clinical_docs_diag_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_clinical_docs_diag_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_clinical_docs_diag_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_clinical_docs_diag_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  _petmed_clinical_docs_diag_case_id="${PETMED_CASE_ID:-${case_id:-}}"
  if [ -n "${_petmed_clinical_docs_diag_auth_header}" ] && [ -n "${_petmed_clinical_docs_diag_case_id}" ]; then
    _petmed_clinical_docs_diag_json="$(mktemp)"
    curl -sS -X POST "${BASE_URL%/}/api/clinical-docs/render-preview" \
      -H "${_petmed_clinical_docs_diag_auth_header}" \
      -H "Content-Type: application/json" \
      --data "{\"case_id\":${_petmed_clinical_docs_diag_case_id},\"template_id\":\"admission_hospitalization_record_bilingual\",\"include_diagnostic_data\":true}" \
      > "${_petmed_clinical_docs_diag_json}"
    python3 - "${_petmed_clinical_docs_diag_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

try:
    assert data.get("message") == "clinical_doc_render_preview"
    merge = data.get("diagnostic_data_merge") or {}
    assert merge.get("mode") == "clinical_docs_diagnostic_data_merge_v1"
    assert merge.get("writes_database") is False
    assert merge.get("updates_diagnostic_report") is False
    assert merge.get("updates_observation") is False
    assert merge.get("updates_imaging_study") is False
    assert merge.get("writes_ai_summary") is False
    assert merge.get("writes_audit_log") is False
    assert merge.get("generates_final_diagnosis") is False
    assert merge.get("creates_treatment_plan") is False
    assert merge.get("writes_prescription") is False
    assert merge.get("returns_drug_dose") is False
    assert merge.get("requires_human_review") is True
    assert merge.get("clinician_signoff_required") is True
    assert (merge.get("quality_gate") or {}).get("status") == "PASS"
except AssertionError:
    print(json.dumps(data, ensure_ascii=False, indent=2))
    raise

print("[smoke] Clinical Docs Diagnostic Data Merge V1 endpoint PASS")
PY
    rm -f "${_petmed_clinical_docs_diag_json}"
  else
    echo "[smoke] Clinical Docs Diagnostic Data Merge V1 endpoint skipped: no auth token or case_id available"
  fi
fi
# --- Clinical Docs Diagnostic Data Merge V1 smoke: end ---

# --- Clinical QA Dashboard V2 smoke: start ---
if [ -f scripts/validate_clinical_qa_dashboard_v2.py ]; then
  echo "[smoke] Clinical QA Dashboard V2 validator"
  python3 scripts/validate_clinical_qa_dashboard_v2.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_clinical_qa_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_clinical_qa_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_clinical_qa_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_clinical_qa_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_clinical_qa_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_clinical_qa_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_clinical_qa_auth_header}" ]; then
    _petmed_clinical_qa_json="$(mktemp)"
    _petmed_clinical_qa_case_param=""
    if [ -n "${case_id:-}" ]; then
      _petmed_clinical_qa_case_param="?case_id=${case_id}"
    fi
    curl -sS -X GET "${BASE_URL%/}/api/diagnostic-data/clinical-qa-dashboard/v2/summary${_petmed_clinical_qa_case_param}" \
      -H "${_petmed_clinical_qa_auth_header}" \
      > "${_petmed_clinical_qa_json}"
    python3 - "${_petmed_clinical_qa_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

assert data.get("message") == "clinical_qa_dashboard_v2_summary", data
assert data.get("mode") == "clinical_qa_dashboard_v2", data
assert data.get("writes_database") is False, data
assert data.get("creates_case") is False, data
assert data.get("updates_diagnostic_report") is False, data
assert data.get("updates_observation") is False, data
assert data.get("updates_imaging_study") is False, data
assert data.get("writes_ai_summary") is False, data
assert data.get("writes_audit_log") is False, data
assert data.get("persists_reasoning_trace") is False, data
assert data.get("generates_final_diagnosis") is False, data
assert data.get("creates_treatment_plan") is False, data
assert data.get("writes_prescription") is False, data
assert data.get("returns_drug_dose") is False, data
assert data.get("requires_human_review") is True, data
assert data.get("clinician_signoff_required") is True, data
assert data.get("not_client_facing") is True, data
assert isinstance(data.get("cards"), list), data
assert isinstance(data.get("metrics"), dict), data
assert isinstance(data.get("qa_queue"), list), data
assert data.get("quality_gate", {}).get("status") == "PASS", data
print("[smoke] Clinical QA Dashboard V2 endpoint PASS")
PY
    rm -f "${_petmed_clinical_qa_json}"
  else
    echo "[smoke] Clinical QA Dashboard V2 endpoint skipped: no auth token available"
  fi
fi
# --- Clinical QA Dashboard V2 smoke: end ---
# --- Ops Dashboard Clinical Core V2 smoke: start ---
if [ -f scripts/validate_ops_dashboard_clinical_core_v2.py ]; then
  echo "[smoke] Ops Dashboard Clinical Core V2 validator"
  python3 scripts/validate_ops_dashboard_clinical_core_v2.py
fi

if [ -n "${BASE_URL:-}" ] && command -v curl >/dev/null 2>&1; then
  _petmed_ops_clinical_core_auth_header=""
  if [ -n "${AUTH_HEADER:-}" ]; then
    _petmed_ops_clinical_core_auth_header="${AUTH_HEADER}"
  elif [ -n "${token_a:-}" ]; then
    _petmed_ops_clinical_core_auth_header="Authorization: Bearer ${token_a}"
  elif [ -n "${PETMED_AUTH_TOKEN:-}" ]; then
    _petmed_ops_clinical_core_auth_header="Authorization: Bearer ${PETMED_AUTH_TOKEN}"
  elif [ -n "${AUTH_TOKEN:-}" ]; then
    _petmed_ops_clinical_core_auth_header="Authorization: Bearer ${AUTH_TOKEN}"
  elif [ -n "${TOKEN:-}" ]; then
    _petmed_ops_clinical_core_auth_header="Authorization: Bearer ${TOKEN}"
  fi

  if [ -n "${_petmed_ops_clinical_core_auth_header}" ]; then
    _petmed_ops_clinical_core_json="$(mktemp)"
    curl -sS "${BASE_URL%/}/api/diagnostic-data/clinical-qa-dashboard/v2/summary" \
      -H "${_petmed_ops_clinical_core_auth_header}" \
      > "${_petmed_ops_clinical_core_json}"
    python3 - "${_petmed_ops_clinical_core_json}" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

if data.get("message") != "clinical_qa_dashboard_v2_summary":
    print(json.dumps(data, indent=2, ensure_ascii=False))
    raise SystemExit("Ops Dashboard Clinical Core V2 smoke: unexpected response message")
assert data.get("mode") == "clinical_qa_dashboard_v2"
assert data.get("writes_database") is False
assert data.get("requires_human_review") is True
assert data.get("clinician_signoff_required") is True
assert data.get("not_client_facing") is True
assert data.get("generates_final_diagnosis") is False
assert data.get("creates_treatment_plan") is False
assert data.get("writes_prescription") is False
assert data.get("returns_drug_dose") is False
assert isinstance(data.get("cards"), list)
assert isinstance(data.get("metrics"), dict)
assert isinstance(data.get("qa_queue"), list)
assert data.get("quality_gate", {}).get("status") == "PASS"
print("[smoke] Ops Dashboard Clinical Core V2 endpoint PASS")
PY
    rm -f "${_petmed_ops_clinical_core_json}"
  else
    echo "[smoke] Ops Dashboard Clinical Core V2 endpoint skipped: no auth token available"
  fi
fi
# --- Ops Dashboard Clinical Core V2 smoke: end ---

# --- Exotics Knowledge Coverage Gap Review V1 smoke: start ---
if [ -f scripts/validate_exotics_knowledge_coverage_gap_review.py ]; then
  echo "[smoke] Exotics Knowledge Coverage Gap Review V1 validator"
  python3 scripts/validate_exotics_knowledge_coverage_gap_review.py
fi
# --- Exotics Knowledge Coverage Gap Review V1 smoke: end ---
# --- Exotics Rabbit Deepening V1 smoke: start ---
if [ -f scripts/validate_exotics_rabbit_deepening.py ]; then
  echo "[smoke] Exotics Rabbit Deepening V1 smoke"
  python3 scripts/validate_exotics_rabbit_deepening.py
fi
# --- Exotics Rabbit Deepening V1 smoke: end ---

# --- Exotics Avian Deepening V1 smoke: start ---
if [ -f scripts/validate_exotics_avian_deepening.py ]; then
  echo "[smoke] Exotics Avian Deepening V1 validator"
  python3 scripts/validate_exotics_avian_deepening.py
fi
# --- Exotics Avian Deepening V1 smoke: end ---
# --- Exotics Reptile Split V1 smoke: start ---
if [ -f scripts/validate_exotics_reptile_split.py ]; then
  echo "[smoke] Exotics Reptile Split V1 smoke"
  python3 scripts/validate_exotics_reptile_split.py
fi
# --- Exotics Reptile Split V1 smoke: end ---

# --- Exotics Small Mammal Split V1 smoke: start ---
if [ -f scripts/validate_exotics_small_mammal_split.py ]; then
  echo "[smoke] Exotics Small Mammal Split V1 validator"
  python3 scripts/validate_exotic_kb.py
  python3 scripts/validate_exotic_intake_templates.py
  python3 scripts/validate_exotics_small_mammal_split.py
fi
# --- Exotics Small Mammal Split V1 smoke: end ---

# --- Exotics Ferret Deepening V1 smoke: start ---
if [ -f scripts/validate_exotics_ferret_deepening.py ]; then
  echo "[smoke] Exotics Ferret Deepening V1 validator"
  python3 scripts/validate_exotics_ferret_deepening.py
fi
# --- Exotics Ferret Deepening V1 smoke: end ---
# --- Exotics Lab / Imaging Interpretation Readiness V1 smoke: start ---
if [ -f scripts/validate_exotics_lab_imaging_interpretation_readiness.py ]; then
  echo "[smoke] Exotics Lab / Imaging Interpretation Readiness V1 validator"
  python3 scripts/validate_exotics_lab_imaging_interpretation_readiness.py
fi
# --- Exotics Lab / Imaging Interpretation Readiness V1 smoke: end ---
# --- Exotics Drug Dose Source Review Pack V1 smoke: start ---
if [ -f scripts/validate_exotics_drug_dose_source_review_pack.py ]; then
  echo "[smoke] Exotics Drug Dose Source Review Pack V1 smoke"
  python3 scripts/validate_exotics_drug_dose_source_review_pack.py
fi
# --- Exotics Drug Dose Source Review Pack V1 smoke: end ---
# --- Exotics Drug Dose Source Review Controlled Research V1 smoke: start ---
if [ -f scripts/validate_exotics_drug_dose_source_review_controlled_research.py ]; then
  echo "[smoke] Exotics Drug Dose Source Review Controlled Research V1 smoke"
  python3 scripts/validate_exotics_drug_dose_source_review_controlled_research.py
fi
# --- Exotics Drug Dose Source Review Controlled Research V1 smoke: end ---

# --- Exotics Drug Dose Source Evidence Abstraction V1 smoke: start ---
if [ -f scripts/validate_exotics_drug_dose_source_evidence_abstraction.py ]; then
  echo "[smoke] Exotics Drug Dose Source Evidence Abstraction V1 validator"
  python3 scripts/validate_exotics_drug_dose_source_evidence_abstraction.py
fi
# --- Exotics Drug Dose Source Evidence Abstraction V1 smoke: end ---

# --- Exotics Drug Dose Source Review Evidence Tables V1 smoke: start ---
if [ -f scripts/validate_exotics_drug_dose_source_review_evidence_tables.py ]; then
  echo "[smoke] Exotics Drug Dose Source Review Evidence Tables V1 validator"
  python3 scripts/validate_exotics_drug_dose_source_review_evidence_tables.py
fi
# --- Exotics Drug Dose Source Review Evidence Tables V1 smoke: end ---
