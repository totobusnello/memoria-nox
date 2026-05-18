# nox-mem Grafana Dashboard Spec — Wave K

> **Status:** specification (Wave K, 2026-05-18). Grafana dashboard JSON importável
> (Phase 4) depende do Prometheus exporter estar wired (Phase 3 — staged-prometheus,
> Wave J). Ver seção [Pré-requisitos](#pré-requisitos) antes de importar.
>
> Métricas Prometheus: `staged-prometheus/edits/docs/PROMETHEUS-METRICS.md` (28 métricas).
> Monitoring doc: `docs/ops/MONITORING.md`.

---

## Hierarquia visual

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ROW 1 — STAT PANELS (4 panels, largura 6 cada)                            │
│  [Chunks Total] [Search p95 ms] [Cost/day USD] [Error Rate %]              │
├─────────────────────────────────────────────────────────────────────────────┤
│  ROW 2 — LINE CHARTS (3 panels, largura 8 cada)                            │
│  [Search latency 24h] [Answer latency 24h] [Embed latency 24h]            │
├─────────────────────────────────────────────────────────────────────────────┤
│  ROW 3 — HEATMAPS + GROWTH (3 panels, largura 8 cada)                     │
│  [KG entities+relations growth] [conflict_audit growth] [Hooks pipeline]  │
├────────────────────────────────────────────────────────────────────────────┤
│  SIDE PANEL — ALERTS ACTIVE (largura 24, coluna de alertas, collapsed)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pré-requisitos

Antes de importar o dashboard, os seguintes items devem estar wired:

| Item | Status | Ação necessária |
|------|--------|-----------------|
| `/metrics` endpoint ativo | Wave J staged — não merged | Merge staged-prometheus; montar endpoint em `src/api/server.ts` |
| `nox_search_duration_seconds` histogram | Definido em PROMETHEUS-METRICS.md §3.2 | Wire `recordSearch()` em search handler |
| `nox_answer_duration_seconds` histogram | Definido em §3.3 | Wire `withAnswerMetrics()` adapter (P1-adapter) |
| `nox_provider_duration_seconds` histogram | Definido em §3.4 | Wire `instrumentProviderCall()` em provider chain (A3-adapter) |
| `nox_provider_cost_usd_total` counter | Definido em §3.4 | Wire cost recording no CostCappedProvider |
| `nox_chunks_active` gauge | Definido em §3.7 | Wire `startDbStatsCollector()` no bootstrap |
| `nox_kg_entities_total` counter | Definido em §3.1 | Wire `recordKgEntity()` em kg-extract |
| `nox_kg_relations_total` counter | Definido em §3.1 | Wire `recordKgRelation()` em kg-extract |
| `nox_viewer_connections` gauge | Definido em §3.6 | Wire `trackConnection()` no SSE handler (P5-adapter) |
| `nox_hooks_events_total` counter | Definido em §3.5 | Wire `recordHookEvent()` no hooks pipeline (P2) |
| Prometheus scrape configurado | — | Ver `prometheus.yml` config em PROMETHEUS-METRICS.md §8 |

Métricas não wired aparecem como `No data` nos panels — não causam crash do dashboard.

---

## Row 1 — Stat Panels

### Panel 1: Chunks Total

```json
{
  "id": 1,
  "type": "stat",
  "title": "Chunks Total",
  "gridPos": { "x": 0, "y": 0, "w": 6, "h": 4 },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"] },
    "colorMode": "background",
    "graphMode": "area",
    "textMode": "auto",
    "thresholds": {
      "mode": "absolute",
      "steps": [
        { "color": "green", "value": null },
        { "color": "yellow", "value": 100000 },
        { "color": "red", "value": 500000 }
      ]
    }
  },
  "targets": [
    {
      "expr": "nox_chunks_active",
      "legendFormat": "active",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": {}
    }
  }
}
```

**Fonte:** `nox_chunks_active` gauge (coleta periódica via `startDbStatsCollector`, intervalo 30s).
**Baseline:** 62.9k (2026-05-18 v3.7). Alerta se delta > -10% (chunks perdidos).

---

### Panel 2: Search Latency p95

```json
{
  "id": 2,
  "type": "stat",
  "title": "Search Latency p95",
  "gridPos": { "x": 6, "y": 0, "w": 6, "h": 4 },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"] },
    "colorMode": "background",
    "thresholds": {
      "mode": "absolute",
      "steps": [
        { "color": "green", "value": null },
        { "color": "yellow", "value": 1000 },
        { "color": "red", "value": 2500 }
      ]
    }
  },
  "targets": [
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000",
      "legendFormat": "p95 ms",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ms",
      "custom": {}
    }
  }
}
```

**Fonte:** `nox_search_duration_seconds` histogram, janela 5m rolling.
**Baseline:** ~500ms p50 (pós wizard v.25, 2026-04-27). p95 alvo ≤ 2500ms (5x baseline).
**Sem dados:** check se `/metrics` está ativo e `recordSearch()` está wired.

---

### Panel 3: Provider Cost / Day

```json
{
  "id": 3,
  "type": "stat",
  "title": "Provider Cost / Day (USD)",
  "gridPos": { "x": 12, "y": 0, "w": 6, "h": 4 },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"] },
    "colorMode": "background",
    "thresholds": {
      "mode": "absolute",
      "steps": [
        { "color": "green", "value": null },
        { "color": "yellow", "value": 0.50 },
        { "color": "red", "value": 1.00 }
      ]
    }
  },
  "targets": [
    {
      "expr": "increase(nox_provider_cost_usd_total[24h])",
      "legendFormat": "cost 24h",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "currencyUSD",
      "decimals": 4,
      "custom": {}
    }
  }
}
```

**Fonte:** `nox_provider_cost_usd_total` counter, janela 24h increase.
**Baseline:** ~$0.17/day (10k queries/mo ÷ 30d, Gemini flash-lite). Alerta NoxMemProviderCostDailyCap em $10/24h.
**Derivado:** `nox:provider_cost_24h_usd` recording rule (PROMETHEUS-METRICS.md §8).

---

### Panel 4: Error Rate (5xx)

```json
{
  "id": 4,
  "type": "stat",
  "title": "Error Rate (answer failures)",
  "gridPos": { "x": 18, "y": 0, "w": 6, "h": 4 },
  "options": {
    "reduceOptions": { "calcs": ["lastNotNull"] },
    "colorMode": "background",
    "thresholds": {
      "mode": "absolute",
      "steps": [
        { "color": "green", "value": null },
        { "color": "yellow", "value": 0.05 },
        { "color": "red", "value": 0.10 }
      ]
    }
  },
  "targets": [
    {
      "expr": "sum(rate(nox_answer_requests_total{failure_reason!=\"success\"}[5m])) / sum(rate(nox_answer_requests_total[5m]))",
      "legendFormat": "error rate",
      "refId": "A"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "percentunit",
      "custom": {}
    }
  }
}
```

**Fonte:** `nox_answer_requests_total` counter, ratio failure vs total.
**Alerta:** NoxMemAnswerFailureSpike (>10% em 5min, PROMETHEUS-METRICS.md §8).

---

## Row 2 — Line Charts (latência 24h)

### Panel 5: Search Latency 24h

```json
{
  "id": 5,
  "type": "timeseries",
  "title": "Search Latency 24h (p50 / p95 / p99)",
  "gridPos": { "x": 0, "y": 5, "w": 8, "h": 8 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "histogram_quantile(0.50, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000",
      "legendFormat": "p50",
      "refId": "A"
    },
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000",
      "legendFormat": "p95",
      "refId": "B"
    },
    {
      "expr": "histogram_quantile(0.99, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000",
      "legendFormat": "p99",
      "refId": "C"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ms",
      "custom": {
        "lineWidth": 2,
        "fillOpacity": 10
      }
    },
    "overrides": [
      { "matcher": { "id": "byName", "options": "p95" }, "properties": [{ "id": "color", "value": { "fixedColor": "orange", "mode": "fixed" } }] },
      { "matcher": { "id": "byName", "options": "p99" }, "properties": [{ "id": "color", "value": { "fixedColor": "red", "mode": "fixed" } }] }
    ]
  }
}
```

**Fonte:** `nox_search_duration_seconds` histogram.
**Recording rule:** `nox:search_p99_seconds` (PROMETHEUS-METRICS.md §8).
**Baseline:** p50 ~500ms. Alerta NoxMemSearchP99High (>2s por 10min).

---

### Panel 6: Answer Latency 24h

```json
{
  "id": 6,
  "type": "timeseries",
  "title": "Answer Latency 24h — per phase (total / retrieve / synthesize)",
  "gridPos": { "x": 8, "y": 5, "w": 8, "h": 8 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"total\"}[5m]))) * 1000",
      "legendFormat": "total p95",
      "refId": "A"
    },
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"retrieve\"}[5m]))) * 1000",
      "legendFormat": "retrieve p95",
      "refId": "B"
    },
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"synthesize\"}[5m]))) * 1000",
      "legendFormat": "synthesize p95",
      "refId": "C"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ms",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

**Fonte:** `nox_answer_duration_seconds` histogram, label `phase` ∈ {total, retrieve, rerank, synthesize, verify}.
**Baseline P1 bench (mock LLM 100ms):** total p95 = 101.7ms. Real Gemini flash-lite adiciona ~1000-3000ms no phase synthesize.
**Recording rule:** `nox:answer_p95_seconds`.

---

### Panel 7: Embed Latency 24h

```json
{
  "id": 7,
  "type": "timeseries",
  "title": "Embed (Provider) Latency 24h — Gemini flash-lite",
  "gridPos": { "x": 16, "y": 5, "w": 8, "h": 8 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "histogram_quantile(0.50, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"embedding\"}[5m]))) * 1000",
      "legendFormat": "embed p50",
      "refId": "A"
    },
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"embedding\"}[5m]))) * 1000",
      "legendFormat": "embed p95",
      "refId": "B"
    },
    {
      "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"llm\"}[5m]))) * 1000",
      "legendFormat": "llm p95",
      "refId": "C"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ms",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

**Fonte:** `nox_provider_duration_seconds` histogram, label `kind` ∈ {embedding, llm}.
**Nota A3:** abstraction layer overhead = ~0.002ms abs em zero-network mock. In prod, dominado pela latência Gemini (~200ms+ network).

---

## Row 3 — Heatmaps + Crescimento

### Panel 8: KG Growth

```json
{
  "id": 8,
  "type": "timeseries",
  "title": "KG Growth (entities + relations / 24h)",
  "gridPos": { "x": 0, "y": 14, "w": 8, "h": 7 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "increase(nox_kg_entities_total[24h])",
      "legendFormat": "entities +24h",
      "refId": "A"
    },
    {
      "expr": "increase(nox_kg_relations_total[24h])",
      "legendFormat": "relations +24h",
      "refId": "B"
    },
    {
      "expr": "increase(nox_chunks_total[24h])",
      "legendFormat": "chunks +24h",
      "refId": "C"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

**Fonte:** `nox_kg_entities_total`, `nox_kg_relations_total`, `nox_chunks_total` — counters cumulativos.
**Baseline:** ~402 entities, ~544 relations (v3.7 snapshot 2026-05-01). Corpus cresceu 20.8k → 62.9k chunks em 1 dia (2026-04-27 sprint).

---

### Panel 9: Conflict Audit Growth

```json
{
  "id": 9,
  "type": "timeseries",
  "title": "Audit Table Write Rates (ops_audit / answer_telemetry / search_telemetry)",
  "gridPos": { "x": 8, "y": 14, "w": 8, "h": 7 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "rate(nox_audit_rows_total{table=\"ops_audit\"}[5m])",
      "legendFormat": "ops_audit",
      "refId": "A"
    },
    {
      "expr": "rate(nox_audit_rows_total{table=\"answer_telemetry\"}[5m])",
      "legendFormat": "answer_telemetry",
      "refId": "B"
    },
    {
      "expr": "rate(nox_audit_rows_total{table=\"search_telemetry\"}[5m])",
      "legendFormat": "search_telemetry",
      "refId": "C"
    },
    {
      "expr": "rate(nox_audit_rows_total{table=\"provider_telemetry\"}[5m])",
      "legendFormat": "provider_telemetry",
      "refId": "D"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ops",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

**Fonte:** `nox_audit_rows_total` counter, label `table` ∈ {ops_audit, provider_telemetry, search_telemetry, agent_events, answer_telemetry}.
**Nota:** `ops_audit` é append-only (triggers CWE-693 — DELETE/UPDATE bloqueados em rows terminais). Crescimento anômalo pode indicar cron loops.

---

### Panel 10: Hooks Pipeline + Viewer

```json
{
  "id": 10,
  "type": "timeseries",
  "title": "Hooks Capture + Viewer Backpressure",
  "gridPos": { "x": 16, "y": 14, "w": 8, "h": 7 },
  "options": {
    "tooltip": { "mode": "multi", "sort": "none" },
    "legend": { "displayMode": "list", "placement": "bottom" }
  },
  "targets": [
    {
      "expr": "sum by (reason) (rate(nox_hooks_events_total{reason=\"captured\"}[5m]))",
      "legendFormat": "hooks captured/s",
      "refId": "A"
    },
    {
      "expr": "sum by (reason) (rate(nox_hooks_events_total{reason=\"filtered\"}[5m]))",
      "legendFormat": "hooks filtered/s",
      "refId": "B"
    },
    {
      "expr": "rate(nox_viewer_dropped_total[5m])",
      "legendFormat": "viewer dropped/s",
      "refId": "C"
    },
    {
      "expr": "nox_viewer_connections",
      "legendFormat": "viewer open connections",
      "refId": "D"
    }
  ],
  "fieldConfig": {
    "defaults": {
      "unit": "ops",
      "custom": { "lineWidth": 2, "fillOpacity": 10 }
    }
  }
}
```

**Fonte:** `nox_hooks_events_total` (P2), `nox_viewer_connections` + `nox_viewer_dropped_total` (P5).
**Alerta:** NoxMemViewerBackpressureDrops (>1 drop/s por 10min, PROMETHEUS-METRICS.md §8).

---

## Side Panel — Alerts Active

```json
{
  "id": 11,
  "type": "alertlist",
  "title": "Alerts Active",
  "gridPos": { "x": 0, "y": 22, "w": 24, "h": 6 },
  "options": {
    "alertName": "",
    "dashboardAlerts": false,
    "groupMode": "tags",
    "groupBy": ["severity"],
    "maxItems": 20,
    "showStateHistory": true,
    "sortOrder": 1,
    "stateFilter": {
      "firing": true,
      "pending": true,
      "noData": false,
      "normal": false,
      "error": false
    }
  }
}
```

**Alerting rules wired** (definidas em PROMETHEUS-METRICS.md §8, requerem Phase 5):

| Alert name | Condição | Severidade |
|------------|----------|------------|
| `NoxMemSearchP99High` | search p99 > 2s por 10min | warning |
| `NoxMemAnswerFailureSpike` | answer error rate > 10% em 5min | critical |
| `NoxMemProviderCostDailyCap` | provider cost > $10/24h por 30min | warning |
| `NoxMemViewerBackpressureDrops` | viewer drops > 1/s por 10min | warning |
| `NoxMemDbSizeGrowth` | DB projetado > 30GB em 7d | warning |
| `NoxMemEventLoopLag` | nodejs_eventloop_lag_seconds > 100ms por 5min | warning |

---

## Dashboard JSON completo (importável)

```json
{
  "title": "nox-mem — overview",
  "uid": "nox-mem-overview-wave-k",
  "schemaVersion": 38,
  "version": 1,
  "timezone": "browser",
  "refresh": "30s",
  "time": { "from": "now-24h", "to": "now" },
  "timepicker": {},
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": { "type": "grafana", "uid": "-- Grafana --" },
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "tags": ["nox-mem", "wave-k", "memory"],
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "Chunks Total",
      "gridPos": { "x": 0, "y": 0, "w": 6, "h": 4 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"] },
        "colorMode": "background",
        "graphMode": "area",
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "green", "value": null },
            { "color": "yellow", "value": 100000 },
            { "color": "red", "value": 500000 }
          ]
        }
      },
      "targets": [
        { "expr": "nox_chunks_active", "legendFormat": "active", "refId": "A" }
      ],
      "fieldConfig": { "defaults": { "unit": "short" } }
    },
    {
      "id": 2,
      "type": "stat",
      "title": "Search p95 (ms)",
      "gridPos": { "x": 6, "y": 0, "w": 6, "h": 4 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"] },
        "colorMode": "background",
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "green", "value": null },
            { "color": "yellow", "value": 1000 },
            { "color": "red", "value": 2500 }
          ]
        }
      },
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000",
          "legendFormat": "p95 ms",
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": { "unit": "ms" } }
    },
    {
      "id": 3,
      "type": "stat",
      "title": "Provider Cost / Day (USD)",
      "gridPos": { "x": 12, "y": 0, "w": 6, "h": 4 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"] },
        "colorMode": "background",
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "green", "value": null },
            { "color": "yellow", "value": 0.50 },
            { "color": "red", "value": 1.00 }
          ]
        }
      },
      "targets": [
        {
          "expr": "increase(nox_provider_cost_usd_total[24h])",
          "legendFormat": "cost 24h",
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": { "unit": "currencyUSD", "decimals": 4 } }
    },
    {
      "id": 4,
      "type": "stat",
      "title": "Answer Error Rate",
      "gridPos": { "x": 18, "y": 0, "w": 6, "h": 4 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"] },
        "colorMode": "background",
        "thresholds": {
          "mode": "absolute",
          "steps": [
            { "color": "green", "value": null },
            { "color": "yellow", "value": 0.05 },
            { "color": "red", "value": 0.10 }
          ]
        }
      },
      "targets": [
        {
          "expr": "sum(rate(nox_answer_requests_total{failure_reason!=\"success\"}[5m])) / sum(rate(nox_answer_requests_total[5m]))",
          "legendFormat": "error rate",
          "refId": "A"
        }
      ],
      "fieldConfig": { "defaults": { "unit": "percentunit" } }
    },
    {
      "id": 5,
      "type": "timeseries",
      "title": "Search Latency 24h (p50 / p95 / p99)",
      "gridPos": { "x": 0, "y": 5, "w": 8, "h": 8 },
      "targets": [
        { "expr": "histogram_quantile(0.50, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000", "legendFormat": "p50", "refId": "A" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000", "legendFormat": "p95", "refId": "B" },
        { "expr": "histogram_quantile(0.99, sum by (le) (rate(nox_search_duration_seconds_bucket[5m]))) * 1000", "legendFormat": "p99", "refId": "C" }
      ],
      "fieldConfig": { "defaults": { "unit": "ms", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 6,
      "type": "timeseries",
      "title": "Answer Latency 24h — per phase",
      "gridPos": { "x": 8, "y": 5, "w": 8, "h": 8 },
      "targets": [
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"total\"}[5m]))) * 1000", "legendFormat": "total p95", "refId": "A" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"retrieve\"}[5m]))) * 1000", "legendFormat": "retrieve p95", "refId": "B" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_answer_duration_seconds_bucket{phase=\"synthesize\"}[5m]))) * 1000", "legendFormat": "synthesize p95", "refId": "C" }
      ],
      "fieldConfig": { "defaults": { "unit": "ms", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 7,
      "type": "timeseries",
      "title": "Embed / LLM Provider Latency 24h",
      "gridPos": { "x": 16, "y": 5, "w": 8, "h": 8 },
      "targets": [
        { "expr": "histogram_quantile(0.50, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"embedding\"}[5m]))) * 1000", "legendFormat": "embed p50", "refId": "A" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"embedding\"}[5m]))) * 1000", "legendFormat": "embed p95", "refId": "B" },
        { "expr": "histogram_quantile(0.95, sum by (le) (rate(nox_provider_duration_seconds_bucket{kind=\"llm\"}[5m]))) * 1000", "legendFormat": "llm p95", "refId": "C" }
      ],
      "fieldConfig": { "defaults": { "unit": "ms", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 8,
      "type": "timeseries",
      "title": "KG Growth (entities + relations / 24h)",
      "gridPos": { "x": 0, "y": 14, "w": 8, "h": 7 },
      "targets": [
        { "expr": "increase(nox_kg_entities_total[24h])", "legendFormat": "entities +24h", "refId": "A" },
        { "expr": "increase(nox_kg_relations_total[24h])", "legendFormat": "relations +24h", "refId": "B" },
        { "expr": "increase(nox_chunks_total[24h])", "legendFormat": "chunks +24h", "refId": "C" }
      ],
      "fieldConfig": { "defaults": { "unit": "short", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 9,
      "type": "timeseries",
      "title": "Audit Table Write Rates",
      "gridPos": { "x": 8, "y": 14, "w": 8, "h": 7 },
      "targets": [
        { "expr": "rate(nox_audit_rows_total{table=\"ops_audit\"}[5m])", "legendFormat": "ops_audit", "refId": "A" },
        { "expr": "rate(nox_audit_rows_total{table=\"answer_telemetry\"}[5m])", "legendFormat": "answer_telemetry", "refId": "B" },
        { "expr": "rate(nox_audit_rows_total{table=\"search_telemetry\"}[5m])", "legendFormat": "search_telemetry", "refId": "C" },
        { "expr": "rate(nox_audit_rows_total{table=\"provider_telemetry\"}[5m])", "legendFormat": "provider_telemetry", "refId": "D" }
      ],
      "fieldConfig": { "defaults": { "unit": "ops", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 10,
      "type": "timeseries",
      "title": "Hooks Capture + Viewer Backpressure",
      "gridPos": { "x": 16, "y": 14, "w": 8, "h": 7 },
      "targets": [
        { "expr": "sum by (reason) (rate(nox_hooks_events_total{reason=\"captured\"}[5m]))", "legendFormat": "hooks captured/s", "refId": "A" },
        { "expr": "sum by (reason) (rate(nox_hooks_events_total{reason=\"filtered\"}[5m]))", "legendFormat": "hooks filtered/s", "refId": "B" },
        { "expr": "rate(nox_viewer_dropped_total[5m])", "legendFormat": "viewer dropped/s", "refId": "C" },
        { "expr": "nox_viewer_connections", "legendFormat": "viewer connections", "refId": "D" }
      ],
      "fieldConfig": { "defaults": { "unit": "ops", "custom": { "lineWidth": 2, "fillOpacity": 10 } } }
    },
    {
      "id": 11,
      "type": "alertlist",
      "title": "Alerts Active",
      "gridPos": { "x": 0, "y": 22, "w": 24, "h": 6 },
      "options": {
        "alertName": "",
        "dashboardAlerts": false,
        "groupMode": "tags",
        "groupBy": ["severity"],
        "maxItems": 20,
        "showStateHistory": true,
        "stateFilter": {
          "firing": true,
          "pending": true,
          "noData": false,
          "normal": false,
          "error": false
        }
      }
    }
  ]
}
```

---

## Cross-links de métricas (wiring checklist)

Cada linha indica qual arquivo precisa ser editado para que o panel correspondente
receba dados. Nenhuma dessas edições faz parte do Wave K — são dependências de
sprints anteriores (Wave J staged-prometheus) e futuros.

| Panel | Métrica Prometheus | Arquivo a editar | Função |
|-------|--------------------|-----------------|--------|
| Chunks Total | `nox_chunks_active` | `src/api/server.ts` (bootstrap) | `startDbStatsCollector()` |
| Search p95 | `nox_search_duration_seconds` | `src/handlers/search.ts` | `recordSearch()` |
| Answer Error Rate | `nox_answer_requests_total` | `src/handlers/answer.ts` | `withAnswerMetrics()` adapter |
| Cost/Day | `nox_provider_cost_usd_total` | `src/providers/llm/chain.ts` | `instrumentProviderCall()` |
| Search Latency 24h | `nox_search_duration_seconds` | mesma acima | — |
| Answer Latency 24h | `nox_answer_duration_seconds` | `src/handlers/answer.ts` | `withAnswerMetrics()` |
| Embed Latency 24h | `nox_provider_duration_seconds` | `src/providers/embedding/gemini.ts` | `instrumentProviderCall()` |
| KG Growth | `nox_kg_entities_total`, `nox_kg_relations_total`, `nox_chunks_total` | `src/lib/kg-extract/*.ts` | `recordKgEntity()`, `recordKgRelation()`, `recordChunkIngest()` |
| Audit Rates | `nox_audit_rows_total` | `src/lib/op-audit.ts` | `recordAuditWrite()` |
| Hooks + Viewer | `nox_hooks_events_total`, `nox_viewer_*` | `src/hooks/*.ts`, `src/sse/*.ts` | `recordHookEvent()`, `trackConnection()`, `wrapBroadcast()` |

Recording API completa: `staged-prometheus/edits/docs/PROMETHEUS-METRICS.md §4`.

---

## Números de referência para threshold tuning

Extraídos de `benchmark/baseline-2026-05-18.json` (Wave K):

| Métrica | Baseline | Budget / Alerta |
|---------|---------|----------------|
| Search latency p95 | ~500ms (VPS v.25 p50) | Alerta: >2500ms (5x baseline) |
| Answer latency p95 (total, mock LLM 100ms) | 101.7ms | Budget: 4300ms |
| Answer non-LLM overhead p95 | 0.38ms | — |
| Provider abstraction overhead (embed+LLM abs) | ~0.002ms | <0.5ms |
| Export plain 500 chunks p50 | 168ms | — |
| Import plain 500 chunks p50 | 17ms | — |
| Export encrypted 500 chunks | 288ms | — (KDF fixed cost) |
| Import encrypted 500 chunks | 1144ms | — (KDF fixed cost) |
| Chunks active | 62,900 | Alerta: delta < -10% |
| KG entities | ~402 | Baseline v3.7 |
| KG relations | ~544 | Baseline v3.7 |
| Provider cost/day | ~$0.17 | Alerta: >$10/24h |

---

*Wave K — 2026-05-18. Dashboard Phase 4 depende de Phase 3 (Prometheus exporter
wired no staged-prometheus). Alerting Phase 5 depende de Phase 3 + configuração
do Prometheus alertmanager no VPS.*
