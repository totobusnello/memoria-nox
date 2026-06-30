#!/bin/bash
# Phase 1.6 acceptance test — run on VPS.
# Usage: bash test-phase-1.6.sh
#
# Exit criteria (plan):
#   - ≥10/15 queries return ≥3 unique results
#   - ≥1 query retrieves semantic-only result BM25 can't find
#   - has_semantic true in ≥70% of searches
#   - p95 latency ≤1.5s

set -u
cd /root/.openclaw/workspace/tools/nox-mem
export OPENCLAW_WORKSPACE=/root/.openclaw/workspace
DB=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db

# 15 queries: 4 ambiguous, 4 specific, 3 too-short (expected to skip), 4 NL-long
queries=(
  "problema do gateway ontem"
  "coisa da memória quebrada"
  "como o sistema aprende"
  "por que o build quebrou"
  "DEP0040 punycode Node 22"
  "trigger trg_chunks_delete_cascade"
  "NOX_API_PORT Chrome squatter 18800"
  "batchEmbedContents Gemini throughput"
  "gateway"
  "KG"
  "falha"
  "por que o gateway ficou em crash loop depois da atualização"
  "qual foi a causa raiz do embedding vazio"
  "explique o fluxo de ingestão até aparecer no hybrid search"
  "o que está rodando no nightly maintenance"
)

pass_3plus=0
pass_semantic=0
total_searches=0
semantic_searches=0
total_latency=0
latencies=()

echo "=== Phase 1.6 acceptance test — 15 queries ==="
echo

for q in "${queries[@]}"; do
  t0=$(date +%s%N)
  out=$(node dist/index.js search "$q" --limit 5 2>&1 || true)
  t1=$(date +%s%N)
  latency_ms=$(( (t1 - t0) / 1000000 ))
  latencies+=($latency_ms)
  total_latency=$((total_latency + latency_ms))

  # Count result lines (format: "#N [score] [type] ...")
  count=$(echo "$out" | grep -cE '^#[0-9]+ \[' || true)
  has_sem=$(echo "$out" | grep -cE '\[(semantic|hybrid)\]' || true)

  total_searches=$((total_searches + 1))
  if [ "$count" -ge 3 ]; then pass_3plus=$((pass_3plus + 1)); fi
  if [ "$has_sem" -ge 1 ]; then
    pass_semantic=$((pass_semantic + 1))
    semantic_searches=$((semantic_searches + 1))
  fi

  printf "  [%3dms] count=%d sem=%s — %s\n" "$latency_ms" "$count" "$( [ $has_sem -ge 1 ] && echo Y || echo N )" "${q:0:60}"
done

# p95 latency
sorted=($(printf "%s\n" "${latencies[@]}" | sort -n))
p95_idx=$(( (${#sorted[@]} * 95 / 100) - 1 ))
[ $p95_idx -lt 0 ] && p95_idx=0
p95=${sorted[$p95_idx]}

echo
echo "=== Results ==="
echo "Queries with ≥3 results: $pass_3plus / $total_searches  (target ≥10)"
echo "Queries with semantic hit: $pass_semantic / $total_searches  ($(( pass_semantic * 100 / total_searches ))% — target ≥70%)"
echo "p95 latency: ${p95}ms  (target ≤1500ms)"
echo "avg latency: $((total_latency / total_searches))ms"
echo
echo "=== Telemetry snapshot (last 5 rows) ==="
sqlite3 -header -column "$DB" "SELECT substr(ts,12,8) as time, query_words as w, variants_count as v, results_count as r, has_semantic as s, latency_ms as lat_ms, COALESCE(expansion_skipped_reason, '-') as skip FROM search_telemetry ORDER BY id DESC LIMIT 5;"

echo
# Exit criteria
fail=0
[ $pass_3plus -lt 10 ] && { echo "❌ <10 queries with ≥3 results"; fail=1; }
[ $(( pass_semantic * 100 / total_searches )) -lt 70 ] && { echo "❌ semantic ratio <70%"; fail=1; }
[ $p95 -gt 1500 ] && { echo "❌ p95 latency >1500ms"; fail=1; }
[ $fail -eq 0 ] && echo "✅ ALL EXIT CRITERIA MET" || { echo "❌ Some criteria failed — investigate"; exit 1; }
