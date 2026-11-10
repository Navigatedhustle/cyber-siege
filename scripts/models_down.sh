#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/model_common.sh
# Infinity is explicitly managed only through its vendor launcher.
if (cd vendor/infinity && ./run.sh status) >/dev/null 2>&1; then
  (cd vendor/infinity && ./run.sh stop)
fi
name=cyber-siege-challenger
if docker inspect "$name" >/dev/null 2>&1; then
  [[ $(docker inspect --format '{{index .Config.Labels "cyber-siege.repo"}}' "$name") == "$REPO_ROOT" ]] || { echo 'Refusing to stop container owned elsewhere'; exit 1; }
  docker stop --timeout 120 "$name"
fi
# Never remove images, model caches or volumes.
