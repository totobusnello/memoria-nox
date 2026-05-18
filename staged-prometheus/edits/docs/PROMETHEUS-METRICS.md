# Prometheus / OpenMetrics Exporter — nox-mem

> MONITORING.md Phase 3. Status: implemented (staged-prometheus, Wave J, 2026-05-18).

This document describes the `/metrics` endpoint exposed by nox-mem, the metric
catalog, the wiring patterns for each pillar, and the privacy + cardinality
invariants that protect the endpoint from leaking data or blowing up storage.

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Endpoint `/metrics`](#2-endpoint-metrics)
3. [Catálogo de métricas](#3-catálogo-de-métricas)
4. [Recording API](#4-recording-api)
5. [Adapters por pilar](#5-adapters-por-pilar)
6. [Coletores periódicos](#6-coletores-periódicos)
7. [Cardinalidade e privacidade](#7-cardinalidade-e-privacidade)
8. [Config de scrape (Prometheus)](#8-config-de-scrape-prometheus)
9. [Esqueleto de dashboard Grafana](#9-esqueleto-de-dashboard-grafana)
10. [Operação](#10-operação)
11. [FAQ](#11-faq)

---

## 1. Visão geral

O exporter expõe métricas no formato **OpenMetrics 1.0** (compatível com
Prometheus 0.0.4+, VictoriaMetrics, Grafana Agent e qualquer scraper conforme
o padrão). Você habilita o endpoint dentro do `nox-mem-api` (porta 18802) e
um Prometheus externo coleta a cada 15-60s.

Pilares cobertos:

| Pilar | Sigla | Métricas principais |
|---|---|---|
| Search (hybrid BM25 + Gemini + RRF) | core | `nox_search_*` |
| Answer (P1, /api/answer) | P1 | `nox_answer_*` |
| Provider routing (A3) | A3 | `nox_provider_*` |
| Hooks auto-capture (P2) | P2 | `nox_hooks_*` |
| Viewer (P5 SSE bus) | P5 | `nox_viewer_*` |
| Pipeline / KG / Audit | core | `nox_chunks_*`, `nox_kg_*`, `nox_audit_*` |
| Runtime (Node) | runtime | `process_*`, `nodejs_*` |

Princípios de design (não-negociáveis):

- **Fire-and-forget**: gravação de métrica nunca lança erro nem bloqueia o hot path.
- **Cardinalidade bounded**: cada métrica tem `maxSeries` + allowlist de valores.
- **Sem PII**: query text, user_id, paths e chaves NUNCA aparecem em labels.
- **Sem dependência forte**: cada coletor é DB-agnostic via injection.

---

## 2. Endpoint `/metrics`

### URL

```
GET http://127.0.0.1:18802/metrics
```

### Headers

```
Content-Type: application/openmetrics-text; version=1.0.0; charset=utf-8
Cache-Control: no-store
X-Metrics-Snapshot-At: <unix-ms-da-coleta>
```

Se o cliente envia `Accept-Encoding: gzip`, o body retorna comprimido com
header `Content-Encoding: gzip`.

### Query params

| Param | Descrição |
|---|---|
| `names=m1,m2,m3` | Filtra a resposta para o conjunto de métricas (CSV). Útil pra dashboards que só consomem um subset. |

### Autenticação

Auth é **opt-in**: se a variável de ambiente `NOX_METRICS_TOKEN` estiver
definida, o exporter exige `Authorization: Bearer <token>`. Sem o env, o
endpoint fica aberto (assumindo bind em localhost ou rede privada).

```bash
# habilita auth
export NOX_METRICS_TOKEN="$(openssl rand -hex 32)"

# scrape autenticado
curl -H "Authorization: Bearer $NOX_METRICS_TOKEN" http://127.0.0.1:18802/metrics
```

### Exemplo de saída (truncado)

```text
# HELP nox_search_requests_total Total search requests handled.
# TYPE nox_search_requests_total counter
nox_search_requests_total{method="api",outcome="success"} 12345
nox_search_requests_total{method="cli",outcome="success"} 678
# HELP nox_search_duration_seconds End-to-end search latency in seconds.
# TYPE nox_search_duration_seconds histogram
# UNIT nox_search_duration_seconds seconds
nox_search_duration_seconds_bucket{le="0.001",method="api"} 0
nox_search_duration_seconds_bucket{le="0.01",method="api"} 4500
nox_search_duration_seconds_bucket{le="0.1",method="api"} 11800
nox_search_duration_seconds_bucket{le="0.5",method="api"} 12300
nox_search_duration_seconds_bucket{le="1",method="api"} 12340
nox_search_duration_seconds_bucket{le="5",method="api"} 12345
nox_search_duration_seconds_bucket{le="+Inf",method="api"} 12345
nox_search_duration_seconds_sum{method="api"} 482.13
nox_search_duration_seconds_count{method="api"} 12345
# EOF
```

---

## 3. Catálogo de métricas

Total: **28 métricas**. Cada bloco lista nome, tipo, labels e semântica.

### 3.1 Pipeline

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_chunks_total` | Counter | `provenance_kind` | Total de chunks ingeridos (cumulativo). |
| `nox_embeddings_total` | Counter | `provider`, `outcome` | Embeddings criados. |
| `nox_kg_entities_total` | Counter | `type` | Entidades KG criadas. |
| `nox_kg_relations_total` | Counter | `predicate` | Relações KG criadas. |

### 3.2 Search

| Métrica | Tipo | Labels | Buckets | Semântica |
|---|---|---|---|---|
| `nox_search_requests_total` | Counter | `method` (cli\|api\|mcp), `outcome` (success\|empty\|error) | — | Total de queries. |
| `nox_search_duration_seconds` | Histogram | `method` | `[0.001, 0.01, 0.1, 0.5, 1, 5]` | Latência end-to-end. |
| `nox_search_results_returned` | Histogram | `method` | `[1, 5, 10, 20, 50, 100]` | Distribuição de tamanho de resultado. |

### 3.3 Answer (P1)

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_answer_requests_total` | Counter | `failure_reason` (success\|no_chunks\|llm_failed\|hallucination\|timeout\|cost_cap) | Total de chamadas a `/api/answer`. |
| `nox_answer_duration_seconds` | Histogram | `phase` (total\|retrieve\|rerank\|synthesize\|verify) | Latência por fase. |
| `nox_answer_tokens_total` | Counter | `direction` (input\|output) | Total de tokens consumidos. |

### 3.4 Provider (A3)

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_provider_calls_total` | Counter | `provider`, `model`, `outcome` (success\|rate_limit\|error\|fallback) | Total de calls. |
| `nox_provider_duration_seconds` | Histogram | `provider`, `kind` (embedding\|llm) | Latência por provider. |
| `nox_provider_cost_usd_total` | Counter | `provider`, `model` | Custo cumulativo USD. |
| `nox_provider_tokens_total` | Counter | `provider`, `direction` | Tokens cumulativos. |

### 3.5 Hooks (P2)

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_hooks_events_total` | Counter | `layer` (pre-tool\|post-tool\|...), `reason` (captured\|filtered\|redacted\|error\|dropped) | Eventos capturados pelos hooks. |
| `nox_hooks_pipeline_duration_seconds` | Histogram | `layer` | Latência do pipeline de captura. |

### 3.6 Viewer (P5)

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_viewer_connections` | Gauge | — | Conexões SSE abertas no momento. |
| `nox_viewer_events_total` | Counter | `type` (ingest\|search\|kg_update\|answer\|provider_call\|audit\|hook\|other) | Eventos broadcast. |
| `nox_viewer_dropped_total` | Counter | `reason` (slow_consumer\|queue_full\|client_gone) | Drops por backpressure. |

### 3.7 Sistema

| Métrica | Tipo | Labels | Semântica |
|---|---|---|---|
| `nox_db_size_bytes` | Gauge | `component` (main\|wal\|shm) | Tamanho do arquivo SQLite. |
| `nox_chunks_active` | Gauge | — | Chunks ativos (provenance ≠ stale). |
| `nox_chunks_stale` | Gauge | — | Chunks marcados como stale. |
| `nox_audit_rows_total` | Counter | `table` (ops_audit\|provider_telemetry\|search_telemetry\|agent_events\|answer_telemetry) | Linhas escritas em tabelas de auditoria. |

### 3.8 Process / Runtime

| Métrica | Tipo | Semântica |
|---|---|---|
| `process_cpu_user_seconds_total` | Counter | CPU user cumulativa. |
| `process_cpu_system_seconds_total` | Counter | CPU system cumulativa. |
| `process_resident_memory_bytes` | Gauge | RSS atual. |
| `process_open_fds` | Gauge | FDs abertos (Linux only). |
| `nodejs_eventloop_lag_seconds` | Gauge | Lag médio do event loop desde o último sample. |

---

## 4. Recording API

A camada de gravação fica em `src/observability/record.ts`. **Sempre use as
funções `record*` — nunca chame `counter.inc()` direto.** Isso garante que
cardinalidade + privacy sejam aplicados em todos os pontos de captura.

### Search

```ts
import { recordSearch, startTimer } from "src/observability";

const end = startTimer();
const results = await hybridSearch(query);
recordSearch({
  method: "api",
  durationSeconds: end(),
  resultsCount: results.length,
  outcome: results.length === 0 ? "empty" : "success",
});
```

### Answer

```ts
import { recordAnswer } from "src/observability";

recordAnswer({
  outcome: "success",
  timing: {
    total: 0.85,
    retrieve: 0.12,
    rerank: 0.08,
    synthesize: 0.60,
    verify: 0.05,
  },
  tokensIn: 1240,
  tokensOut: 320,
});
```

### Provider

```ts
import { recordProviderCall } from "src/observability";

recordProviderCall({
  provider: "gemini",
  model: "gemini-2.5-flash-lite",
  kind: "llm",
  durationSeconds: 0.18,
  outcome: "success",
  costUsd: 0.00012,
  tokensIn: 800,
  tokensOut: 150,
});
```

### Pipeline / Hooks / Viewer

```ts
import {
  recordChunkIngest,
  recordEmbedding,
  recordKgEntity,
  recordKgRelation,
  recordHookEvent,
  recordViewerConnect,
  recordViewerEvent,
  recordViewerDropped,
  recordAuditWrite,
} from "src/observability";

recordChunkIngest({ provenanceKind: "fresh", count: 7 });
recordEmbedding({ provider: "gemini", outcome: "success", count: 7 });
recordKgEntity({ type: "person" });
recordKgRelation({ predicate: "advises" });
recordHookEvent({ layer: "post-tool", reason: "captured", durationSeconds: 0.001 });
recordViewerConnect();
recordViewerEvent("ingest");
recordViewerDropped("slow_consumer");
recordAuditWrite("ops_audit");
```

---

## 5. Adapters por pilar

Os adapters envelopam handlers existentes para emitir métricas sem invadir a
lógica de negócio.

### 5.1 P1 — Answer

`src/observability/adapters/p1-adapter.ts`

```ts
import { withAnswerMetrics } from "src/observability";

// 1 import + 1 wrapping call:
export const answerHandler = withAnswerMetrics(async (req, res) => {
  // … existing logic
  return { outcome: "success", tokensIn, tokensOut, timing };
});
```

### 5.2 A3 — Provider chain

`src/observability/adapters/a3-adapter.ts`

```ts
import { instrumentProviderCall } from "src/observability";

const out = await instrumentProviderCall(
  { provider: "gemini", model, kind: "llm" },
  async () => {
    const r = await callGemini(input);
    return {
      result: r,
      tokensIn: r.usage.in,
      tokensOut: r.usage.out,
      costUsd: estimateCost(r),
    };
  },
);
```

### 5.3 P5 — Viewer broadcast

`src/observability/adapters/p5-adapter.ts`

```ts
import { trackConnection, wrapBroadcast } from "src/observability";

const broadcast = wrapBroadcast(rawBroadcast);

sseRouter.get("/events", (req, res) => {
  trackConnection(res);
  subscribe((evt) => broadcast(evt));
});
```

Cada adapter custa **5-10 LOC** no call site.

---

## 6. Coletores periódicos

Coletores são pollers que enchem gauges (estado atual) ou drenam tabelas de
telemetria (incrementam counters). Inicialize-os no bootstrap do
`nox-mem-api`:

```ts
import {
  startProcessCollector,
  startDbStatsCollector,
  startSearchTelemetryCollector,
  startProviderTelemetryCollector,
  attachEventBusCollector,
} from "src/observability";

startProcessCollector({ intervalMs: 10_000 });
startDbStatsCollector({
  dbPath: process.env.NOX_DB_PATH!,
  query: (sql, params) => db.prepare(sql).all(...(params ?? [])),
  intervalMs: 30_000,
});
startSearchTelemetryCollector({
  query: (sql, params) => db.prepare(sql).all(...(params ?? [])),
  intervalMs: 5_000,
});
startProviderTelemetryCollector({
  query: (sql, params) => db.prepare(sql).all(...(params ?? [])),
  intervalMs: 5_000,
});
attachEventBusCollector(eventBus);
```

Características:

- **Idempotente**: chamar `start*` duas vezes é no-op.
- **Cursor-based**: telemetria avança via id watermark; reinício do processo
  não re-conta linhas antigas (cursor in-memory).
- **Tolerante a falha**: erros são engolidos, não derrubam o servidor.

---

## 7. Cardinalidade e privacidade

### 7.1 Cardinalidade — invariante

Cada métrica tem:

- `maxSeries`: cap absoluto (default 1000).
- `labelAllowlist`: valores aceitos; tudo fora → `"other"`.
- `labelDenylist`: chaves proibidas (user_id, query_text, path, ...).

Política aplicada **globalmente** (`applyDefaultPolicies()`):

```
FORBIDDEN_LABELS = [
  user_id, session_id, query, query_text, prompt, response,
  email, ip, path, filename, chunk_id, entity_id
]
```

Qualquer tentativa de incluir uma label proibida é silenciosamente dropada.
A primeira ocorrência em 60s emite warning no console:

```
[cardinality] dropped label-set for metric nox_search_requests_total (cap reached; total drops=1)
```

### 7.2 Privacidade — invariante

`privacy-guard.ts` aplica regex de strip antes da cardinalidade:

- Emails → `<redacted-email>`
- API keys (sk-…, AIza…, gsk_…) → `<redacted-key>`
- IPv4 → `<redacted-ip>`
- CPF, CNPJ, CEP (BR) → `<redacted-cpf>`, `<redacted-cnpj>`, `<redacted-cep>`
- Paths, URLs, UUIDs → tags próprias
- Qualquer valor > 64 chars, ou com espaços/SQL → `<redacted>`
- Qualquer label cujo nome contenha "query", "prompt", "user", "ip", ... → `<redacted>` forçado

### 7.3 Por que isso importa

Cardinalidade unbounded é o problema #1 de Prometheus em produção. Cada nova
combinação de labels = nova série = nova entrada em memória + disco do TSDB.
A história clássica: alguém usa `user_id` como label "pra debug" e em 1
semana o TSDB consome 200GB.

O guard composto **bloqueia tanto o vazamento de dados quanto a explosão de
recursos** com uma chamada única — `guardLabels(metricName, rawLabels)`.

---

## 8. Config de scrape (Prometheus)

`prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  scrape_timeout: 10s

scrape_configs:
  - job_name: nox-mem
    metrics_path: /metrics
    static_configs:
      - targets: ["127.0.0.1:18802"]
    # Opcional — Bearer auth
    authorization:
      type: Bearer
      credentials_file: /etc/prometheus/secrets/nox-metrics-token
    # Opcional — subset de métricas
    params:
      names: ["nox_search_requests_total","nox_answer_requests_total","nox_provider_cost_usd_total"]
```

Em VictoriaMetrics / vmagent o formato é idêntico — tem suporte nativo a
OpenMetrics.

### Recording rules sugeridas

```yaml
groups:
  - name: nox-mem.derived
    interval: 30s
    rules:
      - record: nox:search_p99_seconds
        expr: histogram_quantile(0.99, sum by (le, method) (rate(nox_search_duration_seconds_bucket[5m])))
      - record: nox:answer_p95_seconds
        expr: histogram_quantile(0.95, sum by (le, phase) (rate(nox_answer_duration_seconds_bucket[5m])))
      - record: nox:provider_cost_24h_usd
        expr: increase(nox_provider_cost_usd_total[24h])
      - record: nox:search_success_rate
        expr: |
          sum(rate(nox_search_requests_total{outcome="success"}[5m]))
          /
          sum(rate(nox_search_requests_total[5m]))
```

### Alerting rules sugeridas (Phase 5)

```yaml
groups:
  - name: nox-mem.alerts
    rules:
      - alert: NoxMemSearchP99High
        expr: nox:search_p99_seconds > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "nox-mem search p99 latency >2s (10 min)"
      - alert: NoxMemAnswerFailureSpike
        expr: |
          sum(rate(nox_answer_requests_total{failure_reason!="success"}[5m]))
            / sum(rate(nox_answer_requests_total[5m])) > 0.10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Answer error rate > 10% in last 5 min"
      - alert: NoxMemProviderCostDailyCap
        expr: nox:provider_cost_24h_usd > 10
        for: 30m
        labels:
          severity: warning
        annotations:
          summary: "Provider cost > $10 in the last 24h"
      - alert: NoxMemViewerBackpressureDrops
        expr: rate(nox_viewer_dropped_total[5m]) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Viewer events being dropped > 1/s"
      - alert: NoxMemDbSizeGrowth
        expr: predict_linear(nox_db_size_bytes{component="main"}[24h], 86400 * 7) > 30e9
        for: 6h
        labels:
          severity: warning
        annotations:
          summary: "DB projected to exceed 30GB in 7 days"
      - alert: NoxMemEventLoopLag
        expr: nodejs_eventloop_lag_seconds > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Node event loop lag > 100ms"
```

---

## 9. Esqueleto de dashboard Grafana

Pasta sugerida: `grafana/dashboards/nox-mem-overview.json`. Estrutura mínima:

```json
{
  "title": "nox-mem — overview",
  "uid": "nox-mem-overview",
  "schemaVersion": 38,
  "timezone": "browser",
  "refresh": "30s",
  "panels": [
    {
      "type": "stat",
      "title": "Search QPS",
      "targets": [
        {
          "expr": "sum(rate(nox_search_requests_total[1m]))",
          "refId": "A"
        }
      ]
    },
    {
      "type": "timeseries",
      "title": "Search p50 / p95 / p99 (s)",
      "targets": [
        { "expr": "histogram_quantile(0.50, sum by (le) (rate(nox_search_duration_seconds_bucket[5m])))", "legendFormat": "p50" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_search_duration_seconds_bucket[5m])))", "legendFormat": "p95" },
        { "expr": "histogram_quantile(0.99, sum by (le) (rate(nox_search_duration_seconds_bucket[5m])))", "legendFormat": "p99" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Answer outcome rate",
      "targets": [
        { "expr": "sum by (failure_reason) (rate(nox_answer_requests_total[5m]))", "legendFormat": "{{failure_reason}}" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Provider cost USD/h",
      "targets": [
        { "expr": "sum by (provider) (rate(nox_provider_cost_usd_total[5m])) * 3600", "legendFormat": "{{provider}}" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Provider error rate",
      "targets": [
        { "expr": "sum by (provider, outcome) (rate(nox_provider_calls_total{outcome!=\"success\"}[5m]))", "legendFormat": "{{provider}} {{outcome}}" }
      ]
    },
    {
      "type": "stat",
      "title": "DB size",
      "targets": [
        { "expr": "sum(nox_db_size_bytes)", "legendFormat": "total" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Chunks (active vs stale)",
      "targets": [
        { "expr": "nox_chunks_active", "legendFormat": "active" },
        { "expr": "nox_chunks_stale", "legendFormat": "stale" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Viewer connections + dropped",
      "targets": [
        { "expr": "nox_viewer_connections", "legendFormat": "open" },
        { "expr": "sum(rate(nox_viewer_dropped_total[5m]))", "legendFormat": "dropped/s" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Hook capture rate",
      "targets": [
        { "expr": "sum by (layer, reason) (rate(nox_hooks_events_total[5m]))", "legendFormat": "{{layer}} / {{reason}}" }
      ]
    },
    {
      "type": "timeseries",
      "title": "Process resources",
      "targets": [
        { "expr": "process_resident_memory_bytes", "legendFormat": "RSS" },
        { "expr": "rate(process_cpu_user_seconds_total[1m])", "legendFormat": "CPU user" },
        { "expr": "nodejs_eventloop_lag_seconds", "legendFormat": "EL lag" }
      ]
    }
  ]
}
```

O esqueleto cobre 10 painéis. O dashboard completo (Phase 4) acrescenta:

- Heatmaps de latência (search, answer, provider).
- Per-method e per-provider breakdowns.
- Cost budget vs realized (com annotation).
- KG growth (entities + relations).
- Audit table write rates.

---

## 10. Operação

### 10.1 Habilitando localmente

Em `src/api/server.ts` (ou onde quer que `app.listen()` aconteça), monte o
endpoint:

```ts
import { handle } from "src/observability";

app.get("/metrics", (req, res) => {
  const resp = handle(
    {
      searchParams: req.query as Record<string, string>,
      headers: req.headers,
    },
    {
      // token opcional via env
    },
  );
  res.status(resp.status);
  for (const [k, v] of Object.entries(resp.headers)) res.setHeader(k, v);
  res.send(resp.body);
});
```

### 10.2 Smoke test

```bash
curl -s http://127.0.0.1:18802/metrics | head -40
curl -sI -H "Accept-Encoding: gzip" http://127.0.0.1:18802/metrics
# Deve mostrar Content-Encoding: gzip
```

### 10.3 Filtragem

```bash
curl -s 'http://127.0.0.1:18802/metrics?names=nox_search_requests_total,nox_answer_requests_total'
```

### 10.4 Verificando cardinalidade no runtime

```ts
import { getDefaultRegistry } from "src/observability";

const reg = getDefaultRegistry();
console.log("total series:", reg.totalSeries());
console.log("names:", reg.names());
```

### 10.5 Rotação de token

```bash
new_token="$(openssl rand -hex 32)"
echo "$new_token" > /etc/prometheus/secrets/nox-metrics-token
chmod 0600 /etc/prometheus/secrets/nox-metrics-token
# atualizar nox-mem-api env:
sed -i "s/^NOX_METRICS_TOKEN=.*/NOX_METRICS_TOKEN=$new_token/" /root/.openclaw/.env
systemctl restart nox-mem-api
systemctl restart prometheus
```

### 10.6 Coletor manual em sessão de debug

```ts
import {
  collectProcessOnce,
  collectDbStats,
  drainSearchTelemetry,
} from "src/observability";

collectProcessOnce();
collectDbStats({ dbPath, query });
drainSearchTelemetry(query);
```

---

## 11. FAQ

### Por que não usar `prom-client` (lib oficial Node)?

Três motivos:

1. **Dependência**: nox-mem prioriza ESM minimal sem libs externas. Métrica é
   1 arquivo de tipos + 1 registry; libar isso pra dependência externa não
   reduz superfície.
2. **Cardinalidade**: `prom-client` não tem guard nativo. Você teria que
   reimplementar a denylist em cima dele. Mesma quantidade de código.
3. **Privacy**: a regra de não logar query text é específica de nox-mem.
   Coupar isso com o gravador é mais limpo que decorar uma lib de terceiros.

A API ainda é compatível — qualquer scraper Prometheus consome o output.

### Por que histogramas com 6 buckets e não SLO buckets exatos?

Buckets defaults `[0.001, 0.01, 0.1, 0.5, 1, 5]` cobrem latência de search
(p50 ~10ms, p99 ~500ms) e answer (p50 ~500ms, p99 ~3s). Você pode reconfigurar
por métrica no ponto de criação — basta passar buckets custom no construtor
`Histogram`. Manter defaults conservadores reduz cardinalidade (cada bucket
extra = +1 série por label-set).

### O endpoint é seguro de expor publicamente?

Não. Recomendação:

- Bind em `127.0.0.1` (default do nox-mem-api).
- Se acessível externamente, **sempre** com `NOX_METRICS_TOKEN`.
- Ou usar firewall iptables/nftables.
- Ou expor via reverse proxy com auth (nginx/Caddy).

### Como confirmar que privacy guard está ativo?

Rode em produção:

```bash
curl -s http://127.0.0.1:18802/metrics | grep -E '(user_id|query|email)'
```

Saída esperada: **vazia**. Se aparecer qualquer linha, é bug — abra issue.

### Como adicionar uma métrica nova?

1. Edite `src/observability/metrics.ts`, registre o `Counter`/`Gauge`/`Histogram`.
2. Adicione política em `src/observability/cardinality.ts` (allowlist + denylist).
3. Adicione função `record*` em `src/observability/record.ts`.
4. Exporte em `src/observability/index.ts`.
5. Adicione linha na seção 3 deste doc.
6. (Opcional) crie adapter em `src/observability/adapters/`.
7. Adicione teste em `__tests__/`.

---

*Última atualização: 2026-05-18 (Wave J). Próximas fases: Grafana
dashboard JSON completo (Phase 4), alerting rules wired no Prometheus
(Phase 5).*
