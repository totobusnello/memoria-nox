# P5 Implementation Kickoff — Real-time Viewer (SSE + 4 panels)

**Status:** ready to start (planning artifact, not implementation)
**Date:** 2026-05-18
**Owner:** overnight automode push (memoria-nox)
**Spec:** `specs/2026-05-17-P5-viewer-realtime.md` (PR #10, 2,958 words, draft)
**Pillar:** **P5 — Real-time Viewer** (Q/A/P framework, last in P-pillar order)
**Branch:** `overnight/2026-05-18/P5-impl-kickoff`
**Tagline alignment:** *"Pain-weighted hybrid memory with shadow discipline — yours by design."*

---

## 1. Cross-references

| Ref | Source | Why it matters |
|---|---|---|
| **PR #10** | `[overnight] P5 — Spec: real-time viewer (SSE + 4 panels)` | Authoritative spec — SSE over GET /api/events, bounded ring buffer, 4 panels (feed/counters/charts/heatmap), 9 event kinds metadata-only, htm+preact+uPlot zero build step. |
| **D41 #5** | OPS log — P-pillar sequencing | **P5 ships LAST in P-pillar.** Order: P1 → A2 → P2 → P4 → **P5**. Lowest user-impact priority, depends on operational maturity (events bus, ingest hooks). |
| **PR #4 (P2)** | `[overnight] P2 — Spec: Claude Code hooks auto-capture` | **HARD dependency on internal event bus.** P2 introduces ingest-router emit points P5 reuses; without P2's event emit hooks, P5 must add them itself (T3). |
| **A3 (provider abstraction)** | `[overnight] A3 — Spec: provider abstraction` | **SOFT dependency.** `provider.call` events become richer post-A3 (uniform provider/op_type/cost_usd fields). Pre-A3, only Gemini calls surface. |
| **P1 (answer primitive)** | `[overnight] P1 — Spec` | **SOFT dependency.** `answer.executed` event possible post-P1 — not in v1 event kind enum (extensible later). |
| **F10 (trend dashboard)** | hub-dashboard repo | **Anti-overlap:** F10 = trend/historical analytics. P5 = live/realtime. Spec §11 enforces no functional overlap. |
| **A1 (privacy filter)** | `[overnight] A1 — Privacy filter` | Applies upstream of P5. P5 events MUST NOT bypass A1; viewer surfaces only post-redaction metadata. |

> **Single source-of-truth for "what we ship":** `specs/2026-05-17-P5-viewer-realtime.md`. This kickoff doc enumerates tasks, DoD, file structure — does NOT redefine the spec.

---

## 2. Architecture locked

### Transport: SSE (Server-Sent Events), NOT WebSocket

| Decision | Rationale |
|---|---|
| **SSE over GET /api/events** | Unidirectional fits the model (server → browser). Reuses existing HTTP API (port 18802) and Express stack. `curl http://127.0.0.1:18802/api/events` works for debugging. Auto-reconnect via `Last-Event-ID` header is free. |
| **NOT WebSocket** | Bidirectional unneeded. WS adds dep + handshake protocol + proxy hostility + harder to debug. |
| **Bounded ring buffer 1000 events** | In-memory deque. Oldest dropped if client slow. Bounded memory regardless of producer rate. Per-client cursor via `Last-Event-ID`. |
| **Async event emit** | `setImmediate(() => emit(...))` — emit NEVER blocks the DB write or ingest path. Backpressure absorbed by ring buffer drop, not by stalling producers. |
| **Bind 127.0.0.1 default** | Local-only. Remote access opt-in via `NOX_VIEWER_TOKEN` env (off by default). |
| **Hash query / entity name (privacy default)** | Raw content NEVER on /api/events. `NOX_VIEWER_SHOW_QUERY=1` opt-in env with stderr WARN on boot. |

### Frontend: htm + preact + uPlot via CDN (zero build step)

| Choice | Why |
|---|---|
| **htm + preact** | ~10KB combined. JSX-like ergonomics without build tooling. Dev velocity. |
| **uPlot** | ~40KB canvas-based. ~100x faster than chart.js for time-series. Latency p50/p95 + cost + growth all canvas-rendered. |
| **No bundler** | Single `index.html` + ES modules. Total page <100KB JS, <1MB transferred. Edit-reload-debug cycle is `Cmd+R`. |
| **Served by Express** | `/viewer` route same process as `/api/*`. No nginx step. Self-contained. |

---

## 3. Task breakdown (15 tasks)

| # | Task | Module / File | Est. hours |
|---|---|---|---|
| **T1** | Verify (or add) internal event bus — `EventEmitter` singleton | `src/lib/events/bus.ts` | 3-4 if absent (P5a refactor); 0.5 if exists |
| **T2** | SSE endpoint `GET /api/events` — bounded ring buffer + `Last-Event-ID` resume | `src/api/events.ts` | 3 |
| **T3** | Event emit hooks across producers | `src/ingest-router.ts`, `src/api/search.ts`, `src/lib/op-audit.ts`, `src/kg/extract.ts` | 2-3 |
| **T4** | Event schema TypeScript types + JSONL framing | `src/lib/events/types.ts` | 1 |
| **T5** | Privacy filter — `redactEvent()` pre-emit | `src/lib/events/emit.ts` (helper) | 1.5 |
| **T6** | Frontend entry HTML + bootstrap (htm + preact via CDN) | `src/viewer/index.html`, `src/viewer/app.js` | 1.5 |
| **T7** | Live feed panel — virtualized scroll, color by kind, pause/resume | `src/viewer/panels/feed.js` | 2 |
| **T8** | Counters panel — poll `/api/health` every 1s | `src/viewer/panels/counters.js` | 1 |
| **T9** | Charts panel — uPlot growth + latency p50/p95 + cost | `src/viewer/panels/charts.js` | 3 |
| **T10** | Heatmap panel — chunk activity by hour-of-day, last 7d | `src/viewer/panels/heatmap.js` | 1.5 |
| **T11** | Auth — bind 127.0.0.1 + optional `NOX_VIEWER_TOKEN` | `src/api/events.ts`, `src/api/viewer.ts` | 1 |
| **T12** | Performance — async emit + SSE handler <1ms overhead | `src/lib/events/bus.ts`, `src/api/events.ts` | 1 |
| **T13** | Telemetry — count viewer connections/disconnects (no content) | `src/api/events.ts`, `ops_audit` row or `viewer_telemetry` table | 1 |
| **T14** | Tests — reconnection, ring buffer drop, ordering, frontend 1000 events, privacy guards | `src/api/events.test.ts`, `src/lib/events/__tests__/`, `src/viewer/__tests__/` (Playwright) | 3-4 |
| **T15** | Documentation — viewer entry, env vars, browser compat, troubleshooting | `docs/VIEWER.md`, `README.md` snippet | 1.5 |

**Total:** ~22-28h (best case with event bus present) → **+3-4h P5a refactor** if T1 verifies absence = **25-32h realistic**.

---

## 4. Per-task DoD criteria

### T1 — internal event bus
- `src/lib/events/bus.ts` exports `eventBus` singleton (`EventEmitter`).
- Listener count cap of 100; warn on overflow.
- `emit(kind, data)` is non-blocking — wrapped in `setImmediate`.
- Unit test: 1000 sequential emits complete in <10ms aggregate.
- **DECISION POINT:** if grep `grep -rl "EventEmitter\|emit(" src/` returns zero results → **add BLOCKED.md entry** flagging P5a as prerequisite (3-4h refactor, plumb emit into ingest-router/search/op-audit). If existing event bus found → reuse and document.

### T2 — SSE endpoint
- `GET /api/events` responds with `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `Connection: keep-alive`.
- Heartbeat ping `: keepalive\n\n` every 30s.
- Ring buffer 1000 events in-memory; oldest dropped silently when full.
- `Last-Event-ID` header resumes from offset; missing or stale offset → send full buffer + new events.
- Per-event line format: `id: <ulid>\nevent: <kind>\ndata: <JSON>\n\n`.
- Curl smoke test passes: `curl -N http://127.0.0.1:18802/api/events` streams events live.

### T3 — emit hooks
- `ingest-router.ts` calls `emit("chunk.created", {...})` AFTER redact+insert succeeds.
- `trg_chunks_delete_cascade` trigger or `deleteChunks()` wrapper fires `chunk.deleted`.
- `kg-extract.ts` fires `kg.entity.created` + `kg.relation.created` per row.
- `hybrid search` fires `search.executed` after fusion.
- `withOpAudit` wrapper fires `op_audit.started` + `op_audit.completed`.
- Optional `provider.call` from Gemini wrapper (richer post-A3).
- Optional `health.warning` from `/api/health` threshold checks.
- All emits async; verified by latency benchmark unchanged (T12 DoD).

### T4 — event schema
- `src/lib/events/types.ts` exports discriminated-union `ViewerEvent` (see §6).
- Per-kind payload typed; `ts: string` (ISO8601); `kind` literal.
- Frozen at v1 — additive only post-launch; no rename/remove without major bump.

### T5 — privacy filter
- `redactEvent(raw)` strips: chunk content, raw query text, file paths beyond basename, user identifiers (replaced by `session_id_hash`).
- `NOX_VIEWER_SHOW_QUERY=1` env opt-in surfaces raw query in `search.executed.data.query_raw` field — boot emits `[WARN] NOX_VIEWER_SHOW_QUERY=1 — raw queries on /api/events. Do NOT enable in shared environments.`
- Unit test: 100 synthetic events emitted; grep for raw content in stream output returns zero matches (with opt-in OFF).

### T6 — frontend entry
- `src/viewer/index.html` loads htm+preact+uPlot from CDN with `integrity` + `crossorigin` attrs.
- Single bootstrap `<script type="module" src="app.js">`.
- Layout grid: 4 panels (feed top-left, counters top-right, charts bottom-left, heatmap bottom-right). CSS grid, responsive ≥1024px.
- Palette D minimal + accent `#00C896` (matches GTM assets).

### T7 — live feed panel
- EventSource subscribes to `/api/events`; on message, prepend to scroll list.
- Color coding: chunk.* = green, kg.* = blue, search.* = amber, op_audit.* = purple, provider.* = teal, health.warning = red.
- Pause/resume button — pauses prepend (events still buffered server-side via ring buffer + `Last-Event-ID` cursor).
- Virtualizes after 1000 visible rows (drop bottom 200 when reaching 1200).
- Click event row → JSON detail modal (no raw content surfaced).

### T8 — counters panel
- Poll `GET /api/health` every 1000ms (cancellable on tab hide).
- Display: `chunks_total`, `kg_entities`, `kg_relations`, `embedded_pct`, `events_today`.
- Diff highlight: number flashes accent color when changes since last poll.

### T9 — charts panel
- uPlot 3 stacked charts:
  - chunk growth (last 24h, 5min buckets) — line
  - search latency p50 + p95 (last 1h, 1min buckets) — dual-line
  - provider cost USD (today / month) — bar
- Data source: `/api/health/timeseries` (new endpoint or reuse search_telemetry aggregation).
- Redraw on each `search.executed` event (debounced 500ms).

### T10 — heatmap panel
- 7d × 24h grid (168 cells). Cell = chunk count in that hour-of-day-of-week.
- Color scale: white → accent `#00C896`.
- Tooltip on hover: `Wed 14:00 — 47 chunks`.
- Data source: `SELECT strftime('%w', created_at), strftime('%H', created_at), COUNT(*) FROM chunks WHERE created_at > datetime('now', '-7 days') GROUP BY 1,2`.

### T11 — auth
- Default: Express binds 127.0.0.1 (existing config, verify).
- Optional `NOX_VIEWER_TOKEN` env — if set, `/api/events` + `/viewer` require `Authorization: Bearer <token>` OR `?token=<token>` query param.
- Boot WARN if token unset AND `NOX_VIEWER_BIND=0.0.0.0` set together (refuse to start unless `NOX_VIEWER_FORCE_OPEN=1`).

### T12 — performance budget
- `bus.emit()` overhead <100µs (microbenchmark, 10k iterations).
- SSE write per event <1ms (server-side stopwatch around `res.write`).
- Frontend feed panel renders 100 events/sec without dropped frames (Chrome DevTools FPS counter ≥55).
- 24h soak test (T14 cross-ref): memory growth bounded (<50MB over 24h).

### T13 — telemetry
- On SSE connect: increment counter `viewer_connect_total`; insert row `{ts, session_id_hash}` (NO IP, NO UA beyond major-version).
- On disconnect: increment `viewer_disconnect_total`, log duration_ms.
- Surface via `/api/health.viewer = { active_connections, total_connects_today }`.
- **OPEN:** reuse `ops_audit` (single audit table) vs add `viewer_telemetry`? Default = reuse `ops_audit` with `op="viewer.connect"`.

### T14 — tests
- **SSE reconnection** — kill server mid-stream, restart; client auto-reconnects within 5s and resumes from `Last-Event-ID`.
- **Ring buffer drop** — emit 1500 events; verify oldest 500 dropped, newest 1000 in buffer, no crash.
- **Event ordering** — within a single kind, ordering preserved (FIFO).
- **Frontend 1000-event render** — Playwright headless, inject 1000 events, asserts FPS ≥55 + scroll-to-top works.
- **Privacy guards** — fuzz 100 events with chunk_content/query_raw fields; grep stream output for forbidden substrings returns 0 matches (with `NOX_VIEWER_SHOW_QUERY=0`).
- **Load test** — 100 events/sec for 60s with 5 concurrent SSE clients; no event loss verified by per-client counter == total emitted.

### T15 — documentation
- `docs/VIEWER.md` — open `http://127.0.0.1:18802/viewer` in modern browser.
- Env vars table: `NOX_VIEWER_TOKEN`, `NOX_VIEWER_SHOW_QUERY`, `NOX_VIEWER_BIND`, `NOX_VIEWER_FORCE_OPEN`.
- Browser compat: Chrome 90+, Firefox 90+, Safari 15+ (SSE + ES modules baseline). NOT IE.
- Troubleshooting: SSE proxy timeout → check heartbeat ping; events not appearing → check `/api/health.viewer.active_connections`; raw query not visible → set opt-in env.
- `README.md` link to `docs/VIEWER.md` under "Operability".

---

## 5. File structure

```
src/
  api/
    events.ts                # SSE endpoint + ring buffer + Last-Event-ID
    viewer.ts                # GET /viewer/* static serving (index.html + assets)
  lib/
    events/
      bus.ts                 # internal EventEmitter singleton (verify/add)
      types.ts               # event kind enum + payload schemas (discriminated union)
      emit.ts                # helper functions per event kind + redactEvent()
      __tests__/
        bus.test.ts          # 1000-emit microbenchmark, listener cap
        emit.test.ts         # redaction guards, privacy fuzz
        sse.test.ts          # reconnection, ring buffer, ordering
  viewer/
    index.html               # entry — grid layout + CDN imports
    app.js                   # bootstrap — EventSource + panel mount
    panels/
      feed.js                # live event scrolling (virtualized)
      counters.js            # chunk/KG/embedded stats (1s poll)
      charts.js              # uPlot latency + cost + growth
      heatmap.js             # activity by hour-of-day, last 7d
    styles.css               # palette D minimal + accent #00C896
    __tests__/
      playwright.spec.ts     # 1000-event render + FPS assertion

docs/
  VIEWER.md                  # entry point, env vars, browser compat, troubleshooting

specs/
  2026-05-17-P5-viewer-realtime.md      # spec (PR #10, unchanged)
  2026-05-18-P5-implementation-kickoff.md  # THIS FILE
```

---

## 6. Event schema (locked v1)

```typescript
type ViewerEvent =
  | { ts: string; kind: "chunk.created"; data: { chunk_id: number; kind: string; length: number; redaction_count: number } }
  | { ts: string; kind: "chunk.deleted"; data: { chunk_id: number } }
  | { ts: string; kind: "kg.entity.created"; data: { entity_id: number; canonical_name: string } }
  | { ts: string; kind: "kg.relation.created"; data: { relation_id: number; predicate: string } }
  | { ts: string; kind: "search.executed"; data: { query_hash: string; latency_ms: number; top_k: number; hybrid_breakdown: { bm25: number; vec: number; kg: number } } }
  | { ts: string; kind: "provider.call"; data: { provider: string; op_type: string; latency_ms: number; cost_usd: number } }
  | { ts: string; kind: "op_audit.started"; data: { op: string; audit_id: string } }
  | { ts: string; kind: "op_audit.completed"; data: { op: string; audit_id: string; status: string; duration_ms: number } }
  | { ts: string; kind: "health.warning"; data: { metric: string; value: number; threshold: number } };
```

**Schema discipline:** v1 frozen at 9 kinds. Additive-only post-launch (new kinds OK, removing/renaming forbidden without major bump). Discriminated union enforces exhaustive switch in frontend.

---

## 7. Privacy guards (locked)

**NEVER on `/api/events`** (default):
- Raw chunk content (only `length` + `redaction_count`).
- Raw query text (only `query_hash` = `sha256(query).slice(0,16)`).
- File paths beyond basename (`/Users/lab/X.md` → `X.md`).
- User identifiers (replace with `session_id_hash`).

**Opt-in via env (with boot WARN):**
- `NOX_VIEWER_SHOW_QUERY=1` → adds `query_raw` to `search.executed` payload. Boot emits `[WARN] NOX_VIEWER_SHOW_QUERY=1 — raw queries visible on /api/events. Do NOT enable in shared environments.`

**Validation:** T14 fuzz test injects 100 events containing known forbidden substrings; stream output grep returns zero matches with opt-in OFF.

---

## 8. SSE reliability

- **`Last-Event-ID` header** — browser auto-reconnect resumes from last seen offset. Server matches against ring buffer; if offset stale (dropped), sends full buffer + new events from next emit.
- **Heartbeat ping every 30s** — `: keepalive\n\n` comment line prevents proxy timeout (HAProxy/nginx default 60s). Comment lines ignored by EventSource.
- **Graceful shutdown** — on server `SIGTERM`, server sends `event: shutdown\ndata: {"reason":"restart"}\n\n` and closes; client reconnects on backoff (1s → 2s → 4s → 8s capped).
- **Per-connection cursor** — server tracks `lastSentId` per client; ring buffer sweep filters by `id > lastSentId`.

---

## 9. Tests plan

Covered in T14 above plus **load test**:

- 100 events/sec for 60s = 6,000 events total.
- 5 concurrent SSE clients.
- Per-client counter `eventsReceived` vs server `eventsEmitted` must match (zero loss).
- p95 SSE write latency <2ms under load.
- No memory leak — RSS bounded within 50MB of baseline after 60s + 30s cooldown.

---

## 10. DoD overall (5 criteria)

1. **Live propagation:** chunk ingest → event visible in viewer in **<500ms** (T2 + T3 + frontend EventSource).
2. **24h uptime no leak:** ring buffer bounded; RSS growth <50MB over 24h soak test (T12).
3. **Latency unchanged:** ingest/search latency benchmark **identical** with viewer connected vs disconnected (async emit, never blocks DB write — T12).
4. **Raw content NEVER leaks via /api/events:** fuzz test passes; hashed query only by default (T5 + T14 privacy guards).
5. **Privacy opt-in visible:** `NOX_VIEWER_SHOW_QUERY=1` emits boot WARN on stderr (T5).

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Slow client backpressure stalls server | Bounded ring buffer 1000 events + drop oldest; SSE `res.write` non-blocking; per-client cursor independent. |
| SSE behind corporate proxy buffers/timeouts | Heartbeat ping every 30s; `X-Accel-Buffering: no` header for nginx; long-poll fallback **documented but NOT v1**. |
| Event-emitter coupling slows ingest path | Async emit (`setImmediate`); microbenchmark T12 asserts <100µs overhead per emit; T12 DoD asserts unchanged ingest latency. |
| Browser memory leak with 24h tab open | Virtualized feed (drop after 1200, keep 1000); frontend ring buffer mirrors server bound. Playwright soak test in T14 follow-up. |
| Auth misconfig exposes events publicly | Default bind 127.0.0.1; boot refuses to start with `NOX_VIEWER_BIND=0.0.0.0` + no token unless `NOX_VIEWER_FORCE_OPEN=1` (T11). |
| Raw content sneaks into payload via new event kind | Schema discriminated union + lint rule banning `content` / `query_raw` field names outside opt-in path; T14 fuzz test. |
| **P5a refactor surprise** (no event bus) | T1 verifies first; if absent, **BLOCKED.md entry filed** flagging 3-4h prerequisite (plumb EventEmitter through ingest-router, search, op-audit). Doc continues but tasks T2-T15 wait. |

---

## 12. Timeline estimate

| Phase | Tasks | Hours |
|---|---|---|
| **Foundation** | T1, T2, T3, T4, T5 | 7-10.5 (+ 3-4 if P5a) |
| **Frontend** | T6, T7, T8, T9, T10 | 9 |
| **Hardening** | T11, T12, T13 | 3 |
| **Quality** | T14, T15 | 4.5-5.5 |
| **Total** | 15 tasks | **~22-28h** (or **25-32h** with P5a) |

Suggested split across 3 sessions: foundation (day 1) → frontend (day 2) → hardening + tests + docs (day 3).

---

## 13. Open questions (non-blocking)

1. **`viewer_telemetry` table vs reuse `ops_audit`?** → default reuse `ops_audit` with `op="viewer.connect"` / `op="viewer.disconnect"`. Simpler, one audit surface. Decide on T13.
2. **uPlot vs chart.js?** → default uPlot (40KB, canvas perf). 100x faster on time-series.
3. **htm+preact vs vanilla JS?** → default htm+preact. Dev velocity beats 10KB savings; component reuse across 4 panels.
4. **Bundle served from same Express or nginx static?** → default same Express (`/viewer/*`). Self-contained, no nginx dep, mirrors `/api/*`.
5. **`NOX_VIEWER_SHOW_QUERY` opt-in acceptable for debug?** → **needs Toto sign-off before T5 implementation.** Default OFF + boot WARN; flagged in spec §17.

---

## 14. Dependencies declared

### HARD
- **HTTP API existing on port 18802** — verified (`nox-mem-api` already runs; spec §4 confirms).
- **Internal event bus** — T1 verifies; if absent, **P5a refactor prerequisite** (3-4h, plumb `EventEmitter` through `ingest-router.ts`, `api/search.ts`, `lib/op-audit.ts`, `kg/extract.ts`). **BLOCKED.md filed if grep returns zero EventEmitter usage.**

### SOFT
- **A3 (provider abstraction)** — `provider.call` event richer post-A3 (uniform provider/op_type/cost_usd). Pre-A3, only Gemini surfaces; viewer still functional.
- **P1 (answer primitive)** — `answer.executed` event possible post-P1; NOT in v1 schema, extensible later via additive kind.

### REUSES
- `search_telemetry` table (existing, A0 query logging extension) — feeds charts panel latency series.
- `withOpAudit()` hooks (existing, A1 op-audit module) — `op_audit.started/completed` events emit from there.
- `/api/health` endpoint (existing) — counters panel polls every 1s; new `/api/health.viewer` sub-key added in T13.

---

## 15. PR + branch protocol

| Action | Value |
|---|---|
| **Branch** | `overnight/2026-05-18/P5-impl-kickoff` |
| **PR title** | `[overnight] P5-kickoff — Implementation tasks for real-time viewer (SSE, 4 panels)` |
| **Auto-merge** | **NO** — review required before T1 starts |
| **Reviewers** | Toto (architecture sign-off on §13 q5 opt-in env) |
| **Labels** | `pillar:P`, `kickoff`, `viewer`, `do-not-auto-merge` |
| **BLOCKED.md** | **YES if T1 grep returns zero EventEmitter usage** (P5a 3-4h refactor prerequisite). File entry at top of `BLOCKED.md` referencing this doc §11. |

---

*"Pain-weighted hybrid memory with shadow discipline — yours by design."*

P5 closes the P-pillar: P1 answers, A2 portability, P2 capture, P4 surfaces, **P5 shows it all live.**
