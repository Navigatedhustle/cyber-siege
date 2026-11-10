#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/model_common.sh
name=cyber-siege-challenger
image=$CYBER_CHALLENGER_IMAGE
if docker container inspect "$name" >/dev/null 2>&1; then
  [[ $(docker inspect --format '{{index .Config.Labels "cyber-siege.repo"}}' "$name") == "$REPO_ROOT" ]] || { echo 'Container name owned elsewhere'; exit 1; }
  docker start "$name" >/dev/null
  exit 0
fi
snapshot="$HF_HUB_CACHE/models--openai--gpt-oss-120b/snapshots/b5c939de8f754692c1647ca79fbf85e8c1e70f8a"
mkdir -p runtime/vllm-cache
if [[ ! -d runtime/vllm-cache/tiktoken_cache ]]; then
  docker run --rm --network none --entrypoint tar "$image" -C /root/.cache -cf - tiktoken_cache > runtime/tiktoken-cache.tar
  tar -xf runtime/tiktoken-cache.tar -C runtime/vllm-cache
fi
# Options verified using this image's vllm serve --help=all, retained in runtime/.
docker run -d --name "$name" --label "cyber-siege.repo=$REPO_ROOT" --label cyber-siege.profile=gptoss-memory032-v1 \
  --gpus device=0 --ipc private --shm-size 4g --restart unless-stopped \
  -p 127.0.0.1:8001:8000 \
  --mount "type=bind,src=$HF_HUB_CACHE,dst=/models,readonly" \
  --mount "type=bind,src=$REPO_ROOT/runtime/vllm-cache,dst=/root/.cache" \
  --entrypoint vllm "$image" serve \
  "/models/models--openai--gpt-oss-120b/snapshots/$(basename "$snapshot")" \
  --host 0.0.0.0 --port 8000 --served-model-name openai/gpt-oss-120b \
  --gpu-memory-utilization 0.32 --max-model-len 8192 --max-num-seqs 16
