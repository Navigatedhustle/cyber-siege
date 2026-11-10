#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python || ! -f .env ]]; then
  bash scripts/setup.sh
fi
exec .venv/bin/python scripts/start.py "$@"
