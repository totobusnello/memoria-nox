# MONITORING — nox-mem

> Versão: 1.0 — 2026-05-18
> Maintainer: ver `docs/HANDOFF.md`
> VPS path: `/root/.openclaw/workspace/tools/nox-mem/`
> API: `http://127.0.0.1:18802/`

---

## TL;DR — Checks manuais imediatos

```bash
# Liveness: serviço respondendo?
curl -sf http://127.0.0.1:18802/api/health | jq '{status, total, schemaVersion}'

# Latência: quanto tempo levou a última requisição?
time curl -sf "http://127.0.0.1:18802/api/search?q=salience&limit=3" > /dev/null

# Logs recentes
journalctl -u nox-mem-api --since "10 minutes ago" -n 50

# Disco: espaço livre
df -h /var/backups/nox-mem /root/.openclaw/workspace/tools/nox-mem/
```

---

## 1. O que Monitorar

### 1.1 Liveness

O serviço está respondendo? Porta 18802 está aberta?

```bash
# Ping básico
curl -sf --max-time 5 http://127.0.0.1:18802/api/health > /dev/null && echo "UP" || echo "DOWN"

# Processo rodando
systemctl is-active nox-mem-api
# active = OK; inactive/failed = problema

# Porta aberta
ss -tlnp | grep 18802
# Deve mostrar LISTEN na porta 18802
```

**Nota:** a porta é 18802, não 18800 (Chrome squata 18800 — CLAUDE.md regra #4).

### 1.2 Latência

Tempo de resposta dos endpoints principais.

```bash
# Tempo de search (inclui FTS5 + embedding + RRF)
time curl -sf "http://127.0.0.1:18802/api/search?q=salience&limit=5" > /dev/null

# Tempo de health (deve ser < 500ms)
time curl -sf http://127.0.0.1:18802/api/health > /dev/null

# Tempo de answer (inclui retrieval + LLM)
time curl -sf http://127.0.0.1:18802/api/answer \
  -X POST -H "Content-Type: application/json" \
  -d '{"question": "o que é salience?"}' > /dev/null
```

**Baseline de referência** (pós-fix wizard v.25, 2026-04-27): p50 search ~500ms, p50 answer ~3-5s.

### 1.3 Erros

Taxa de erros 5xx e falhas de provider.

```bash
# Ver erros recentes no journal
journalctl -u nox-mem-api --since "1 hour ago" | grep -i "error\|500\|fail" | tail -20

# Checar se embeddings estão parando de funcionar
curl -sf http://127.0.0.1:18802/api/health | jq .vectorCoverage
# Se embedded << total: embeddings não estão sendo gerados (checar GEMINI_API_KEY)
```

### 1.4 Recursos

CPU, memória, disco, file descriptors.

```bash
# CPU + memória do processo nox-mem-api
systemctl status nox-mem-api | grep -E "CPU|Memory"
# Ou via ps:
ps aux | grep "node.*dist/index" | grep -v grep

# Disco — DB size e backups
du -sh /root/.openclaw/workspace/tools/nox-mem/nox-mem.db
du -sh /var/backups/nox-mem/

# Disco disponível
df -h /root/

# File descriptors (SQLite + better-sqlite3 pode abrir muitos fd em WAL mode)
ls /proc/$(pgrep -f "nox-mem-api")/fd 2>/dev/null | wc -l
```

### 1.5 Quotas de Provider

Gemini tem limite diário. Ultrapassar estoura silenciosamente e vetorização para.

```bash
# Checar uso de tokens de hoje (via provider_telemetry, Wave B+)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
  SELECT 
    SUM(tokens_in + tokens_out) as total_tokens_today,
    COUNT(*) as calls_today
  FROM provider_telemetry
  WHERE created_at >= date('now');
" 2>/dev/null || echo "provider_telemetry não disponível (pré-Wave-B)"

# Validar que chave Gemini ainda responde
curl -s --max-time 10 \
  "https://generativelanguage.googleapis.com/v1beta/models?key=${GEMINI_API_KEY}" \
  | jq '.error.code // "OK"'
# OK = chave válida e com quota
# 429 = quota esgotada
# 401 = chave inválida/revogada
```

**Regra:** usar `gemini-2.5-flash-lite` (CLAUDE.md regra #3). Nunca voltar para `gemini-2.5-flash` (quota 3M/d estoura com carga normal).

### 1.6 Schema

user_version correto? integrity_check passou?

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Schema version
sqlite3 ${NM}/nox-mem.db "PRAGMA user_version;"
# Esperado: 20 (pós-Wave-B) ou 10 (baseline)

# Integrity check rápido
sqlite3 ${NM}/nox-mem.db "PRAGMA quick_check;"
# Deve retornar: ok

# Integrity check completo (mais lento, usar com parcimônia)
sqlite3 ${NM}/nox-mem.db "PRAGMA integrity_check;"
# Deve retornar: ok
```

### 1.7 Audit

`ops_audit` crescendo de forma anômala? Operações stuck em `started`?

```bash
export NM=/root/.openclaw/workspace/tools/nox-mem

# Operações recentes
sqlite3 ${NM}/nox-mem.db "
  SELECT op_name, status, started_at 
  FROM ops_audit 
  ORDER BY started_at DESC 
  LIMIT 10;
"

# Operações stuck em 'started' há mais de 1h (possível crash)
sqlite3 ${NM}/nox-mem.db "
  SELECT id, op_name, started_at
  FROM ops_audit
  WHERE status = 'started'
    AND datetime(started_at) < datetime('now', '-1 hour');
"
# Qualquer resultado aqui = operação que crashou sem atualizar status
```

---

## 2. Métricas expostas em /api/health

Endpoint canonical: `GET http://127.0.0.1:18802/api/health`

### 2.1 Campos atuais (pré-Wave-B e pós-Wave-B)

```bash
curl -sf http://127.0.0.1:18802/api/health | jq
```

Campos de saída esperados:

| Campo | Tipo | Descrição | Valor saudável |
|---|---|---|---|
| `status` | string | Estado geral do serviço | `"ok"` |
| `total` | number | Total de chunks ativos | >= 62000 |
| `embedded` | number | Chunks com embedding | == `total` (idealmente) |
| `schemaVersion` | number | PRAGMA user_version | 20 (pós-Wave-B) |
| `dbSizeMB` | number | Tamanho do DB em MB | < 5000 (alerta acima de 8GB) |
| `vectorCoverage` | object | `{embedded, total}` | `embedded == total` |
| `sectionDistribution` | object | Contagem por section | `.compiled >= 183` |
| `salience.mode` | string | Modo do salience formula | `"shadow"` (até ativação) |
| `kg_entities` | number | Entidades no KG | ~402 |
| `kg_relations` | number | Relações no KG | ~544 |
| `opsAudit` | object | Resumo do ops_audit | `recentFailed == 0` idealmente |

### 2.2 Campos futuros — candidatos para Wave G/I

Estes campos **não existem ainda** e são candidatos para sprints futuros:

| Campo | Sprint | Descrição |
|---|---|---|
| `requestRate.last1min` | Wave G | Requisições por segundo (janela 1min) |
| `requestRate.last5min` | Wave G | Requisições por segundo (janela 5min) |
| `latencyP95ms` | Wave G | Latência P95 em ms (janela 5min rolling) |
| `errorRate5xx` | Wave G | Taxa de erros 5xx (%) |
| `providerCallsToday` | Wave G | Chamadas Gemini hoje |
| `providerTokensToday` | Wave G | Tokens Gemini hoje |

---

## 3. Alerting Rules

### 3.1 CRITICAL — Agir imediatamente

| Condição | Check | Ação |
|---|---|---|
| Processo down > 1 min | `systemctl is-active nox-mem-api` != `active` | `systemctl restart nox-mem-api` |
| Disco > 90% cheio | `df /root/` > 90% | Limpar backups antigos, investigar crescimento anômalo |
| integrity_check FAIL | `PRAGMA integrity_check` != `ok` | Ver DISASTER-RECOVERY SCENARIO B |
| API retorna 500 em > 5% das chamadas (5min) | `journalctl -u nox-mem-api` | Checar logs, reiniciar se necessário |

### 3.2 HIGH — Agir durante horário comercial

| Condição | Check | Ação |
|---|---|---|
| Latência P95 > 5x baseline | `time curl /api/search` | Investigar: DB lock? Provider lento? CPU? |
| Memória > 80% sustained 10min | `systemctl status` Memory | Verificar leak, reiniciar serviço |
| Token usage > 80% cap diário | `provider_telemetry` | Reduzir frequência de vetorização, não fazer KG extract até renovar |
| `embedded` << `total` por > 1h | `/api/health.vectorCoverage` | Checar GEMINI_API_KEY, rodar `nox-mem vectorize` manualmente |

### 3.3 MEDIUM — Próximo dia útil

| Condição | Check | Ação |
|---|---|---|
| Rate de 4xx > 10% | `journalctl` | Clientes com configs erradas? |
| `sectionDistribution.compiled` < 183 | `/api/health.sectionDistribution` | Entity chunks corrompidos — ver SCENARIO F |
| ops_audit stuck em `started` > 1h | query ops_audit | Marcar como `crashed` se processo não existe mais |
| Nenhum backup nightly nos últimos 2 dias | `ls -lt /var/backups/nox-mem/nightly/` | Checar cron, rodar backup manual |

### 3.4 LOW — Resumo semanal

| Condição | Check | Frequência |
|---|---|---|
| Tendência de crescimento de disco | `du -sh` trends | Semanal |
| Tendência de crescimento de chunks | `/api/health.total` | Semanal |
| Volume de telemetria (search + answer) | `COUNT(*) FROM search_telemetry` | Semanal |

---

## 4. Stack de Monitoramento

### 4.1 Lightweight (estado atual — recomendado enquanto sistema pequeno)

Cron + curl + log files. Zero infraestrutura extra.

**Implementação atual:**
- `backup-all.sh` roda às 02:00 BRT e gera log
- `check-schema-invariants.sh` roda a cada 15 minutos (memória: `a3-a4-invariants-canary`) e envia alerta Discord se falhar
- `sync-verify` grava heartbeat em `shared/agent-activity.log` (memória: `sync-verify-activity-log`)

**Script de health check via cron (lightweight)**:

```bash
#!/bin/bash
# /root/.openclaw/workspace/scripts/health-check.sh
# Adicionar ao crontab: */5 * * * * /root/.openclaw/workspace/scripts/health-check.sh

set -a; source /root/.openclaw/.env; set +a

HEALTH=$(curl -sf --max-time 10 http://127.0.0.1:18802/api/health 2>&1)
STATUS=$(echo "${HEALTH}" | jq -r .status 2>/dev/null)

if [ "${STATUS}" != "ok" ]; then
  echo "$(date -u) ALERT: nox-mem-api unhealthy: ${HEALTH}" \
    >> /var/log/nox-mem-alerts.log
  # Opcional: Discord webhook
  # curl -s -X POST "${DISCORD_WEBHOOK}" \
  #   -H "Content-Type: application/json" \
  #   -d "{\"content\": \"ALERTA: nox-mem-api unhealthy — $(date -u)\"}"
fi
```

### 4.2 Medium — Prometheus + Grafana (recomendado quando escalar)

Quando a complexidade justificar (múltiplos usuários, SLA formal, ou DB > 2GB):

**Arquitetura:**
```
nox-mem-api → /metrics endpoint (novo) → Prometheus scrape → Grafana visualização
```

**Endpoint `/metrics` (futuro — Wave I candidate):**
```
# HELP nox_chunks_total Total de chunks ativos
# TYPE nox_chunks_total gauge
nox_chunks_total 62836

# HELP nox_embeddings_coverage_ratio Cobertura de embeddings (0-1)
# TYPE nox_embeddings_coverage_ratio gauge
nox_embeddings_coverage_ratio 0.9997

# HELP nox_search_latency_seconds Latência de search (histogram)
# TYPE nox_search_latency_seconds histogram
nox_search_latency_seconds_bucket{le="0.5"} 234
nox_search_latency_seconds_bucket{le="1.0"} 489
...

# HELP nox_provider_tokens_total Total de tokens usados por provider hoje
# TYPE nox_provider_tokens_total counter
nox_provider_tokens_total{provider="gemini",direction="in"} 1234567
nox_provider_tokens_total{provider="gemini",direction="out"} 987654
```

### 4.3 Heavy — Datadog / New Relic (não recomendado agora)

Custo não justificado para o volume atual. Reconsiderar quando:
- Múltiplos usuários pagantes (SLA contratual)
- > 1M chunks
- Equipe de engenharia > 2 pessoas

---

## 5. Estratégia de Logging

### 5.1 Logs atuais

Os logs do serviço ficam no systemd journal:

```bash
# Ver logs em tempo real
journalctl -u nox-mem-api -f

# Ver últimos 100 lines
journalctl -u nox-mem-api -n 100

# Ver logs das últimas 2 horas
journalctl -u nox-mem-api --since "2 hours ago"

# Filtrar por nível (erro)
journalctl -u nox-mem-api -p err --since today

# Logs com contexto de timestamp UTC
journalctl -u nox-mem-api --since today --output=json | \
  jq '[.REALTIME_TIMESTAMP // "?", .MESSAGE] | @tsv'
```

**Retenção:** journald default (7 dias ou tamanho máximo configurado).

### 5.2 PII scrubbing

Logs de operações em `src/lib/op-audit.ts` já fazem redação de dados sensíveis via privacy filter (Wave B staged-privacy). Verificar:

```bash
# Garantir que chaves de API não aparecem em logs
journalctl -u nox-mem-api --since today | grep -i "GEMINI_API\|ANTHROPIC\|sk-ant" | wc -l
# Deve retornar: 0
```

### 5.3 Logs estruturados (futuro — Wave I candidate)

Atualmente os logs são texto livre. Para análise automática e alertas sofisticados, migrar para JSON estruturado:

```json
{
  "ts": "2026-05-18T15:34:22.123Z",
  "level": "info",
  "op": "search",
  "query_hash": "sha256:ab12...",
  "results_count": 5,
  "duration_ms": 487,
  "pipeline": ["fts5", "semantic", "rrf"],
  "session_id": "s-abc123"
}
```

Esta é uma refatoração não-trivial (modifica output de todos os handlers). Candidata a Wave I.

---

## 6. Dashboard — Descrição das Tiles

Uma implementação visual completa (Grafana ou UI própria) teria as seguintes tiles:

### Tile 1: Corpus Health

```
+----------------------------------+
| Chunks Total: 62,836             |
| Delta últimas 24h: +142          |
| Embeddings: 62,830 (99.99%)      |
| Entities: 402 | Relations: 544   |
+----------------------------------+
```

Fonte: `/api/health` polling a cada 5min.

### Tile 2: Latência P95 — Search (linha de tendência 24h)

```
+----------------------------------+
| Search P95: 842ms                |
| Baseline: ~500ms                 |
| Trend: ↑ 12% (24h)               |
| [linha chart 24h]                |
+----------------------------------+
```

Fonte: `search_telemetry.duration_ms` (Wave A0 — disponível via `PRAGMA user_version >= 11`).

### Tile 3: Taxa de Erros por Endpoint

```
+----------------------------------+
| /api/search:  0.1% 5xx           |
| /api/answer:  0.0% 5xx           |
| /api/health:  0.0% 5xx           |
| [stack chart 24h]                |
+----------------------------------+
```

Fonte: journal logs + futura tabela `request_log`.

### Tile 4: Uso de Tokens Gemini

```
+----------------------------------+
| Hoje: 1.2M / 3M cap (40%)       |
| Estimativa custo: $0.003         |
| Provider: gemini-2.5-flash-lite  |
| [gauge]                          |
+----------------------------------+
```

Fonte: `provider_telemetry` (Wave B — disponível via `PRAGMA user_version >= 11`).

### Tile 5: Schema + Integridade

```
+----------------------------------+
| Schema: v20 (OK)                 |
| Last integrity_check: PASSED     |
| Checado há: 4h 32min             |
| Disk: 1.2GB / 40GB (3%)          |
+----------------------------------+
```

Fonte: cron check + `/api/health.schemaVersion`.

### Tile 6: Operações Recentes (ops_audit tail)

```
+----------------------------------+
| 14:22 reindex success (47s)      |
| 12:01 consolidate success (12s)  |
| 02:00 backup-all success (8s)    |
| [tabela scrollável]              |
+----------------------------------+
```

Fonte: `ops_audit` ORDER BY started_at DESC LIMIT 10.

---

## 7. Roadmap de Implementação

### Fase 1 (este doc) — Documentação

Estado atual: este arquivo documenta o que monitorar, quais métricas existem e onde buscar. Sem nova implementação.

### Fase 2 (sprint futuro) — Extensões de /api/health

Adicionar ao endpoint existente:

```typescript
// Candidatos para Wave G
{
  requestRatePerMin: computeRollingRate(1),   // últimos 60s
  latencyP95ms: computeP95(300),              // últimos 5min
  errorRate5xx: computeErrorRate(300),         // últimos 5min
  providerCallsToday: queryProviderTelemetry(),
  providerTokensToday: queryProviderTokens(),
}
```

Estimativa de esforço: 4-6h (backend + testes).

### Fase 3 (sprint futuro) — Prometheus Exporter

Novo endpoint `GET /metrics` com output no formato Prometheus text exposition format.

Estimativa de esforço: 8-12h.

### Fase 4 (sprint futuro) — Grafana Dashboard JSON

Dashboard declarativo (arquivo `.json`) importável no Grafana. Inclui as 6 tiles descritas acima.

Estimativa de esforço: 6-8h (após Fase 3).

### Fase 5 (sprint futuro) — Alertas Automáticos

Regras de alertas wired em Discord webhook ou PagerDuty baseadas nas métricas Prometheus.

Estimativa de esforço: 4-6h (após Fase 3).

---

## 8. Checks de Estado Rápido (one-liner bundle)

Para uso em triagem rápida de incidente:

```bash
#!/bin/bash
# /root/.openclaw/workspace/scripts/triage.sh
# Bundle de checks de leitura — não modifica nada

set -a; source /root/.openclaw/.env; set +a
NM=/root/.openclaw/workspace/tools/nox-mem

echo "=== LIVENESS ==="
systemctl is-active nox-mem-api
curl -sf --max-time 5 http://127.0.0.1:18802/api/health | \
  jq '{status, total, embedded, schemaVersion, dbSizeMB}'

echo ""
echo "=== VECTOR COVERAGE ==="
curl -sf http://127.0.0.1:18802/api/health | jq .vectorCoverage

echo ""
echo "=== SECTION DISTRIBUTION ==="
curl -sf http://127.0.0.1:18802/api/health | jq .sectionDistribution

echo ""
echo "=== RECENTES OPS_AUDIT ==="
sqlite3 ${NM}/nox-mem.db "
  SELECT op_name, status, started_at
  FROM ops_audit
  ORDER BY started_at DESC
  LIMIT 5;
"

echo ""
echo "=== DISCO ==="
df -h /root/ | tail -1
du -sh ${NM}/nox-mem.db
du -sh /var/backups/nox-mem/

echo ""
echo "=== LOGS RECENTES (5min) ==="
journalctl -u nox-mem-api --since "5 minutes ago" -n 20
```

---

## 9. Referências cruzadas

| Tópico | Documento |
|---|---|
| Recovery procedures quando alerta dispara | `docs/ops/DISASTER-RECOVERY.md` |
| Backup commands e restore | `docs/ops/BACKUP-RUNBOOK.md` |
| Regras críticas operacionais | `CLAUDE.md §Regras críticas` |
| Deploy commands | `docs/DEPLOY-WAVE-B.md` |
| Incident log histórico | `docs/INCIDENTS.md` |
| Audit canary invariants | `scripts/check-schema-invariants.sh` |

---

*Preparado: 2026-05-18 | Wave H — Operational Readiness*
