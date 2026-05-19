#!/usr/bin/env bash
# Q1 LoCoMo ablation orchestrator — starts/stops the eval API on :18803 per
# config and runs locomo_ablation_eval.py against it. Outputs one JSON per
# ablation into $RESULTS_DIR.
#
# Designed for VPS srv1465941.hstgr.cloud — eval.db at /root/.openclaw/eval/locomo-prod-path/eval.db
# 2nd nox-mem instance bind to 18803 with NOX_DB_PATH override.
#
# Pre-reqs satisfied at top of this script:
#   - nox-mem source patched with NOX_DISABLE_BOOSTS / NOX_DISABLE_EXPANSION /
#     NOX_SEMANTIC_POOL_SIZE env-var toggles
#   - dist/ rebuilt
#   - /tmp/locomo10.json present (5882 turns LoCoMo corpus)
#
# Usage:
#   bash run_locomo_ablations.sh                    # all ablations
#   bash run_locomo_ablations.sh D_full_prod        # single ablation
set -euo pipefail

NOX_MEM_DIR="${NOX_MEM_DIR:-/root/.openclaw/workspace/tools/nox-mem}"
EVAL_DB="${EVAL_DB:-/root/.openclaw/eval/locomo-prod-path/eval.db}"
EVAL_PORT="${EVAL_PORT:-18803}"
EVAL_HOST="${EVAL_HOST:-127.0.0.1}"
RESULTS_DIR="${RESULTS_DIR:-/root/.openclaw/eval/q1-ablations}"
LOGS_DIR="${LOGS_DIR:-$RESULTS_DIR/logs}"
HARNESS="${HARNESS:-/root/.openclaw/eval/paper/baselines/locomo_ablation_eval.py}"

mkdir -p "$RESULTS_DIR" "$LOGS_DIR"

# Common API env (NOX_DB_PATH override + port).
# Note: .env exports happen at the caller (set -a; . /root/.openclaw/.env; set +a).
export NOX_DB_PATH="$EVAL_DB"
export NOX_API_PORT="$EVAL_PORT"
# Avoid double-writing the prod telemetry; the eval DB has its own meta table.
export NOX_SEARCH_LOG_TEXT="0"
# Reranker has no impact on eval (chunks too noisy); leave off explicitly for reproducibility.
export NOX_RERANKER_MODE="off"

# ─── ablation configs ───────────────────────────────────────────────────────
# Each ablation is: name|toggles (NAME=VAL,NAME=VAL...)
ABLATIONS=(
  "D_full_prod|"
  "B_no_boosts|NOX_DISABLE_BOOSTS=1"
  "C1_no_expansion|NOX_DISABLE_EXPANSION=1"
  "C2_pool_20|NOX_SEMANTIC_POOL_SIZE=20"
  "C3_no_expansion_pool_20|NOX_DISABLE_EXPANSION=1,NOX_SEMANTIC_POOL_SIZE=20"
  "E_fts5_only_via_pipeline|NOX_SEMANTIC_DISABLE=1,NOX_DISABLE_EXPANSION=1,NOX_DISABLE_BOOSTS=1"
  "F_semantic_only|NOX_FTS_DISABLE=1,NOX_DISABLE_EXPANSION=1,NOX_DISABLE_BOOSTS=1"
)

# Optional: filter to one
FILTER="${1:-}"

# ─── helpers ────────────────────────────────────────────────────────────────
wait_for_health() {
  local port="$1"
  local timeout="${2:-30}"
  local elapsed=0
  while [ $elapsed -lt $timeout ]; do
    if curl -s -o /dev/null -w '' --max-time 2 "http://${EVAL_HOST}:${port}/api/health" 2>/dev/null; then
      local chunks
      chunks=$(curl -s --max-time 2 "http://${EVAL_HOST}:${port}/api/health" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("chunks",{}).get("total",0))' 2>/dev/null || echo 0)
      if [ "$chunks" -gt 0 ]; then
        echo "[orchestrator] eval API up on :${port} with ${chunks} chunks (after ${elapsed}s)"
        return 0
      fi
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "[orchestrator][FATAL] eval API failed to come up on :${port} within ${timeout}s" >&2
  return 1
}

kill_eval_api() {
  # Kill any process on EVAL_PORT (graceful then KILL).
  local pids
  pids=$(ss -tlnp "sport = :${EVAL_PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)
  if [ -n "$pids" ]; then
    echo "[orchestrator] killing existing :${EVAL_PORT} pids: $pids"
    for pid in $pids; do
      kill -TERM "$pid" 2>/dev/null || true
    done
    sleep 2
    for pid in $pids; do
      if kill -0 "$pid" 2>/dev/null; then
        kill -KILL "$pid" 2>/dev/null || true
      fi
    done
    sleep 1
  fi
}

start_eval_api() {
  local toggles="$1"
  local label="$2"
  local log="$LOGS_DIR/api-${label}.log"

  kill_eval_api

  # Build env-var prefix.
  local env_prefix=""
  if [ -n "$toggles" ]; then
    IFS=',' read -ra kvs <<< "$toggles"
    for kv in "${kvs[@]}"; do
      env_prefix+="$kv "
    done
  fi

  echo "[orchestrator] starting eval API for ${label}: env: ${env_prefix:-(default)}"
  # nohup ensures it survives if shell exits; explicit env vars passed inline.
  (
    cd "$NOX_MEM_DIR"
    nohup env $env_prefix \
      NOX_DB_PATH="$EVAL_DB" \
      NOX_API_PORT="$EVAL_PORT" \
      NOX_SEARCH_LOG_TEXT=0 \
      NOX_RERANKER_MODE=off \
      GEMINI_API_KEY="${GEMINI_API_KEY}" \
      node dist/api-server.js >"$log" 2>&1 &
    echo "[orchestrator] api pid: $!"
  )

  wait_for_health "$EVAL_PORT" 30
}

# ─── main loop ──────────────────────────────────────────────────────────────
echo "[orchestrator] eval DB: $EVAL_DB"
echo "[orchestrator] results: $RESULTS_DIR"

OVERALL_START=$(date +%s)
RESULTS_INDEX="$RESULTS_DIR/index.txt"
: > "$RESULTS_INDEX"

for entry in "${ABLATIONS[@]}"; do
  label="${entry%%|*}"
  toggles="${entry##*|}"
  [ "$toggles" = "$label" ] && toggles=""

  if [ -n "$FILTER" ] && [ "$FILTER" != "$label" ]; then
    continue
  fi

  out="$RESULTS_DIR/${label}.json"
  echo ""
  echo "════════════════════════════════════════════════════════════════════════"
  echo "[orchestrator] ABLATION: $label   toggles: ${toggles:-(none)}"
  echo "════════════════════════════════════════════════════════════════════════"

  start_eval_api "$toggles" "$label"

  T0=$(date +%s)
  python3 "$HARNESS" --label "$label" --out "$out" --toggles "$toggles" \
    --endpoint "http://${EVAL_HOST}:${EVAL_PORT}/api/search" \
    || { echo "[orchestrator][FAIL] harness failed for $label"; continue; }
  T1=$(date +%s)
  echo "[orchestrator] $label done in $((T1 - T0))s"
  echo "$label|$((T1 - T0))s|$out" >> "$RESULTS_INDEX"

  # Show concise summary
  python3 -c "import json,sys; d=json.load(open('$out'))['summary']; print(f\"  D2={d['ndcg_at_10_D2']:.4f}  D1={d['ndcg_at_10_D1']:.4f}  MRR={d['mrr']:.4f}  Recall@10={d['recall_at_10']:.4f}\")"
done

kill_eval_api

OVERALL_END=$(date +%s)
echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "[orchestrator] ALL DONE in $((OVERALL_END - OVERALL_START))s"
echo "[orchestrator] results dir: $RESULTS_DIR"
echo "════════════════════════════════════════════════════════════════════════"
cat "$RESULTS_INDEX"
