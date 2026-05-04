#!/bin/bash
# Fix-up para falhas do setup-vps.sh inicial:
# - faiss-cpu missing (Pyserini transitive não veio)
# - FlagEmbedding 1.2.10 incompat com Python 3.13 (Optional import error)
# - BEIR pytrec_eval precisa gcc + python3-dev pra compilar wheel

set -euo pipefail

LOG="/var/log/nox-paper-setup.log"
WORKDIR="/root/paper-experiments"
VENV="$WORKDIR/venv"

log() { echo "[$(date -Iseconds)] FIX: $*" | tee -a "$LOG"; }

log "=== START fix-up ==="

# 1. Build deps pra pytrec_eval
log "[1/4] Installing build deps (gcc + python3-dev)..."
apt-get install -y -qq build-essential python3-dev >>"$LOG" 2>&1

# shellcheck source=/dev/null
source "$VENV/bin/activate"

# 2. faiss-cpu (Pyserini dense parts)
log "[2/4] Installing faiss-cpu..."
pip install -q faiss-cpu >>"$LOG" 2>&1 || log "[2/4] WARN: faiss-cpu failed"

# 3. FlagEmbedding latest (BGE-M3) — Python 3.13 compatible
log "[3/4] Upgrading FlagEmbedding to latest (drop pin 1.2.10)..."
pip uninstall -y -q FlagEmbedding 2>>"$LOG" || true
pip install -q --upgrade 'FlagEmbedding>=1.3.0' >>"$LOG" 2>&1 || {
    log "[3/4] WARN: FlagEmbedding latest failed, trying with peft override..."
    pip install -q FlagEmbedding peft transformers >>"$LOG" 2>&1 || log "[3/4] FAIL"
}

# 4. BEIR retry (now with build tools)
log "[4/4] BEIR retry with build tools..."
pip install -q 'beir==2.0.0' 'datasets' >>"$LOG" 2>&1 || {
    log "[4/4] beir 2.0.0 still failed, trying latest..."
    pip install -q beir datasets >>"$LOG" 2>&1 || log "[4/4] FAIL"
}

# Smoke test final
log "=== SMOKE TEST FINAL ==="
python3 -c "
import sys
ok = True
def chk(name, imp):
    global ok
    try: exec(imp); print(f'[OK] {name}')
    except Exception as e: ok = False; print(f'[FAIL] {name}: {e}')
chk('pyserini', 'from pyserini.search.lucene import LuceneSearcher')
chk('FlagEmbedding', 'from FlagEmbedding import BGEM3FlagModel')
chk('beir', 'import beir; print(\"  beir version:\", beir.__version__)')
chk('faiss', 'import faiss')
chk('datasets', 'import datasets')
sys.exit(0 if ok else 1)
" 2>&1 | tee -a "$LOG"

EXIT=${PIPESTATUS[0]}
log "Final smoke exit=$EXIT"
log "Disk: $(df -h /root | tail -1)"

if [ $EXIT -eq 0 ]; then
    log "✅ ALL READY — venv at $VENV"
else
    log "⚠️ Partial — check $LOG for failed packages"
fi

exit $EXIT
