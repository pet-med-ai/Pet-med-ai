#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://pet-med-ai-backend.onrender.com}"
FRONTEND_URL="${FRONTEND_URL:-https://pet-med-ai-frontend-static.onrender.com}"
KEEP_TMP="${KEEP_TMP:-0}"

TMP_DIR="$(mktemp -d 2>/dev/null || mktemp -d -t petmed_smoke)"
cleanup() {
  if [ "${KEEP_TMP}" = "1" ]; then
    echo "[smoke_petmed] kept tmp: ${TMP_DIR}"
  else
    rm -rf "${TMP_DIR}"
  fi
}
trap cleanup EXIT

VERSION_JSON="${TMP_DIR}/system_version.json"
FLAGS_JSON="${TMP_DIR}/feature_flags.json"
FRONTEND_HTML="${TMP_DIR}/frontend.html"

printf '%s\n' "[smoke_petmed] backend version: ${BASE_URL}/api/system/version"
curl -fsS "${BASE_URL}/api/system/version" -o "${VERSION_JSON}"
python3 - "${VERSION_JSON}" <<'PY_VERSION_CHECK'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

expected = {
    "database_revision": "0009_diag_data",
    "alembic_head": "0009_diag_data",
    "schema_ok": True,
    "writes_database": False,
    "exposes_database_url": False,
}

errors = []
for key, value in expected.items():
    if data.get(key) != value:
        errors.append("{0}: expected {1!r}, got {2!r}".format(key, value, data.get(key)))

migration_errors = data.get("migration_errors")
if migration_errors != []:
    errors.append("migration_errors: expected [], got {0!r}".format(migration_errors))

if errors:
    print("NO-GO: production system version hard gate failed")
    for error in errors:
        print(error)
    sys.exit(1)

print("PASS: system version hard gate")
print("database_revision=0009_diag_data")
print("alembic_head=0009_diag_data")
print("schema_ok=true")
print("migration_errors=[]")
print("writes_database=false")
print("exposes_database_url=false")
PY_VERSION_CHECK

printf '%s\n' "[smoke_petmed] feature flags: ${BASE_URL}/api/system/feature-flags"
curl -fsS "${BASE_URL}/api/system/feature-flags" -o "${FLAGS_JSON}"
python3 - "${FLAGS_JSON}" <<'PY_FLAGS_CHECK'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    data = json.load(handle)

flags = data.get("flags", {})
keys = [
    "ENABLE_EMR_REAL_IMPORT",
    "ENABLE_EMR_IMPORT_CASE_UPDATE",
    "ENABLE_EMR_ATTACHMENT_DOWNLOAD",
    "ENABLE_PREVENTIVE_AUTO_DELIVERY",
    "ENABLE_PREVENTIVE_SMS_DELIVERY",
    "ENABLE_PREVENTIVE_WECHAT_DELIVERY",
    "ENABLE_PREVENTIVE_EMAIL_DELIVERY",
    "ENABLE_PRESCRIPTION_STRUCTURED_WRITE",
    "ENABLE_DEVICE_REAL_INGEST",
    "ENABLE_BILLING_REAL_WRITE",
]

bad = []
missing = []
for key in keys:
    if key not in flags:
        print("{0} MISSING".format(key))
        missing.append(key)
        continue
    raw_value = flags[key]
    if isinstance(raw_value, dict):
        value = raw_value.get("enabled")
    else:
        value = raw_value
    print("{0} {1}".format(key, value))
    if value is not False:
        bad.append(key)

print("MISSING= {0}".format(missing))
print("NOT_FALSE= {0}".format(bad))
if bad or missing:
    print("NO-GO: dangerous feature flags are not all disabled")
    sys.exit(1)

print("PASS: dangerous feature flags disabled")
PY_FLAGS_CHECK

if [ -n "${FRONTEND_URL}" ]; then
  printf '%s\n' "[smoke_petmed] frontend reachable: ${FRONTEND_URL}"
  curl -fsSL "${FRONTEND_URL}" -o "${FRONTEND_HTML}"
  test -s "${FRONTEND_HTML}" || { echo "NO-GO: frontend response is empty" >&2; exit 1; }
  printf '%s\n' "PASS: frontend reachable"
fi

printf '%s\n' "ALL PASS: smoke_petmed"
printf '%s\n' "read_only=true"
printf '%s\n' "no DB write"
printf '%s\n' "dangerous_feature_flags_disabled=true"
printf '%s\n' "decision=GO_TO_CONFIRMED_DIAGNOSIS_TREATMENT_FRAMEWORK_DRAFT_V1"
