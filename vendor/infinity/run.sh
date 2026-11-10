#!/usr/bin/env bash
set -euo pipefail

action=${1:-run}
if (($#)); then shift; fi
name=${HP_CONTAINER_NAME:-hp-nemotron-serve}
candidate=${RELEASE_CANDIDATE:-1}
[[ "$candidate" =~ ^[0-9]+$ ]] || { echo "RELEASE_CANDIDATE must be non-negative" >&2; exit 2; }
image=${HP_PRODUCTION_IMAGE:-public.ecr.aws/s8i0z9d5/prod/infinity-nemotron-3-super-120b-nvfp4:1.3.0rc24-rc${candidate}}
stop_timeout=${HP_STOP_TIMEOUT:-120}
case "$action" in
  stop)
    docker stop --timeout "$stop_timeout" "$name"
    docker container rm "$name"
    exit 0
    ;;
  status) exec docker inspect --format '{{json .State}}' "$name" ;;
  logs) exec docker logs -f "$name" ;;
  run) ;;
  *) echo "usage: bash run.sh [run|stop|status|logs] [server options]" >&2; exit 2 ;;
esac

hf_home=${HF_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/huggingface}
hf_hub_cache=${HF_HUB_CACHE:-$hf_home/hub}
model_cache=${HP_MODEL_CACHE:-$hf_hub_cache/models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4}
revision=${HP_MODEL_REVISION:-ff433f5493e25d631c9f12b5d55c674229923d02}
[[ -r "$model_cache/snapshots/$revision/config.json" ]] || {
  echo "missing model snapshot: $model_cache/snapshots/$revision" >&2
  exit 2
}
docker image inspect "$image" >/dev/null
replace=0
if docker container inspect "$name" >/dev/null 2>&1; then
  [[ ${HP_RECREATE:-0} == 1 ]] || {
    echo "container $name already exists; stop it first or set HP_RECREATE=1" >&2
    exit 2
  }
  replace=1
fi

args=(run -d --name "$name" --gpus "device=${HP_GPU_DEVICE:-0}"
  --user 10001:10001 --read-only --cap-drop ALL --cap-add SYS_NICE
  --security-opt no-new-privileges=true --init --stop-timeout "$stop_timeout"
  --restart "${HP_RESTART_POLICY:-unless-stopped}" --ipc private
  --shm-size "${HP_SHM_SIZE:-2g}" --ulimit memlock=-1:-1
  --tmpfs "/tmp:rw,nosuid,nodev,exec,size=${HP_TMPFS_SIZE:-8g},mode=1777"
  --mount "type=bind,src=$model_cache,dst=/model-cache,readonly"
  -e "MODEL_PATH=/model-cache/snapshots/$revision"
  -e "PORT=${PORT:-8000}")
shared_blobs=$(dirname "$model_cache")/blobs
if [[ -d "$shared_blobs" ]]; then
  args+=(--mount "type=bind,src=$shared_blobs,dst=/blobs,readonly")
fi
for variable in MAX_BATCH_SIZE MAX_NUM_TOKENS MAX_INPUT_LEN MAX_SEQ_LEN; do
  if [[ -v "$variable" ]]; then
    args+=(-e "$variable=${!variable}")
  fi
done
for variable in HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY http_proxy https_proxy all_proxy no_proxy; do
  if [[ -v "$variable" ]]; then
    args+=(-e "$variable")
  fi
done
if [[ -n ${HP_RUNTIME_CACHE:-} ]]; then
  [[ -d "$HP_RUNTIME_CACHE" && $(stat -c %u "$HP_RUNTIME_CACHE") == 10001 ]] || {
    echo "HP_RUNTIME_CACHE must be an existing service-owned directory (UID 10001)" >&2
    exit 2
  }
  args+=(--mount "type=bind,src=$HP_RUNTIME_CACHE,dst=/work/cache")
else
  volume=${HP_CACHE_VOLUME:-hp-trtllm-rc${candidate}-cache}
  docker volume create "$volume" >/dev/null
  args+=(--mount "type=volume,src=$volume,dst=/work/cache")
fi
case ${HP_NETWORK_MODE:-bridge} in
  bridge)
    args+=(-e "HOST=${HOST:-0.0.0.0}" -p "${HP_BIND_ADDRESS:-127.0.0.1}:${HP_HOST_PORT:-8000}:${PORT:-8000}")
    ;;
  host) args+=(--network host -e "HOST=${HOST:-127.0.0.1}") ;;
  *) echo "HP_NETWORK_MODE must be bridge or host" >&2; exit 2 ;;
esac
[[ -z ${HP_MEMORY_LIMIT:-} ]] || args+=(--memory "$HP_MEMORY_LIMIT")
[[ -z ${HP_PIDS_LIMIT:-} ]] || args+=(--pids-limit "$HP_PIDS_LIMIT")
if [[ "$replace" == 1 ]]; then
  if [[ $(docker inspect --format '{{.State.Running}}' "$name") == true ]]; then
    docker stop --timeout "$stop_timeout" "$name"
  fi
  docker container rm "$name"
fi
exec docker "${args[@]}" "$image" "$@"

