# E12-followup Deployment Checklist

**Target:** nox-mem VPS — /root/.openclaw/workspace/tools/nox-mem/
**Risk:** Minimal. Additive schema change + 2 function signature extensions.
**Downtime:** Zero. ALTER TABLE ADD COLUMN in SQLite does not lock reads/writes.

---

## Pre-flight (read-only, 2 min)

```bash
# 1. Confirm current schema — column must be ABSENT
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT name FROM pragma_table_info('search_telemetry');"
# Expected: requesting_agent NOT in the list

# 2. Confirm current row count (sanity baseline)
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT COUNT(*) FROM search_telemetry;"
```

---

## Step 1 — Apply DB migration

```bash
cd /root/.openclaw/workspace/tools/nox-mem

# Run migration — idempotent (error on re-run is suppressed by || true)
sqlite3 nox-mem.db "ALTER TABLE search_telemetry ADD COLUMN requesting_agent TEXT;" 2>/dev/null || true

# Backfill historical rows
sqlite3 nox-mem.db "UPDATE search_telemetry SET requesting_agent = 'unknown' WHERE requesting_agent IS NULL;"

# Validate
sqlite3 nox-mem.db "
SELECT
  COUNT(*) AS total_rows,
  COUNT(requesting_agent) AS rows_with_agent,
  COUNT(*) - COUNT(requesting_agent) AS still_null
FROM search_telemetry;"
# Expected: still_null = 0
```

Alternatively, run the full migration.sql directly:
```bash
sqlite3 nox-mem.db < /path/to/migration.sql
```

---

## Step 2 — Verify schema

```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  ".schema search_telemetry"
# Must show: requesting_agent TEXT at the end
```

---

## Step 3 — Patch src/search.ts

Open `/root/.openclaw/workspace/tools/nox-mem/src/search.ts` in your editor.

Apply three changes as described in `search.ts.patch`:

**3a.** Add `requestingAgent?: string | null` as the last parameter of `logTelemetry()`.

**3b.** Extend the INSERT statement inside `logTelemetry()`:
- Column list: append `, requesting_agent`
- Values list: append `, ?`
- `.run(...)` call: append `, requestingAgent ?? null`

**3c.** Update `searchHybrid()`:
- Add `requestingAgent?: string | null` as third parameter (default: undefined)
- Add `const resolvedAgent = requestingAgent ?? process.env.NOX_AGENT_NAME ?? null;` at top of function body
- Change the `logTelemetry()` call to pass `resolvedAgent` as the last argument

---

## Step 4 — Patch src/api-server.ts

Open `/root/.openclaw/workspace/tools/nox-mem/src/api-server.ts` in your editor.

**4a.** In the `"/api/search"` case, extract agent identifier before calling `searchHybrid`:
```typescript
const agentHeader = req.headers["x-agent-name"];
const requestingAgent =
  (Array.isArray(agentHeader) ? agentHeader[0] : agentHeader)
  ?? process.env.NOX_AGENT_NAME
  ?? null;
const results = await searchHybrid(q.q, limit, requestingAgent);
```

**4b.** In the `json()` helper, update `Access-Control-Allow-Headers`:
```typescript
"Access-Control-Allow-Headers": "Content-Type, X-Agent-Name",
```

No changes needed to `src/index.ts` (CLI) — it already calls `searchHybrid()` with no third argument, and the function will resolve `NOX_AGENT_NAME` from env automatically.

---

## Step 5 — Build

```bash
cd /root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a
npm run build
# Watch for TypeScript errors. Expected: zero errors.
```

---

## Step 6 — Restart services

```bash
systemctl restart nox-mem-api nox-mem-watcher
# Wait ~5s for startup
systemctl status nox-mem-api nox-mem-watcher
```

---

## Step 7 — Smoke tests

```bash
# Test 1: CLI — agent resolved from env
NOX_AGENT_NAME=nox nox-mem search "session state"
# Then verify telemetry row
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT query_hash, requesting_agent FROM search_telemetry ORDER BY ts DESC LIMIT 3;"
# Expected: requesting_agent = 'nox' on the latest row

# Test 2: HTTP API without header — falls back to env
curl -s "http://127.0.0.1:18802/api/search?q=salience" | jq 'length'
# Then check telemetry again

# Test 3: HTTP API with header
curl -s -H "X-Agent-Name: atlas" "http://127.0.0.1:18802/api/search?q=kg+entities" | jq 'length'
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db \
  "SELECT query_hash, requesting_agent FROM search_telemetry ORDER BY ts DESC LIMIT 1;"
# Expected: requesting_agent = 'atlas'

# Test 4: Health endpoint still works
curl -s http://127.0.0.1:18802/api/health | jq '.searchTelemetry'
```

---

## Step 8 — Per-agent systemd unit configuration

Each agent's nox-mem-api unit (if they run separate instances) should export:

```ini
[Service]
Environment="NOX_AGENT_NAME=atlas"
```

For the shared singleton on the VPS, the HTTP header approach is preferred — each OpenClaw agent sets `X-Agent-Name: <slug>` on its search calls. Coordinate with openclaw-vps config if needed.

---

## Step 9 — Post-deploy monitoring (2 weeks)

Check weekly that new rows populate `requesting_agent`:

```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
SELECT requesting_agent, COUNT(*) as queries
FROM search_telemetry
WHERE ts >= datetime('now', '-7 days')
GROUP BY requesting_agent
ORDER BY queries DESC;"
```

---

## Step 10 — Re-run cross_agent_quantifier.py (after 2 weeks)

```bash
cd /root/.openclaw/workspace/tools/nox-mem
python3 scripts/cross_agent_quantifier.py --questions Q2 Q3 Q4 Q5 Q6
```

Gate: any non-null result (positive or null cross-agent retrieval effect) is publishable evidence for paper §5.6.

---

## Rollback

No action needed. `requesting_agent` is nullable — removing the column would require a table rebuild, which is unnecessary. If the code change causes build errors, revert `src/search.ts` and `src/api-server.ts` to the pre-patch version and rebuild. The column in the DB is harmless whether or not the application code uses it.
