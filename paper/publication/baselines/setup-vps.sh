#!/bin/bash
# Setup VPS para baselines paper (Pyserini BM25 + BGE-M3 dense + BEIR).
# Idempotente: reentrante seguro, skip de etapas já feitas.
# Roda em /root/paper-experiments/ (isolado de /root/.openclaw/).
# Dependências: apt access (JDK 21), python3.13 system, ~6-8GB disk.

set -euo pipefail

LOG="/var/log/nox-paper-setup.log"
WORKDIR="/root/paper-experiments"
VENV="$WORKDIR/venv"

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

log "=== START paper baseline setup ==="

# 1. JDK 21 (Pyserini requirement)
if ! command -v java >/dev/null 2>&1; then
    log "[1/5] Installing JDK 21..."
    apt-get update -qq >>"$LOG" 2>&1
    apt-get install -y openjdk-21-jdk-headless >>"$LOG" 2>&1
    log "[1/5] JDK installed: $(java -version 2>&1 | head -1)"
else
    log "[1/5] JDK already present: $(java -version 2>&1 | head -1)"
fi

# 2. Workdir
log "[2/5] Workdir at $WORKDIR"
mkdir -p "$WORKDIR"
cd "$WORKDIR"

# 3. Venv Python 3.13
if [ ! -d "$VENV" ]; then
    log "[3/5] Creating venv (python3.13)..."
    python3 -m venv "$VENV" >>"$LOG" 2>&1
    log "[3/5] Venv created at $VENV"
else
    log "[3/5] Venv exists at $VENV"
fi

# shellcheck source=/dev/null
source "$VENV/bin/activate"

# 4. Upgrade pip + base deps
log "[4/5] Upgrading pip + installing base deps..."
pip install -q --upgrade pip wheel setuptools >>"$LOG" 2>&1

# Install in groups so partial failure logs cleanly
log "[4/5a] Installing Pyserini (BM25 baseline)..."
pip install -q 'pyserini==0.36.0' >>"$LOG" 2>&1 || {
    log "[4/5a] WARN: pyserini install failed — see $LOG"
}

log "[4/5b] Installing FlagEmbedding (BGE-M3 baseline)..."
pip install -q 'FlagEmbedding==1.2.10' >>"$LOG" 2>&1 || {
    log "[4/5b] WARN: FlagEmbedding install failed"
}

log "[4/5c] Installing BEIR (external corpora)..."
pip install -q 'beir==2.0.0' 'datasets' >>"$LOG" 2>&1 || {
    log "[4/5c] WARN: beir install failed"
}

log "[4/5d] Installing utility deps (numpy/scipy/torch already pulled transitively)..."
pip install -q jsonlines tqdm >>"$LOG" 2>&1 || true

# 5. Smoke test
log "[5/5] Smoke testing imports..."
python3 -c "
import sys
errors = []
try:
    from pyserini.search.lucene import LuceneSearcher; print('[OK] pyserini')
except Exception as e: errors.append(f'pyserini: {e}'); print(f'[FAIL] pyserini: {e}')
try:
    from FlagEmbedding import BGEM3FlagModel; print('[OK] FlagEmbedding')
except Exception as e: errors.append(f'FlagEmbedding: {e}'); print(f'[FAIL] FlagEmbedding: {e}')
try:
    import beir; print(f'[OK] beir {beir.__version__}')
except Exception as e: errors.append(f'beir: {e}'); print(f'[FAIL] beir: {e}')
sys.exit(1 if errors else 0)
" 2>&1 | tee -a "$LOG"

SMOKE_EXIT=${PIPESTATUS[0]}

log "=== END setup. Smoke exit=$SMOKE_EXIT ==="
log "Disk after setup: $(df -h /root | tail -1)"

if [ "$SMOKE_EXIT" -eq 0 ]; then
    log "✅ READY. To use: source $VENV/bin/activate"
else
    log "⚠️  PARTIAL. Check $LOG for failed packages."
fi

exit $SMOKE_EXIT
