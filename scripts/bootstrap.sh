#!/usr/bin/env bash
# One-shot setup for a fresh clone on a new machine:
#   1. restore device datasheets/SVDs from the GitHub release
#   2. build the Docker image
#   3. regenerate the local vector DB for the default device from its PDF
#
# Prerequisites: docker, gh (authenticated: `gh auth login`), python3.
#
# Usage:
#   scripts/bootstrap.sh                 # default device (rm0041)
#   scripts/bootstrap.sh rm0008          # a different device
#   scripts/bootstrap.sh --skip-preprocess   # assets + image only
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

DEVICE="rm0041"
PDF="devices/stm/rm0041/rm0041.pdf"
SKIP_PREPROCESS=0
for arg in "$@"; do
  case "$arg" in
    --skip-preprocess) SKIP_PREPROCESS=1 ;;
    rm0041) DEVICE=rm0041; PDF="devices/stm/rm0041/rm0041.pdf" ;;
    *) echo "note: device '$arg' — pass its PDF path with docker_run.sh preprocess if it differs from the default layout" ;;
  esac
done

command -v docker >/dev/null || { echo "!! docker not found"; exit 1; }
command -v gh >/dev/null     || { echo "!! gh (GitHub CLI) not found — needed to download device assets"; exit 1; }

# --- .env ---
if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ">> created .env from .env.example — fill in OPENAI_API_KEY / GROQ_API_KEY before running the pipeline"
fi

# --- 1. restore datasheets/SVDs from the release ---
echo ">> restoring device assets from GitHub release (tag: device-assets)"
python3 scripts/unpack_device_assets.py --tag device-assets

# --- 2. build the image ---
scripts/docker_run.sh build

# --- 3. regenerate the local vector DB from the PDF ---
if [[ "$SKIP_PREPROCESS" -eq 1 ]]; then
  echo ">> skipping preprocessing (--skip-preprocess)"
else
  if grep -q '^OPENAI_API_KEY=$' .env; then
    echo "!! OPENAI_API_KEY is empty in .env — skipping preprocessing."
    echo "   Fill it in, then run: scripts/docker_run.sh preprocess $PDF $DEVICE"
  else
    echo ">> building local vector DB for $DEVICE from $PDF"
    scripts/docker_run.sh preprocess "$PDF" "$DEVICE"
  fi
fi

cat <<EOF

Done. Next:
  scripts/docker_run.sh s0 --devices $DEVICE      # full pipeline (long-running)
  scripts/docker_run.sh shell                     # interactive testing
Outputs are written to agent_output/ and evaluation/ on the host.
EOF
