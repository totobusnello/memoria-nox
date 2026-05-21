# F10 — Observability Dashboard

> Static-HTML dashboard sobre dados que JÁ existem em `nox-mem.db` + `/api/health` + audits/data-*/ + journalctl shadow events. Sem stack nova (Grafana/Prometheus/time-series DB): leitura direta do SQLite. Phased rollout, P0 (Prod Health) implementation-ready em ~4h.

**Status:** REFRESH 2026-05-21 — design spec implementation-ready, Phase A scope-limited
**Data original:** 2026-05-01
**Data refresh:** 2026-05-21
**ID:** F10
**Vision §:** §10 (observability)
**Esforço estimado:** ~24h total spread 4 semanas (1 fase/semana); **Phase A standalone ~4h**
**Dependências:** `/api/health` endpoint (✅ existe), `ops_audit` cleaned (✅ PR #193), search_telemetry expanded (✅), shadow telemetry scrape (✅ D49 phase 2 running)
**Bloqueia:** D06 recall stats worker (pode ficar coberto por Phase B)
**Cross-ref:** `docs/ROADMAP.md` F10 row, `docs/RUNBOOKS.md`, `docs/VISION.md §10`, `audits/2026-05-21-opsaudit-hygiene-deployed.md`, `specs/d50-template.md`

---

## O que mudou desde 2026-05-01 (refresh rationale)

Spec original (2026-05-01) propunha Next.js + Vercel + recharts no `agent-hub-dashboard` repo, focado em time-series visualization via IndexedDB ring buffer. Refresh consolida 3 semanas de evolução observability:

- **`ops_audit` table cleaned** (PR #193, 2026-05-21) — Issue #1 (started_at TEXT chaos) + Issue #3 (test ops pollution) resolved. Data source agora confiável para timeline visualization.
- **`search_telemetry` expanded** (A0, 2026-04-25) — `+query_text +golden_id +top_chunk_ids +top_scores` (opt-in `NOX_SEARCH_LOG_TEXT=1`). Permite per-query drilldown impossível antes.
- **D49 phase 2 shadow telemetry rolling** (2026-05-20+) — `temporal_path` JSONL events sendo emitidos com signalSource + confidence tiers. Daily scrape cron já existe (`scrape-temporal-shadow.sh`).
- **G-series ablation artifacts** (G3 → G11) — historical eval scores stored em `audits/data-*/` (JSON + derived). Permite "score over time per config" sem rodar nada.
- **Schema invariants canary cron** (`*/15min`, F05) — write log `/var/log/nox-schema-invariants.log` + Discord webhook se quebra.

Refresh pivot:
- **Stack:** static HTML + lightweight charts (não Next.js/Vercel) — single-user dashboard, mantém regra "lean stack"
- **Persistence:** read direto do SQLite + audits/data-*/ + journalctl — NO time-series DB, NO IndexedDB ring buffer (data já persiste no DB de origem)
- **Phased:** P0 (Prod Health, 4h) independente; P1-P5 incrementais

---

## Problema

Hoje observamos saúde do nox-mem via canais fragmentados:
- **Pull manual** `curl /api/health | jq` durante session (sob demanda)
- **Cron canary** `*/15min` escreve em `/var/log/nox-schema-invariants.log` + Discord alert se quebra
- **Morning report** (briefing) summa health uma vez/dia
- **Audits dir** `audits/data-*/` armazena eval results mas sem visualização cumulativa
- **journalctl grep** para shadow telemetry (D49) — não-visual, requer comando

Gaps observados na semana 2026-05-17 → 2026-05-21:
- "Quanto tempo a vectorCoverage gap durou?" → grep journal
- "G5 V3 vs G6 vs G7 score trajectory?" → ler 3 JSON files separados
- "D49 shadow detection rate trending up?" → rodar scrape script manual
- "Quais ops crashed nas últimas 24h em qual db_source?" → SQL ad hoc
- Decisões de tuning reativas (após Discord alert), não proativas

---

## Data sources disponíveis (current state)

Inventário do que JÁ existe e pode ser consumido sem nova infra:

| Source | Schema/format | Cadência | Cobertura | Notas |
|---|---|---|---|---|
| `ops_audit` (SQLite) | INT started_at + status + db_source + op_name + duration_ms | event-driven | infinite (7d retention cron) | Cleaned PR #193 — types normalized, test-% filtered |
| `search_telemetry` (SQLite) | timestamp + query_text + golden_id + top_chunk_ids + top_scores + matchTypes + ms | per-query | opt-in via NOX_SEARCH_LOG_TEXT=1 | Expanded A0 2026-04-25 |
| `/api/health` endpoint | JSON snapshot — chunks count, vec coverage, salience mode, retention dist, KG counts, sectionDistribution | on-demand | live | Existing endpoint, no changes needed |
| `audits/data-G*/` | JSON eval results per config + Python aggregators | per ablation run | manual (G-series cadence) | G3 → G11 already stored |
| journalctl shadow logs | `temporal_path` JSONL events | per-query (when temporal detected) | D49 phase 2 active 2026-05-20+ | Scraper `scripts/scrape-temporal-shadow.sh` daily |
| `/var/log/nox-schema-invariants.log` | timestamped check results | `*/15min` cron | infinite | F05 canary |
| `kg_entities` + `kg_relations` (SQLite) | id + type + confidence + created_at | event-driven | infinite | Snapshot via `/api/health.knowledgeGraph` |

---

## Use cases (priority order)

### P0 — PROD HEALTH (Phase A, ~4h)

**Question:** "Está tudo OK agora?"

Single-page status pulled live from `/api/health` + last 5 entries from `ops_audit`:

- chunks.total + dbSizeMB (text + delta vs 24h ago)
- vectorCoverage.embedded / total + orphans (color-coded: green if embedded==total, red otherwise)
- NOX_SALIENCE_MODE (text: off/shadow/active)
- last cron success (timestamp + age) — read from `/var/log/nox-schema-invariants.log` tail
- recent failed/crashed ops 24h — table from ops_audit WHERE status IN ('failed','crashed')

Refresh: 30s polling. Render: HTML table + sparklines (no charts lib needed).

### P1 — EVAL DASHBOARD (Phase B, ~6h)

**Question:** "Como o score evoluiu por config ao longo de G3 → G+1?"

Historical view of G-series ablation results:

- Line chart: nDCG@10 over time per ablation row (A0/A5/A8/A10/...)
- Line chart: MRR over time same axis
- Anotações verticais: gate transitions (G5 V3 wave-A merge, G10 mutex deploy, G11 trim rejection, etc)
- Filter por DB (entity-eval.db / g5.db / entity-eval-v2.db) — crucial after G6 fiasco

Source: parse `audits/data-G*/aggregate.py` outputs OR pre-aggregate via build step.

### P2 — TELEMETRY DRILLDOWN (Phase C, ~4h)

**Question:** "Latência p95 está degradando? Qual reason?"

Per-query latency distribution from `search_telemetry`:

- Histogram: latency p50/p95/p99 per hour (24h window)
- Bar chart: semantic_ratio distribution per query
- Bar chart: expansion_enabled rate
- Pie chart: skip_reasons distribution (when applicable)
- Recent slow queries table (top 10 by ms) com expand para top_chunk_ids

Source: `SELECT * FROM search_telemetry WHERE timestamp > now - 24h`.

### P3 — SHADOW MODE TRACKER (Phase C continuation, ~4h)

**Question:** "D49 temporal shadow está catching queries? Confidence distribution?"

D49 phase 2 telemetry view:

- Line: temporal_path emit rate per hour (queries detected as temporal / total queries)
- Bar: signalSource distribution (iso_date / month_year / adverbial / keyword_inferred)
- Bar: confidence tiers (1.0 / 0.8 / 0.6 / 0.3) histogram
- Counter: cumulative events since shadow activation

Source: parse `scripts/scrape-temporal-shadow.sh aggregate Nd` JSON output (daily cron writes to `/var/log/nox-shadow-temporal/`).

Cross-link: ranking decision D50 (ETA 2026-05-27) — dashboard makes go/no-go visual.

### P4 — OPS AUDIT TIMELINE (Phase D, ~3h)

**Question:** "Quem crashed quando, em qual DB, qual op?"

Cleaned ops_audit visualization:

- Timeline plot: ops over 7d window, color-coded by status (success green / failed yellow / crashed red)
- Hover: op_name + duration_ms + db_source + reason
- Filter: by db_source (main / entity-eval / unknown)
- Filter: by op_name (regex)
- Retention: 7d (matches ops_audit retention cron)

Source: `SELECT * FROM ops_audit WHERE started_at > now - 7d`.

### P5 — KG STATS (Phase D continuation, ~3h)

**Question:** "Entidades + relações crescendo a que taxa? Extract mode mix?"

Knowledge graph growth view:

- Line: kg_entities + kg_relations count over time (snapshots from `/api/health.knowledgeGraph.history` — TBD if endpoint added)
- Bar: extract_mode distribution (regex / gemini / hybrid) from kg_relations metadata
- Histogram: confidence distribution
- Pie: entity types

Source: TBD — may need new endpoint `/api/health/kg-history` OR cron snapshot to `kg_snapshots` table (deferrable).

---

## Technology stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | Static HTML + vanilla JS + lightweight charts (chart.js OR sparklines) | NO React/Vue overhead; matches "lean stack" rule; deployable as single file |
| Backend | `/api/observability/{health,evals,telemetry,shadow,opsAudit,kg}` endpoints | Read-only; reuse existing nox-mem-api process (port 18802) |
| Data refresh | 30s polling P0; 5min P1-P5; manual reload OK | Single user = irrelevant load |
| Auth | localhost-only (18802 already bound localhost) OR Tailscale ACL | Matches existing access pattern; no new auth surface |
| Persistence | Read direct from nox-mem.db + audits/data-*/ + journalctl | NO separate metrics store; data já persiste no DB |
| Hosting | Sub-route `/observability/` no nox-mem-api OR `agent-hub-dashboard` (TBD — see Open Questions) | Avoid 2nd deploy target if possible |

---

## Implementation phases

| Phase | Scope | Effort | Pre-req |
|---|---|---|---|
| **A** | P0 Prod Health page — chunks, vec coverage, salience mode, last cron, recent crashed | **~4h** | None — ops_audit cleaned ✅ |
| **B** | P1 Eval dashboard reading `audits/data-*/` | ~6h | After Phase A live; audits/data-*/ structure stable |
| **C** | P2 Telemetry drilldown + P3 Shadow tracker | ~8h | After Phase B; D49 phase 2 baseline ≥ 7d collected |
| **D** | P4 Ops audit timeline + P5 KG stats | ~6h | After Phase C; may require `kg_snapshots` table for P5 |
| **Total** | All phases | **~24h** spread 4 weeks (one phase/week) | — |

**Critical:** Phase A standalone. Subsequent phases gated on Phase A acceptance + relevant data sources stabilizing.

---

## Phase A detalhada (implementation-ready)

### Endpoints novos

| Endpoint | Returns | Source |
|---|---|---|
| `GET /api/observability/health` | JSON: same shape as `/api/health` + delta vs 24h ago for key metrics | `/api/health` + cached snapshot 24h ago |
| `GET /api/observability/recent-ops?n=10` | JSON array: last N ops_audit rows where status IN ('failed','crashed') | `SELECT FROM ops_audit ORDER BY started_at DESC LIMIT N` |
| `GET /api/observability/canary-tail` | JSON: last 3 entries from `/var/log/nox-schema-invariants.log` | `tail -3` parsed |

### UI single page `observability/health.html`

```
┌──────────────────────────────────────────────────────────┐
│ nox-mem Health  ⚪ live (30s polling)         [Refresh]  │
├──────────────────────────────────────────────────────────┤
│ Chunks       │ 68,995  (+412 vs 24h ago)                 │
│ Vec coverage │ 100.0%  (68,995 / 68,995, 0 orphans)  🟢  │
│ Salience     │ shadow                                    │
│ DB size      │ 1.07 GB  (+8.2 MB vs 24h ago)             │
│ Last canary  │ 2026-05-21 14:45 UTC  (5min ago)  🟢      │
├──────────────────────────────────────────────────────────┤
│ Recent failed/crashed ops (24h)                          │
│ ┌─────────────────┬──────────┬───────────┬────────────┐  │
│ │ op_name         │ status   │ db_source │ when       │  │
│ ├─────────────────┼──────────┼───────────┼────────────┤  │
│ │ (vazio se all OK)                                   │  │
│ └─────────────────┴──────────┴───────────┴────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### Arquivos novos (Phase A)

| Arquivo | LOC | Descrição |
|---|---|---|
| `src/api/observability.ts` | ~120 | 3 endpoints (health/recent-ops/canary-tail) |
| `public/observability/health.html` | ~80 | Single static page |
| `public/observability/health.js` | ~150 | Polling + render + delta calc |
| `public/observability/health.css` | ~60 | Lean styling, monospace, color-coded health |

### Arquivos modificados (Phase A)

| Arquivo | Mudança |
|---|---|
| `src/api-server.ts` | Mount observability router em `/api/observability/*` |
| (none else) | Phase A é additive, zero risk |

---

## Non-goals (explicit)

| Item | Por que NÃO |
|---|---|
| Prometheus/Grafana integration | +200MB RAM permanent VPS + bus factor; lean stack rule violation |
| Time-series DB (InfluxDB/TimescaleDB) | Data já persiste em SQLite com timestamps; new store = drift risk |
| Alerting / pages / SMS | Cron canary `*/15min` + Discord webhook já cobre (F05) |
| Multi-user / RBAC | Single-user dashboard; complexity not warranted |
| Mobile-first responsive design | Toto consulta principalmente desktop; mobile = nice-to-have not blocker |
| Real-time updates via SSE everywhere | P5 viewer already has SSE for live events; observability dashboard polling (30s/5min) is sufficient |
| Annotations editor UI | Hardcode gate annotations em JSON file; full editor adds 4h+ for marginal value |
| Cross-VPS aggregation | Single VPS deployment; N/A |

---

## Riscos + mitigação

| Risco | Probabilidade | Mitigação |
|---|---|---|
| `/api/health` JSON shape muda → dashboard quebra silencioso | Média | TypeScript types em endpoint code + runtime guards na boundary |
| Polling satura nox-mem-api | Baixa | n=1 user (Toto); 30s polling = 2880 req/day = trivial |
| `audits/data-*/` directory structure muda (Phase B) | Média | Parse adapter layer; semver structure files |
| journalctl rotation drops shadow events (Phase C) | Média | Daily scrape cron writes to `/var/log/nox-shadow-temporal/` already persists |
| KG snapshots endpoint não existe (Phase D P5) | Alta | Phase D pode deferrar P5 até endpoint adicionado |
| db_source filter UX confusing post-G6 lesson | Média | Default filter "main" + dropdown to switch; document semantics inline |

---

## Open questions

1. **Onde hospedar UI?**
   - **Opção A:** Sub-route do nox-mem-api (`/observability/health.html` served from `public/`)
     - + Único deploy target; localhost-bound natural
     - − Mistura HTML+API no mesmo process
   - **Opção B:** `agent-hub-dashboard` repo (Next.js standalone)
     - + Separação de concerns; hub já existe
     - − 2nd deploy target; precisa Tailscale ACL cross-process
   - **Recomendação:** A (Phase A). Re-avaliar pre-Phase B.

2. **Embed em README hero OR standalone page?**
   - Live dashboard screenshot estático no README pode servir de marketing
   - Standalone page (Tailscale-only) é onde operação real acontece
   - **Recomendação:** standalone página + screenshot estático mensal no README (manual update)

3. **Real-time updates via SSE OR polling?**
   - P5 viewer já tem SSE infrastructure (`src/api/viewer-sse.ts`)
   - Polling 30s é mais simples + browser-tab-friendly
   - **Recomendação:** polling P0-P4. SSE só se P3 (shadow tracker) demandar < 30s latency.

4. **Phase A go-live antes ou depois de D50 decision (2026-05-27)?**
   - D50 vai gate temporal rerank active/off
   - Phase A é independente de D50 outcome
   - **Recomendação:** Phase A pode shipping antes; Phase C (P3 shadow tracker) depende de D49 estar shadow active (já está)

---

## Critérios de aceitação (Phase A)

- [ ] `/api/observability/health` retorna JSON com all 6 P0 metrics (chunks, vec coverage, salience, db size, last canary, recent crashed)
- [ ] `/api/observability/recent-ops` retorna últimas N falhas, formatted com timestamp + db_source
- [ ] `/api/observability/canary-tail` parsea last 3 linhas do log invariants
- [ ] HTML page renderiza com polling 30s + delta vs 24h ago calculated client-side
- [ ] Color-coded health indicators (🟢 OK / 🟡 warn / 🔴 crit) baseado em thresholds documented
- [ ] Acesso via `http://localhost:18802/observability/health.html` OU via Tailscale tunnel
- [ ] Zero overhead novo no VPS (apenas reads do DB já existente)
- [ ] 24h smoke test: polling estável, no memory leaks, no crashes

---

## Cross-reference

| Item | Onde |
|---|---|
| `ops_audit` cleaned | PR #193 + `audits/2026-05-21-opsaudit-hygiene-deployed.md` |
| `search_telemetry` A0 expansion | `[[a0-query-logging-extension]]` memory + commit 2026-04-25 |
| D49 phase 2 shadow data | `specs/d50-template.md` + `scripts/scrape-temporal-shadow.sh` |
| G-series ablation results | `audits/data-G*/` dirs |
| F05 canary invariants | `CLAUDE.md` regra 6 + `scripts/check-schema-invariants.sh` |
| Roadmap F10 | `docs/ROADMAP.md` Foundation table |
| `/api/health` endpoint | `src/api-server.ts` (port 18802) |

---

## Histórico

- **2026-05-01** — Spec original, status QUEUED, stack Next.js + agent-hub-dashboard
- **2026-05-21** — REFRESH. Stack pivot para static HTML; phased rollout; data sources inventariadas; Phase A implementation-ready

---

**Próximo passo:** se aprovado, kickoff PR para Phase A em branch `feat/F10-phase-a-prod-health` no `memoria-nox` repo (não `agent-hub-dashboard`). Time-box 4h Phase A.
