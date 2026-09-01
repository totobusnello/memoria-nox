#!/bin/bash
# morning-report.sh — Daily 06:30 UTC summary to Discord.
# Runs the 6-step post-Tier-0+1 verification checklist and posts a single
# colored summary. Read-only — never fixes anything automatically.

set -u

LOG="/var/log/nox-morning.log"
DB="/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"

if [ -f /root/.openclaw/.env ]; then
    set -a; . /root/.openclaw/.env; set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG"; }

# --- gather all signals ---
# Restarts: 1h window reflects CURRENT probe health; 24h contaminates with pre-fix history.
# grep -c returns "0" with exit 1 when no matches — `|| true` to always succeed.
RESTARTS=$( { journalctl -u nox-mem-api --since "1 hour ago" --no-pager 2>/dev/null | grep -c "Started nox-mem-api" || true; } | head -1 )
# Integer guard — if RESTARTS isn't purely numeric, force "?"
case "$RESTARTS" in ''|*[!0-9]*) RESTARTS="?" ;; esac

RATELIMITS=$( { journalctl --since "24 hours ago" --no-pager 2>/dev/null | grep -cE "Resource exhausted" || true; } | head -1 )
case "$RATELIMITS" in ''|*[!0-9]*) RATELIMITS="?" ;; esac

HEALTH=$(curl -sf --max-time 5 "http://127.0.0.1:${NOX_API_PORT:-18802}/api/health" 2>/dev/null || echo "{}")
EMBEDDED=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("embedded","?"))' 2>/dev/null || echo "?")
TOTAL=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("total","?"))' 2>/dev/null || echo "?")
ORPHANS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("vectorCoverage",{}).get("orphans","?"))' 2>/dev/null || echo "?")
# ─── discrepancia vec0: vetores no INDICE que nao existem no MAP ──────────────
#
# `orphans` do /api/health e `prune-orphan-vectors` medem AMBOS a partir de
# `vec_chunk_map` (orphans = totalMap - embedded). Logo nenhum dos dois enxerga um
# vetor cuja linha de map desapareceu: para eles a sujeira nao existe. Medido em
# 2026-08-27: 69.261 rowids validos no indice contra 67.187 no map = 2.074
# inalcancaveis e imprunaveis.
#
# Este contador nao conserta e nao alcança os 2.074. Ele troca "cresce em silencio"
# por "cresce visivel" — e se a diferenca ficar estavel, isso por si e evidencia de
# que o mecanismo que os produziu morreu. Le as shadow tables direto: sao tabelas
# normais e nao exigem o modulo vec0 carregado.
VEC_DISCREP=$(sqlite3 "file:${DB}?mode=ro" \
  "SELECT (SELECT COUNT(*) FROM vec_chunks_rowids) - (SELECT COUNT(*) FROM vec_chunk_map);" \
  2>/dev/null || echo "?")
VEC_DISCREP_BASE_FILE=/var/lib/nox-mem/vec-discrepancia.txt
VEC_DISCREP_ANTES=$(cat "$VEC_DISCREP_BASE_FILE" 2>/dev/null || echo "")
case "$VEC_DISCREP" in
    ''|*[!0-9-]*) VEC_DISCREP="?" ;;
esac

PROCEDURES=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("procedures","?"))' 2>/dev/null || echo "?")
CACHE_HITS=$(echo "$HEALTH" | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("reflectCache",{}).get("total_hits","?"))' 2>/dev/null || echo "?")

TRIGGER_OK=$(sqlite3 "$DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' AND name='trg_chunks_delete_cascade';" 2>/dev/null || echo "?")

# Canary result: read the latest line from the 06:00 run
CANARY_LINE=$(tail -1 /var/log/nox-canary.log 2>/dev/null | sed 's/^\[[^]]*\] //' || echo "no canary log")

# Nightly-maintenance: check log for errors in last run
NIGHTLY_ERRORS=$( { tail -100 /var/log/nox-maintenance.log 2>/dev/null | grep -icE '\[(ERROR|FATAL|FAIL)\]|[1-9][0-9]* errors|(50[0-9]|429) |exception|traceback|FAILED' || true; } | head -1 )
case "$NIGHTLY_ERRORS" in ''|*[!0-9]*) NIGHTLY_ERRORS="?" ;; esac
NIGHTLY_LAST=$(tail -1 /var/log/nox-maintenance.log 2>/dev/null | head -c 200)

# --- reliability checks (added 2026-06-11) ---
# WAL size in MB (rounded). Growing WAL = checkpoint starvation or missing truncate.
WAL_MB=$( { stat -c %s "${DB}-wal" 2>/dev/null || echo 0; } | awk '{printf "%d", $1/1000000}' )
case "$WAL_MB" in ''|*[!0-9]*) WAL_MB="?" ;; esac

# Backup freshness: hours since newest daily-main snapshot (cron 03:00 UTC).
NEWEST_BACKUP=$(ls -t /var/backups/nox-mem/daily-main/*.db.gz 2>/dev/null | head -1)
if [ -n "$NEWEST_BACKUP" ]; then
    BACKUP_AGE_H=$(( ( $(date +%s) - $(stat -c %Y "$NEWEST_BACKUP") ) / 3600 ))
else
    BACKUP_AGE_H="?"
fi

# Vectorize catch-up (cron 43 */4): last completion line must report 0 errors.
CATCHUP_LINE=$(grep "Vectorize complete" /var/log/nox-vectorize-catchup.log 2>/dev/null | tail -1 | head -c 120)
[ -z "$CATCHUP_LINE" ] && CATCHUP_LINE="no runs yet"
CATCHUP_ERRORS=$( { tail -50 /var/log/nox-vectorize-catchup.log 2>/dev/null | grep -cE "[1-9][0-9]* errors|SqliteError|FATAL" || true; } | head -1 )
case "$CATCHUP_ERRORS" in ''|*[!0-9]*) CATCHUP_ERRORS=0 ;; esac

# --- reliability checks round 2 (added 2026-06-11) ---
# Disk usage on / (ingest, WAL, backups all die on disk-full)
DISK_PCT=$(df / --output=pcent 2>/dev/null | tail -1 | tr -dc "0-9")
case "$DISK_PCT" in ''|*[!0-9]*) DISK_PCT="?" ;; esac

# Weekly integrity check (Sunday 05:53): latest PASS/FAIL line + age in days
INTEGRITY_LINE=$(grep -E "PASS|FAIL" /var/log/nox-integrity.log 2>/dev/null | tail -1 | head -c 160)
[ -z "$INTEGRITY_LINE" ] && INTEGRITY_LINE="no runs yet"
INTEGRITY_AGE_D="?"
INTEGRITY_TS=$(echo "$INTEGRITY_LINE" | grep -oE "^\[[0-9T:Z-]+\]" | tr -d "[]")
if [ -n "$INTEGRITY_TS" ]; then
    INTEGRITY_AGE_D=$(( ( $(date +%s) - $(date -d "$INTEGRITY_TS" +%s 2>/dev/null || date +%s) ) / 86400 ))
fi

# --- classify signals ---
RED=0
YELLOW=0
DETAILS=""

# vectorCoverage classification:
#   Orphans > 0 = RED always (cascade trigger failed)
#   Embedded == Total = green
#   Gap <= 10% = YELLOW (transient; watcher ingested chunks not yet vectorized)
#   Gap > 10% = RED (real drift, vectorize cron not running or failing)
if [ "$ORPHANS" != "0" ] && [ "$ORPHANS" != "?" ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 vectorCoverage: ${ORPHANS} orphans (cascade trigger failed?)"
elif [ "$EMBEDDED" != "$TOTAL" ] && [ "$EMBEDDED" != "?" ] && [ "$TOTAL" != "?" ]; then
    # Compute gap percentage
    GAP_PCT=$(python3 -c "t=$TOTAL; e=$EMBEDDED; print(round((t-e)*100/max(t,1))) if t > 0 else 0" 2>/dev/null || echo "?")
    if [ "$GAP_PCT" = "?" ] || [ "$GAP_PCT" -gt 10 ] 2>/dev/null; then
        RED=$((RED+1))
        DETAILS="${DETAILS}\n🔴 vectorCoverage: ${EMBEDDED}/${TOTAL} embedded (${GAP_PCT}% gap — vectorize not running)"
    else
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 vectorCoverage: ${EMBEDDED}/${TOTAL} embedded (${GAP_PCT}% gap — transient, next vectorize catches up)"
    fi
fi

if [ "$RESTARTS" = "?" ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nox-mem-api restart count unavailable (journalctl failed)"
elif [ "$RESTARTS" -gt 2 ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 nox-mem-api restarted ${RESTARTS}x in last hour (probe likely broken again)"
elif [ "$RESTARTS" -gt 0 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nox-mem-api restarted ${RESTARTS}x in last hour"
fi

if [ "$RATELIMITS" = "?" ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Gemini 429 count unavailable"
elif [ "$RATELIMITS" -gt 100 ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 Gemini 429 count: ${RATELIMITS} in 24h (possible runaway loop)"
elif [ "$RATELIMITS" -gt 20 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Gemini 429 count: ${RATELIMITS} in 24h (elevated)"
fi

if [ "$TRIGGER_OK" != "1" ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 trg_chunks_delete_cascade trigger missing (CASCADE disabled)"
fi

if echo "$CANARY_LINE" | grep -q "^RED\|^FAIL"; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 Canary: ${CANARY_LINE}"
elif ! echo "$CANARY_LINE" | grep -q "^OK"; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 Canary: ${CANARY_LINE}"
fi

if [ "$NIGHTLY_ERRORS" != "?" ] && [ "$NIGHTLY_ERRORS" -gt 5 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 nightly-maintenance: ${NIGHTLY_ERRORS} errors in log tail"
fi

# --- reliability checks (added 2026-06-11) ---
if [ "$WAL_MB" != "?" ]; then
    if [ "$WAL_MB" -gt 1000 ]; then
        RED=$((RED+1))
        DETAILS="${DETAILS}\n🔴 WAL ${WAL_MB}MB (checkpoint starvation — long reader holding DB?)"
    elif [ "$WAL_MB" -gt 200 ]; then
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 WAL ${WAL_MB}MB (above 200MB — wal-checkpoint cron not truncating?)"
    fi
fi

if [ "$BACKUP_AGE_H" = "?" ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 backup: no daily-main snapshot found"
elif [ "$BACKUP_AGE_H" -gt 30 ]; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 backup: newest daily-main is ${BACKUP_AGE_H}h old (snapshot cron failing)"
elif [ "$BACKUP_AGE_H" -gt 26 ]; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 backup: newest daily-main is ${BACKUP_AGE_H}h old"
fi

if [ "$CATCHUP_ERRORS" -gt 0 ] 2>/dev/null; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 vectorize-catchup: ${CATCHUP_ERRORS} error lines in log tail"
fi

# --- reliability checks round 2 (added 2026-06-11) ---
if [ "$DISK_PCT" != "?" ]; then
    if [ "$DISK_PCT" -gt 90 ]; then
        RED=$((RED+1))
        DETAILS="${DETAILS}\n🔴 disk: ${DISK_PCT}% used (ingest/WAL/backups at risk)"
    elif [ "$DISK_PCT" -gt 80 ]; then
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 disk: ${DISK_PCT}% used"
    fi
fi

if [ "$VEC_DISCREP" != "?" ] && [ -n "$VEC_DISCREP_ANTES" ] \
   && [ "$VEC_DISCREP" -gt "$VEC_DISCREP_ANTES" ] 2>/dev/null; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 vec0 discrepancia CRESCEU: ${VEC_DISCREP_ANTES} -> ${VEC_DISCREP} vetores no indice sem linha no map (invisiveis ao prune e ao orphans do health)"
fi
if [ "$VEC_DISCREP" != "?" ]; then
    mkdir -p "$(dirname "$VEC_DISCREP_BASE_FILE")" 2>/dev/null
    printf '%s\n' "$VEC_DISCREP" > "$VEC_DISCREP_BASE_FILE"
fi

if echo "$INTEGRITY_LINE" | grep -q "FAIL"; then
    RED=$((RED+1))
    DETAILS="${DETAILS}\n🔴 integrity: ${INTEGRITY_LINE}"
elif [ "$INTEGRITY_AGE_D" != "?" ] && [ "$INTEGRITY_AGE_D" -gt 8 ] 2>/dev/null; then
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 integrity: last check ${INTEGRITY_AGE_D}d ago (weekly cron failing?)"
elif [ "$INTEGRITY_LINE" = "no runs yet" ]; then
    # Sem esta perna, ausencia PERPETUA de execucao ficava verde: a perna de idade
    # exige INTEGRITY_AGE_D != "?", e a idade e "?" exatamente quando nao existe
    # linha nenhuma. Silencio ficava identico a "esta tudo bem". Agora alarma
    # enquanto nao houver a PRIMEIRA evidencia de integridade neste host.
    YELLOW=$((YELLOW+1))
    DETAILS="${DETAILS}\n🟡 integrity: sem execucao registrada (cron 53 5 * * 0; host novo desde 2026-08-23 — 1o domingo e 30/08)"
fi

# --- write-path cost telemetry (added 2026-08-07, PRs nox-workspace #40/#41) ---
# INFORMATIVO: nao altera RED/YELLOW. Constroi a serie diaria de custo por fase
# (construction | query | maintenance) que sustenta a comparacao com o paper de
# Stanford (arXiv 2606.06448: "construction domina, e colide com QA quando
# co-locada"). id>4 exclui as 4 linhas de teste pre-deploy.
WP=$(sqlite3 "$DB" "SELECT phase||' '||COUNT(*)||'x '||COALESCE(SUM(tokens_in+tokens_out),0)||'tok '||printf('%.6f',COALESCE(SUM(cost_estimate_usd),0))||' '||CAST(COALESCE(AVG(latency_ms),0) AS INT)||'ms' FROM provider_telemetry WHERE id>4 AND timestamp_ms >= (strftime('%s','now')-86400)*1000 GROUP BY phase;" 2>/dev/null | paste -sd'|' -)
if [ -n "$WP" ]; then
    DETAILS="${DETAILS}\n\xf0\x9f\x93\x8a write-path 24h: ${WP}"
else
    DETAILS="${DETAILS}\n\xf0\x9f\x93\x8a write-path 24h: nenhuma chamada registrada"
fi

# --- Paper 2: gatilhos de canal (added 2026-08-27) ---
# Lê ARQUIVOS DE STATUS. Nunca sonda /api/brief: o endpoint ESCREVE em brief_log o
# estado que mede, e isso já contaminou medição antes (5 sondas, 25 linhas).
#
# Status ausente ou VELHO nao e green. Gatilho que parou de rodar e indistinguivel de
# gatilho que nao achou nada, e essa confusao e a mais cara que existe em
# monitoramento — silencio nao e sucesso. Qualquer coisa que nao seja GREEN/YELLOW
# conta RED (fail-closed): linha ilegivel e falha, nao ausencia de falha.
p2_gatilho() {   # $1=rotulo  $2=arquivo  $3=idade_max_horas
    local rot="$1" arq="$2" maxh="$3" linha idade
    if [ ! -s "$arq" ]; then
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 ${rot}: sem status (${arq})"
        return 0
    fi
    idade=$(( ( $(date +%s) - $(stat -c %Y "$arq") ) / 3600 ))
    linha=$(head -1 "$arq")
    if [ "$idade" -gt "$maxh" ]; then
        YELLOW=$((YELLOW+1))
        DETAILS="${DETAILS}\n🟡 ${rot}: status com ${idade}h (max ${maxh}h) — gatilho parado? ${linha}"
        return 0
    fi
    case "$linha" in
        GREEN*)  ;;
        YELLOW*) YELLOW=$((YELLOW+1)); DETAILS="${DETAILS}\n🟡 ${rot}: ${linha}" ;;
        *)       RED=$((RED+1));       DETAILS="${DETAILS}\n🔴 ${rot}: ${linha}" ;;
    esac
    return 0
}
# ⚠️ REGRA DO TETO DE IDADE (lesson 2026-08-28):
#   O teto codifica QUANTAS RODADAS PULADAS voce tolera. Esse numero tem de ser
#   ESCOLHIDO, nao herdado do horario do cron.
#     rodadas_toleradas = (teto - idade_normal_no_momento_deste_report) / intervalo_do_cron
#   Se der < 1, o guarda esta CEGO: uma rodada pulada envelhece menos que o teto
#   e o dia inteiro passa GREEN. Tolerancia > 1 pode ser deliberada (transiente) —
#   o que nao pode e' cair do horario sem ninguem escolher.
# Este report roda 06:30Z. Ao mexer no horario de um gatilho, REFAZER a conta.
#
#   composicao  cron "9 * * * *" (horario)   -> idade normal 0,35h; 1 falha=1,35h (silencio,
#               tolerancia deliberada a transiente), 3 falhas=3,35h > 3 dispara.
#   saturacao   cron "12 9 * * *" (09:12Z)   -> idade normal 21,3h; 1 falha=45,3h > 30 dispara.
#               (era 05:41Z: idade normal 0,8h, 1 falha=24,8h < 30 => CEGO por um dia inteiro)
p2_gatilho "p2 composicao-do-canal" /var/lib/nox-mem/p2/status-composicao.txt 3
p2_gatilho "p2 saturacao-da-dose"   /var/lib/nox-mem/p2/status-saturacao.txt 30

# --- format summary ---
if [ "$RED" -gt 0 ]; then
    HEADER="🚨 nox-mem morning report: **${RED} RED** / ${YELLOW} yellow"
elif [ "$YELLOW" -gt 0 ]; then
    HEADER="⚠️ nox-mem morning report: ${YELLOW} yellow / all else green"
else
    HEADER="✅ nox-mem morning report: all green"
fi

BODY="${HEADER}\n\`\`\`\nchunks embedded  : ${EMBEDDED}/${TOTAL} (orphans: ${ORPHANS})\nvec0 fora do map : ${VEC_DISCREP}\nprocedures       : ${PROCEDURES}\nreflect hits     : ${CACHE_HITS}\nrestarts 1h      : ${RESTARTS}\ngemini 429 24h   : ${RATELIMITS}\ntrigger active   : $([ "$TRIGGER_OK" = "1" ] && echo yes || echo NO)\ncanary           : ${CANARY_LINE}\nnightly errors   : ${NIGHTLY_ERRORS}\nwal size         : ${WAL_MB}MB\nbackup age       : ${BACKUP_AGE_H}h\ncatchup          : ${CATCHUP_LINE}\ndisk             : ${DISK_PCT}%\nintegrity        : ${INTEGRITY_LINE}\n\`\`\`"

if [ -n "${DETAILS}" ]; then
    BODY="${BODY}\n**Details:**${DETAILS}"
fi

log "summary: red=${RED} yellow=${YELLOW} embedded=${EMBEDDED}/${TOTAL} restarts=${RESTARTS} rl=${RATELIMITS}"

if [ -n "${DISCORD_WEBHOOK:-}" ]; then
    # Discord max 2000 chars per message — truncate body safely
    CONTENT=$(echo -e "$BODY" | head -c 1900)
    # Build JSON payload via python to escape properly
    PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'content': sys.argv[1]}))" "$CONTENT")
    curl -sf -X POST "$DISCORD_WEBHOOK" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1
    log "posted to Discord"
fi

# Exit code mirrors severity for external orchestration (0 green, 1 yellow, 2 red)
if [ "$RED" -gt 0 ]; then exit 2
elif [ "$YELLOW" -gt 0 ]; then exit 1
else exit 0
fi
