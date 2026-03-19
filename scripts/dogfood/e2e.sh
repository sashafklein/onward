#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BOOTSTRAP_SCRIPT="${ROOT_DIR}/scripts/dogfood/bootstrap.sh"
APP_DIR="${ROOT_DIR}/.dogfood/consumer-app"
VENV_BIN="${APP_DIR}/.venv/bin"

echo "[e2e] bootstrapping dogfood workspace"
"${BOOTSTRAP_SCRIPT}" >/dev/null

# shellcheck disable=SC1091
source "${VENV_BIN}/activate"

run() {
  "$@"
}

assert_contains() {
  local haystack="$1"
  local needle="$2"
  if [[ "${haystack}" != *"${needle}"* ]]; then
    echo "[e2e] assertion failed: expected output to contain '${needle}'"
    exit 1
  fi
}

echo "[e2e] doctor"
DOCTOR_OUT="$(run train doctor --root "${APP_DIR}")"
assert_contains "${DOCTOR_OUT}" "Doctor check passed"

echo "[e2e] create chunk + task"
CHUNK_CREATE_OUT="$(run train new --root "${APP_DIR}" chunk PLAN-001 "E2E Chunk" --description "created by e2e")"
CHUNK_ID="$(echo "${CHUNK_CREATE_OUT}" | awk '{print $2}')"
TASK_CREATE_OUT="$(run train new --root "${APP_DIR}" task "${CHUNK_ID}" "E2E Task" --description "created by e2e")"
TASK_ID="$(echo "${TASK_CREATE_OUT}" | awk '{print $2}')"

echo "[e2e] list"
LIST_OUT="$(run train list --root "${APP_DIR}")"
assert_contains "${LIST_OUT}" "PLAN-001"
assert_contains "${LIST_OUT}" "${CHUNK_ID}"
assert_contains "${LIST_OUT}" "${TASK_ID}"

echo "[e2e] show"
SHOW_OUT="$(run train show --root "${APP_DIR}" "${TASK_ID}")"
assert_contains "${SHOW_OUT}" "# ${TASK_ID}"
assert_contains "${SHOW_OUT}" "type: task"
assert_contains "${SHOW_OUT}" "status: open"

echo "[e2e] PASS"
