#!/usr/bin/env bash
# One-shot team setup: .venv (Python 3.12) + deps + free-dog-sdk in vendor/ + .env.
# Safe to re-run. Run it BEFORE connecting to the dog's Wi-Fi (it needs Internet).
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3.12}"
FREE_DOG_SDK_URL="https://github.com/Bin4ry/free-dog-sdk"
FREE_DOG_SDK_REV="0ececb5ed3b04c6bd88dbdc40c89db86bedc6543"   # pinned, tested 2026-11-04
MENAGERIE_URL="https://github.com/google-deepmind/mujoco_menagerie"
MENAGERIE_REV="98a70c569c4c1b6da467a20012f766ee1f8dc521"      # pinned 2026-11-04 (models: unitree_go1, universal_robots_ur5e)

if ! command -v "$PY" >/dev/null 2>&1; then
  echo "ERROR: $PY not found. macOS: brew install python@3.12 | Ubuntu: apt install python3.12 python3.12-venv"
  echo "       Or point to another interpreter: PYTHON=/path/to/python3.12 $0"
  exit 1
fi

echo "==> venv (.venv) with $("$PY" --version)"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

echo "==> free-dog-sdk -> vendor/free-dog-sdk @ ${FREE_DOG_SDK_REV:0:7}"
mkdir -p vendor
[ -d vendor/free-dog-sdk/.git ] || git clone -q "$FREE_DOG_SDK_URL" vendor/free-dog-sdk
git -C vendor/free-dog-sdk checkout -q "$FREE_DOG_SDK_REV"

echo "==> mujoco_menagerie -> vendor/mujoco_menagerie @ ${MENAGERIE_REV:0:7}"
if [ ! -d vendor/mujoco_menagerie/.git ]; then
  git clone -q --filter=blob:none --no-checkout "$MENAGERIE_URL" vendor/mujoco_menagerie
fi
git -C vendor/mujoco_menagerie checkout -q "$MENAGERIE_REV"

# Make `import ucl` work from anywhere inside the venv.
SITE="$(.venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')"
echo "$PWD/vendor/free-dog-sdk" > "$SITE/free_dog_sdk.pth"

if [ ! -f .env ]; then cp .env.example .env; echo "==> created .env (fill in XAI_API_KEY)"; fi

echo "==> smoke test"
.venv/bin/python - <<'PY'
import ucl.highCmd, ucl.unitreeConnection, ucl.enums  # free-dog-sdk
import xai_sdk, openai, dotenv, websockets  # noqa: F401
import mujoco
print("imports ok: free-dog-sdk (ucl), xai_sdk, openai, dotenv, websockets, mujoco", mujoco.__version__)
PY
.venv/bin/python src/sim/check_mujoco.py && echo "mujoco sim ok (src/sim/check_mujoco.py)"
.venv/bin/python src/dog/walk1m.py --distance 0.2 </dev/null >/dev/null && echo "mock dog walk ok (src/dog/walk1m.py)"

echo
echo "Done. Next: source .venv/bin/activate && python src/dog/walk1m.py   (mock)"
echo "      Simulazione: mjpython src/sim/view.py go1   (viewer MuJoCo; su macOS serve mjpython)"
