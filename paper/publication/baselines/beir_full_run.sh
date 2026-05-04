#!/usr/bin/env bash
# BEIR TREC-COVID Full Evaluation Run
# Closes C5 (external validity, single-corpus).
# Paper section: §5.3 Cross-corpus generalization
#
# Pipeline:
#   1. build-db   — 50K subset from cached BEIR corpus
#   2. convert-queries — 50 TREC-COVID queries → eval harness JSONL
#   3. bm25-fts5  — BM25 via FTS5 (Anserini-equivalent, no JVM needed)
#   4. e5-embed   — multilingual-e5-base embeddings + dense retrieval
#   5. compare    — print Table 3 for §5.3
#
# Guardrails (lesson 2026-05-04 VPS alert):
#   - nice -n 19 + ionice -c 3 + cpulimit --limit=200 (2 cores)
#   - progress logged to /var/log/nox-mem/beir-progress.log every 5min
#   - run inside tmux session beir-trec
#
# Kill-switch cron (set up separately):
#   */30 * * * * root /usr/local/bin/beir-kill-if-overload.sh
#
# Usage: launch from tmux:
#   tmux new-session -d -s beir-trec 'bash /root/beir-baselines/beir_full_run.sh 2>&1 | tee /var/log/nox-mem/beir-full-run.log'
#
# Monitor:
#   tmux attach -t beir-trec
#   tail -f /var/log/nox-mem/beir-progress.log
#   tail -f /var/log/nox-mem/beir-full-run.log

set -euo pipefail

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VENV="/root/beir-adapter-venv"
PY="${VENV}/bin/python"
BASELINES_DIR="/root/beir-baselines"
CACHE_DIR="$HOME/.cache/beir"
RESULTS_DIR="/root/beir-results"
LOG_FILE="/var/log/nox-mem/beir-progress.log"

TEMP_DB="/tmp/nox-mem-trec-covid.db"
EVAL_QUERIES="/tmp/trec-covid-eval-queries.jsonl"
BM25_RESULTS="${RESULTS_DIR}/baselines-bm25-beir.jsonl"
E5_NPZ="${RESULTS_DIR}/e5-trec-covid.npz"
E5_RESULTS="${RESULTS_DIR}/baselines-e5-beir.jsonl"
COMPARE_CSV="${RESULTS_DIR}/baselines-comparison-beir.csv"

CORPUS="${CACHE_DIR}/trec-covid/corpus.jsonl"
QUERIES="${CACHE_DIR}/trec-covid/queries.jsonl"
QRELS="${CACHE_DIR}/trec-covid/qrels/test.tsv"

SUBSET_SIZE=50000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_progress() {
    local msg="$1"
    local ts
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "${ts} | ${msg}" | tee -a "${LOG_FILE}"
}

die() {
    log_progress "FATAL: $1"
    exit 1
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

mkdir -p "${RESULTS_DIR}" /var/log/nox-mem
log_progress "=== BEIR TREC-COVID full run started ==="
log_progress "PID=$$, subset=${SUBSET_SIZE}, results=${RESULTS_DIR}"

# Verify corpus cache exists (should never download — we have it)
[[ -f "${CORPUS}" ]]   || die "corpus.jsonl not found at ${CORPUS}"
[[ -f "${QUERIES}" ]]  || die "queries.jsonl not found at ${QUERIES}"
[[ -f "${QRELS}" ]]    || die "qrels/test.tsv not found at ${QRELS}"

log_progress "Corpus cache verified"

# ---------------------------------------------------------------------------
# Phase 1: Build TEMP DB (50K subset, ~2-3 min)
# ---------------------------------------------------------------------------

log_progress "Phase 1: build-db subset=${SUBSET_SIZE}"

if [[ -f "${TEMP_DB}" ]]; then
    log_progress "TEMP DB already exists — checking row count..."
    ROW_COUNT=$("${PY}" -c "import sqlite3; conn=sqlite3.connect('${TEMP_DB}'); print(conn.execute('SELECT COUNT(*) FROM chunks').fetchone()[0])" 2>/dev/null || echo 0)
    log_progress "Existing TEMP DB: ${ROW_COUNT} rows"
    if [[ "${ROW_COUNT}" -lt 45000 ]]; then
        log_progress "Row count below threshold — recreating TEMP DB"
        rm -f "${TEMP_DB}"
    else
        log_progress "TEMP DB OK — skipping rebuild"
    fi
fi

if [[ ! -f "${TEMP_DB}" ]]; then
    nice -n 19 ionice -c 3 \
        "${PY}" "${BASELINES_DIR}/beir_trec_covid_adapter.py" build-db \
            --corpus "${CORPUS}" \
            --qrels  "${QRELS}" \
            --db     "${TEMP_DB}" \
            --subset-size "${SUBSET_SIZE}" \
        || die "build-db failed"
    log_progress "Phase 1 complete: TEMP DB built at ${TEMP_DB}"
else
    log_progress "Phase 1 skipped (TEMP DB exists)"
fi

# ---------------------------------------------------------------------------
# Phase 2: Convert queries to eval harness format (~10 s)
# ---------------------------------------------------------------------------

log_progress "Phase 2: convert-queries"

nice -n 19 ionice -c 3 \
    "${PY}" "${BASELINES_DIR}/beir_trec_covid_adapter.py" convert-queries \
        --queries "${QUERIES}" \
        --qrels   "${QRELS}" \
        --db      "${TEMP_DB}" \
        --output  "${EVAL_QUERIES}" \
    || die "convert-queries failed"

log_progress "Phase 2 complete: ${EVAL_QUERIES}"

# ---------------------------------------------------------------------------
# Phase 3: BM25 baseline via FTS5 (pure SQLite, no JVM)
# ---------------------------------------------------------------------------

log_progress "Phase 3: BM25-FTS5 baseline"

nice -n 19 ionice -c 3 \
    "${PY}" "${BASELINES_DIR}/beir_bm25_fts5.py" \
        --db      "${TEMP_DB}" \
        --queries "${EVAL_QUERIES}" \
        --output  "${BM25_RESULTS}" \
    || die "BM25-FTS5 baseline failed"

log_progress "Phase 3 complete: BM25 results at ${BM25_RESULTS}"

# ---------------------------------------------------------------------------
# Phase 4: multilingual-e5-base dense baseline (~3-6 h on CPU, 2 cores)
# ---------------------------------------------------------------------------

log_progress "Phase 4: e5-multilingual-base embed + eval"
log_progress "ETA: 3-6 hours on 2 cores (50K docs × 768d)"

nice -n 19 ionice -c 3 \
    cpulimit --limit=200 -m -- \
    "${PY}" "${BASELINES_DIR}/beir_e5_runner.py" \
        --db      "${TEMP_DB}" \
        --queries "${EVAL_QUERIES}" \
        --npz     "${E5_NPZ}" \
        --output  "${E5_RESULTS}" \
    || die "e5 baseline failed"

log_progress "Phase 4 complete: e5 results at ${E5_RESULTS}"

# ---------------------------------------------------------------------------
# Phase 5: Compare (print Table 3 for §5.3)
# ---------------------------------------------------------------------------

log_progress "Phase 5: compare"

"${PY}" "${BASELINES_DIR}/beir_trec_covid_adapter.py" compare \
    --nox  "${E5_RESULTS}" \
    --bm25 "${BM25_RESULTS}" \
    --csv  "${COMPARE_CSV}" \
    || die "compare failed"

log_progress "=== BEIR TREC-COVID run COMPLETE === results at ${RESULTS_DIR}"
