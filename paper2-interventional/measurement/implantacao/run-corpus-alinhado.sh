#!/bin/bash
# Cadência horária. READ-ONLY (só le /proc e stat). Vigia §10.10.
set -uo pipefail
exec /root/.openclaw/scripts/p2/gatilho-corpus-alinhado.sh \
  --status /var/lib/nox-mem/p2/status-corpus-alinhado.txt \
  --ndjson /var/lib/nox-mem/p2/gatilhos.ndjson
