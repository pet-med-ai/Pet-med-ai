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

# 2. signup/login user A
http_json POST "/auth/signup" "{\"email\":\"${email_a}\",\"password\":\"${PASSWORD}\",\"full_name\":\"Smoke A\"}"
expect_status 200 "signup user A"

http_form "/auth/login" "username=${email_a}&password=${PASSWORD}"
expect_status 200 "login user A"
token_a="$(json_get "$RESPONSE_BODY" "access_token")"
[[ -n "$token_a" ]] || fail "login user A：没有 access_token"

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
http_json POST "/api/ai/consult/session/${session_id}/save-case" '{"patient_name":"Smoke乐乐","species":"dog","sex":"M","age_info":"4y"}' "$token_a"
expect_status 200 "save consult as case"
case_id="$(json_get "$RESPONSE_BODY" "case_id")"
message="$(json_get "$RESPONSE_BODY" "message")"
[[ -n "$case_id" ]] || fail "save consult as case：没有 case_id"
[[ "$message" == "saved" || "$message" == "already_saved" ]] || fail "save consult as case：message 异常：$message"

# 6. history contains case_id
http_json GET "/api/ai/consult/sessions?limit=20" "" "$token_a"
expect_status 200 "history list user A"
json_assert_session_case "$RESPONSE_BODY" "$session_id" "$case_id" >/dev/null || fail "history list user A：没有找到带 case_id 的 session"
pass "history contains case_id"

# 7. repeat save returns already_saved
http_json POST "/api/ai/consult/session/${session_id}/save-case" '{"patient_name":"Smoke乐乐","species":"dog","sex":"M","age_info":"4y"}' "$token_a"
expect_status 200 "repeat save consult"
repeat_msg="$(json_get "$RESPONSE_BODY" "message")"
repeat_case_id="$(json_get "$RESPONSE_BODY" "case_id")"
[[ "$repeat_msg" == "already_saved" ]] || fail "repeat save：期望 already_saved，实际 $repeat_msg"
[[ "$repeat_case_id" == "$case_id" ]] || fail "repeat save：case_id 不一致"
pass "repeat save returns already_saved"

# 8. continue consult and update bound case
answer_2="今天仍有干呕，腹部紧张，精神比昨天更差"
question_2="今天症状是否缓解？腹部触诊和精神状态如何？"
http_json POST "/api/ai/consult/session/${session_id}/answer" "{\"question\":\"${question_2}\",\"answer\":\"${answer_2}\"}" "$token_a"
expect_status 200 "continue consult"

http_json POST "/api/ai/consult/session/${session_id}/update-case" "" "$token_a"
expect_status 200 "update bound case"
update_msg="$(json_get "$RESPONSE_BODY" "message")"
[[ "$update_msg" == "updated" ]] || fail "update bound case：message 应为 updated，实际 $update_msg"

# 9. read case detail and confirm updated history
http_json GET "/api/cases/${case_id}" "" "$token_a"
expect_status 200 "read user A case"
json_assert_text_contains "$RESPONSE_BODY" "history" "$answer_2" >/dev/null || fail "case detail：history 未包含继续追问内容"
json_assert_text_contains "$RESPONSE_BODY" "analysis" "风险" >/dev/null || fail "case detail：analysis 未包含风险信息"
pass "case detail contains updated consult"

# 10. signup/login user B
http_json POST "/auth/signup" "{\"email\":\"${email_b}\",\"password\":\"${PASSWORD}\",\"full_name\":\"Smoke B\"}"
expect_status 200 "signup user B"

http_form "/auth/login" "username=${email_b}&password=${PASSWORD}"
expect_status 200 "login user B"
token_b="$(json_get "$RESPONSE_BODY" "access_token")"
[[ -n "$token_b" ]] || fail "login user B：没有 access_token"

# 11. user B cannot see/read user A session
http_json GET "/api/ai/consult/sessions?limit=20" "" "$token_b"
expect_status 200 "history list user B"
json_assert_not_contains_session "$RESPONSE_BODY" "$session_id" >/dev/null || fail "user B history：看到了 user A session"
pass "user B cannot see user A session"

http_json GET "/api/ai/consult/session/${session_id}" "" "$token_b"
expect_status 404 "user B cannot read user A session"

# 12. user B cannot read/update/delete/reanalyze user A case
http_json GET "/api/cases/${case_id}" "" "$token_b"
expect_status 404 "user B cannot read user A case"

http_json PUT "/api/cases/${case_id}" '{"patient_name":"非法修改"}' "$token_b"
expect_status 404 "user B cannot update user A case"

http_json POST "/api/cases/${case_id}/analyze" '{"chief_complaint":"非法重分析"}' "$token_b"
expect_status 404 "user B cannot reanalyze user A case"

http_json DELETE "/api/cases/${case_id}" "" "$token_b"
expect_status 404 "user B cannot delete user A case"

echo
echo "ALL PASS"
echo "Created smoke artifacts:"
echo "  user A: $email_a"
echo "  user B: $email_b"
echo "  session_id: $session_id"
echo "  case_id: $case_id"
