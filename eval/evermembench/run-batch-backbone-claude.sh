#!/bin/bash
# Backbone Matrix — Claude Sonnet 4.6 — 5-batch parallel launcher (2026-06-28).
#
# Espelho de run-parallel-backbone-matrix.sh, hardcoded para Claude Sonnet 4.6.
# NÃO chama run-batch-backbone-matrix.sh (que não tem case Claude no preflight).
# Lógica per-batch embutida como subshells paralelos.
#
# Metodologia preservada de Phase H v2 (PR #377) + Backbone Matrix (PR que criou esta pasta):
#   - Phase B DBs pré-warmed (skip Add + Vectorize)
#   - top_k=20
#   - Rerank OFF (NOX_RERANKER_ENABLED=0)
#   - Adapter mode: phaseB (baseline; sem Wave A/B/C knobs)
#   - Judge constante: gemini-2.5-flash
#   - Gate canônico: 5-batch (n≈626/batch) + 95% CI — single-batch NÃO confiável
#
# PREREQS:
#   1. ANTHROPIC_API_KEY em /root/.openclaw/.env  (standard key, NÃO MAX OAuth)
#   2. GEMINI_API_KEY em /root/.openclaw/.env     (judge stays on gemini-2.5-flash)
#   3. pipeline-backbone-claude.yaml em $WORK/
#   4. Harness instalado em $WORK/everos/benchmarks/EverMemBench
#      (link: ln -sf /root/.openclaw/evermembench-phaseB-1779978778/everos $WORK/everos)
#   5. Phase B DBs nos paths canônicos (validados em PHASEB_DBS abaixo)
#
# Usage:
#   WORK=/root/.openclaw/backbone-matrix-claude-<ts> bash run-batch-backbone-claude.sh
#   WORK=... BATCHES_ENV="004,005" bash run-batch-backbone-claude.sh   # subset (smoke)
#
# Para Opus 4.7: editar BACKBONE + SLUG abaixo E pipeline-backbone-claude.yaml
#   (concurrency: 2, timeout: 600, max_tokens: 4000 no yaml; ~60-90min/batch esperado).
#
# NÃO EXECUTE AGORA — requer ANTHROPIC_API_KEY provisionada (ver RESULTS-BACKBONE-CLAUDE.md).

set -uo pipefail

BACKBONE="claude-sonnet-4-6"   # ← Opus 4.7: "claude-opus-4-7"
SLUG="claude"                   # ← slug do pipeline yaml + run dirs

WORK="${WORK:?WORK env var must be set}"
EVAL="$WORK/everos/benchmarks/EverMemBench"
PIPELINE_CFG="$EVAL/eval/config/pipeline.yaml"
PIPELINE_BAK="$WORK/pipeline.yaml.bak.bb-$SLUG"
PIPELINE_SRC="$WORK/pipeline-backbone-claude.yaml"

echo "[BB-CLAUDE] BACKBONE=$BACKBONE WORK=$WORK"

# Source prod env — garante ANTHROPIC_API_KEY + GEMINI_API_KEY
set -a; source /root/.openclaw/.env; set +a

# Activate venv (reuse phaseB harness install)
source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate
echo "[BB-CLAUDE] venv python: $(which python)"

# Validar keys obrigatórias
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[BB-CLAUDE] ERROR: ANTHROPIC_API_KEY ausente em /root/.openclaw/.env"
    echo "[BB-CLAUDE] LEMBRETE: ANTHROPIC_MAX_API_KEY (sk-ant-oat01-...) = MAX OAuth session"
    echo "[BB-CLAUDE]           NAO pode ser usado para bench automatizado (policy violation)."
    echo "[BB-CLAUDE]           Provisionar standard key em https://console.anthropic.com/"
    exit 1
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "[BB-CLAUDE] ERROR: GEMINI_API_KEY ausente (judge: gemini-2.5-flash)"; exit 1
fi

# Preflight: billing path Anthropic (native /v1/messages — formato nativo confirmado)
# NOTA: harness vai chamar /v1/chat/completions via OpenAI SDK. Preflight usa /v1/messages.
# Gap de formato — ver RESULTS-BACKBONE-CLAUDE.md §incertezas para smoke test recomendado.
echo "[BB-CLAUDE] === Preflight: $BACKBONE billing path (native /v1/messages) ==="
PREFLIGHT=$(curl -s --max-time 30 "https://api.anthropic.com/v1/messages" \
    -H "Content-Type: application/json" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -d '{"model":"claude-sonnet-4-6","max_tokens":5,"messages":[{"role":"user","content":"Reply only OK"}]}')

if ! echo "$PREFLIGHT" | grep -qi '"content"'; then
    echo "[BB-CLAUDE] ERROR: preflight /v1/messages falhou"
    echo "$PREFLIGHT" | head -c 600
    exit 1
fi
PREFLIGHT_TOKENS=$(echo "$PREFLIGHT" | python3 -c \
    'import json,sys; d=json.load(sys.stdin); u=d.get("usage",{}); print(u.get("input_tokens",0)+u.get("output_tokens",0))' \
    2>/dev/null || echo "?")
echo "[BB-CLAUDE] preflight /v1/messages OK (tokens=$PREFLIGHT_TOKENS)"
echo "[BB-CLAUDE] WARN: preflight usa x-api-key. Harness usa Authorization: Bearer."
echo "[BB-CLAUDE]   Se harness der erro no 1o answer call, confirmar Hipotese A vs B no yaml."

# Instalar pipeline.yaml
if [ ! -f "$PIPELINE_SRC" ]; then
    echo "[BB-CLAUDE] ERROR: $PIPELINE_SRC ausente — copiar pipeline-backbone-claude.yaml para WORK"; exit 1
fi
if [ ! -f "$PIPELINE_CFG" ]; then
    echo "[BB-CLAUDE] ERROR: $PIPELINE_CFG ausente — harness nao instalado?"; exit 1
fi
cp "$PIPELINE_CFG" "$PIPELINE_BAK"
cp "$PIPELINE_SRC" "$PIPELINE_CFG"
echo "[BB-CLAUDE] pipeline.yaml instalado (backup: $PIPELINE_BAK)"
echo "[BB-CLAUDE] answer.model = $(grep -A2 '^answer:' "$PIPELINE_CFG" | grep 'model:' | tr -d ' ')"

restore_pipeline() {
    if [ -f "$PIPELINE_BAK" ]; then
        cp "$PIPELINE_BAK" "$PIPELINE_CFG"
        echo "[BB-CLAUDE] pipeline.yaml restaurado"
    fi
}
trap restore_pipeline EXIT

# Batches + ports (mesmos da backbone matrix original)
BATCHES=(004 005 010 011 016)
PORTS=(18830 18831 18832 18833 18834)
declare -A PHASEB_DBS=(
    [004]=/root/.openclaw/evermembench-runs/phaseB-004-1779988559/nox-mem.db
    [005]=/root/.openclaw/evermembench-runs/phaseB-005-1779990311/nox-mem.db
    [010]=/root/.openclaw/evermembench-runs/phaseB-010-1779990316/nox-mem.db
    [011]=/root/.openclaw/evermembench-runs/phaseB-011-1779990322/nox-mem.db
    [016]=/root/.openclaw/evermembench-runs/phaseB-016-1779990327/nox-mem.db
)

if [ -n "${BATCHES_ENV:-}" ]; then
    IFS=',' read -r -a BATCHES <<< "$BATCHES_ENV"
    echo "[BB-CLAUDE] BATCHES_ENV override: ${BATCHES[*]}"
fi

TS=$(date +%s)
PIDS=()
RUN_DIRS=()

for i in "${!BATCHES[@]}"; do
    BATCH="${BATCHES[$i]}"
    PORT="${PORTS[$i]:-$((18830 + i))}"
    SRC_DB="${PHASEB_DBS[$BATCH]:-}"
    if [ -z "$SRC_DB" ] || [ ! -f "$SRC_DB" ]; then
        echo "[BB-CLAUDE] WARN: DB ausente para batch=$BATCH (path=$SRC_DB) — skipping"
        continue
    fi
    RUN_DIR="/root/.openclaw/evermembench-runs/backbone-$SLUG-$BATCH-$TS"
    mkdir -p "$RUN_DIR"
    cp "$SRC_DB" "$RUN_DIR/nox-mem.db"
    [ -f "${SRC_DB}-wal" ] && cp "${SRC_DB}-wal" "$RUN_DIR/nox-mem.db-wal" || true
    [ -f "${SRC_DB}-shm" ] && cp "${SRC_DB}-shm" "$RUN_DIR/nox-mem.db-shm" || true
    echo "[BB-CLAUDE] launch batch=$BATCH port=$PORT run=$RUN_DIR"

    # Per-batch subshell (captura BATCH, PORT, SRC_DB, RUN_DIR por closure)
    (
        set -uo pipefail
        LABEL="[BB-CLAUDE B$BATCH P$PORT]"

        # Re-source env no subshell (garante vars mesmo se env foi alterado)
        set -a; source /root/.openclaw/.env; set +a
        source /root/.openclaw/evermembench-phaseB-1779978778/venv/bin/activate

        # Variáveis de isolamento por run
        export NOX_DB_PATH="$RUN_DIR/nox-mem.db"
        export NOX_API_PORT="$PORT"
        export NOX_API_BASE="http://127.0.0.1:$PORT"
        export NOX_ADAPTER_MODE="${NOX_ADAPTER_MODE:-phaseB}"
        export NOX_RERANKER_ENABLED=0
        unset NOX_RERANKER_MODEL 2>/dev/null || true

        # LLM env para harness (base_url/api_key definidos no pipeline.yaml têm prioridade,
        # mas fallback env vars garantem que cli.py não rejeite por LLM_API_KEY ausente)
        export LLM_API_KEY="$ANTHROPIC_API_KEY"
        export LLM_BASE_URL="https://api.anthropic.com/v1/"

        echo "$LABEL NOX_DB_PATH=$NOX_DB_PATH"
        echo "$LABEL NOX_ADAPTER_MODE=$NOX_ADAPTER_MODE"

        # Verificar DB pré-warmed
        EXISTING_CHUNKS=$(sqlite3 "$NOX_DB_PATH" "SELECT COUNT(*) FROM chunks;" 2>/dev/null || echo 0)
        echo "$LABEL DB chunks=$EXISTING_CHUNKS"
        if [ "$EXISTING_CHUNKS" -lt 5000 ]; then
            echo "$LABEL ERROR: DB nao pre-warmed (chunks=$EXISTING_CHUNKS)"; exit 1
        fi

        # Cleanup api-server no exit do subshell
        API_PID=""
        cleanup_api() {
            if [ -n "$API_PID" ]; then
                kill "$API_PID" 2>/dev/null || true
                wait "$API_PID" 2>/dev/null || true
                echo "$LABEL killed api-server pid=$API_PID"
            fi
        }
        trap cleanup_api EXIT

        echo "$LABEL === Step 1: spawn isolated api-server ==="
        cd /root/.openclaw/workspace/tools/nox-mem
        nohup node --no-warnings dist/api-server.js > "$RUN_DIR/api.log" 2>&1 &
        API_PID=$!
        echo "$LABEL api pid=$API_PID, waiting 5s..."
        sleep 5

        HEALTH=$(curl -s --max-time 10 "$NOX_API_BASE/api/health" || true)
        if ! echo "$HEALTH" | grep -q '"chunks"'; then
            echo "$LABEL ERROR: api nao respondeu"
            echo "$HEALTH" | head -c 300
            exit 1
        fi
        TOTAL=$(echo "$HEALTH" | python3 -c \
            "import json,sys;d=json.load(sys.stdin);c=d['chunks'];print(c.get('total') if isinstance(c,dict) else c)" \
            2>/dev/null || echo "?")
        echo "$LABEL api health: chunks=$TOTAL"

        echo "$LABEL === Step 1b: clear stale harness results ==="
        RESULTS_DIR="$EVAL/eval/results/nox_mem"
        rm -f "$RESULTS_DIR/answer_results_$BATCH.json" \
              "$RESULTS_DIR/evaluation_results_$BATCH.json" \
              "$RESULTS_DIR/search_results_$BATCH.json"

        echo "$LABEL === Step 2: Search + Answer + Evaluate ==="
        cd "$EVAL"
        python -m eval.cli \
            --dataset "dataset/$BATCH/dialogue.json" \
            --qa "dataset/$BATCH/qa_$BATCH.json" \
            --system nox_mem \
            --user-id "$BATCH" \
            --stages search answer evaluate \
            --top-k 20 \
            > "$RUN_DIR/eval.log" 2>&1

        echo "$LABEL === Step 3: Analyze ==="
        RESULTS_FILE="$RESULTS_DIR/evaluation_results_$BATCH.json"
        if [ -f "$RESULTS_FILE" ]; then
            python tools/analyze_results.py "$RESULTS_FILE" > "$RUN_DIR/analysis.txt" 2>&1 || true
            cp "$RESULTS_FILE" "$RUN_DIR/results-batch-$BATCH.json"
            cp "$RESULTS_DIR/answer_results_$BATCH.json" \
               "$RUN_DIR/answer-results-batch-$BATCH.json" 2>/dev/null || true
            echo "$LABEL results → $RUN_DIR/results-batch-$BATCH.json"
        else
            echo "$LABEL ERROR: results file ausente em $RESULTS_FILE"
            ls "$RESULTS_DIR" 2>&1 || true
            exit 1
        fi
        echo "$LABEL === DONE ==="
        ls -la "$RUN_DIR/"
    ) > "$RUN_DIR/stream.log" 2>&1 &

    PIDS+=($!)
    RUN_DIRS+=("$RUN_DIR")
    sleep 3   # stagger de 3s por batch (padrão backbone matrix)
done

echo "[BB-CLAUDE] launched ${#PIDS[@]} batches — aguardando..."
RC_TOTAL=0
for idx in "${!PIDS[@]}"; do
    wait "${PIDS[$idx]}"
    rc=$?
    echo "[BB-CLAUDE] pid=${PIDS[$idx]} (batch ${BATCHES[$idx]}) exited rc=$rc"
    [ "$rc" -ne 0 ] && RC_TOTAL=1
done

echo "[BB-CLAUDE] === tails de analysis por batch ==="
for RUN_DIR in "${RUN_DIRS[@]}"; do
    echo "--- $RUN_DIR ---"
    tail -5 "$RUN_DIR/analysis.txt" 2>/dev/null || echo "  (sem analysis.txt)"
done

echo "[BB-CLAUDE] === DONE (rc=$RC_TOTAL) ==="
echo "[BB-CLAUDE] Agregar resultados:"
echo "[BB-CLAUDE]   python3 $WORK/aggregate_backbone_matrix.py --json $WORK/RESULTS-BACKBONE-CLAUDE.json --md $WORK/RESULTS-BACKBONE-CLAUDE.md"
exit $RC_TOTAL
