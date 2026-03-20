#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${ROOT_DIR}/.dogfood/consumer-app"
VENV_DIR="${APP_DIR}/.venv"

die() {
  echo "dogfood bootstrap: $*" >&2
  exit 1
}

pick_python() {
  local cmd
  for cmd in python3.13 python3.12 python3.11 python3; do
    if command -v "${cmd}" >/dev/null 2>&1; then
      if "${cmd}" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        command -v "${cmd}"
        return 0
      fi
    fi
  done
  return 1
}

PY_BIN="$(pick_python)" || die "need Python 3.11+ on PATH (try python3.11, python3.12, or python3.13)"

mkdir -p "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" init >/dev/null
fi

recreate_venv=1
if [[ -x "${VENV_DIR}/bin/python" ]]; then
  if "${VENV_DIR}/bin/python" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    recreate_venv=0
  fi
fi

if [[ "${recreate_venv}" -eq 1 ]]; then
  rm -rf "${VENV_DIR}"
  "${PY_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

SITE_PACKAGES="$(python -c 'import site; print(site.getsitepackages()[0])')"
echo "${ROOT_DIR}/src" > "${SITE_PACKAGES}/onward-local.pth"

ONWARD_WRAPPER="${VENV_DIR}/bin/onward"
cat > "${ONWARD_WRAPPER}" <<'TRAIN'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${HERE}/python" -m onward.cli "$@"
TRAIN
chmod +x "${ONWARD_WRAPPER}"

onward init --root "${APP_DIR}"

if ! onward doctor --root "${APP_DIR}" >/dev/null; then
  echo "dogfood bootstrap: onward doctor failed; output:" >&2
  onward doctor --root "${APP_DIR}" >&2 || true
  exit 1
fi

if ! onward list --root "${APP_DIR}" | grep -q '^PLAN-'; then
  onward new --root "${APP_DIR}" plan "Dogfood Onward Core Loop" --description "Use onward to build onward"
fi

echo
echo "Dogfood workspace ready: ${APP_DIR}"
echo "Activate with: source ${VENV_DIR}/bin/activate"
echo "Try: onward list --root ${APP_DIR}"
