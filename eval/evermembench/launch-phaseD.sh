#!/bin/bash
# Launcher for Phase D batch 004 — activates venv
set -u
export WORK=/root/.openclaw/evermembench-phaseB-1779978778
export NOX_ADAPTER_MODE=phaseB
cd "$WORK"
# Activate venv so 'python' resolves
source "$WORK/venv/bin/activate"
which python
python --version
bash "$WORK/run-batch-phaseD.sh" 004 18810
