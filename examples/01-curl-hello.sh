#!/usr/bin/env bash
# 30-second hello to nox-mem via curl + jq
# Usage: ./examples/01-curl-hello.sh [query]
#
# Override VPS:  BASE_URL=http://localhost:18802 ./examples/01-curl-hello.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://187.77.234.79:18802}"
QUERY="${1:-pain-weighted memory}"

# curl --data-urlencode encodes the query; we capture the encoded form
ENCODED_QUERY=$(curl -Gso /dev/null -w "%{url_effective}" \
  --data-urlencode "q=$QUERY" \
  "" 2>/dev/null | sed 's|?||')

echo "=== Health snapshot ==="
curl -sf "$BASE_URL/api/health" | jq '{
  chunks_total,
  vec_coverage,
  salience_mode,
  kg_entities,
  kg_relations
}'

echo ""
echo "=== Search: '$QUERY' (limit 3) ==="
curl -sf "$BASE_URL/api/search?${ENCODED_QUERY}&limit=3" \
  | jq '.results[] | {
      score: (.score | tonumber * 1000 | round / 1000),
      source_file,
      snippet: .snippet[:120]
    }'
