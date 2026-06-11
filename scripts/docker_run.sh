#!/usr/bin/env bash
# Run hal_agent inside Docker. The whole repo is bind-mounted at /app, so code
# edits on the host take effect with no rebuild and all outputs (agent_output/,
# evaluation/, databases/, chunked_datasheets/) are written straight to the host.
#
# Usage:
#   scripts/docker_run.sh build                 # build (or rebuild) the image
#   scripts/docker_run.sh preprocess <pdf> <dev>  # build the local vector DB from a datasheet
#   scripts/docker_run.sh s0 [args...]          # run the full pipeline (long-running)
#   scripts/docker_run.sh shell                 # interactive shell for testing
#   scripts/docker_run.sh run <args...>         # run an arbitrary `python ...` command
#
# Examples:
#   scripts/docker_run.sh preprocess devices/stm/rm0041/rm0041.pdf rm0041
#   scripts/docker_run.sh s0 --devices rm0041 --coverage-improver-iterations 0
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

IMAGE="${HAL_AGENT_IMAGE:-hal_agent:latest}"

image_exists() { docker image inspect "$IMAGE" >/dev/null 2>&1; }

build() {
  echo ">> building $IMAGE"
  docker build -t "$IMAGE" "$REPO_ROOT"
}

# Assemble the common `docker run` invocation. Host dirs are created first so
# Docker doesn't make them root-owned. Models are cached under .docker_cache/.
docker_run() {
  if [[ ! -f .env ]]; then
    echo "!! .env not found — copy .env.example to .env and fill in your keys" >&2
    exit 1
  fi
  if ! image_exists; then build; fi

  mkdir -p databases chunked_datasheets agent_output evaluation .docker_cache/hf .docker_cache/fastembed

  local interactive=()
  [[ -t 0 && -t 1 ]] && interactive=(-it)

  exec docker run --rm "${interactive[@]}" \
    --env-file .env \
    -v "$REPO_ROOT":/app \
    -v "$REPO_ROOT/.docker_cache":/cache \
    -w /app \
    "$IMAGE" "$@"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  build)      build ;;
  preprocess)
    # preprocess <pdf_path> <device_name> [extra pipeline args]
    pdf="${1:?need <pdf_path>}"; dev="${2:?need <device_name>}"; shift 2 || true
    docker_run python context_retrieval/preprocessing/pipeline.py \
      "$pdf" "$dev" --format markdown --embed-metadata --backend local "$@" ;;
  s0)         docker_run python core/s0_run_full_analysis.py "$@" ;;
  shell)      docker_run bash ;;
  run)        docker_run python "$@" ;;
  ""|-h|--help)
    sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
  *)
    echo "unknown command: $cmd (try: build | preprocess | s0 | shell | run)" >&2
    exit 1 ;;
esac
