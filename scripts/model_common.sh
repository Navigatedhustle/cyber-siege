#!/usr/bin/env bash
# Source from repo root. Never change the shared Docker daemon.
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export HF_HOME="$REPO_ROOT/runtime/huggingface"
export HF_HUB_CACHE="$HF_HOME/hub"
export PATH="$REPO_ROOT/scripts/container-bin:$PATH"
source "$REPO_ROOT/config/model-images.sh"
if ! /usr/bin/docker info >/dev/null 2>&1; then
  if [[ ${CYBER_DOCKER_GROUP:-0} != 1 ]]; then
    export CYBER_DOCKER_GROUP=1
    exec sg docker -c "bash '$0'"
  fi
  echo 'Docker unavailable; check account membership. Shared daemon is left untouched.' >&2
  exit 1
fi
if ! /usr/bin/docker info --format '{{json .Runtimes}}' | /usr/bin/python3 -c 'import json,sys;sys.exit(0 if "nvidia" in json.load(sys.stdin) else 1)'; then
  export CYBER_GPU_DIRECT=1
fi
