# F10 Phase C Phase 1 — production deploy audit

**Date:** 2026-05-23 14:03 BRT
**Operator:** executor-high agent
**Target:** VPS `187.77.234.79` (`/root/.openclaw/workspace/tools/nox-mem/`)
**Source PR:** #267 (merged into main as `04165de`) — telemetry collector + dashboard
**Pre-deploy SHA:** `8866642` (main, post-#266 nox_mem adapter fix)
**Time-box:** 1h (consumed ~25min)

## Outcome

**SUCCESS** — all 3 new endpoints live in prod, zero regression on existing endpoints, telemetry capturing real traffic w/ correct latency + result_count + path_used.

## Pre-deploy state

- VPS `api-server.ts`: 492 lines, contained Phase A (`handleObsHealth`/`handleObsRecentOps`/`handleObsCanaryTail`) + Phase B (`handleObsEvals`) — both intact.
- Service `nox-mem-api` was `active` listening on `127.0.0.1:18802`.
- Backup created: `/tmp/api-server.ts.pre-f10c` (21337 bytes, mtime 2026-05-23 13:54).
- Dist file `dist/api-server.js` 23670 bytes (May 22 13:48 — stale `[[vps-build-broken-runs-on-stale-dist]]` symptom).
- `/api/answer` handler **not present** in current VPS source → CHANGE 3 in wire-up.md SKIPPED cleanly.

## Files SCP'd

| Source (repo) | Destination (VPS) | Bytes |
|---|---|---|
| `staged-1.7c/edits/lib/telemetry-collector.ts` | `src/lib/telemetry-collector.ts` | 12679 |
| `staged-1.7c/edits/public/observability/telemetry.html` | `public/observability/telemetry.html` | 3035 |
| `staged-1.7c/edits/public/observability/telemetry.js` | `public/observability/telemetry.js` | 12159 |
| `staged-1.7c/edits/public/observability/telemetry.css` | `public/observability/telemetry.css` | 4236 |
| `/tmp/api-server.ts.patched` (local edit) | `src/api-server.ts` | 22086 (+749 vs pre) |

## Wire-up changes applied (5 of 6 — CHANGE 3 N/A)

| # | Change | Lines added | Status |
|---|---|---|---|
| 1 | Add `recordRequest` + `handleObsTelemetry` import | +4 | DONE |
| 2 | Hook `/api/search` with telemetry capture | +20 | DONE |
| 3 | Hook `/api/answer` with telemetry capture | — | **SKIPPED** (endpoint absent in current VPS source) |
| 4 | Add `/api/observability/telemetry` case after evals | +6 | DONE |
| 5 | Extend static-serving case list with telemetry.{html,js,css} | +3 | DONE |
| 6 | Append telemetry endpoints to 404 hint list | +1 | DONE |

**Note on CHANGE 2:** During smoke test, discovered `searchHybrid` returns array OR `{results, vaultFacts}` depending on shape. Initial patch used naive `(results as {results?: unknown[]})?.results` which yielded `result_count_sum: 0`. Iteration 2 added `Array.isArray(results)` probe both shapes → `result_count_sum: 28` for 3 searches confirms fix lands clean.

## Build status

`npm run build` emitted both new dist files despite pre-existing tsc errors unrelated to F10 (lesson `[[vps-build-broken-runs-on-stale-dist]]` — tsc emits with `noEmitOnError unset`):

- `dist/api-server.js` 23670 → 25220 bytes (+1550, matches our 30+ added lines)
- `dist/lib/telemetry-collector.js` created at 10359 bytes
- Pre-existing errors in `src/api/answer.example.ts`, `src/api/export.example.ts`, `src/index.ts:264`, multiple `__tests__/*.ts` paths — NOT related to this deploy

## Smoke test results

Service restart: `2026-05-23 14:03:01 -03`. Listening on `http://127.0.0.1:18802` clean (PID 2279535).

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/observability/telemetry?window=24h&bucket=1h` | GET | **200** | Returns 24 empty buckets + aggregate (initial state) |
| `/observability/telemetry.html` | GET | **200** | 3035 bytes served |
| `/observability/telemetry.js` | GET | **200** | 12159 bytes served |
| `/observability/telemetry.css` | GET | **200** | 4236 bytes served |
| `/api/health` (regression) | GET | **200** | chunks=68995 vectors=68995 services_active=2 |
| `/api/observability/health` (regression) | GET | **200** | keys: current/delta_24h/generated_at_ms/indicators |
| `/api/observability/evals` (regression) | GET | **200** | OK |
| `/observability/health.html` (regression) | GET | **200** | 3321 bytes (unchanged) |

## End-to-end telemetry capture validation

Drove 3 sequential search requests, polled `/api/observability/telemetry?window=1h` after 3s:

```json
{
  "aggregate": {
    "count": 3,
    "avg_latency_ms": 632,
    "p50_ms": 630,
    "p95_ms": 671,
    "p99_ms": 671,
    "by_path": { "search": 3, "answer": 0 },
    "semantic_ratio": 1
  },
  "latest_bucket": {
    "label": "2026-05-23T17:00Z",
    "count": 3,
    "by_path_used": { "hybrid": 3 },
    "semantic_count": 3,
    "result_count_sum": 28
  }
}
```

**Confirmed:**
- Per-request latency captured (avg 632ms, plausible for hybrid search).
- `by_path_used.hybrid: 3` confirms fallback default kicked in (`searchHybrid` exposes no `meta`).
- `semantic_count: 3` (default `_semantic = _meta?.semantic_used !== false`) — TODO: make exact once `search.ts` surfaces `semantic_used` boolean.
- `result_count_sum: 28` confirms result-array reading works for both response shapes.

## Anomalies + watch-items

1. **`searchHybrid` returns no `meta`** — telemetry always reports `path_used=hybrid` + `semantic_used=true`. Functionally OK (current default IS hybrid+semantic), but breaks per-path slice if future search.ts adds `fts-only` or `semantic-only` modes. **Follow-up:** D52 (TBD) — make `searchHybrid` return `{results, meta: {path_used, semantic_used}}` and remove fallback defaults.
2. **Pre-existing tsc errors** — same `[[vps-build-broken-runs-on-stale-dist]]` pattern from 2026-05-19. Build emits dist despite errors. Not a new regression; flagged again for tracking.
3. **CHANGE 3 SKIPPED** — `/api/answer` endpoint not present in current VPS api-server.ts (was removed/refactored between PR #114 and now, or `/api/answer` lives in a wire-up route module). Phase 2 of F10-C may need to wire telemetry into wire-up.ts answer handler if it exists there. **Follow-up:** locate `/api/answer` in `src/api/wire-up.ts` or `src/api/answer/*` and apply CHANGE 3 there.

## Rollback playbook (if needed)

```bash
# 1. Restore api-server.ts from pre-deploy backup
ssh root@187.77.234.79 'cp /tmp/api-server.ts.pre-f10c /root/.openclaw/workspace/tools/nox-mem/src/api-server.ts'

# 2. Rebuild
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && npm run build 2>&1 | tail -5'

# 3. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 3 && systemctl is-active nox-mem-api'

# 4. Verify rollback
ssh root@187.77.234.79 'curl -sS http://127.0.0.1:18802/api/observability/telemetry?window=1h'
# Expected: 404 with endpoints list
```

**Risk profile:** ZERO data loss risk — telemetry data is in-process ring buffer, lost on restart anyway. No DB migration, no schema change. Backup file `/tmp/api-server.ts.pre-f10c` persists until VPS reboot. After 24h confidence window, can promote backup to `/var/backups/nox-mem/api-server.ts.pre-f10c-2026-05-23` for longer retention.

## Operational handoff

- Dashboard URL (Tailscale): `http://nox-vps.tailnet:18802/observability/telemetry.html`
- API contract: `GET /api/observability/telemetry?window={1-24}h&bucket=1h` returns `{window, buckets[24], aggregate}`
- No env var changes required — collector is pure in-memory.
- No cron impact — no schedule changes.
- No DB impact — no schema/data writes.

## Next steps (post-deploy)

1. **Today (Sat 2026-05-23):** monitor `journalctl -u nox-mem-api` for 1h — confirm no late-binding errors.
2. **Sun 2026-05-24:** check telemetry shows real traffic accumulation (expect ~50-200 searches/day baseline).
3. **Mon 2026-05-25:** review p50/p95 vs Q3 latency numbers (p50=940ms p95=2342ms baseline) — confirm prod within bounds.
4. **F10 Phase C Phase 2:** locate `/api/answer` handler + apply CHANGE 3 telemetry hook (separate PR).
5. **F10 Phase C Phase 3:** spec persistence (SQLite-backed telemetry beyond process restarts) — gated on Phase 1 stability.
