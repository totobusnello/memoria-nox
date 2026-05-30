#!/bin/bash
# Backbone Matrix bench — orchestrator (2026-05-29).
#
# Revised plan (2026-05-29, after preflight pivots):
#   1) gemini-3-flash-preview (5 batches; cheapest, runs first)
#   2) gemini-2.5-pro (batch 004 only — frontier-pro single-batch sample for budget)
#
# Skipped backbones (documented as blockers):
#   - gpt-5 / gpt-5-mini: OpenAI quota exhausted mid-session (insufficient_quota
#     hit between initial preflight and smoke run). Adapter patch is shipped
#     and validated for reasoning-family models; rerun when quota refreshes.
#   - claude-sonnet-4-6 + claude-opus-4-7: ANTHROPIC_API_KEY missing in env
#     (ANTHROPIC_MAX_API_KEY is OAuth/MAX session token — using for batch
#     automation = account-policy violation per platform classifier).
#
# Expected wallclock: ~5-6h sequential (gemini-3-flash ~2h, gemini-2.5-pro 1-batch ~30min)
# Expected cost: ~$8 cap total (gemini-3-flash ~$5, gemini-2.5-pro 1-batch ~$2-3)
#
# Usage:
#   WORK=/root/.openclaw/backbone-matrix-<uuid> bash run-backbone-matrix.sh

set -uo pipefail

WORK="${WORK:?WORK env var must be set}"
LOG="$WORK/backbone-matrix.log"
mkdir -p "$WORK"

echo "[BB-MATRIX-ORCH] starting at $(date -u +%FT%TZ)" | tee -a "$LOG"
echo "[BB-MATRIX-ORCH] WORK=$WORK"  | tee -a "$LOG"

run_backbone() {
    local backbone="$1"
    local batches_env="$2"
    echo "" | tee -a "$LOG"
    echo "===========================================================" | tee -a "$LOG"
    echo "[BB-MATRIX-ORCH] === START $backbone (batches=$batches_env) ===" | tee -a "$LOG"
    echo "===========================================================" | tee -a "$LOG"
    BACKBONE="$backbone" BATCHES_ENV="$batches_env" WORK="$WORK" \
        bash "$WORK/run-parallel-backbone-matrix.sh" 2>&1 | tee -a "$LOG"
    local rc=${PIPESTATUS[0]}
    echo "[BB-MATRIX-ORCH] === END $backbone rc=$rc ===" | tee -a "$LOG"
    return $rc
}

# Phase 1: gemini-3-flash-preview (5-batch, smoke validated 63.90% Overall on batch 004)
run_backbone "gemini-3-flash-preview" "004,005,010,011,016" || \
    echo "[BB-MATRIX-ORCH] WARN gemini-3-flash-preview partial fail" | tee -a "$LOG"

# Phase 2: gemini-2.5-pro single-batch sample (budget-conscious; flag as sample, not 5-batch)
# Frontier-pro Gemini family; uses reasoning tokens (max_tokens raised to 4000 in pipeline).
run_backbone "gemini-2.5-pro" "004" || \
    echo "[BB-MATRIX-ORCH] WARN gemini-2.5-pro sample fail" | tee -a "$LOG"

echo "[BB-MATRIX-ORCH] all backbones done at $(date -u +%FT%TZ)" | tee -a "$LOG"
echo "[BB-MATRIX-ORCH] aggregating..."  | tee -a "$LOG"

python3 "$WORK/aggregate_backbone_matrix.py" \
    --json "$WORK/RESULTS-BACKBONE-MATRIX.json" \
    --md "$WORK/RESULTS-BACKBONE-MATRIX.md" 2>&1 | tee -a "$LOG"

echo "[BB-MATRIX-ORCH] FINAL artifacts: $WORK/RESULTS-BACKBONE-MATRIX.{md,json}" | tee -a "$LOG"
