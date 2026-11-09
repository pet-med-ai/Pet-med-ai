#!/bin/bash
set -euo pipefail
kit_root="$(cd "$(dirname "$0")/.." && pwd -P)"
cd "$kit_root"
if [[ "$(uname -s)" != Darwin ]]; then
  echo '此启动入口用于 Mac；Linux 使用 Python CLI。'
  exit 1
fi
kit_python="$(command -v python3.11 || true)"
if [[ -z "$kit_python" ]]; then
  echo '需要 Python 3.11；安装命令：brew install python@3.11'
  exit 1
fi
if [[ ! -x .acceptance-venv/bin/python ]]; then
  "$kit_python" -m venv .acceptance-venv
fi
if [[ ! -f .acceptance-venv/dependencies-ready ]]; then
  .acceptance-venv/bin/python -m pip install -r requirements.txt -r backend/requirements.txt
  touch .acceptance-venv/dependencies-ready
fi
if [[ "${1:-serve}" == serve ]]; then
  if [[ ! -d frontend/node_modules ]]; then
    (cd frontend && npm ci)
  fi
  exec .acceptance-venv/bin/python scripts/treatment_acceptance.py serve --open-safari
else
  exec .acceptance-venv/bin/python scripts/treatment_acceptance.py "$@"
fi
