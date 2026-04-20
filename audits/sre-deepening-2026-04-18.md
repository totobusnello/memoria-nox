# SRE Deepening — 2026-04-18

Read-only audit. Architect's hypothesis on Gap 2 is **confirmed with a twist**.

---

## 1. Gap 2 — Full RCA: the 5-minute restart loop

### Evidence
- `/root/.openclaw/.env` sets `NOX_API_PORT=18802`. `api-server.ts:16` reads it. Logs confirm: `Listening on http://0.0.0.0:18802`.
- `/root/.openclaw/scripts/health-probe.sh:38` probes `http://127.0.0.1:**18800**/api/health` with a 3s timeout.
- Cron `*/5 * * * * health-probe.sh` runs every 5 min.
- `ss -tlnp`: port **18800 is held by a stale Chrome process (pid 279690)**, not nox-mem. nox-mem listens on 18802. So the probe gets a TCP connect to Chrome which does NOT speak HTTP → `curl -sf` fails → `systemctl restart nox-mem-api`.
- Journal shows the pattern precisely: start at :HH:00, restart at :HH:05, :10, :15…
- `Restart=on-failure` + `RestartSec=10` + **no** `StartLimitBurst`/`StartLimitIntervalSec`. Service comes back cleanly each time so `on-failure` doesn't trigger infinite loops — but there's also no crash-loop ceiling.

### Architect's twist
The probe isn't just misaligned — the port it probes is being *silently swallowed* by an unrelated process (Chrome remote debugging?). Without that stale listener the probe would get `ECONNREFUSED` which `curl -sf` would also fail on, so either way the restart fires. **Port drift is the root cause; Chrome squatting the old port is the reason nobody noticed sooner** (no "connection refused" in logs to trigger suspicion).

### Minimal fix (port alignment) — RECOMMENDED
Change line 38 of `health-probe.sh` to `http://127.0.0.1:${NOX_API_PORT:-18800}/api/health` and source `/root/.openclaw/.env` at the top. Zero service changes, honors the env-var contract already established, and any future port change propagates automatically. Also: kill the stale Chrome pid 279690 or reboot — it's been holding 18800 since whenever Chrome was launched with `--remote-debugging-port=18800`.

**Do NOT "unify on 18800"** — the env var explicitly says 18802, which means someone moved it deliberately (likely to dodge the Chrome squatter). Fighting that is how you get a second incident.

### Defense-in-depth (unit-file hardening)
Following the `CLAUDE.md` gateway convention:
- Add `StartLimitBurst=5` + `StartLimitIntervalSec=120` to `[Unit]` — matches gateway policy, prevents runaway restart if the real service ever crash-loops.
- Add `ExecStartPre=/bin/sh -c 'fuser -k ${NOX_API_PORT}/tcp || true'` to `[Service]` — same pattern as gateway, kills orphans by port. Currently nox-mem has no orphan protection at all.
- `Restart=always` (not `on-failure`) + `RestartSec=10` — the API is stateless, we always want it back.
- Add a proper HTTP liveness probe in the service itself: `/api/health` should return 503 (not 200) when the DB is unreadable. Today it likely returns 200 even when sqlite is locked, which defeats the probe.
- Split liveness (is the process answering TCP?) from readiness (can it serve a search?). The probe should hit liveness every 5 min and only restart on 3 consecutive failures — a single 429 from Gemini (visible in the 11:53 log) should NOT count as unhealthy.

---

## 2. Path A — Single Write Coordinator Blueprint

### Topology
```
              ┌──────────────────────────────────────────┐
              │   nox-mem-writer (daemon, new)           │
              │   - Owns the ONLY RW sqlite connection   │
              │   - Serializes: ingest, vectorize,       │
              │     kg-build, consolidate, crystallize,  │
              │     reflect-cache, decision-set          │
              │   - Manages WAL checkpoint cadence       │
              │   - Publishes metrics + queue depth      │
              └────────────▲─────────────────────────────┘
                           │ IPC (Unix socket)
      ┌────────────────────┼───────────────────┬────────────────┐
      │                    │                   │                │
┌─────┴──────┐     ┌───────┴────────┐   ┌──────┴──────┐  ┌──────┴──────┐
│ nox-mem-api│     │ nox-mem MCP    │   │ CLI (write  │  │ watcher     │
│ READ-ONLY  │     │ READ-ONLY      │   │ commands)   │  │ (ingest→    │
│ sqlite     │     │ sqlite         │   │ → RPC to    │  │  writer RPC)│
│ handle     │     │ handle         │   │ writer      │  │             │
└────────────┘     └────────────────┘   └─────────────┘  └─────────────┘
```

### IPC choice: Unix domain socket with JSON-RPC 2.0
**Chosen over HTTP** because:
- Zero port management (one more port = one more health probe to misconfigure — see Gap 2).
- FS permissions (0600 on socket) give instant AuthN — no tokens.
- ~5-10x lower latency than loopback TCP for small payloads (sub-ms).
- Cannot be accidentally exposed by a ufw rule gone wrong.

**Why not reuse HTTP on 18800?** The existing API is read-only by design and exposed to the Tailscale net (for the dashboard). Mixing write-admin endpoints into a net-exposed service expands blast radius. Keep them separate.

**Alternative kept on the table:** HTTP on 127.0.0.1:18801 bound to `lo` only, with a shared secret from `.env`. Simpler to debug with curl, marginally worse security.

### Failure modes
1. **Writer crashes mid-transaction** — sqlite WAL guarantees atomicity per-statement. Wrap multi-step ops (crystallize = insert procedure + 3 FTS updates + 2 KG inserts) in an explicit `BEGIN IMMEDIATE…COMMIT`. On crash, sqlite rolls back automatically at next open. Add a `startup_recovery` step that runs `PRAGMA wal_checkpoint(TRUNCATE)` and `PRAGMA integrity_check` before accepting RPCs.
2. **Startup ordering** — systemd: `nox-mem-writer.service` as `Type=notify` (socket-ready signal), then `nox-mem-api.service` with `After=nox-mem-writer.service` + `Requires=` (not just `Wants=`). Readers *can* start without the writer if you accept degraded mode (search works, ingest fails) — recommend `Wants=` + graceful degradation in clients.
3. **Backpressure** — bounded in-memory queue per op class (e.g., 100 ingests, 10 kg-builds). On full, RPC returns 503 with `Retry-After`. Never silently drop. Expose `queue_depth_by_class` as a metric.
4. **Slow consumer starves others** — priority queues: interactive (crystallize from a user's reflect call) > batch (cron vectorize). kg-build is the classic starver — cap it at 2 concurrent and schedule off-peak.
5. **Writer hangs (not crash)** — systemd `WatchdogSec=30` + heartbeat in the notify loop. Autokill if no heartbeat.

### Migration plan (zero-downtime)
1. **Ship writer as shadow-only** (2 days): writer reads `WRITE_COORDINATOR_MODE=shadow` — receives RPCs, logs them, but doesn't execute. CLI/watcher call it AND do their own writes. Validate the RPC surface and queue behavior.
2. **Canary one op class** (3 days): switch `crystallize` only to `mode=real`. It's the newest, lowest volume, easiest to roll back. Observe for 72h.
3. **Cutover by class** (1-2 weeks): vectorize → reflect-cache → ingest → kg-build → consolidate. Each class gets 48h of burn-in before the next.
4. **Disable direct writes** (final): readers use read-only sqlite handle (`mode=ro` in URI).
5. **Rollback**: each class has a feature flag. Flip back in seconds.

### What Path A does NOT solve (be honest)
- **Read latency under heavy write** — WAL means readers don't block, but `PRAGMA wal_checkpoint` does. You still need to tune checkpoint cadence.
- **Gemini/Ollama API dependencies** — KG extraction calls external APIs. Writer still needs retry/circuit-breaker logic. Today's 429 from Gemini (11:53 log) is a visible symptom.
- **Disk fills up** — single writer doesn't help you spot WAL bloat or backup explosion.
- **The dashboard** — still hits read-only API on 18802. Path A is invisible to it.
- **Scale ceiling** — eventually a single writer becomes the bottleneck. At nox-mem's scale (1,880 chunks, 384 KG entities, writes measured in ops/minute not ops/second), **Path A is appropriate for the next 12-24 months**. Past that, consider per-agent shards.

**Honest verdict:** Path A is worth doing *now*, not because contention is breaking things today (it isn't — busy_timeout handles it), but because it makes crystallize/reflect behave predictably and unblocks the observability work below. It is NOT premature for a system this complex. It WOULD be premature for a system half this size.

---

## 3. Observability Gaps

### What's missing from `/api/health` today
Based on the current probe behavior and the logs:
- No latency histograms (search p50/p95/p99)
- No cache hit-rate telemetry (reflect cache, embedding cache)
- No consolidation staleness (when was the last successful run?)
- No external-API cost/quota tracking (the 429 at 11:53 was invisible to ops)
- No disk/WAL/tmp pressure
- No MCP tool usage counts — can't tell if `kg_path`, `cross_kg`, `self_improve` are even being called (Gap 5)

### Proposed metrics (name, source, alert threshold)

| Metric | Source | Alert when |
|---|---|---|
| `nox_search_latency_seconds{layer,quantile}` | wrap `search()` in api-server + MCP | p95 > 1.0s for 10 min (search is the user-facing SLI) |
| `nox_reflect_cache_hit_ratio` | reflect.ts cache lookup counters | < 0.25 over 24h (cache is worthless) |
| `nox_consolidation_last_success_seconds` | `meta` table `consolidation:last_ok_ts` | > 3 days (cron is a cadence of 2d, so 3d = missed one) |
| `nox_gemini_quota_errors_total` | embed.ts 429 counter | rate > 5/hour (we're hitting quota) |
| `nox_gemini_cost_usd_today` | token counter × price table | > $2/day (early warning; current $5 hard cap) |
| `nox_sqlite_wal_bytes` | stat `nox-mem.db-wal` | > 100 MB (WAL checkpoint broken) |
| `nox_disk_free_gb{mount="/"}` | statvfs | < 5 GB warn, < 2 GB page |
| `nox_mcp_tool_calls_total{tool}` | MCP server middleware | rate = 0 for 7 days on a non-deprecated tool (dead feature) |

### `/api/health` vs `/api/metrics` — argue

**Do both. Different audiences.**
- `/api/health` stays as a **liveness probe**: returns 200 or 503, sub-10ms, no DB reads beyond a pragma. This is what the cron probe should hit (and once it does, fix Gap 2 properly).
- Add `/api/metrics` in Prometheus exposition format. It's the de facto standard, the dashboard can scrape it directly via `prom-client` or parse text, and if you ever add Grafana/VictoriaMetrics it's plug-and-play. JSON fields on `/api/health` don't scale past ~10 metrics and conflate liveness with telemetry.

### Gap 5 — minimal-overhead MCP telemetry
In the MCP server entry point, wrap each tool handler with:
```
const start = performance.now();
try { return await tool.handler(args); }
finally {
  db.prepare('INSERT INTO mcp_tool_calls (tool, duration_ms, ts) VALUES (?,?,?)').run(name, performance.now()-start, Date.now());
}
```
A single insert per call. At ~200 MCP calls/day, that's noise. Expose as `nox_mcp_tool_calls_total{tool}` (counter) + `nox_mcp_tool_duration_seconds{tool}` (histogram via aggregated query). Reveals zombie features in 7 days.

**Alternative, even cheaper:** async append to a JSONL file, rollup to a table in a cron. Good if you're paranoid about write contention — but Path A solves that anyway.

---

## 4. Reliability SLOs (single-VPS, no HA)

Realistic for this system. Measured over 30 days unless noted.

1. **Search availability ≥ 99.5%** (allows ~3.6h downtime/month). NOT 99.9% — one VPS, one power supply, Hostinger has had multi-hour incidents. Promising 99.9% is lying. Error budget math works: a 1h reboot + a few restart blips fit inside 0.5%.

2. **Search latency p95 < 500ms** (end-to-end, hybrid). Today's system hits this comfortably when healthy; codifying it catches regressions from KG growth or index bloat. p99 < 2s as a secondary.

3. **Reflect cache hit rate ≥ 40% over 7 days.** Cache exists to cut Gemini cost and latency. Below 40% means the cache key is wrong or TTL is too short; that's actionable. 40% is conservative for a synthesis cache — if we hit 70% great, but committing to 40% is defensible.

4. **Consolidation freshness: last successful run < 72h, 99% of the time.** Cron runs every 48h; 72h budget absorbs one miss. If this breaks the symptom is silent memory rot — this SLO is the guardrail.

5. **Zero data loss on writer-handled ops, measured monthly.** Every `crystallize`/`kg-build`/`ingest` RPC either commits fully or rolls back fully — no partial states. Auditable via `dedup_log` and a new `write_audit` table. This is the SLO Path A actually buys you.

**Explicitly NOT an SLO:** MCP tool availability (nice to have, not user-facing), KG entity count growth (throughput, not reliability), dashboard uptime (separate repo, separate problem).

---

## Summary for commit

- **Gap 2 = port 18800/18802 drift + Chrome squatter on 18800.** Fix probe to use env var. Add `StartLimitBurst` and `ExecStartPre=fuser -k` to unit. Kill stale Chrome pid 279690.
- **Path A: ship it, via Unix socket, migrate by op class over 2 weeks.** Worth doing now for crystallize/reflect predictability and for observability hooks. Not a silver bullet — doesn't help external APIs or disk.
- **Observability: add `/api/metrics` (Prometheus), 8 new metrics, wrap MCP handlers for Gap 5.** Keep `/api/health` as pure liveness.
- **SLOs: 99.5% availability, p95 < 500ms, reflect cache ≥ 40%, consolidation < 72h stale, zero partial writes.**
