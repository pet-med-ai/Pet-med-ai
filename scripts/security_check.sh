#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "== Pet-Med-AI security check V1 =="
echo "Mode: report-only. Review findings manually."

RG_EXCLUDES=(
  --glob '!.git/**'
  --glob '!node_modules/**'
  --glob '!frontend/node_modules/**'
  --glob '!frontend/dist/**'
  --glob '!dist/**'
  --glob '!build/**'
  --glob '!*.png'
  --glob '!*.jpg'
  --glob '!*.jpeg'
  --glob '!*.gif'
  --glob '!*.pdf'
  --glob '!*.docx'
  --glob '!*.sqlite'
  --glob '!*.db'
)

if ! command -v rg >/dev/null 2>&1; then
  echo "WARN: ripgrep (rg) not installed. Install with: brew install ripgrep"
  echo "Skipping deep source scan."
  exit 0
fi

echo
echo "== 1) Secret echo / print scan =="
rg -n --hidden "${RG_EXCLUDES[@]}" -i 'print\(.*(SECRET|TOKEN|KEY|PASSWORD)|echo .*(SECRET|TOKEN|KEY|PASSWORD)' . || true

echo
echo "== 2) Common hardcoded credential patterns =="
rg -n --hidden "${RG_EXCLUDES[@]}" -i '(ghp_[0-9A-Za-z]{36,})|(github_pat_[0-9A-Za-z_]{20,})|(AKIA[0-9A-Z]{16})|(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})' . || true

echo
echo "== 3) render.yaml secret marker scan =="
if [[ -f render.yaml ]]; then
  rg -n --hidden -i 'secret|token|password|apikey|database_url' render.yaml || true
else
  echo "render.yaml not found"
fi

echo
echo "== 4) tracked sensitive filename scan =="
git ls-files | rg -n -i '(^|/)(\.env|.*\.pem|.*\.key|id_rsa|id_dsa|id_ed25519|credentials\.json)$' || true

echo
echo "== Done =="
echo "If any real secret value appears above, rotate it and remove it from git/logs."
exit 0
