#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/model_common.sh
need_space() {
  local available
  available=$(df -B1 --output=avail . | tail -1)
  (( available >= $1*1024*1024*1024 )) || { echo "Need at least $1 GiB free before this download" >&2; exit 1; }
  df -h .
}
need_space 144
.venv/bin/hf download nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4 --revision ff433f5493e25d631c9f12b5d55c674229923d02 --cache-dir "$HF_HUB_CACHE"
# The supplied server runs as UID 10001. Only public model artifacts must be
# readable there; runtime databases, private configuration and credentials stay private.
.venv/bin/python scripts/public_model_permissions.py "$HF_HUB_CACHE"
need_space 80
docker pull "$HP_PRODUCTION_IMAGE"
need_space 100
.venv/bin/hf download openai/gpt-oss-120b --revision b5c939de8f754692c1647ca79fbf85e8c1e70f8a --cache-dir "$HF_HUB_CACHE"
need_space 50
docker pull "$CYBER_CHALLENGER_IMAGE"
mkdir -p runtime/vllm-cache
# Preserve the image's bundled vocabulary when binding our persistent cache.
docker run --rm --network none --entrypoint tar "$CYBER_CHALLENGER_IMAGE" -C /root/.cache -cf - tiktoken_cache > runtime/tiktoken-cache.tar
tar -xf runtime/tiktoken-cache.tar -C runtime/vllm-cache
.venv/bin/python scripts/release_download_cache.py
