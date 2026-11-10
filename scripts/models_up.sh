#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/model_common.sh
[[ -f "$HF_HUB_CACHE/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4/snapshots/ff433f5493e25d631c9f12b5d55c674229923d02/config.json" ]] || { echo 'Pinned hero weights missing; see RUNBOOK'; exit 1; }
.venv/bin/python scripts/release_download_cache.py
bash scripts/start_challenger.sh
wait_for() {
  local port=$1
  for ((i=0;i<240;i++)); do
    if curl -sf --max-time 3 "http://127.0.0.1:$port/health" >/dev/null; then return 0; fi
    sleep 10
  done
  echo "Model $port failed readiness after 40 minutes" >&2
  return 1
}
wait_for 8001
# Infinity reserves 80% of remaining free memory. Start after the capped challenger.
existing=$(cd vendor/infinity && ./run.sh status 2>/dev/null || true)
if [[ -n "$existing" ]]; then
  previous=$(python3 -c 'import json,sys; print(json.load(sys.stdin).get("Status",""))' <<< "$existing")
  if [[ "$previous" == exited || "$previous" == created ]]; then
    (cd vendor/infinity && ./run.sh stop)
    existing=''
  fi
fi
if [[ -z "$existing" ]]; then
  (cd vendor/infinity && HP_BIND_ADDRESS=127.0.0.1 MAX_BATCH_SIZE=64 MAX_NUM_TOKENS=16384 MAX_INPUT_LEN=8192 MAX_SEQ_LEN=12288 ./run.sh)
fi
for ((i=0;i<240;i++)); do
  state=$(cd vendor/infinity && ./run.sh status)
  if [[ $(python3 -c 'import json,sys; print(json.load(sys.stdin).get("Health",{}).get("Status",""))' <<< "$state") == healthy ]]; then
    .venv/bin/python scripts/record_model_processes.py
    echo 'Infinity container is healthy. Run warmup and gates before opening a live session.'
    exit 0
  fi
  if [[ $(python3 -c 'import json,sys; print(json.load(sys.stdin).get("Status",""))' <<< "$state") == exited ]]; then
    echo 'Infinity exited. Inspect with vendor/infinity/run.sh logs.' >&2
    exit 1
  fi
  sleep 10
done
echo 'Infinity did not reach healthy within 40 minutes. Inspect vendor logs.' >&2
exit 1
