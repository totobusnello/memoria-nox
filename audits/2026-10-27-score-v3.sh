#!/usr/bin/env bash
# Score ruler v3 on the production search path, isolated. Strict arm only — it
# needs no LLM, and it is the lower bound that gets quoted.
#
# Isolation, both layers the harness documents: NOX_DB_PATH points at a VACUUM
# INTO copy so every write lands there, and trackAccess=false so access_count is
# not bumped even inside the copy (it feeds salience, which is being scored).
#
# /var/tmp, never /tmp: /tmp on this VPS is tmpfs, i.e. RAM, and the database is
# 1.6 GB.
set -euo pipefail
N=/root/.openclaw/workspace/tools/nox-mem
W=/var/tmp/score-v3-$(date -u +%H%M%S)
mkdir -p "$W"
DB="$W/eval.db"

echo "== VACUUM INTO a copy (no write touches production)"
sqlite3 -readonly "$N/nox-mem.db" "VACUUM INTO '$DB';"
ls -la "$DB" | awk '{print "   copy:", $5, "bytes"}'

echo "== resolve gold ON THE COPY — ids minted elsewhere would not match"
cd /root/medicoes
GOLD_DB="$DB" python3 resolve-gold-anchors.py golden-queries-v3.jsonl "$W/resolve.json" \
  > "$W/resolve.log" 2>&1
echo "   resolver exit=$?"
grep -E "^  (resolved|moved|ambiguous|unresolved)" "$W/resolve.log" | sed 's/^/   /'

python3 - "$W/resolve.json" "$W/resolved-map.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
m = {}
for e in d["entries"]:
    if e["state"] in ("resolved", "moved", "ambiguous_structural", "ambiguous_duplicate"):
        m.setdefault(str(e["query_id"]), []).extend(e["resolved_ids"])
json.dump({k: sorted(set(v)) for k, v in m.items()}, open(sys.argv[2], "w"))
print(f"   gold resolved for {len(m)} queries, "
      f"{sum(len(v) for v in m.values())} chunk ids")
PY

echo "== score"
cp /root/medicoes/run-gold-eval-v3.mjs "$W/run.mjs"
cd "$N"
NOX_DB_PATH="$DB" NOX_DIST="$N/dist" node "$W/run.mjs" \
  /root/medicoes/golden-queries-v3.jsonl "$W/resolved-map.json" "$W/out.json" \
  > "$W/score.log" 2>&1 || echo "   harness exit=$?"
tail -32 "$W/score.log"
echo "== artefacts in $W"
