# E12 requesting_agent — Deployment Log

**Date:** 2026-05-04  
**Operator:** typescript-pro (Claude subagent)  
**Authorization:** Toto C2 — SSH write + npm build + 1x systemctl restart

---

## Files Modified (VPS)

| File | Path | Lines changed |
|------|------|---------------|
| `search.ts` | `/root/.openclaw/workspace/tools/nox-mem/src/search.ts` | L204–214 (sig), L227–230 (INSERT), L235–237 (searchHybrid sig + env fallback), L309 (call site) |
| `api-server.ts` | `/root/.openclaw/workspace/tools/nox-mem/src/api-server.ts` | L32 (CORS), L277–279 (agent extraction) |
| `index.ts` | `/root/.openclaw/workspace/tools/nox-mem/src/index.ts` | L40–42 (CLI NOX_AGENT_NAME read) |

Backup suffix: `.bak-pre-E12-20260504-0855` (all 3 files)

---

## Changes Applied

### search.ts — 6 changes total

**1. `logTelemetry()` signature** — added `requestingAgent?: string` as last param (after `goldenId`).

**2. INSERT statement** — column list now includes `requesting_agent`; `.run()` appends `requestingAgent || null`.

**3. `searchHybrid()` signature** — added `requestingAgent?: string` as third param.

**4. Env fallback inside `searchHybrid()`** — first line of function body:
```typescript
const resolvedAgent = requestingAgent ?? process.env.NOX_AGENT_NAME ?? undefined;
```

**5. `logTelemetry()` call** — passes `resolvedAgent` (not raw `requestingAgent`) so env fallback propagates.

**6. Type safety** — `undefined` passed for unused `goldenId` slot; no `any` introduced.

### api-server.ts — 2 changes

**1. CORS header** — `Access-Control-Allow-Headers: "Content-Type, X-Agent-Name"`.

**2. Agent extraction in `/api/search`** — array-safe, env fallback:
```typescript
const agentHeader = req.headers["x-agent-name"];
const requestingAgent = (Array.isArray(agentHeader) ? agentHeader[0] : agentHeader)
  ?? process.env.NOX_AGENT_NAME;
const results = await searchHybrid(q.q, limit, requestingAgent);
```

### index.ts — 1 change

**CLI agent resolution** — reads `NOX_AGENT_NAME` before calling `searchHybrid`:
```typescript
const cliAgent = process.env.NOX_AGENT_NAME || "cli";
const results = await searchHybrid(query, parseInt(opts.limit, 10), cliAgent);
```

---

## Build Output

```
> nox-mem@3.0.0 build
> tsc
(exit 0 — zero errors, zero warnings)
```

Two builds total: after initial 3-file patch, and after final env-fallback + CORS patch. Both clean.

---

## Smoke Test Results

### Telemetry rows populated (last 5 min at 12:01 BRT):

```
id   | ts                  | requesting_agent | results | latency_ms
-----|---------------------|------------------|---------|----------
1164 | 2026-05-04 12:01:20 | atlas            | 9       | 907
1163 | 2026-05-04 12:01:17 | test-cli         | 2       | 1610
1162 | 2026-05-04 11:59:12 | test-api         | 10      | 980
1161 | 2026-05-04 11:59:10 | test-cli         | 3       | 1447
```

All 4 rows have non-null `requesting_agent`. Propagation verified for:
- CLI via `NOX_AGENT_NAME=test-cli`
- HTTP API via `X-Agent-Name: test-api`
- HTTP API via `X-Agent-Name: atlas`

### Coverage stats post-deployment:

```
total_rows | has_agent | unknown_count
-----------|-----------|---------------
1132       | 1131      | 1129
```

The 1129 `unknown` rows are the pre-deployment backfill (historical). The 2 post-deployment rows (ids 1161–1162 from first smoke test run) already have real agents. Going forward, all new rows will have real agent identifiers.

---

## Restart

```
systemctl restart nox-mem-api  (2026-05-04 ~12:01 BRT)
/api/health response: {"up": 61258, "salience": "active"}
~30s downtime window honored.
```

---

## Rollback Procedure

Backups confirmed at `/root/.openclaw/workspace/tools/nox-mem/src/*.bak-pre-E12-20260504-0855`.

To rollback:
```bash
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem/src && \
  for bak in search.ts.bak-pre-E12-20260504-0855 api-server.ts.bak-pre-E12-20260504-0855 index.ts.bak-pre-E12-20260504-0855; do \
    orig=${bak%.bak-pre-E12-20260504-0855}; cp "$bak" "$orig"; echo "Restored $orig"; \
  done && cd .. && npm run build && systemctl restart nox-mem-api'
```

Rollback was NOT needed. Deployment fully successful.

---

## 7-Day Collection Clock

**Clock starts: 2026-05-04 12:01 BRT**  
**Gate date: 2026-05-11 12:01 BRT**

After 7 days, run:
```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db "
SELECT requesting_agent, COUNT(*) as queries
FROM search_telemetry
WHERE ts >= datetime('now', '-7 days')
  AND requesting_agent IS NOT NULL
  AND requesting_agent != 'unknown'
GROUP BY requesting_agent
ORDER BY queries DESC;"
```

Then execute `scripts/cross_agent_quantifier.py --questions Q2 Q3 Q4 Q5 Q6` per deployment-checklist Step 10.
