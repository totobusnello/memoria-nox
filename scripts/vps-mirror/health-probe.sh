#!/bin/bash
# Health probe — runs every 10min via cron, checks critical services + resources.
# Circuit breaker: stops restarting after 3 failures.
# Thresholds atualizados 2026-06-01 (post-VPS-upgrade: 4→8 vCPU, 15→31GB RAM).
LOG="/var/log/nox-health.log"
CIRCUIT_FILE="/tmp/openclaw-circuit-open"

# Source env so NOX_API_PORT matches the bound port. Hardcoded 18800 caused
# a 5-min restart loop after the service moved to 18802 to dodge a port squatter.
if [ -f /root/.openclaw/.env ]; then
    set -a
    . /root/.openclaw/.env
    set +a
fi
NOX_API_PORT="${NOX_API_PORT:-18800}"

# Load notify-discord helper for severity-tagged alerts (Frente C 2026-05-31)
NOTIFY_AVAILABLE=0
if [ -f /root/.openclaw/scripts/notify-discord.sh ]; then
    source /root/.openclaw/scripts/notify-discord.sh
    NOTIFY_AVAILABLE=1
fi

log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1" >> "$LOG"; }

# Alert helper — uses notify-discord if available, fallback to raw curl
alert() {
    local severity="$1"  # info | warn | critical
    local tag="$2"
    local msg="$3"
    if [ "$NOTIFY_AVAILABLE" -eq 1 ]; then
        notify_discord "$severity" "$tag" "$msg"
    elif [ -n "${DISCORD_WEBHOOK:-}" ]; then
        # Fallback: raw webhook (no throttle)
        local emoji
        case "$severity" in
            critical) emoji="🚨";;
            warn) emoji="⚠️";;
            info) emoji="ℹ️";;
        esac
        curl -sf -X POST "$DISCORD_WEBHOOK" -H "Content-Type: application/json" \
            -d "{\"content\":\"${emoji} [${tag}] ${msg}\"}" > /dev/null 2>&1 || true
    fi
}

FAILED=0

# ────────────────────────────────────────────────────────────────────────
# CHECK 1: Gateway port (retry 3x with 3s delay to avoid false positives)
# ────────────────────────────────────────────────────────────────────────
GW_UP=0
for attempt in 1 2 3; do
    if ss -tlnp | grep -q ":18789"; then
        GW_UP=1
        break
    fi
    [ "$attempt" -lt 3 ] && sleep 3
done
if [ "$GW_UP" -eq 1 ]; then
    log "OK: Gateway port 18789"
else
    # SMART-SILENCE 2026-06-02: se DOWN foi causado por SIGUSR1 (graceful restart
    # via gateway-tool, chamado por agents como Forge pra context-watchdog),
    # esperar 20s extras e re-testar. Sistema autocura via systemd Restart=.
    # Só alertar Discord se realmente está DOWN persistente.
    if journalctl -u openclaw-gateway --since "90 seconds ago" 2>/dev/null | grep -q "SIGUSR1 received"; then
        log "INFO: Gateway DOWN coincide com SIGUSR1 nos ultimos 90s — graceful restart em curso, aguardando 20s"
        sleep 20
        if ss -tlnp | grep -q ":18789"; then
            log "OK: Gateway port 18789 (recuperou apos SIGUSR1, sem alerta)"
            GW_UP=1
        fi
    fi
fi

if [ "$GW_UP" -ne 1 ]; then
    log "FAIL: Gateway port 18789 not listening (after 3 retries + SIGUSR1 wait)"
    FAILED=1

    # Circuit breaker check
    if [ -f "$CIRCUIT_FILE" ]; then
        log "CIRCUIT OPEN: Not restarting gateway. Manual intervention required."
        alert critical health-probe-gateway "Gateway DOWN + CIRCUIT OPEN — manual intervention required"
    else
        FAIL_COUNT=$(systemctl show openclaw-gateway -p NRestarts --value 2>/dev/null || echo 0)
        if [ "$FAIL_COUNT" -gt 3 ]; then
            touch "$CIRCUIT_FILE"
            log "CIRCUIT OPENED: Gateway exceeded 3 restarts."
            alert critical health-probe-gateway "CIRCUIT BREAKER OPENED — gateway ${FAIL_COUNT} restarts. Remove ${CIRCUIT_FILE} to re-enable."
        else
            log "Restarting gateway (attempt $FAIL_COUNT) — reset-failed + start"
            systemctl reset-failed openclaw-gateway 2>/dev/null
            systemctl start openclaw-gateway
            alert critical health-probe-gateway "Gateway DOWN — attempting restart (${FAIL_COUNT} prior)"
        fi
    fi
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 2: nox-mem API
# 2026-05-09: trocado /api/health → /api/health/lite (zero-DB, ~1ms).
# Timeout 5s pra tolerar lock contention com canary-bundle (*/15).
# ────────────────────────────────────────────────────────────────────────
if curl -sf --max-time 5 "http://127.0.0.1:${NOX_API_PORT:-18802}/api/health/lite" > /dev/null 2>&1; then
    log "OK: nox-mem API port ${NOX_API_PORT}"
else
    log "WARN: nox-mem API not responding on ${NOX_API_PORT}, restarting"
    systemctl restart nox-mem-api 2>/dev/null
    alert warn health-probe-nox-mem-api "nox-mem API not responding on :${NOX_API_PORT} — restarting"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 3: Disk space (% based — escala automática com expansão de disk)
# Warn: >85% | Critical: >95%
# ────────────────────────────────────────────────────────────────────────
DISK_PCT=$(df / | tail -1 | awk "{print \$5}" | tr -d "%")
DISK_FREE_G=$(df -BG / | tail -1 | awk "{print \$4}" | tr -d "G")
if [ "$DISK_PCT" -gt 95 ]; then
    log "CRITICAL: Disk at ${DISK_PCT}% (${DISK_FREE_G}G free)"
    alert critical health-probe-disk "Disk ${DISK_PCT}% used (only ${DISK_FREE_G}G free) — IMMEDIATE cleanup needed"
    FAILED=1
elif [ "$DISK_PCT" -gt 85 ]; then
    log "WARN: Disk at ${DISK_PCT}% (${DISK_FREE_G}G free)"
    alert warn health-probe-disk "Disk ${DISK_PCT}% used (${DISK_FREE_G}G free) — cleanup recommended"
else
    log "OK: Disk ${DISK_PCT}% (${DISK_FREE_G}G free)"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 4: SQLite readable
# ────────────────────────────────────────────────────────────────────────
DB=/root/.openclaw/workspace/tools/nox-mem/nox-mem.db
if sqlite3 "$DB" "SELECT count(*) FROM chunks LIMIT 1" > /dev/null 2>&1; then
    log "OK: SQLite DB readable"
else
    log "FAIL: SQLite DB unreadable"
    alert critical health-probe-sqlite "nox-mem SQLite DB unreadable"
    FAILED=1
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 5: Node.js wrapper integrity
# ────────────────────────────────────────────────────────────────────────
# KVM2 (2026-08-23): aqui /usr/bin/node e o binario real, NAO ha wrapper node.real
# (a cirurgia de wrapper era especifica do KVM8). Valida o que importa: node funciona.
if ! NODE_V=$(node --version 2>/dev/null) || [ -z "$NODE_V" ]; then
    log "CRITICAL: node nao executa"
    alert critical health-probe-node "node nao executa — runtime BROKEN"
    FAILED=1
elif [ -f /usr/bin/node ] && head -c 4 /usr/bin/node 2>/dev/null | grep -q ELF; then
    log "OK: node ${NODE_V} (binario direto)"
elif [ ! -f /usr/bin/node.real ]; then
    log "CRITICAL: /usr/bin/node e wrapper mas node.real sumiu"
    alert critical health-probe-node "node.real missing — wrapper BROKEN"
    FAILED=1
else
    log "OK: node ${NODE_V} (wrapper + node.real)"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 6: Memory (warn <4GB free / critical <2GB)
# Atualizado 2026-06-01 pós-VPS upgrade (15GB→31GB). Antes era 1GB warn.
# 4GB warn = 13% de 31GB; 2GB crit = 6%.
# ────────────────────────────────────────────────────────────────────────
FREE_MB=$(free -m | awk "/Mem:/{print \$7}")
FREE_GB=$(awk "BEGIN {printf \"%.1f\", $FREE_MB/1024}")
# KVM2 (2026-08-23): limiares viraram PERCENTUAIS para escalar com a maquina,
# igual ao CHECK 3 de disco. Os antigos (2GB/4GB absolutos) eram calibrados para os
# 31GB do KVM8; nos 7.9GB do KVM2 o warn de 4GB = 51% livre e dispararia por nada.
TOTAL_MB=$(free -m | awk "/Mem:/{print \$2}")
FREE_PCT=$(awk "BEGIN {printf \"%d\", ($FREE_MB/$TOTAL_MB)*100}")
if [ "$FREE_PCT" -lt 10 ]; then
    log "CRITICAL: RAM available ${FREE_GB}GB (${FREE_PCT}% <10%)"
    alert critical health-probe-ram "RAM available only ${FREE_GB}GB (${FREE_PCT}%) — risk of OOM"
elif [ "$FREE_PCT" -lt 20 ]; then
    log "WARN: RAM available ${FREE_GB}GB (${FREE_PCT}% <20%)"
    alert warn health-probe-ram "RAM available ${FREE_GB}GB (${FREE_PCT}%)"
else
    log "OK: RAM ${FREE_GB}GB available"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 7: Swap pressure (corrigido 2026-06-29 — gate por MemAvailable)
# Swap usado SÓ é pressão real se a RAM também estiver apertada. Swap residual/stale
# (paginado num pico passado, nunca repaginado porque sobra RAM) é benigno e não alerta.
# Incidente 2026-06-29: 2.5GB swap stale + 26GB MemAvailable disparava CRITICAL indevido.
# ────────────────────────────────────────────────────────────────────────
SWAP_USED_MB=$(free -m | awk "/Swap:/{print \$3}")
SWAP_USED_GB=$(awk "BEGIN {printf \"%.1f\", $SWAP_USED_MB/1024}")
MEM_AVAIL_MB=$(awk "/MemAvailable:/{printf \"%d\", \$2/1024}" /proc/meminfo)
if [ "$SWAP_USED_MB" -gt 2048 ] && [ "$MEM_AVAIL_MB" -lt 2048 ]; then
    log "CRITICAL: Swap ${SWAP_USED_GB}GB + MemAvailable ${MEM_AVAIL_MB}MB"
    alert critical health-probe-swap "Swap ${SWAP_USED_GB}GB in use + MemAvailable ${MEM_AVAIL_MB}MB — heavy memory pressure"
elif [ "$SWAP_USED_MB" -gt 1024 ] && [ "$MEM_AVAIL_MB" -lt 4096 ]; then
    log "WARN: Swap ${SWAP_USED_GB}GB + MemAvailable ${MEM_AVAIL_MB}MB low"
    alert warn health-probe-swap "Swap ${SWAP_USED_GB}GB in use + MemAvailable ${MEM_AVAIL_MB}MB low — memory pressure suspected"
else
    log "OK: Swap ${SWAP_USED_GB}GB (MemAvailable ${MEM_AVAIL_MB}MB)"
fi

# CHECK 8: CPU load (novo 2026-06-01; WARN recalibrado 2026-08-23 no KVM2)
# Warn: load1 > nproc * 2 | Critical: load1 > nproc * 3
# Com 8 cores: warn >16, critical >24. Com 2 cores: warn >4, critical >6.
#
# SEGUNDA recalibragem (2026-08-23 16:20): 2x/3x ainda alertava demais. Trabalho
# normal de agente aqui (uma sessao codex + gateway) sustenta load 7-9 com CPU 100%
# ocupada e 8 processos em R — saturacao real, mas ROTINA nesta maquina. Subido pra
# 4x/6x (warn 8.0, crit 12.0 em 2 cores). O que o load deixou de pegar passou a ser
# coberto pelo CHECK 8b (PSI), que detecta a patologia de verdade em vez do proxy.
#
# Por que 2x e nao 1.5x (mudanca de 2026-08-23): o openclaw migrou de uma VPS de
# 8 cores (KVM8) para uma de 2 (KVM2). Em 8 cores, 1.5x = 12 e so dispara com a
# maquina afogada; em 2 cores, 1.5x = 3.0 e UMA unica sessao codex app-server
# (medida: 1.32 cores sustentados por 29min) ja estourava o limiar. Decisao do
# Toto: aceitar que load 3-4 e normal durante trabalho de agente aqui e subir o
# WARN, em vez de silenciar o alerta. O CRITICAL (3x) fica intacto.
# ────────────────────────────────────────────────────────────────────────
NCPU=$(nproc)
LOAD1=$(awk "{print \$1}" /proc/loadavg)
LOAD_WARN=$(awk "BEGIN {printf \"%.1f\", $NCPU * 4}")
LOAD_CRIT=$(awk "BEGIN {printf \"%.1f\", $NCPU * 6}")
LOAD_OVER_WARN=$(awk "BEGIN {print ($LOAD1 > $LOAD_WARN) ? 1 : 0}")
LOAD_OVER_CRIT=$(awk "BEGIN {print ($LOAD1 > $LOAD_CRIT) ? 1 : 0}")
if [ "$LOAD_OVER_CRIT" -eq 1 ]; then
    log "CRITICAL: Load avg 1min ${LOAD1} (>${LOAD_CRIT} = ${NCPU}x6)"
    alert critical health-probe-cpu "CPU load1 ${LOAD1} (threshold ${LOAD_CRIT}, ${NCPU}cores) — heavy CPU saturation"
elif [ "$LOAD_OVER_WARN" -eq 1 ]; then
    log "WARN: Load avg 1min ${LOAD1} (>${LOAD_WARN} = ${NCPU}x4)"
    alert warn health-probe-cpu "CPU load1 ${LOAD1} (threshold ${LOAD_WARN}, ${NCPU}cores) — sustained high load"
else
    log "OK: Load ${LOAD1} (${NCPU} cores)"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 8b: PSI de memoria (novo 2026-08-23)
#
# Por que existe: em 2026-08-23 o gateway ficou estrangulado por MemoryHigh de cgroup
# (485k eventos de throttle). O sintoma era load 9.8 — mas com CPU 38% OCIOSA e 9
# processos presos em D. Load alto sozinho nao distingue "trabalhando muito" de
# "travado esperando memoria"; PSI distingue. Ver:
#   lessons/2026-08-23-load-alto-cpu-ociosa-throttle-de-cgroup.md
#
# some avg10 = % do tempo com PELO MENOS UM processo parado esperando memoria.
# Em operacao normal fica <1. No incidente estava em 98.13.
# ────────────────────────────────────────────────────────────────────────
if [ -r /proc/pressure/memory ]; then
    PSI_SOME=$(awk "/some/{split(\$2,a,\"=\"); print a[2]}" /proc/pressure/memory)
    PSI_OVER_CRIT=$(awk "BEGIN {print ($PSI_SOME > 50) ? 1 : 0}")
    PSI_OVER_WARN=$(awk "BEGIN {print ($PSI_SOME > 20) ? 1 : 0}")
    NPROC_D=$(ps -eo stat --no-headers 2>/dev/null | grep -c "^D" || true)
    if [ "$PSI_OVER_CRIT" -eq 1 ]; then
        log "CRITICAL: PSI memoria some=${PSI_SOME} (>50), ${NPROC_D} procs em D"
        alert critical health-probe-psi "Stall de MEMORIA: PSI some=${PSI_SOME}%, ${NPROC_D} procs travados em D — checar MemoryHigh do cgroup, NAO e CPU"
        FAILED=1
    elif [ "$PSI_OVER_WARN" -eq 1 ]; then
        log "WARN: PSI memoria some=${PSI_SOME} (>20), ${NPROC_D} procs em D"
        alert warn health-probe-psi "Pressao de memoria: PSI some=${PSI_SOME}%, ${NPROC_D} procs em D"
    else
        log "OK: PSI memoria some=${PSI_SOME} (${NPROC_D} em D)"
    fi
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 9: nox-mem-watch service running (consolidated 2026-05-31)
# ────────────────────────────────────────────────────────────────────────
if ! systemctl is-active --quiet nox-mem-watch.service 2>/dev/null; then
    log "FAIL: nox-mem-watch service down — restarting"
    alert critical health-probe-nox-watch "nox-mem-watch DOWN — restarting"
    systemctl start nox-mem-watch.service 2>/dev/null || true
    sleep 2
    if systemctl is-active --quiet nox-mem-watch.service 2>/dev/null; then
        log "OK: nox-mem-watch recovered"
    else
        log "CRITICAL: nox-mem-watch restart FAILED"
        alert critical health-probe-nox-watch "nox-mem-watch restart FAILED — manual"
        FAILED=1
    fi
else
    log "OK: nox-mem-watch active"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 10: Crontab sanity (consolidated 2026-05-31; teto 40->45 em 2026-07-26)
# Range: 25-45 lines is healthy.
#
# O PISO e o que ja salvou o dia: pega o crontab zerado (incident do
# `crontab -l | sed | crontab -`). O TETO pega injecao.
#
# Subiu de 40 para 45 em 2026-07-26 porque os dois jobs do Paper 2
# (nox-epoch-boundary 06:00 + nox-archive-transcripts 4x/dia) levaram a
# contagem legitima a 41. Ao adicionar job novo, conferir esta faixa junto:
# um alerta que dispara sempre e um alerta que ninguem le.
# ────────────────────────────────────────────────────────────────────────
CRON_LINES=$(crontab -l 2>/dev/null | grep -v "^#" | grep -v "^$" | wc -l)
if [ "$CRON_LINES" -lt 25 ] || [ "$CRON_LINES" -gt 45 ]; then
    log "WARN: Crontab suspicious ($CRON_LINES lines, expected 25-45)"
    alert warn health-probe-crontab "Crontab line count ${CRON_LINES} (expected 25-45)"
else
    log "OK: Crontab ($CRON_LINES lines)"
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 11: Backup summary (novo 2026-08-27)
#
# O backup-all.sh sempre emitiu "BACKUP SUMMARY: N failures" de proposito,
# como gancho pra este check — mas o gancho nunca foi ligado. Resultado:
# "Git backup FAILED (exit 5)" todo dia de 2026-07-28 a 2026-08-27 sem
# ninguem ver, com o auto-commit do workspace morto por 23 dias.
#
# Cobre os DOIS modos de falha: backup que roda e falha, e backup que
# parou de rodar (log velho). O segundo e o que mais engana — sem falha
# no log, parece que esta tudo bem.
# ────────────────────────────────────────────────────────────────────────
BACKUP_LOG=/var/log/nox-backup.log
if [ -f "$BACKUP_LOG" ]; then
    LAST_SUMMARY=$(grep "BACKUP SUMMARY" "$BACKUP_LOG" 2>/dev/null | tail -1)
    if [ -z "$LAST_SUMMARY" ]; then
        log "WARN: nox-backup.log sem linha BACKUP SUMMARY"
        alert warn health-probe-backup "nox-backup.log sem BACKUP SUMMARY — backup-all.sh pode nao estar rodando"
    else
        BK_FAILURES=$(echo "$LAST_SUMMARY" | grep -oE "SUMMARY: [0-9]+" | grep -oE "[0-9]+$")
        BK_DATE=$(echo "$LAST_SUMMARY" | grep -oE "^\\[[0-9-]+" | tr -d "[")
        BK_EPOCH=$(date -d "$BK_DATE" +%s 2>/dev/null || echo 0)
        BK_AGE_H=$(( ( $(date +%s) - BK_EPOCH ) / 3600 ))
        if [ "${BK_FAILURES:-0}" -gt 0 ]; then
            log "WARN: backup com ${BK_FAILURES} falha(s) em ${BK_DATE}"
            alert warn health-probe-backup "backup-all.sh: ${BK_FAILURES} falha(s) em ${BK_DATE} — ver /var/log/nox-backup.log"
        elif [ "$BK_EPOCH" -gt 0 ] && [ "$BK_AGE_H" -gt 30 ]; then
            log "WARN: ultimo backup ha ${BK_AGE_H}h"
            alert warn health-probe-backup "backup-all.sh nao roda ha ${BK_AGE_H}h (esperado diario 02:00)"
        else
            log "OK: Backup (${BK_DATE}, 0 falhas)"
        fi
    fi
fi

# ────────────────────────────────────────────────────────────────────────
# CHECK 12: Sessao envenenada por restart-recovery claim (novo 2026-08-27)
#
# Quarta ocorrencia do mesmo bug em 3 semanas (06/ago, 09/ago, 24/ago,
# 27/ago), sempre sem alarme. A de 06/ago custou 3 DIAS de Discord mudo
# (546 falhas) e so apareceu porque o Toto reclamou. O gateway segue
# "active" e o systemctl nao diz nada — o canal simplesmente para.
#
# Dois sinais, deliberadamente distintos:
#   (a) LOG: o bug acontecendo agora. Janela de 20min = >=2 ciclos do
#       retry (a licao de 09/ago: snapshot cai no vao entre retries).
#       Threshold 3 porque 1-2 ocorrencias logo apos restart legitimo
#       podem ser transitorias e se auto-resolvem.
#   (b) SQL: veneno ARMADO que ainda nao recebeu inbound. Discriminador
#       e restartRecoveryDeliveryRunId pendente — NAO a presenca de
#       campos restartRecovery* (medido em 27/ago: da falso positivo em
#       3 dos 6 agentes, que carregam TerminalRunIds benigno).
# ────────────────────────────────────────────────────────────────────────
# NB: `grep -c` imprime "0" E sai com exit 1 quando nao acha nada — um
# `|| echo 0` aqui produz "0\n0" e quebra o `[ -ge ]` adiante (bug pego
# no primeiro teste, 2026-08-27). `|| true` + sanitizacao numerica.
CLAIM_ERRORS=$(journalctl -u openclaw-gateway.service --since "20 min ago" --no-pager 2>/dev/null \
    | grep -c "restart recovery claim changed" || true)
CLAIM_ERRORS=$(printf '%s' "${CLAIM_ERRORS:-0}" | tr -dc '0-9')
CLAIM_ERRORS=${CLAIM_ERRORS:-0}

CLAIM_ARMED=""
for AG in atlas boris cipher forge lex nox; do
    AGDB="/root/.openclaw/workspace/agents/${AG}/agent/openclaw-agent.sqlite"
    [ -f "$AGDB" ] || continue
    N=$(timeout 10 sqlite3 "$AGDB" \
        "SELECT COUNT(*) FROM session_nodes WHERE json_extract(entry_json,'\$.restartRecoveryDeliveryRunId') IS NOT NULL;" \
        2>/dev/null || echo 0)
    [ "${N:-0}" -gt 0 ] 2>/dev/null && CLAIM_ARMED="${CLAIM_ARMED}${AG}(${N}) "
done

if [ "${CLAIM_ERRORS:-0}" -ge 3 ]; then
    log "WARN: ${CLAIM_ERRORS} restart-recovery claim errors em 20min — canal provavelmente mudo"
    alert warn health-probe-claim "Sessao envenenada: ${CLAIM_ERRORS} 'restart recovery claim changed' em 20min. Canal(is) mudo(s). Cura em infra/docs/INCIDENTS.md (2026-08-27)"
elif [ -n "$CLAIM_ARMED" ]; then
    # Persistencia exigida antes de alertar (ajuste 2026-08-27 20:57 UTC).
    #
    # Motivo: o primeiro alerta deste sinal (20:30 UTC) referia-se a um claim
    # que se dissolveu em <26min SEM intervencao — nenhum erro no journal,
    # zero falha de entrega, canal intacto. O sinal (a) acima ja tratava isso
    # ("1-2 ocorrencias podem ser transitorias") com threshold 3; eu nao havia
    # aplicado o mesmo raciocinio aqui, e alerta que se auto-resolve treina a
    # ignorar o alerta real — o de 06/ago custou 3 DIAS de Discord mudo.
    #
    # Cron roda a cada 10min, entao 2 deteccoes consecutivas = claim vivo por
    # >=10min. Um travamento real dura horas ou dias (centenas de ciclos), logo
    # nada de grave e perdido; so o transitorio para de gritar.
    CLAIM_STATE=/var/lib/nox-health/claim-armed.prev
    mkdir -p /var/lib/nox-health 2>/dev/null
    CLAIM_PREV=$(cat "$CLAIM_STATE" 2>/dev/null || true)
    printf '%s' "$CLAIM_ARMED" > "$CLAIM_STATE"

    if [ -n "$CLAIM_PREV" ]; then
        log "WARN: claim de recovery pendente (armado, 2o ciclo consecutivo): ${CLAIM_ARMED}"
        alert warn health-probe-claim "Claim de restart-recovery PERSISTENTE (>=10min) em: ${CLAIM_ARMED}— proximo inbound pode travar o canal. Anterior: ${CLAIM_PREV}"
    else
        log "INFO: claim armado detectado (1o ciclo, aguardando confirmacao): ${CLAIM_ARMED}"
    fi
else
    rm -f /var/lib/nox-health/claim-armed.prev 2>/dev/null
    log "OK: Restart-recovery claim (${CLAIM_ERRORS} erros/20min, nenhum armado)"
fi

# ────────────────────────────────────────────────────────────────────────
# Clear circuit breaker if gateway is healthy
# ────────────────────────────────────────────────────────────────────────
if [ "$FAILED" -eq 0 ] && [ -f "$CIRCUIT_FILE" ]; then
    rm -f "$CIRCUIT_FILE"
    log "Circuit breaker cleared — gateway healthy"
    alert info health-probe-recovery "Circuit breaker cleared — gateway healthy"
fi

exit 0
