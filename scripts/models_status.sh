#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/model_common.sh
(cd vendor/infinity && ./run.sh status) || true
docker inspect --format '{{json .State}}' cyber-siege-challenger 2>/dev/null || true
for port in 8000 8001; do
  echo "Loopback model endpoint $port"
  curl --max-time 4 -sf "http://127.0.0.1:$port/v1/models" || true
  echo
done
