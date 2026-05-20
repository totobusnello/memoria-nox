#!/usr/bin/env bash
# G5 ablation matrix — post-Wave-A-fixes (PRs #150 + #151)
#
# Mede a contribuição real de cada componente da boost stack pós:
#   - salience refactor multiplicativo → aditivo evidence-weighted (PR #150)
#   - tier_boost DEFAULT OFF (PR #150)
#   - source_type backfill (PR #151) — 67,949 chunks de NULL → mapeados
#
# Lições do G4 (incident memory `agent_stall_on_multi_phase_pipelines`):
#   - DB pre-staged (clone do prod isolado), não re-ingest
#   - Manual SSH (Agent tool stalls em pipelines com >3 fases sequenciais)
#   - Tmux + script standalone (nohup/systemd-run inline falham)
#   - Per-config restart + curl health gate antes do eval
#
# Pre-requisites:
#   1. PR #150 + #151 deployed (rsync staged-1.7a/edits/ → src/, tsc, restart)
#   2. Backfill source_type executado em prod (nox-mem backfill-source-type)
#   3. DB clone isolado em $EVAL_DB (NOX_DB_PATH override mandatory)
#   4. queries.jsonl idêntico ao G4 (n=100 entity-flavored)
#
# Usage (SSH manual no VPS):
#   ssh root@srv1465941
#   cd /root/.openclaw/workspace/tools/nox-mem
#   # 1. Clone DB isolado:
#   mkdir -p /root/.openclaw/workspace/eval-data/g5-2026-05-20
#   cp nox-mem.db /root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db
#   # 2. Run:
#   bash /tmp/run-g5.sh

set -euo pipefail

EVAL_DB="${EVAL_DB:-/root/.openclaw/workspace/eval-data/g5-2026-05-20/g5.db}"
API="${API:-http://127.0.0.1:18803}"
QUERIES="${QUERIES:-/root/.openclaw/workspace/eval-data/g3-rerun-2026-05-19/queries.jsonl}"
RESULTS="${RESULTS:-/tmp/g5-results.log}"
NOX_DIR="${NOX_DIR:-/root/.openclaw/workspace/tools/nox-mem}"
EVAL_PY="${EVAL_PY:-/tmp/g5-eval.py}"
API_PORT="${API_PORT:-18803}"

# Sanity: required files exist
for f in "$EVAL_DB" "$QUERIES" "$EVAL_PY" "$NOX_DIR/dist/api-server.js"; do
  [ -e "$f" ] || { echo "MISSING: $f"; exit 1; }
done

# Sanity: NOX_DB_PATH guard — bail if eval DB resolves to prod
PROD_DB="/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
if [ "$(realpath "$EVAL_DB")" = "$(realpath "$PROD_DB")" ]; then
  echo "REFUSE: EVAL_DB resolves to prod DB. ISOLATE FIRST."
  exit 2
fi

> "$RESULTS"
echo "G5 ablation — $(date -u +%Y-%m-%dT%H:%M:%SZ)" | tee -a "$RESULTS"
echo "EVAL_DB=$EVAL_DB" | tee -a "$RESULTS"
echo "QUERIES=$QUERIES" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"

# ─── Config matrix ────────────────────────────────────────────────────────────
#
# Note: tier_boost is DEFAULT OFF (PR #150). To enable, use NOX_ENABLE_TIER_BOOST=1.
#       salience is DEFAULT shadow (no rank impact). To activate, NOX_SALIENCE_MODE=active.
#       Other boosts (type, source_type, section, recency) are DEFAULT ON.
#
# Configs:
#   A0  = FTS5 alone (all boosts disabled, semantic disabled)
#   A1  = Semantic alone (FTS5 disabled, all boosts disabled)
#   A2  = Hybrid sem boosts (RRF on, all boosts disabled)
#   A3  = section_boost only (others disabled)
#   A4  = BOOST_TYPES only
#   A5  = source_type only — NOW ALIVE post-backfill (compare to G4 A5=0.4817 INERT)
#   A6  = tier_boost only (with NOX_ENABLE_TIER_BOOST=1)
#   A7  = Full + salience SHADOW (compare to A8 active)
#   A8  = Full + salience ACTIVE (CANONICAL prod config, compare to G4 A8=0.5702)
#   A9  = Full + salience ACTIVE + tier_boost ENABLED (test if backfill changes A6 verdict)
#   A10 = Full sem source_type (isolate post-backfill contribution)
#   A11 = Full sem section_boost (sanity: should drop most given A3 was peak)

declare -A CONFIGS
CONFIGS[A0]="NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_DISABLE_FTS5=0 NOX_SALIENCE_MODE=off"
CONFIGS[A1]="NOX_DISABLE_FTS5=1 NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A2]="NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A3]="NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A4]="NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A5]="NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A6]="NOX_ENABLE_TIER_BOOST=1 NOX_DISABLE_TYPE_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_RECENCY_BOOST=1 NOX_SALIENCE_MODE=off"
CONFIGS[A7]="NOX_SALIENCE_MODE=shadow"
CONFIGS[A8]="NOX_SALIENCE_MODE=active"
CONFIGS[A9]="NOX_ENABLE_TIER_BOOST=1 NOX_SALIENCE_MODE=active"
CONFIGS[A10]="NOX_DISABLE_SOURCE_TYPE_BOOST=1 NOX_SALIENCE_MODE=active"
CONFIGS[A11]="NOX_DISABLE_SECTION_BOOST=1 NOX_SALIENCE_MODE=active"

# ─── Execute matrix ───────────────────────────────────────────────────────────

for cfg in A0 A1 A2 A3 A4 A5 A6 A7 A8 A9 A10 A11; do
  echo "=== Starting $cfg ===" | tee -a "$RESULTS"
  tmux kill-session -t g5-api 2>/dev/null || true
  sleep 2
  ENV_VARS="${CONFIGS[$cfg]}"
  echo "  env=$ENV_VARS" | tee -a "$RESULTS"

  tmux new-session -d -s g5-api \
    "cd $NOX_DIR && set -a; . /root/.openclaw/.env; set +a; \
     NOX_DB_PATH=$EVAL_DB NOX_API_PORT=$API_PORT $ENV_VARS \
     node dist/api-server.js 2>/tmp/g5-api-$cfg.log"
  sleep 5

  HEALTH=$(curl -s --max-time 5 "$API/api/health" 2>/dev/null || echo "")
  CHUNKS=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('chunks',{}).get('total','?'))" 2>/dev/null || echo "API_NOT_UP")
  echo "  health.chunks.total=$CHUNKS" | tee -a "$RESULTS"
  if [ "$CHUNKS" = "API_NOT_UP" ] || [ "$CHUNKS" = "?" ]; then
    echo "CFG=$cfg SKIPPED — API not up" | tee -a "$RESULTS"
    continue
  fi

  timeout 180 python3 "$EVAL_PY" "$API" "$QUERIES" "$cfg" 2>>"$RESULTS" | tee -a "$RESULTS"
done

tmux kill-session -t g5-api 2>/dev/null || true

echo "" | tee -a "$RESULTS"
echo "=== SUMMARY ===" | tee -a "$RESULTS"
grep "^CFG=" "$RESULTS" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"
echo "G4 baselines for comparison (canonical):" | tee -a "$RESULTS"
echo "  A0 FTS5 alone      = 0.4817" | tee -a "$RESULTS"
echo "  A1 Semantic alone  = 0.5702" | tee -a "$RESULTS"
echo "  A2 Hybrid no boost = 0.5739" | tee -a "$RESULTS"
echo "  A3 section only    = 0.6222 (peak)" | tee -a "$RESULTS"
echo "  A5 source_type     = 0.4817 (INERT — pre backfill)" | tee -a "$RESULTS"
echo "  A6 tier only       = 0.4616 (piora vs A0!)" | tee -a "$RESULTS"
echo "  A7 full + shadow   = 0.5805" | tee -a "$RESULTS"
echo "  A8 full + active   = 0.5702 (canonical)" | tee -a "$RESULTS"
echo "" | tee -a "$RESULTS"
echo "Expected G5 outcomes:" | tee -a "$RESULTS"
echo "  - A5'  > A0 (source_type now alive)" | tee -a "$RESULTS"
echo "  - A8'  > G4 A8=0.5702 (salience aditivo + source_type alive)" | tee -a "$RESULTS"
echo "  - A8'  > A7' (active beats shadow with new formula)" | tee -a "$RESULTS"
echo "  - A9'  ≤ A8' (tier still over-promotes, confirms PR #150 decision)" | tee -a "$RESULTS"
echo "  - A10' < A8' by ~+source_type-contribution (isolated post-backfill)" | tee -a "$RESULTS"
echo "  - A11' << A8' (section drop is biggest hit, matches G4 A3 peak)" | tee -a "$RESULTS"
