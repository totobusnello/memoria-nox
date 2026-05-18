# Embedding Integrity Check — Runbook Operacional

**Criado:** 2026-05-18  
**Motivação:** Incident 2026-05-18 — 57 chunks perderam embedding por Gemini key expirada, sem alerta proativo  
**Relacionado:** `docs/incidents/2026-05-18-orphan-embeddings.md`

---

## Visão Geral

O sistema de embeddings é assíncrono: o watcher ingere chunks primeiro e tenta embed em seguida. Se o embed falha (key expirada, quota esgotada, timeout), o chunk fica sem mapeamento em `vec_chunk_map` permanentemente — sem retry automático.

Este runbook define:
1. Cron diário de verificação de cobertura
2. Política de alerta (Discord webhook)
3. Auto-trigger de re-embed para drift pequeno (<100 chunks)
4. Procedimento de revisão manual para drift grande (>100 chunks)

---

## 1. Verificação Manual Rápida

```bash
# Estado atual via API
curl -s http://127.0.0.1:18802/api/health | jq '{
  total: .vectorCoverage.total,
  embedded: .vectorCoverage.embedded,
  orphans_count: (.vectorCoverage.total - .vectorCoverage.embedded),
  coverage_pct: (.vectorCoverage.embedded / .vectorCoverage.total * 100 | round)
}'

# Query direta no DB (mais precisa que API)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT
    (SELECT count(*) FROM chunks) as total,
    (SELECT count(*) FROM vec_chunk_map) as mapped,
    (SELECT count(*) FROM chunks c LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id WHERE m.chunk_id IS NULL) as orphans;
"

# Identificar orphans recentes (últimas 24h)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT c.id, c.chunk_type, c.source_file, c.created_at
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL
    AND c.created_at >= datetime('now', '-1 day')
  ORDER BY c.created_at DESC
  LIMIT 50;
"
```

---

## 2. Cron Diário de Verificação

### Instalar o script de verificação

Criar `/usr/local/bin/nox-mem-embedding-check.sh`:

```bash
#!/usr/bin/env bash
# nox-mem-embedding-check.sh — verifica cobertura de embeddings e alerta se drift

set -euo pipefail

DB_PATH="${OPENCLAW_WORKSPACE:-/root/.openclaw/workspace}/tools/nox-mem/nox-mem.db"
LOG_FILE="/var/log/nox-mem/embedding-check.log"
DISCORD_WEBHOOK="${NOX_DISCORD_WEBHOOK:-}"
AUTO_REEMBED_THRESHOLD=100  # auto-trigger se drift <= esse valor

timestamp() { date '+%Y-%m-%dT%H:%M:%S%z'; }
log() { echo "[$(timestamp)] $*" | tee -a "$LOG_FILE"; }

# Carregar .env
set -a; source /root/.openclaw/.env; set +a

# Consultar estado
TOTAL=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM chunks;")
MAPPED=$(sqlite3 "$DB_PATH" "SELECT count(*) FROM vec_chunk_map;")
ORPHANS=$((TOTAL - MAPPED))

log "Verificação: total=$TOTAL mapped=$MAPPED orphans=$ORPHANS"

# Sem drift: sair sem alerta
if [[ $ORPHANS -le 1 ]]; then
  log "OK — cobertura plena (orphans=$ORPHANS é pré-existente normal)"
  exit 0
fi

COVERAGE_PCT=$(python3 -c "print(f'{$MAPPED/$TOTAL*100:.2f}')")
log "DRIFT DETECTADO: $ORPHANS chunks sem embedding ($COVERAGE_PCT% coverage)"

# Alerta Discord
if [[ -n "$DISCORD_WEBHOOK" ]]; then
  if [[ $ORPHANS -le $AUTO_REEMBED_THRESHOLD ]]; then
    MSG="⚠️ nox-mem: $ORPHANS chunks sem embedding ($COVERAGE_PCT%). Auto re-embed iniciando..."
  else
    MSG="🚨 nox-mem: $ORPHANS chunks sem embedding ($COVERAGE_PCT%). Revisão manual necessária."
  fi

  curl -s -X POST "$DISCORD_WEBHOOK" \
    -H "Content-Type: application/json" \
    -d "{\"content\": \"$MSG\"}" \
    >> "$LOG_FILE" 2>&1 || log "Falha ao enviar alerta Discord"
fi

# Auto re-embed se drift pequeno e key disponível
if [[ $ORPHANS -le $AUTO_REEMBED_THRESHOLD ]] && [[ -n "${GEMINI_API_KEY:-}" ]]; then
  log "Auto re-embed: $ORPHANS <= $AUTO_REEMBED_THRESHOLD (threshold)"
  NOX_NONINTERACTIVE=1 bash /usr/local/bin/nox-mem-re-embed-orphans.sh --verbose \
    >> "$LOG_FILE" 2>&1
  log "Auto re-embed concluído. Verificar log acima."
else
  log "Drift > threshold ($ORPHANS > $AUTO_REEMBED_THRESHOLD) ou GEMINI_API_KEY ausente."
  log "Ação manual necessária: bash /usr/local/bin/nox-mem-re-embed-orphans.sh --dry-run"
fi
```

```bash
chmod 750 /usr/local/bin/nox-mem-embedding-check.sh
```

### Registrar no cron

```bash
# Editar crontab root
crontab -e

# Adicionar linha (roda às 07:00 BRT = 10:00 UTC):
0 10 * * * /usr/local/bin/nox-mem-embedding-check.sh >> /var/log/nox-mem/embedding-check.log 2>&1
```

### Copiar re-embed script para /usr/local/bin

```bash
cp /root/.openclaw/workspace/tools/nox-mem/scripts/re-embed-orphans.sh \
   /usr/local/bin/nox-mem-re-embed-orphans.sh
chmod 750 /usr/local/bin/nox-mem-re-embed-orphans.sh
```

---

## 3. Verificação Pós-Deploy

Adicionar ao checklist de deploy (`scripts/deploy-validator` ou similar):

```bash
#!/usr/bin/env bash
# Passo adicional no deploy validator: verificar cobertura de embeddings

echo "Verificando cobertura de embeddings pós-deploy..."
ORPHANS=$(sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT count(*)
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL;
")

if [[ $ORPHANS -gt 1 ]]; then
  echo "⚠️  AVISO: $ORPHANS chunks sem embedding após deploy"
  echo "   Rode: bash scripts/re-embed-orphans.sh --dry-run"
  exit 1
else
  echo "✓  Cobertura de embeddings OK (orphans=$ORPHANS)"
fi
```

---

## 4. Política de Alerta

| Condição | Ação |
|---|---|
| orphans == 0 ou 1 | OK — sem alerta (1 é o orphan pré-existente histórico) |
| 2 ≤ orphans ≤ 100 | Alerta Discord + auto re-embed via cron |
| orphans > 100 | Alerta Discord com `@here` + revisão manual obrigatória |
| erro 400 Gemini no syslog | Alerta imediato — renovar chave antes do próximo ingest |

### Configurar alerta para erro Gemini (syslog watcher)

```bash
# /etc/logrotate.d/ não ajuda aqui — usar script de monitoramento leve
# Adicionar ao crontab (a cada 15 min):
*/15 * * * * grep "API key expired" /var/log/syslog | grep "$(date +%Y-%m-%d)" | \
  tail -1 | grep -q "API key expired" && \
  curl -s -X POST "$DISCORD_WEBHOOK" \
    -d '{"content":"🔑 nox-mem: Gemini API key expirada detectada no syslog. Renovar imediatamente."}' \
    -H "Content-Type: application/json" || true
```

---

## 5. Procedimento de Revisão Manual (drift > 100)

Quando orphans > 100, **não usar auto re-embed**. Seguir:

### Passo 1: Identificar causa

```bash
# Checar logs de embedding dos últimos 2 dias
grep -E "gemini|embed|vectorize|400|expired" /var/log/syslog | \
  grep "$(date +%Y-%m-%d)" | head -50

# Checar saúde da API Gemini
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('error', {}).get('message', 'OK'))"
```

### Passo 2: Classificar orphans por data de criação

```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT
    date(c.created_at) as day,
    c.chunk_type,
    count(*) as cnt
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL
  GROUP BY day, c.chunk_type
  ORDER BY day DESC;
"
```

### Passo 3: Se key expirada → renovar, depois re-embed

```bash
# No VPS:
# 1. Editar /root/.openclaw/.env — atualizar GEMINI_API_KEY
# 2. Recarregar env
set -a; source /root/.openclaw/.env; set +a

# 3. Dry-run para confirmar escopo
bash scripts/re-embed-orphans.sh --dry-run

# 4. Executar com verbose
bash scripts/re-embed-orphans.sh --verbose

# 5. Validar
curl -s http://127.0.0.1:18802/api/health | jq .vectorCoverage
```

### Passo 4: Se schema change causou orphans

Verificar se alguma migration criou chunks sem trigger de embed:

```bash
# Checar ops_audit para operações destrutivas recentes
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT op_name, status, started_at, finished_at
  FROM ops_audit
  ORDER BY started_at DESC
  LIMIT 20;
"
```

---

## 6. Métricas para Monitoring Dashboard

Adicionar ao dashboard existente:

```typescript
// src/api/health.ts — já expõe vectorCoverage
// Adicionar campo orphan_ids para diagnóstico:
const orphanIds = db.prepare(`
  SELECT c.id
  FROM chunks c
  LEFT JOIN vec_chunk_map m ON c.id = m.chunk_id
  WHERE m.chunk_id IS NULL
  LIMIT 10
`).pluck().all();

return {
  ...existing,
  vectorCoverage: {
    embedded,
    total,
    orphans: total - embedded,
    orphanSampleIds: orphanIds,  // sample para diagnóstico rápido
  }
};
```

---

## 7. Referências Cruzadas

- Incident raiz: `docs/incidents/2026-05-18-orphan-embeddings.md`
- Script de remediação: `scripts/re-embed-orphans.sh`
- Regra crítica §2 (CLAUDE.md): verificar `/api/health.vectorCoverage` pós-operação
- Regra crítica §3 (CLAUDE.md): modelo Gemini padrão = `gemini-2.5-flash-lite`
- `docs/MONITORING.md` (se existir) — adicionar link para este runbook na seção de alertas
