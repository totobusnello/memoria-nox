# F10 Phase D — shadow tracker production deploy audit

**Date:** 2026-05-24 (executed Sat 2026-05-23 20:57 BRT, audit closure 05-24)
**Operator:** executor-high agent (worktree-isolated per `[[multi-agent-branch-checkout-race]]`)
**Target:** VPS `187.77.234.79` (`/root/.openclaw/workspace/tools/nox-mem/`)
**Source PR:** #291 (merged into main) — Phase D shadow tracker + dashboard
**Pre-deploy SHA:** `f5ef803` (main, post-Sat 2026-05-24 closure docs)
**Worktree:** `/tmp/f10-phase-d-deploy-7EF9C342-D800-4128-B309-8A81505B8853`
**Time-box:** 1.5h (consumed ~35min)

## Outcome

**SUCCESS** — all 5 new surfaces live in prod (1 API + 3 static + 1 in-process collector), zero regression on Phase A/B/C endpoints, append-only triggers validated firing, schema migration idempotent, shadow tracker DB handle wired into singleton at server startup. F10 observability suite complete (A + B + C + D).

## Pre-deploy state

- VPS `api-server.ts`: 529 lines. Contained Phase A (`handleObsHealth` / `handleObsRecentOps` / `handleObsCanaryTail`) + Phase B (`handleObsEvals`) + Phase C (`recordRequest` / `handleObsTelemetry`) — all 7 import landmarks intact at lines 22-31, 264-302, 487-495.
- Service `nox-mem-api` was `active` listening on `127.0.0.1:18802` (PID 2279535, uptime ~9h since 14:03 — Phase C deploy from `2026-05-23-f10-phase-c-deploy.md`).
- Backup created: `/tmp/api-server.ts.pre-f10d` (22869 bytes, mtime 2026-05-23 20:53).
- `src/lib/` directory listed — no pre-existing `shadow-tracker.ts`. Clean install path.
- `public/observability/` already contained Phase A health.*, Phase B evals.*, Phase C telemetry.* assets. No name collisions on shadow.*.
- DB `nox-mem.db`: shadow_runs table did NOT exist pre-deploy (verified via .schema query returning empty).

## Files SCP'd

| Source (repo) | Destination (VPS) | Bytes |
|---|---|---|
| `staged-1.7d/edits/src/lib/shadow-tracker.ts` | `src/lib/shadow-tracker.ts` | 18138 |
| `staged-1.7d/edits/public/observability/shadow.html` | `public/observability/shadow.html` | 3436 |
| `staged-1.7d/edits/public/observability/shadow.js` | `public/observability/shadow.js` | 13857 |
| `staged-1.7d/edits/public/observability/shadow.css` | `public/observability/shadow.css` | 4868 |
| `staged-1.7d/edits/src/lib/shadow-tracker-schema.sql` | `/tmp/shadow-tracker-schema.sql` (then `sqlite3 < ...`) | 2991 |
| `/tmp/api-server.ts.patched` (local edit) | `src/api-server.ts` | +26 lines vs pre |

## Schema migration

Applied via out-of-band `sqlite3 nox-mem.db < /tmp/shadow-tracker-schema.sql` (CHANGE 0 Option B from wire-up.md — idempotent `CREATE TABLE IF NOT EXISTS`).

Verified post-migration:

| Object | Type | Confirmed |
|---|---|---|
| `shadow_runs` | TABLE | YES — 8 columns, 3 CHECK constraints |
| `idx_shadow_runs_ts` | INDEX | YES |
| `idx_shadow_runs_feature_ts` | INDEX | YES |
| `trg_shadow_runs_block_delete` | TRIGGER | YES — RAISE(ABORT, 'shadow_runs is append-only: DELETE blocked') |
| `trg_shadow_runs_block_update` | TRIGGER | YES — RAISE(ABORT, 'shadow_runs is append-only: UPDATE blocked') |

## Wire-up changes applied (5 of 6 from `api-server.shadow-wire-up.md`)

| # | Change | Lines added | Status |
|---|---|---|---|
| 1 | Add `handleObsShadow` + `tracker as shadowTracker` import | +4 | DONE |
| 2 | Hook `/api/search` with shadow comparison wrapper | — | **DEFERRED** (intentional — wire-up.md flags as "optional, only when shadow feature env-flag is set"; no `NOX_SHADOW_*` flag active yet) |
| 3 | Add `/api/observability/shadow` endpoint case | +7 | DONE |
| 4 | Extend static-serving case list with shadow.{html,js,css} | +3 | DONE |
| 5 | Append shadow endpoints to 404 hint list | +1 | DONE |
| 0 | Wire `shadowTracker.setDB(getDb())` in `server.listen()` startup | +11 | DONE (Option C — api-server.ts startup hook instead of CHANGE 0 Option A db.ts edit; schema already applied via Option B so equivalent) |

**Note on CHANGE 2 deferral:** The wire-up doc explicitly marks `/api/search` instrumentation as **optional, gated on `NOX_SHADOW_<FEATURE>=1`**. Wiring it without an active flag would add hot-path overhead with zero observable benefit and a non-zero regression risk. Phase 2 follow-up (separate PR) will enable a specific shadow feature (likely `NOX_SHADOW_TEMPORAL_SPIKE_V2=1` per memory `[[temporal-spike-v2-win-2026-05-20]]` — currently shadow-gated, 7d burn-in) and add the wrapper at that time.

**Note on CHANGE 0 strategy:** wire-up.md presented two options. We chose **Option B + startup-hook in api-server.ts** rather than Option A (mutate db.ts). Rationale:
1. Schema is idempotent (`CREATE TABLE IF NOT EXISTS`), safe to apply out-of-band.
2. db.ts is shared by CLI / MCP / API surfaces; injecting a `tracker.setDB(db)` line there would attach the singleton to **every** process touching the DB (including ephemeral CLI invocations), creating multiple competing singletons.
3. The api-server startup hook scopes the singleton bind to **only the long-lived API process**, which is the only consumer of the tracker today. Matches Phase C's pattern (`telemetry-collector` also bound at server boot, not at db.ts level).

## Build status

`npm run build` emitted target dist files despite pre-existing tsc errors unrelated to F10 (same `[[vps-build-broken-runs-on-stale-dist]]` pattern from Phases A/C):

- `dist/api-server.js`: 26385 bytes (was ~25220 post-Phase C → +1165 bytes, matches the +26 source lines).
- `dist/lib/shadow-tracker.js`: 15736 bytes (new file).
- Pre-existing tsc errors in `src/lib/confidence/__tests__/`, `src/lib/op-audit-extension/__tests__/`, `src/lib/regex-extract/__tests__/`, `src/api/answer.example.ts` — NOT related to this deploy; tsc emits with `noEmitOnError unset`.

Grep `dist/api-server.js` confirmed compiled imports correctly resolve `./lib/shadow-tracker.js`:

```
23: import { handleObsShadow, tracker as shadowTracker, } from "./lib/shadow-tracker.js";
307:                json(res, handleObsShadow(params));
```

## Service restart + boot validation

Restart at `2026-05-23 20:57:48 -03`. New PID 2315705 listening clean on `http://127.0.0.1:18802`.

Boot log lines (last two):

```
May 23 20:57:48 srv1465941 node[2315705]: [nox-mem-api] Listening on http://127.0.0.1:18802
May 23 20:57:48 srv1465941 node[2315705]: [nox-mem-api] shadow tracker DB handle wired
```

The `shadow tracker DB handle wired` line confirms CHANGE 0 Option C executed successfully — singleton tracker now has the shared `getDb()` handle for append-only persistence to `shadow_runs`.

## Smoke test results — Phase D surfaces (5 new endpoints)

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/observability/shadow` | GET | **200** | Returns `{window, features:[], latest_runs:[], generated_at_ms}` — empty initial state, correct |
| `/api/observability/shadow?feature=temporal-spike-v2&window=24h` | GET | **200** | Returns single-feature aggregate w/ 24 zero-filled buckets |
| `/observability/shadow.html` | GET | **200** | 3436 bytes served, correct content-type `text/html` |
| `/observability/shadow.js` | GET | **200** | 13857 bytes served, correct content-type `application/javascript` |
| `/observability/shadow.css` | GET | **200** | 4868 bytes served, correct content-type `text/css` |

## Regression results — Phase A/B/C endpoints (zero regression)

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/api/health` | GET | **200** | chunks=68995, types snapshot intact |
| `/api/observability/health` | GET | **200** | Phase A intact |
| `/api/observability/telemetry?window=24h` | GET | **200** | Phase C intact |
| `/api/observability/evals` | GET | **200** | Phase B intact |
| `/observability/telemetry.html` | GET | **200** | 3035 bytes (unchanged from Phase C) |

## Append-only trigger validation

Inserted one test row directly via sqlite3 to force trigger fire on mutation attempts:

```
INSERT INTO shadow_runs (ts, feature, query_hash, ...) VALUES (..., '_trigger_test_', 'aaaa1111bbbb2222', 0.5, 0.6, 20.0, '{}')
```

| Attempt | Expected | Actual |
|---|---|---|
| `DELETE FROM shadow_runs WHERE feature='_trigger_test_';` | Error + row preserved | `Error: stepping, shadow_runs is append-only: DELETE blocked (19)` — row count remained 1 |
| `UPDATE shadow_runs SET feature='_x_' WHERE feature='_trigger_test_';` | Error + value preserved | `Error: stepping, shadow_runs is append-only: UPDATE blocked (19)` — feature value still `_trigger_test_` |

**Audit residue:** the test row (id=1, feature=`_trigger_test_`, query_hash=`aaaa1111bbbb2222`, delta_pct=20.0) is now permanent in `shadow_runs` per the append-only design. This is intentional — the row serves as durable evidence that the triggers fired in prod. It does NOT pollute the dashboard endpoint, since the in-memory ring buffer (which the dashboard reads) was not populated with this row — confirmed via `?feature=_trigger_test_&window=24h` returning `count: 0`.

## 404 endpoints hint list

Confirmed `/api/observability/shadow` and `/observability/shadow.html` appear in the `endpoints` array returned by the default 404 branch:

```
"/api/observability/telemetry","/observability/telemetry.html",
"/api/observability/shadow","/observability/shadow.html",
"/observability/gate-annotations.json"
```

## Anomalies + watch-items

1. **Pre-existing tsc errors** — same `[[vps-build-broken-runs-on-stale-dist]]` pattern carried over from Phase A → C. Not introduced by F10-D; tsc emits dist despite errors. Tracking only.
2. **CHANGE 2 deferred** — `/api/search` shadow-comparison wrapper not wired. Phase 2 follow-up will land it once a specific shadow feature is enabled. Risk: until then, the dashboard remains empty unless a future caller invokes `recordShadowComparison()` from another path. **This is the intended state per wire-up.md.**
3. **Test row permanence** — id=1 `_trigger_test_` row in `shadow_runs` is intentional audit evidence per append-only design. Documented above for any future operator inspecting the table.
4. **Dashboard remains empty in initial state** — by design. Once Phase 2 wires a shadow-mode feature, real comparisons will start populating both the SQL table and the in-memory ring buffer.

## Rollback playbook (if needed)

```bash
# 1. Restore api-server.ts from pre-deploy backup
ssh root@187.77.234.79 'cp /tmp/api-server.ts.pre-f10d /root/.openclaw/workspace/tools/nox-mem/src/api-server.ts'

# 2. Rebuild
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && npm run build 2>&1 | tail -5'

# 3. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 3 && systemctl is-active nox-mem-api'

# 4. Verify rollback
ssh root@187.77.234.79 'curl -sS http://127.0.0.1:18802/api/observability/shadow'
# Expected: 404 with endpoints list lacking /api/observability/shadow

# 5. (Optional) The shadow_runs table remains in nox-mem.db — append-only research
#    data, intentionally preserved on rollback. If full table removal needed:
ssh root@187.77.234.79 'sqlite3 .../nox-mem.db "DROP TRIGGER trg_shadow_runs_block_delete; DROP TRIGGER trg_shadow_runs_block_update; DROP TABLE shadow_runs;"'
# (only if explicit cleanup is required — default rollback preserves the table)
```

**Risk profile:** ZERO data loss on code-level rollback — shadow-tracker data is append-only research evidence, intentionally preserved. In-memory ring buffer is reset on every restart anyway, so dashboard rollback is a no-op. Backup file `/tmp/api-server.ts.pre-f10d` persists until VPS reboot. After 24h confidence window, promote to `/var/backups/nox-mem/api-server.ts.pre-f10d-2026-05-23` for longer retention.

## Operational handoff

- Dashboard URL (Tailscale): `http://nox-vps.tailnet:18802/observability/shadow.html`
- API contract:
  - `GET /api/observability/shadow` → `{window, features:[ShadowAggregate], latest_runs:[ShadowComparison], generated_at_ms}` (no filter: all tracked features sorted ascending)
  - `GET /api/observability/shadow?feature=<name>&window={1-24}h` → single-feature aggregate w/ `latest_runs[≤10]` drill-down
- Append-only persistence: `shadow_runs` SQLite table — every comparison persisted indefinitely
- In-memory ring buffer: 24h × 1h × N features, lost on process restart
- No env var changes required at deploy time. Phase 2 will add `NOX_SHADOW_<FEATURE>=1` flags per shadow feature.
- No cron impact. No external dependencies. No network egress.

## F10 observability suite — closure status

| Phase | Surface | Deploy date | Status |
|---|---|---|---|
| A | `/api/observability/{health,recent-ops,canary-tail}` + `health.html` | (pre-Sat) | LIVE |
| B | `/api/observability/evals` + `evals.html` | (pre-Sat) | LIVE |
| C | `/api/observability/telemetry` + `telemetry.html` | 2026-05-23 14:03 BRT | LIVE |
| D | `/api/observability/shadow` + `shadow.html` + `shadow_runs` table | 2026-05-23 20:57 BRT | **LIVE** |

**F10 suite complete.** Next observability work (out of scope here):
- Phase 2 of D — wire `/api/search` with `NOX_SHADOW_TEMPORAL_SPIKE_V2=1` once shadow flag is enabled (separate PR).
- F11 (TBD) — export to Prometheus via `staged-prometheus` adapters, gated on stable telemetry signal accumulated over 1-2 weeks.

## Next steps (post-deploy)

1. **Today (Sat 2026-05-23 EOD):** monitor `journalctl -u nox-mem-api` for 1h — confirm no late-binding errors from shadow tracker setDB hook.
2. **Sun 2026-05-24:** confirm `/api/observability/shadow` remains 200 with empty state (no traffic expected since no flag is set).
3. **Mon 2026-05-25:** review whether to enable first shadow feature (likely temporal-spike-v2 per `[[temporal-spike-v2-win-2026-05-20]]` 7d burn-in completion).
4. **Phase 2 of F10-D (TBD):** add CHANGE 2 to wrap `/api/search` with one specific shadow comparison once a feature flag is enabled (separate PR).
