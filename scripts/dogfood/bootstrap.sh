#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_DIR="${ROOT_DIR}/.dogfood/consumer-app"
VENV_DIR="${APP_DIR}/.venv"

mkdir -p "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  git -C "${APP_DIR}" init >/dev/null
fi

python3 -m venv "${VENV_DIR}"
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

SITE_PACKAGES="$(python -c 'import site; print(site.getsitepackages()[0])')"
echo "${ROOT_DIR}/src" > "${SITE_PACKAGES}/trains-local.pth"

cat > "${VENV_DIR}/bin/train" <<'TRAIN'
#!/usr/bin/env bash
set -euo pipefail
exec python -m trains.cli "$@"
TRAIN
chmod +x "${VENV_DIR}/bin/train"

train init --root "${APP_DIR}"

if ! train list --root "${APP_DIR}" | grep -q '^PLAN-'; then
  train new --root "${APP_DIR}" plan "Dogfood Trains Core Loop" --description "Use trains to build trains"
fi

echo
echo "Dogfood workspace ready: ${APP_DIR}"
echo "Activate with: source ${VENV_DIR}/bin/activate"
echo "Try: train list --root ${APP_DIR}"
