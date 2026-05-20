#!/usr/bin/env bash
#
# scrape-temporal-shadow.sh
#
# Coleta journalctl da nox-mem-api e agrega telemetria do shadow-mode
# `NOX_TEMPORAL_PATH=shadow` (D49 Phase 2).
#
# Output:
#   /tmp/temporal-shadow-<YYYY-MM-DD>.jsonl           — raw JSON lines
#   docs/research/temporal-shadow-baselines/<YYYY-MM-DD>-summary.json
#
# Cron sugerido (NÃO instalado automaticamente):
#   0 0 * * * /root/.openclaw/workspace/scripts/scrape-temporal-shadow.sh
#
# Constraints:
#   - Read-only (journalctl only).
#   - Não muta DB nem service.
#   - Idempotente: rodar várias vezes no mesmo dia regenera o resumo.
#
# Roda na VPS (precisa journalctl + jq). Se rodar via SSH local, prefixar
# com `ssh root@<vps>`.

set -euo pipefail

DATE_TAG="${1:-$(date -u +%Y-%m-%d)}"
SINCE="${SCRAPE_SINCE:-1 day ago}"
RAW_OUT="/tmp/temporal-shadow-${DATE_TAG}.jsonl"

# Onde fica o repo (na VPS); ajustável via env
REPO_ROOT="${NOX_REPO_ROOT:-/root/.openclaw/workspace/memoria-nox}"
SUMMARY_DIR="${REPO_ROOT}/docs/research/temporal-shadow-baselines"
SUMMARY_OUT="${SUMMARY_DIR}/${DATE_TAG}-summary.json"

mkdir -p "${SUMMARY_DIR}"

# ─── Step 1: scrape raw JSON lines ────────────────────────────────────────
# `temporal_path` é o marker emitido por logTemporalProbe() em
# staged-1.7a/edits/temporal-retrieval.ts. systemd antepõe metadata → cortar
# até o primeiro `{`.
journalctl -u nox-mem-api --since "${SINCE}" --output=cat 2>/dev/null \
  | grep -oE '\{"type":"temporal_path"[^}]*\}' \
  > "${RAW_OUT}" || true

TOTAL=$(wc -l < "${RAW_OUT}" | tr -d ' ')

# ─── Step 2: aggregate ────────────────────────────────────────────────────
# Caso zero entries (ex: dia sem temporal queries), gera summary degenerado.
if [[ "${TOTAL}" -eq 0 ]]; then
  cat > "${SUMMARY_OUT}" <<EOF
{
  "date": "${DATE_TAG}",
  "since": "${SINCE}",
  "total_queries_logged": 0,
  "note": "no temporal_path entries — service stderr empty for window OR shadow off"
}
EOF
  echo "[scrape] zero entries for ${DATE_TAG} → ${SUMMARY_OUT}"
  exit 0
fi

# jq aggregation: totals + hit_rate + signal-source distribution + top1Delta histogram
jq -s --arg date "${DATE_TAG}" --arg since "${SINCE}" --argjson total "${TOTAL}" '
  {
    date: $date,
    since: $since,
    total_queries_logged: $total,
    detected_temporal: (map(select(.isTemporal == true)) | length),
    has_anchor: (map(select(.anchorIso != null)) | length),
    applied_count: (map(select(.applied == true)) | length),
    hit_rate: (
      if length > 0
      then (map(select(.isTemporal == true)) | length) / length
      else 0 end
    ),
    signal_source_distribution: (
      group_by(.signalSource)
      | map({ signalSource: (.[0].signalSource // "none"), count: length })
    ),
    k_reranked_when_applicable: (
      [.[] | select(.kReranked != null and .kReranked > 0) | .kReranked]
    ),
    top1_delta_days_distribution: {
      n_with_delta: ([.[] | select(.top1DeltaDays != null)] | length),
      min: ([.[] | select(.top1DeltaDays != null) | .top1DeltaDays] | if length > 0 then min else null end),
      max: ([.[] | select(.top1DeltaDays != null) | .top1DeltaDays] | if length > 0 then max else null end),
      median: (
        [.[] | select(.top1DeltaDays != null) | .top1DeltaDays]
        | sort
        | if length == 0 then null
          elif length == 1 then .[0]
          else .[length/2|floor] end
      ),
      buckets_0_7: ([.[] | select(.top1DeltaDays != null and .top1DeltaDays <= 7)] | length),
      buckets_8_30: ([.[] | select(.top1DeltaDays != null and .top1DeltaDays > 7 and .top1DeltaDays <= 30)] | length),
      buckets_31_90: ([.[] | select(.top1DeltaDays != null and .top1DeltaDays > 30 and .top1DeltaDays <= 90)] | length),
      buckets_90_plus: ([.[] | select(.top1DeltaDays != null and .top1DeltaDays > 90)] | length)
    }
  }
' "${RAW_OUT}" > "${SUMMARY_OUT}"

echo "[scrape] ${TOTAL} entries → ${SUMMARY_OUT}"
echo "[scrape] preview:"
jq '{date, total_queries_logged, detected_temporal, hit_rate, signal_source_distribution}' "${SUMMARY_OUT}"
