# F10 — Observability Dashboard

> Time-series view de `/api/health` metrics no `agent-hub-dashboard` existente. Polling cliente-side, store no IndexedDB do dashboard. Sem stack nova (Grafana/Prometheus): reusa infra atual.

**Status:** Design spec (📋 QUEUED)
**Data:** 2026-05-01
**ID novo:** F10
**Vision §:** §10 (observability)
**Esforço estimado:** 2-3h (greenfield 0.7× — código novo no dashboard externo)
**Dependências:** `agent-hub-dashboard` repo + `/api/health` endpoint (✅ existem)
**Bloqueia:** D06 recall stats worker (revisitar Jul antes de R01a) — F10 dashboard pode cobrir
**Cross-ref:** `docs/ROADMAP.md` F10 row, `docs/RUNBOOKS.md` (acionado por dashboard alerts), `docs/VISION.md §10`

---

## Problema

Hoje observamos saúde do nox-mem via:
- **Pull manual** `curl /api/health | jq` durante session (sob demanda)
- **Cron canary** `*/15min` que escreve em `/var/log/nox-schema-invariants.log` + Discord se quebra
- **Morning report** (briefing) que summa health uma vez/dia

Sem trend visualization:
- "Quanto tempo a vectorCoverage gap durou?" requer grep journal
- "Salience formula mean estabilizou ou está drifting?" requer rodar manual
- "QPS do search subiu pós-G02?" inacessível sem agregação
- Decisões de tuning são reativas (após Discord alert), não proativas
- R01a baseline metrics em `evalMetrics` só fazem sentido com trend ao longo do tempo

---

## Solução: time-series view no agent-hub-dashboard

### Por que NÃO Grafana + Prometheus

1. **Stack lean violation** — Grafana + Prometheus + node_exporter = +200MB RAM permanente na VPS
2. **Bus factor** — mais um stack pra Toto manter solo
3. **Setup time** — 8-15h vs 2-3h reuso
4. **agent-hub-dashboard já existe** — React + Tailwind + Vercel deploy; consumindo `/api/health` direto

### Arquitetura proposta

```
┌────────────────────────────────────────────────────────┐
│ agent-hub-dashboard (Vercel + Next.js, existente)      │
│ ┌──────────────────────────────────────────────────┐   │
│ │ Página nox-mem-trends (NOVA)                     │   │
│ │ ─────────────────────────                        │   │
│ │ Polling client-side: setInterval(fetch, 60s)     │   │
│ │ Cada poll → push to IndexedDB ring buffer 7d     │   │
│ │ Charts via recharts (já dep do dashboard)         │   │
│ └──────────────────────────────────────────────────┘   │
└─────────────────────┬──────────────────────────────────┘
                      │ HTTPS poll /api/health
                      ▼
┌────────────────────────────────────────────────────────┐
│ nox-mem-api (porta 18802 VPS, behind Tailscale)        │
│ /api/health → JSON (existente, no changes needed)      │
└────────────────────────────────────────────────────────┘
```

### Painéis (4 inicial)

#### 1. Storage growth
- Line chart: `chunks.total` por dia (7d window)
- Area: `dbSizeMB` mesmo eixo
- Anotações verticais: gates aplicados (G01 04-30, G02 05-01, etc)

#### 2. Search health
- Line: `vectorCoverage.embedded / total` % (esperado 100%)
- Bar: `searchTelemetry.recentQueries` por hora
- Heatmap: `searchTelemetry.matchTypes` (fts/semantic/hybrid distribution)

#### 3. Salience + ranking
- Line: `salience.mean` + `salience.median`
- Stacked bar: `archive_candidates / review_needed / retain / promote_candidates`
- Line: `sectionDistribution.compiled/frontmatter/timeline` overtime

#### 4. KG growth
- Line: `knowledgeGraph.entities` + `knowledgeGraph.relations`
- Quando E05 active: line `relations.byConfidence` distribution

#### 5 (futuro, post-R01a)
- `evalMetrics.byVariant.{hybrid,fts,vector}.ndcg_at_10` over time
- Compare runs side-by-side

### Storage strategy

```typescript
// Cliente-side IndexedDB (não no servidor — mantém VPS lean):
interface HealthSnapshot {
  ts: number;          // unix ms
  health: object;      // raw /api/health response
}

// Ring buffer:
// - Max 10080 entries (7d × 24h × 60min @ 1/min) ~5MB localStorage
// - Older snapshots dropped FIFO
// - On reload, fetch /api/health.history if backend supports it (futuro)
```

**Trade-off:** se browser fechado, polling para. Aceitável — dashboard é human-driven, não alerting (Discord canary cobre alerting).

### Pulling cadence

- **Default:** 60s polling (1 sample/min, cheap)
- **Sob janela ativa:** 30s polling (mais responsivo)
- **Background tab:** 5min polling (poupa bateria/dados)
- **Pause:** se 401 (Tailscale fora) ou 5xx >3 consecutivos, pausar 5min

---

## Implementação

### Arquivos novos no agent-hub-dashboard

| Arquivo | LOC | Descrição |
|---|---|---|
| `src/pages/nox-mem-trends.tsx` | ~120 | Página principal com 4 painéis |
| `src/lib/health-poller.ts` | ~80 | Polling logic + IndexedDB ring buffer |
| `src/components/charts/StorageGrowth.tsx` | ~60 | Painel 1 |
| `src/components/charts/SearchHealth.tsx` | ~80 | Painel 2 |
| `src/components/charts/SalienceTrends.tsx` | ~70 | Painel 3 |
| `src/components/charts/KGGrowth.tsx` | ~60 | Painel 4 |
| `src/lib/idb-ringbuffer.ts` | ~40 | IndexedDB wrapper |

### Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `src/pages/index.tsx` | Adicionar link "nox-mem trends" no nav |
| `package.json` | Confirmar `recharts` + `idb-keyval` (ou similar) listados |

### Features futuras (não v1)

- `/api/health/history?since=<ts>` endpoint server-side pra backfill quando dashboard reload (depende de tabela `health_snapshots` no nox-mem.db)
- Annotations layer (gates, releases, incidents) via JSON manual em `dashboard/annotations.json`
- Slack/Discord webhook quando user clica "anotar" no chart
- Export PNG/PDF dos 4 painéis pra HANDOFF docs

---

## Observability gaps que F10 NÃO cobre

(Documentar pra evitar scope creep)

| Gap | Quem cobre |
|---|---|
| Real-time alerting (Discord) | Cron canary `*/15min` (F05, existente) |
| Log search/grep | journalctl direto (RB-* runbooks) |
| Distributed tracing | Não há sistema distribuído (single VPS) — N/A |
| APM transaction breakdown | `/api/health.searchTelemetry` p50/p95 + grep journal logs |
| Cost/billing trends | F13 cost projection cron monthly (separado) |

---

## Critérios de aceitação

- [ ] Página `nox-mem-trends` deployada em Vercel + acessível via Tailscale
- [ ] 4 painéis renderizam com dados ao vivo (polling 60s)
- [ ] IndexedDB ring buffer persiste entre reloads
- [ ] Annotations verticais para G01/G02/G03 hardcoded como exemplo
- [ ] Mobile-responsive (Toto consulta de iPhone)
- [ ] Zero overhead novo no VPS (apenas polling reads)

---

## Estimativa por etapa (2-3h)

| Etapa | Esforço |
|---|---|
| `health-poller.ts` + IndexedDB ring buffer | 0.5h |
| 4 chart components com recharts | 1h |
| Página `nox-mem-trends.tsx` integrando | 0.5h |
| Annotations + responsive polish | 0.5h |
| Smoke test 24h + adjust | 0.5h |
| **TOTAL** | **2.5-3h** |

Velocity 0.7× greenfield já aplicada — 4-4.3h se projeto sem dashboard existente; aqui reuso reduz pra 2.5-3h.

---

## Riscos + mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| `/api/health` JSON shape muda → dashboard quebra silencioso | Média | TypeScript types + runtime guards (zod) na boundary do fetch |
| Polling 1/min × N usuários satura nox-mem-api | Baixa | n=1 user (Toto) — irrelevante. Re-avaliar em P01 multi-tenant |
| IndexedDB quota cap 50MB browser | Baixa | Ring buffer 7d ~5MB << cap |
| Tailscale offline = 0 dados | Baixa | Aceitável — alerting via Discord canary independente |
| Annotation manual stale (G02 esquecido de adicionar) | Média | v2: ler `docs/HANDOFF.md` parsing pattern `[YYYY-MM-DD] Gate Gxx ✅` |

---

## Cross-reference

| Item | Onde |
|---|---|
| `agent-hub-dashboard` repo | github.com/totobusnello/agent-hub-dashboard |
| `/api/health` endpoint | nox-mem-api porta 18802 |
| F05 canary invariants (alerting) | `CLAUDE.md` regra 6 + `docs/RUNBOOKS.md#rb-03` |
| D06 (recall stats worker) cobertura | `docs/ROADMAP.md` Deferred table |
| Roadmap F10 | `docs/ROADMAP.md` Foundation table |

---

**Próximo passo:** revisar com Toto → se aprovado, branch `feat/F10-observability` no `agent-hub-dashboard` repo, executar 2.5-3h.
