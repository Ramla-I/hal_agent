#!/usr/bin/env bash
#
# Run the headless Claude register-extraction baseline in Docker with BOTH:
#   * filesystem locked  -> only work/ is mounted (no host /tmp, repos, other runs)
#   * network locked      -> egress allowlist proxy; the container can reach ONLY
#                            api.anthropic.com (for the API), nothing else.
#
# Mirrors proctor's docker usage; uses the Nix rootless docker.
#
# Usage:  ./run-docker.sh [run-label]        (MODEL=, BUDGET=, IMAGE= overridable)
# Teardown proxy/networks when done:  ./run-docker.sh --teardown
#
set -euo pipefail
OUTER="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INNER="$OUTER/work"

# The working docker is the Nix rootless one, not the broken snap symlink.
DOCKER=""
for c in /nix/store/*docker-2*/bin/docker; do [ -x "$c" ] && DOCKER="$c" && break; done
[ -n "$DOCKER" ] || DOCKER="$(command -v docker || true)"
[ -n "$DOCKER" ] && "$DOCKER" info >/dev/null 2>&1 || { echo "error: no working docker (tried nix + PATH)" >&2; exit 1; }

IMAGE="${IMAGE:-rm0041-baseline:dev}"
MODEL="${MODEL:-claude-fable-5-1}"
BUDGET="${BUDGET:-100}"
NET_IN="rm0041-noegress"      # internal: no direct internet
NET_OUT="rm0041-egress"       # normal: proxy's path to the internet
PROXY="rm0041-egress-proxy"

teardown() {
  "$DOCKER" rm -f "$PROXY" 2>/dev/null || true
  "$DOCKER" network rm "$NET_IN" "$NET_OUT" 2>/dev/null || true
  echo "torn down proxy + networks"
}
[ "${1:-}" = "--teardown" ] && { teardown; exit 0; }

LABEL="${1:-$(date +%Y%m%d-%H%M%S)}"
OUT="$OUTER/runs/$LABEL"; mkdir -p "$OUT"
[ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "error: ANTHROPIC_API_KEY not set" >&2; exit 1; }

# Build the baseline image once (installs claude into a debian base).
if ! "$DOCKER" image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "building $IMAGE (once)..."
  "$DOCKER" build -t "$IMAGE" -f "$OUTER/Dockerfile" "$OUTER"
fi

# Ensure the two networks exist.
"$DOCKER" network inspect "$NET_IN"  >/dev/null 2>&1 || "$DOCKER" network create --internal "$NET_IN"
"$DOCKER" network inspect "$NET_OUT" >/dev/null 2>&1 || "$DOCKER" network create "$NET_OUT"

# Ensure the egress allowlist proxy is up (on both nets: internal to serve the
# baseline, egress to reach the internet). Reused across runs.
if ! "$DOCKER" ps --format '{{.Names}}' | grep -qx "$PROXY"; then
  "$DOCKER" rm -f "$PROXY" 2>/dev/null || true
  "$DOCKER" run -d --name "$PROXY" --network "$NET_IN" --restart unless-stopped \
    -v "$OUTER/squid.conf:/etc/squid/squid.conf:ro" ubuntu/squid:latest >/dev/null
  "$DOCKER" network connect "$NET_OUT" "$PROXY"
  sleep 3
fi

rm -rf "$INNER/register_info_rm0041"
echo "label=$LABEL model=$MODEL budget=\$$BUDGET  (fs: only work/;  net: only api.anthropic.com)"

# Baseline on the INTERNAL net (no direct internet); all traffic via the proxy.
"$DOCKER" run --rm --network "$NET_IN" \
  -e HTTPS_PROXY="http://$PROXY:3128" \
  -e HTTP_PROXY="http://$PROXY:3128" \
  -e NO_PROXY="" \
  -e ANTHROPIC_API_KEY \
  -v "$INNER":/work:rw -w /work \
  "$IMAGE" \
  claude -p "$(cat "$OUTER/prompt.md")" \
    --model "$MODEL" \
    --output-format json \
    --permission-mode dontAsk \
    --allowedTools "Read" "Glob" "Grep" "Edit" "Write" "Bash" "Task" \
    --disallowedTools "WebFetch" "WebSearch" \
    --max-budget-usd "$BUDGET" \
  > "$OUT/run.json"

# Container wrote as root; chown outputs back to you (throwaway root container).
"$DOCKER" run --rm --user root -v "$INNER":/work --entrypoint chown "$IMAGE" \
  -R "$(id -u):$(id -g)" /work 2>/dev/null || true

NREG=0
if [ -d "$INNER/register_info_rm0041" ]; then
  cp -r "$INNER/register_info_rm0041" "$OUT/"
  NREG=$(find "$OUT/register_info_rm0041" -maxdepth 1 -type f | wc -l | tr -d ' ')
fi
jq -r '.result // ""' "$OUT/run.json" > "$OUT/summary.txt"
jq -c --arg label "$LABEL" --arg model "$MODEL" --argjson nreg "$NREG" \
  '{label:$label,model:$model,registers_written:$nreg,input_tokens:(.usage.input_tokens//0),output_tokens:(.usage.output_tokens//0),cost_usd:(.total_cost_usd//null),duration_ms:(.duration_ms//null),num_turns:(.num_turns//null),is_error:(.is_error//null),model_usage:(.modelUsage//{}),subagent_stats:(.subagent_stats//null)}' \
  "$OUT/run.json" | tee -a "$OUTER/usage_log.jsonl"

echo "done. wrote $NREG register files -> $OUT/register_info_rm0041/"
