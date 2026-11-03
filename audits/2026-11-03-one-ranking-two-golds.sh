#!/usr/bin/env bash
# Kimi's two open gaps on the PT-BR ruler (audits/2026-10-27-kimi-challenge-medicoes.md), on ONE ranking.
#
#   (a) per-query effect of corpus duplication: the corpus-wide rate (1.9%) says nothing about how many
#       of a query's 10 slots are copies of the same text; that needs the real top-10s.
#   (b) v2 -> v3 decomposition: Kimi asked to freeze the v3 rankings and swap the gold. The v3 per-query
#       rows are GONE — the audit said they "stay on the host under /var/tmp/score-v3-161128/out.json"
#       and that directory no longer exists — and the v2 rankings are in chunk ids the re-ingest retired.
#       So the decomposition is redone the only way left: one ranking of TODAY's corpus, scored with the
#       v2 gold and with the v3 gold, both resolved by anchor on the same copy. A difference between the
#       two scores is the gold, because the ranking is literally the same list.
#
# Isolation, as score-v3.sh: VACUUM INTO a copy, NOX_DB_PATH at the copy, trackAccess=false. Nothing
# writes to production. /var/tmp, never /tmp (tmpfs = RAM; the database is 1.6 GB).
# K=10 is the official run. K=20 is a second run used ONLY to refill slots a removed duplicate frees.
set -euo pipefail
set -a; source /root/.openclaw/.env; set +a
N=/root/.openclaw/workspace/tools/nox-mem
W=/var/tmp/kimi-gaps-$(date -u +%Y%m%dT%H%M%S)
mkdir -p "$W"
DB="$W/eval.db"
echo "workdir $W"
sqlite3 -readonly "$N/nox-mem.db" "VACUUM INTO '$DB';"
ls -la "$DB" | awk '{print "copy:", $5, "bytes"}'

cd /root/medicoes
for v in v2 v3; do
  GOLD_DB="$DB" python3 resolve-gold-anchors.py "golden-queries-$v.jsonl" "$W/resolve-$v.json" \
    > "$W/resolve-$v.log" 2>&1 || echo "resolver $v exit=$? (see log; structural ambiguity is non-fatal)"
  python3 - "$W/resolve-$v.json" "$W/map-$v.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); m = {}
for e in d["entries"]:
    if e["state"] in ("resolved", "moved", "ambiguous_structural", "ambiguous_duplicate"):
        m.setdefault(str(e["query_id"]), []).extend(e["resolved_ids"])
json.dump({k: sorted(set(v)) for k, v in m.items()}, open(sys.argv[2], "w"))
print(f"{sys.argv[1].rsplit('/',1)[-1]}: gold resolved for {len(m)} queries")
PY
done

cp /root/medicoes/run-gold-eval-v3.mjs "$W/run.mjs"
cd "$N"
for k in 10 20; do
  GOLD_K_EVAL=$k NOX_DB_PATH="$DB" NOX_DIST="$N/dist" node "$W/run.mjs" \
    /root/medicoes/golden-queries-v3.jsonl "$W/map-v3.json" "$W/out-k$k.json" > "$W/score-k$k.log" 2>&1 \
    || echo "harness k=$k exit=$?"
  grep -c "nDCG=" "$W/score-k$k.log" | sed "s/^/k=$k queries scored: /"
done
# texts of every ranked id, for the duplicate analysis — read from the COPY
python3 - "$W" <<'PY'
import json, sqlite3, sys
W = sys.argv[1]
ids = set()
for k in (10, 20):
    for r in json.load(open(f"{W}/out-k{k}.json"))["rows"]:
        ids.update(r.get("ranked") or [])
con = sqlite3.connect(f"file:{W}/eval.db?mode=ro", uri=True)
q = ",".join("?" * len(ids))
rows = con.execute(f"SELECT id, source_file, chunk_text FROM chunks WHERE id IN ({q})", list(ids)).fetchall()
json.dump({str(i): {"source_file": s, "text": t} for i, s, t in rows}, open(f"{W}/texts.json", "w"))
print(f"texts for {len(rows)} of {len(ids)} ranked ids")
PY
echo "done $W"
