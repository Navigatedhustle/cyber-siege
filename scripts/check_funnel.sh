#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
url=$(.venv/bin/python -c 'from app.config import settings; print(settings.public_base_url)')
[[ "$url" == https://* ]] || { echo 'PUBLIC_BASE_URL must be a public HTTPS URL for Funnel verification'; exit 1; }
curl --fail --max-time 15 "$url/health" | .venv/bin/python -c 'import json,sys; data=json.load(sys.stdin); assert data["status"]=="ok"; print("Public application health verified. Models and metrics remain loopback only.")'
