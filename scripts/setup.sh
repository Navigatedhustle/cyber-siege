#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p runtime exports runtime/tmp runtime/pip-cache runtime/app-cache
export TMPDIR="$PWD/runtime/tmp"
export PIP_CACHE_DIR="$PWD/runtime/pip-cache"
export XDG_CACHE_HOME="$PWD/runtime/app-cache"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv || true
fi
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  curl -fL https://bootstrap.pypa.io/get-pip.py -o runtime/get-pip.py
  .venv/bin/python runtime/get-pip.py
fi
.venv/bin/python -m pip install -r requirements.lock
if [[ ! -f .env ]]; then
  cp .env.example .env
  .venv/bin/python - <<'PY'
from pathlib import Path
p=Path('.env')
p.chmod(0o600)
PY
fi
.venv/bin/python scripts/generate_dataset.py
