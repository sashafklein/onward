#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if python3 -m pytest --version >/dev/null 2>&1; then
  echo "[test] running pytest"
  PYTHONPATH=src python3 -m pytest
  exit 0
fi

echo "[test] pytest is not installed in this environment"
echo "[test] running dogfood e2e smoke check instead"
"${ROOT_DIR}/scripts/dogfood/e2e.sh"
echo "[test] install pytest for full suite: pip install -e .[dev]"
