#!/bin/bash
# Cadência horária. READ-ONLY. NÃO sonda /api/brief.
set -uo pipefail
set -a; . /root/.openclaw/.env 2>/dev/null; set +a
exec node /root/.openclaw/scripts/p2/gatilho-composicao.mjs \
  --raiz /root/.openclaw/workspace/tools/nox-mem \
  --corpus /var/lib/nox-mem/epochs/current.db \
  --agentes nox,atlas,boris,cipher,forge,lex \
  --status /var/lib/nox-mem/p2/status-composicao.txt \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
