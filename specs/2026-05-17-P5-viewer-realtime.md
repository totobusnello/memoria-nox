# P5 — Real-time Viewer Upgrade (SSE + 4 panels)

> **Tagline:** *"See your memory grow as it grows."*
>
> Live observability surface pra **uma instância** de nox-mem. SSE-driven event feed + 4 painéis (live feed, counters, charts, heatmap) servidos pelo próprio `nox-mem-api` em `/viewer`. Complementa F10 (time-series no `agent-hub-dashboard`), não substitui.

**Status:** Design spec (📋 QUEUED — overnight 2026-05-17)
**Data:** 2026-05-17
**ID novo:** P5 (Q/A/P **P**roduct-surface pillar — observability é product surface, não infra)
**Vision §:** §10 (observability) + §11 (developer/operator UX)
**Esforço estimado:** 6-9h (server SSE 2h + emit hooks 2h + frontend 3-4h + tests 1h)
**Dependências:** `nox-mem-api` HTTP server (✅ existe em :18802) + chunks `INSERT` trigger (✅ existe) + KG incremental nightly (✅ existe) + search_telemetry (✅ existe via A0)
**Bloqueia:** nada hard. Soft: F10 polling page pode reciclar charts deste spec se conveniente.
**Cross-ref:** `docs/ROADMAP.md` (adicionar row), `docs/VISION.md §10/§11`, `specs/2026-05-01-F10-observability-dashboard.md` (relação de não-overlap), `reference_a0_query_logging_extension.md` (search_telemetry source)

---

## 1. Motivação

Observability hoje em nox-mem é **pull-based**:

- `curl /api/health | jq` sob demanda em SSH
- Cron canary `*/15min` → Discord alert se invariant break
- Morning report (briefing) summa health 1×/dia
- F10 (queued) traz time-series **polling 60s** no `agent-hub-dashboard` externo

**Lacuna percebida (Toto, sessões 2026-04 a 2026-05):**

> "*Não dá pra ver a memória crescer.*" — Quando ingest watch roda, quando entity é capturada, quando KG extrai relação — é tudo silencioso até alguém puxar health. Auto-capture ficou **4 dias zombie em graph-memory** (lesson `feedback_validate_features_with_db_not_logs.md`) porque logs falavam, DB não — observabilidade visual teria detectado em minutos.

**Competitor pattern (referência):** `agentmemory` (port 3113) tem viewer que streama memórias conforme nascem. UX **product surface**, não dev tool — vende confiança ("você está vendo a memória trabalhar").

**P5 entrega:**

- Live feed scrollando eventos conforme ingest/search/KG/provider rodam
- Counters tickando em tempo real (não em "refresh a cada 60s")
- Charts curtos (1h / 24h / 7d) que respondem "está saudável agora?"
- Heatmap de atividade ("quando minha memória está mais ativa?")

**P5 NÃO entrega:** time-series histórico de 7d+ (= F10), graph viz da KG (= v2), cross-agent aggregation (= F-series futuro).

---

## 2. Live signals to surface (v1 must-have)

| Kind | Payload metadata | Source | Privacy |
|------|------------------|--------|---------|
| `chunk.created` | `chunk_id`, `kind` (entity/event/code/file/note), `length`, `redaction_count`, `section` (compiled/frontmatter/timeline/null), `retention_days`, `pain` | trigger `trg_chunks_after_insert` OU emit explícito em `ingestFile()` / `routeIngest()` | NEVER raw content |
| `chunk.deleted` | `chunk_id`, `reason` (retention/dedup/manual) | trigger `trg_chunks_delete_cascade` | metadata only |
| `kg.entity.created` | `entity_id`, `entity_type`, `name_hash` (sha1 first 8 chars), `confidence` | `src/kg/extract.ts` post-insert hook | name **hashed**, never raw |
| `kg.relation.created` | `relation_id`, `source_entity_id`, `target_entity_id`, `relation_type`, `confidence` | same | FK ids only |
| `search.executed` | `query_hash` (sha1 first 8), `latency_ms`, `top_k`, `fts_contribution`, `vec_contribution`, `rrf_k`, `mode` (hybrid/fts/vec) | `src/search/hybrid.ts` post-query | query **hashed**, raw opt-in via `NOX_VIEWER_SHOW_QUERY=1` (off default) |
| `provider.call` | `provider` (gemini/anthropic), `model`, `op` (embedding/llm), `latency_ms`, `tokens_in`, `tokens_out`, `cost_usd_est` | `src/providers/*.ts` wrappers | no prompt content |
| `op_audit.started` | `op_id`, `op` (reindex/consolidate/crystallize/compact/kg-prune), `dry_run` | `withOpAudit()` enter | n/a |
| `op_audit.completed` | `op_id`, `op`, `status` (success/failed/crashed), `duration_ms`, `rows_affected` | `withOpAudit()` exit | n/a |
| `health.warning` | `metric`, `value`, `threshold`, `severity` (warn/critical) | invariants canary + health checker | n/a |

**Out-of-scope v1:** raw chunk content, raw query text (opt-in flag only), full KG entity name, prompt/response bodies.

---

## 3. Architecture

### 3.1 Server: SSE em `GET /api/events`

**Por quê SSE, não WebSocket:**

1. **Unidirecional** (server → client) — viewer só consome, não envia
2. **HTTP-native** — reusa `nox-mem-api` Express server em :18802, zero dep nova
3. **Reconnect built-in** — browser `EventSource` reconnecta automaticamente com `Last-Event-ID`
4. **Curl-debuggable** — `curl -N http://127.0.0.1:18802/api/events` printa eventos pra terminal
5. **Proxy-friendly** — passa através de reverse proxies sem upgrade handshake (corp setups)

### 3.2 Event bus interno (assumption — validar antes de implementar)

**Premissa P5:** `nox-mem-api` consegue receber `EventEmitter.emit()` calls dos módulos de ingest/search/kg/provider sem reestruturar arquitetura.

**Validation step (pré-implementação, 30min):**

```bash
# No VPS, rodar:
grep -rn "EventEmitter\|emit(" /root/.openclaw/workspace/tools/nox-mem/src/
grep -rn "app.get\|app.post" /root/.openclaw/workspace/tools/nox-mem/src/api/
```

**Se não houver event bus interno** (Express handlers chamam DB direto sem hook layer):

→ **BLOCKED.md candidate.** Spec precisa adicionar épico anterior **P5a — Event bus refactor** (3-4h: criar `src/lib/event-bus.ts` singleton `EventEmitter`, instrumentar 5 call sites canônicos, testar não-blocking emit). P5a precede P5 implementation.

**Se houver** (typical Express + repository pattern): proceed direto.

### 3.3 Backpressure: bounded ring buffer

- Server mantém ring buffer in-memory: **1000 events default** (configurável via `NOX_VIEWER_RING_SIZE`)
- Oldest dropped silently if buffer cheia entre flushes
- Per-client write queue: **100 events**; se client lento e queue cheia → drop oldest do queue desse client (NÃO do ring global)
- Emit `dropped.events` heartbeat a cada 30s com count de drops desde último heartbeat (operator vê client lento)

### 3.4 Heartbeat

A cada 15s o server emite `{ "kind": "heartbeat", "ts": "...", "ring_size": N, "clients": M }` — frontend usa pra detectar gap (server down vs sem atividade real).

---

## 4. Event schema (SSE message format)

Cada SSE message é um JSON object em uma linha (NDJSON-style payload em `data:`):

```
event: chunk.created
id: 1716060858123-0
data: {"ts":"2026-05-17T22:34:18.123Z","kind":"chunk.created","data":{"chunk_id":62847,"kind":"entity","length":1834,"redaction_count":0,"section":"compiled","retention_days":null,"pain":0.2}}

```

**Top-level fields:**

| Field | Type | Notes |
|-------|------|-------|
| `ts` | ISO 8601 UTC | server clock, monotonic per kind |
| `kind` | string enum | dot-delimited (chunk.created etc.) |
| `data` | object | kind-specific (tabela §2) |

**SSE `id:` line** = `<ts_ms>-<seq>` pra Last-Event-ID resume. Server keeps last 5min de eventos em ring; client reconnect com `Last-Event-ID` recebe gap.

**Kind values v1:** `chunk.created`, `chunk.deleted`, `kg.entity.created`, `kg.relation.created`, `search.executed`, `provider.call`, `op_audit.started`, `op_audit.completed`, `health.warning`, `heartbeat`, `dropped.events`.

---

## 5. Frontend: 4 panels

**Route:** `GET /viewer` (servido pelo mesmo Express em :18802, static HTML/JS bundle de `src/viewer/dist/`)

### 5.1 Panel A — Live feed (60% width, left column)

- Scrolling log, latest no topo
- Color-coded por `kind` (ingest=verde, search=azul, KG=roxo, provider=amarelo, op_audit=laranja, warning=vermelho)
- Cada linha: `[HH:MM:SS.mmm] kind │ key metadata` (1 linha, hover expande)
- Pause/Resume button (acumula events em batch quando paused, flush no resume)
- Filter chips: toggle por kind
- Auto-virtualize após 1000 eventos visíveis (drop oldest from DOM, ring buffer fica em memória JS)

### 5.2 Panel B — Counters (40% width, top-right)

- `chunks_total`, `kg_entities`, `kg_relations`, `embedded_pct`, `events_today` (since 00:00 BRT)
- Refresh: combinação push (counter tick em `chunk.created` / `kg.entity.created` event) + pull (`/api/health` GET a cada 5s pra reconciliar)
- Animação flash quando counter tick (200ms green pulse)

### 5.3 Panel C — Charts (40% width, middle-right)

- **Chunk growth** (last 24h, bin=1h) — bar chart, eixo Y = chunks novos/hora
- **Search latency** (last 1h, bin=1min) — line chart com p50 + p95 sobrepostos
- **Provider cost** (today / month) — two-row gauge: today (USD) + month-to-date (USD) com budget bar se `NOX_VIEWER_BUDGET_USD` set

Charts são **rolling** — recebem datapoints via SSE events e shiftam in-place (não re-fetch full window).

### 5.4 Panel D — Heatmap (40% width, bottom-right)

- 7 colunas (dias) × 24 linhas (hour-of-day) grid
- Cor = chunk count nessa célula (verde claro → escuro)
- Hover mostra count + total
- Refresh on load + a cada `chunk.created` event (debounced 1s, only repaint current hour cell)

### 5.5 Layout

```
┌───────────────────────────────────┬─────────────────────┐
│                                   │  Counters (B)       │
│                                   ├─────────────────────┤
│  Live feed (A)                    │  Charts (C)         │
│  scrolling, color-coded           │  growth+latency+$   │
│  pause/resume                     ├─────────────────────┤
│                                   │  Heatmap (D)        │
└───────────────────────────────────┴─────────────────────┘
```

Desktop-first, min-width 1280px. Mobile = out of scope v1.

---

## 6. Tech choices

| Concern | Choice | Justificativa |
|---------|--------|---------------|
| Framework | **htm + preact via CDN** | No build step, total page <100KB gzipped, preact == React API sem 40KB dep |
| Charts | **uPlot via CDN** (~40KB) | recharts (175KB+) overkill; uPlot é canvas-based, 100x faster em 1k pontos rolling |
| Heatmap | **inline SVG** (sem dep) | 7×24 = 168 cells, vanilla SVG é simpler |
| State | **preact signals** | Built-in fine-grained reactivity, sem Redux |
| SSE client | **native `EventSource`** | Reconnect + Last-Event-ID automático |
| Bundle | **single `index.html` + `viewer.js`** (módulo ESM) | servido estático de `dist/viewer/`; deploy = `cp` |

**Princípio:** zero build pipeline. `index.html` `<script type="module">` carrega tudo via CDN imports (htm, preact, uPlot). Maintenance trivial — Toto edita o `.js` direto em SSH.

---

## 7. Existing dashboard integration

Duas opções foram consideradas:

**(a) Replace live page em `agent-hub-dashboard`** — Next.js, Vercel deploy, cross-agent dashboard
**(b) Ship em nox-mem itself em `/viewer`** — served pelo `nox-mem-api`

**Decisão: (b) self-contained.**

| Critério | (a) hub-dashboard | (b) nox-mem /viewer | Vencedor |
|----------|-------------------|---------------------|----------|
| Latência SSE → render | proxy via Vercel | direct LAN/loopback | **(b)** |
| Deploy coupling | precisa redeploy Vercel | `cp` ou `systemctl restart nox-mem-api` | **(b)** |
| Funciona offline VPS | não (Vercel external) | sim (loopback) | **(b)** |
| Cross-agent overview | sim | não | (a) |
| Auth model | Tailscale ACL | bind 127.0.0.1 + opt token | tie |
| Stack complexity | Next.js Pages Router | static HTML+JS | **(b)** |

**Conclusão:** P5 ship em (b). `agent-hub-dashboard` permanece pra cross-agent + F10 time-series. P5 é "per-instance live", F10 é "cross-instance trend". **Não há overlap funcional**, apenas eventual overlap visual nos counters (aceito — fontes diferentes, propósitos diferentes).

---

## 8. Performance budget

| Concern | Budget | Mitigation |
|---------|--------|------------|
| Server emit overhead per event | **<1ms** | `EventEmitter.emit()` é sync + non-blocking, no I/O inline; ring write é array push O(1) |
| Ingest latency impact (with viewer connected, 1 client) | **0% measurable** | emit acontece **after** `INSERT` commit, never blocks transaction |
| Search latency impact | **0% measurable** | emit happens after response sent to caller |
| Frontend FPS @ 100 ev/sec | **60fps** | virtualize feed >1000 visible; uPlot canvas; batch DOM updates via `requestAnimationFrame` |
| Page size first load | **<100KB gzip** | htm+preact+uPlot via CDN, ~85KB total |
| Memory growth 24h connected | **<50MB** | ring buffer fixo + DOM virtualize + chart datapoint cap |

**Acceptance:** rodar 24h com viewer aberto, p50/p95 search via `eval` antes/depois batem dentro do noise band (±5%).

---

## 9. Privacy / threat model

### 9.1 Conteúdo nunca expõe via `/api/events`

- **NEVER:** raw chunk content, raw query text (default), KG entity names completas, prompt/response bodies, embeddings, file paths absolutos
- **Hashed:** `query_hash` (sha1[:8]), `name_hash` (KG entity name sha1[:8])
- **Allowed:** ids, kinds, counts, latencies, sizes, redaction_count, status enums

**Raw query opt-in:** `NOX_VIEWER_SHOW_QUERY=1` no env do server faz `search.executed` carregar `query_text` plain. **Default off**. Documentar como debug-only.

### 9.2 Authentication

- **Default:** bind 127.0.0.1 (loopback only). Mesma postura do resto do `nox-mem-api`.
- **Remote access (Tailscale):** se `NOX_VIEWER_BIND=0.0.0.0` set, **require** `NOX_VIEWER_TOKEN` (mínimo 32 chars). Token via header `Authorization: Bearer <token>` OU query `?token=` (último só pra `EventSource` que não suporta custom headers).
- **Threat model:** local-only is the assumed posture; remote = Tailscale ACL + token. Não há proteção contra atacante já dentro do Tailnet com token (escopo: defesa em depth, não zero-trust).

### 9.3 Content fetch separado (raw on-demand)

Se user/operator quer ver chunk content, query `GET /api/chunks/:id` (endpoint **separado**, auth completo, audit-logged). Viewer link "open chunk" abre essa URL em new tab.

---

## 10. Telemetry

Server logs (apenas metadata, no content):

- `viewer.connect` — ip (hashed se non-loopback), ts
- `viewer.disconnect` — duration_ms, events_sent, drops
- `viewer.events_dropped_global` — count/hour (ring overflow)

Persistido em `viewer_telemetry` (nova tabela, schema v11) ou append em `ops_audit` com `op='viewer.session'`. **Decisão preferida:** ops_audit reuse (1 tabela, append-only triggers já existem).

---

## 11. Tests plan

| Test | Type | Acceptance |
|------|------|------------|
| SSE reconnect on server restart | integration | client recebe Last-Event-ID gap dentro de 5min window |
| Ring buffer drop semantics | unit | inserir 1001 events em buf=1000, primeiro descartado, 1000 mais recentes presentes em ordem |
| Event ordering preserved per kind | integration | injetar 100 `chunk.created` sequenciais, frontend recebe na ordem (seq monotônico) |
| Frontend renders 1000 events without dropped frames | manual + perf | DevTools Performance tab: 60fps mantido durante batch de 1000 events |
| Backpressure: slow client | integration | mock client com 5s delay no read, server detecta queue full, dropa oldest do client queue, ring global intacto |
| Search/ingest latency unchanged | regression | `eval` n=78 antes/depois (viewer connected, 0 viewers, 5 viewers) — médias dentro de ±5% |
| Privacy: no raw content leak | security | grep regex em 1h de SSE stream, zero matches em `password|token|@gmail|chunk content patterns` |
| Auth: 401 sem token (when bind!=loopback) | security | curl sem header → 401 |
| Auth: 200 com token | security | curl com `Bearer $TOKEN` → 200 |

---

## 12. Definition of Done

1. **Latência live:** `chunk.created` event aparece no Panel A em **<500ms** desde `INSERT chunks` commit
2. **Estabilidade 24h:** viewer aberto 24h, memory growth <50MB, zero leaks (heap snapshot estável)
3. **Zero regressão:** search p50/p95 + ingest p50 inalterados (±5%) com 0, 1, 5 viewers connected
4. **Privacy:** test §11 "no raw content leak" passa em 1h stream
5. **Reconnect:** kill -HUP no `nox-mem-api`, client reconnecta automaticamente e recebe events do gap via Last-Event-ID

---

## 13. NÃO-fazemos (v1)

| Item | Por quê / Quando revisitar |
|------|----------------------------|
| Historical replay (events older than ring) | Eventos são live-only; `chunks`/`ops_audit` são persistência canônica; revisitar v2 se demand. |
| KG graph visualization (3D/2D force-directed) | = v2 (P5b). Obsidian 3D Graph + agent-hub-dashboard já cobrem exploration. |
| Multi-instance aggregation (>1 nox-mem) | Cross-agent dashboard já é F-series escopo (`agent-hub-dashboard`). |
| Mobile-optimized layout | Desktop-first; revisitar quando product surface tier B/C (Hotmart) lançar. |
| Custom alerts UI (configurar threshold no frontend) | Alerts ficam em invariants canary + Discord; viewer apenas **mostra** `health.warning` events. |
| Export to CSV / share screenshot | Browser screenshot resolve; CSV é F10 escopo. |
| Auth via OAuth / SSO | Token-based simples basta; SSO = N/A pra single-user instance. |
| WebSocket fallback | SSE basta; long-poll fallback documentado §15 (não implementado v1). |

---

## 14. Open questions

1. **Event bus refactor (P5a) é necessário?** → Validar em 30min antes de start (§3.2). Se sim, P5a precede P5.
2. **`viewer_telemetry` separada ou reuse `ops_audit`?** → Preferida reuse (§10). Decidir no kickoff.
3. **`uPlot` ou `chart.js`?** → uPlot por perf (40KB, canvas, 100x faster em rolling). chart.js (~80KB) é alternativa se uPlot API atritar. Default: uPlot.
4. **htm+preact ou vanilla?** → htm+preact por dev velocity em painéis interativos. Vanilla viável mas mais boilerplate. Default: htm+preact.
5. **Onde servir o bundle estático?** → `dist/viewer/` em mesmo Express ou `nginx` separado? Default: mesmo Express (zero ops surface nova).
6. **`NOX_VIEWER_SHOW_QUERY=1` opt-in está OK?** → Risk: operator esquece on em prod. Mitigação: log WARN no boot se var set. Validar com Toto.

---

## 15. Riscos

| Risco | Severidade | Mitigação |
|-------|------------|-----------|
| Slow client backpressure congestiona event bus | MED | Bounded ring + per-client queue + drop oldest (§3.3) |
| SSE bloqueado por corporate proxy / mod_security | LOW | Long-poll fallback documentado mas **não v1**; assume Tailscale path |
| Event emitter coupling slowing ingest | HIGH if blocking, LOW if async | Emit **after** commit, never inline em transação; benchmark §8 acceptance |
| `EventSource` reconnect loop em network flap | MED | Backoff exponencial 1s → 30s max; show "reconnecting" badge no UI |
| Token leak via query param (`?token=`) em logs | MED | NGINX/Express log filter strip `?token=`; document em runbook |
| Ring buffer perde event crítico durante burst de ingest (>1000 ev/s) | LOW | Heartbeat `dropped.events` count alerta operator; ingest persiste em `chunks` indepedente |
| Frontend JS bug bloqueia Panel A scroll com 10k+ events open | MED | Virtualize após 1000 visible; perf test §11 |
| `NOX_VIEWER_SHOW_QUERY=1` esquecido em prod expõe queries sensíveis | MED | WARN log no boot; doc em RUNBOOKS; auditar a cada `morning report` |

---

## 16. Implementação (ordem sugerida, fora-de-spec)

1. **Validar event bus assumption** (30min, §3.2) — se BLOCKED → write `BLOCKED.md`, spec P5a
2. **Server: SSE endpoint** `/api/events` + ring buffer + heartbeat (2h)
3. **Server: instrumentar 5 emit sites** (chunk insert, chunk delete, kg entity, kg relation, search hybrid) + provider wrappers + op_audit hooks (2h)
4. **Frontend: `index.html` + `viewer.js`** com 4 panels (3-4h)
5. **Tests + DoD validation** (1h)
6. **Doc:** RUNBOOKS entry + CONVENTIONS update (event schema canonical) (30min)

Commit strategy: 1 commit por fase, todos com `[overnight] P5 — <phase>` prefix. PR mantém DRAFT até DoD §12 verde.

---

## 17. Q/A/P pillar mapping

P5 = **P (Product surface)** pillar — observability é product surface, não só infra. Toto vê memória trabalhar = confiança = adoption.

- **Q (Quality):** indireto — viewer detecta zombie features cedo (lesson `feedback_validate_features_with_db_not_logs.md`)
- **A (Adoption):** direto — visual feedback aumenta perceived value pra Tier A/B/C (nox-supermem)
- **P (Product surface):** core — "see your memory grow" é venda

---

## 18. Anti-overlap com F10

| | F10 | P5 |
|---|---|---|
| Source | `/api/health` poll 60s | SSE push event-by-event |
| Window | 7d ring (IndexedDB) | live + last 24h client memory |
| Host | `agent-hub-dashboard` (Vercel) | `nox-mem-api` (loopback) |
| Audience | cross-agent operator | single nox-mem instance owner |
| Latency | 60s | <500ms |
| Persistence | IndexedDB 7d | volatile + chunks/ops_audit canônica |
| Stack | Next.js + recharts | htm+preact+uPlot |

**Decisão de coexistência:** ambos shippam. F10 = "trend across time". P5 = "live as it happens". Counters podem aparecer nos dois — fontes diferentes (poll vs push), mesma verdade no DB.
