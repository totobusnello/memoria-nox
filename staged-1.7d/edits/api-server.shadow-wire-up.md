# Wire-up patch — F10 Phase D shadow tracker endpoint

**APPLIES ON TOP OF:** VPS `src/api-server.ts` (post F10 Phase A + B + C deploy state).
**ADDS:**
  - Import `recordShadowComparison` + `handleObsShadow` from `./lib/shadow-tracker.js`
  - Optional hook in `/api/search` to record a baseline-vs-shadow comparison when
    a shadow-mode feature is enabled (e.g. `NOX_SHADOW_<FEATURE>=1` env).
  - New endpoint `GET /api/observability/shadow?feature=<name>&window=24h&bucket=1h`
  - Static serving for `public/observability/shadow.{html,js,css}`
  - One-time `db.exec(SHADOW_SCHEMA)` on startup so `shadow_runs` exists.

Pattern: surgical manual FIND/REPLACE. No behaviour change to existing endpoints
unless a shadow feature env-flag is explicitly set.

---

## CHANGE 0 — Apply schema on startup

The shadow tracker table is created by executing `staged-1.7d/edits/src/lib/shadow-tracker-schema.sql`
against the main nox-mem.db. Two options:

**Option A — execute SQL file on boot (recommended):**

**FIND** the db.ts initialisation block (right after the existing schema migrations,
e.g. where `applyMigrations(db)` is invoked):

```ts
// Existing migrations applied above
applyMigrations(db);
```

**ADD BELOW:**

```ts
// F10 Phase D — shadow tracker append-only table
import { readFileSync } from "node:fs";
const shadowSchema = readFileSync(
  join(process.cwd(), "src", "lib", "shadow-tracker-schema.sql"),
  "utf-8",
);
db.exec(shadowSchema);

// Wire the in-process tracker to the shared DB handle
import { tracker } from "./lib/shadow-tracker.js";
tracker.setDB(db);
```

**Option B — out-of-band migration:** run the SQL once manually:

```bash
sqlite3 /root/.openclaw/workspace/tools/nox-mem/nox-mem.db < src/lib/shadow-tracker-schema.sql
```

Either is safe; the schema is idempotent (`CREATE TABLE IF NOT EXISTS` + triggers).

---

## CHANGE 1 — Add import

**FIND** the existing observability imports added in Phases A/C:

```ts
import {
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
} from "./observability.js";

import {
  recordRequest,
  handleObsTelemetry,
} from "./lib/telemetry-collector.js";
```

**ADD BELOW:**

```ts
import {
  recordShadowComparison,
  handleObsShadow,
  tracker as shadowTracker,
} from "./lib/shadow-tracker.js";
```

---

## CHANGE 2 — (Optional) hook /api/search to feed the tracker

Shadow-mode features run BOTH the baseline ranker and the candidate ranker for
a fraction of traffic, then forward the BASELINE response to the client. Wire
the tracker like this only inside features that are already shadow-gated by an
env flag (e.g. `NOX_SHADOW_TEMPORAL_SPIKE_V2=1`):

**FIND** the `/api/search` handler, around where results are assembled:

```ts
case "/api/search": {
  const _t0 = Date.now();
  const params = parseQuery(url);
  // ... existing logic unchanged ...
  const results = search(db, query, ...);
  // [Phase C telemetry hook stays unchanged]
  recordRequest("search", _t0, Date.now(), results.results?.length ?? 0, _pathUsed, _semantic);
  json(res, { results });
  break;
}
```

**WRAP with optional shadow comparison (example for temporal-spike-v2):**

```ts
case "/api/search": {
  const _t0 = Date.now();
  const params = parseQuery(url);
  // ... existing logic unchanged ...
  const results = search(db, query, ...);

  // ── F10 Phase D — shadow comparison (only when env flag enabled) ──
  if (process.env["NOX_SHADOW_TEMPORAL_SPIKE_V2"] === "1") {
    try {
      const shadowResults = searchWithShadow(db, query, { temporal_spike_v2: true });
      recordShadowComparison(
        "temporal-spike-v2",
        query,
        results.results ?? [],
        shadowResults.results ?? [],
        {
          baseline: results.meta?.ndcg10 ?? 0,
          shadow: shadowResults.meta?.ndcg10 ?? 0,
        },
      );
    } catch (err) {
      // Never break the hot-path — shadow is observation-only.
      process.stderr.write(`[shadow] temporal-spike-v2 comparison failed: ${err.message}\n`);
    }
  }

  recordRequest("search", _t0, Date.now(), results.results?.length ?? 0, _pathUsed, _semantic);
  json(res, { results });
  break;
}
```

**Notes:**
- The tracker call is fire-and-forget synchronous — same model as
  `recordRequest`. Persistence failures bump `tracker.getSkippedPersistCount()`
  without throwing.
- For multiple shadow features, repeat the `if (process.env[…] === "1")`
  block per feature; each one writes to its own bucket map.
- Salience shadow already runs unconditionally (per
  memory `[[shadow-mode-for-ranking-changes]]`). Wire it the same way against
  the active salience formula.

---

## CHANGE 3 — Add shadow endpoint case

**FIND** the three Phase A observability cases and the Phase C
`/api/observability/telemetry` case, then ADD AFTER:

```ts
      case "/api/observability/shadow": {
        const params = parseQuery(url);
        json(res, handleObsShadow(params));
        break;
      }
```

---

## CHANGE 4 — Static serving for shadow dashboard

**FIND** the Phase C telemetry static-serving block (or Phase A health one):

```ts
case "/observability/telemetry.html":
case "/observability/telemetry.js":
case "/observability/telemetry.css": {
  // ...existing serving code...
}
```

**ADD three more cases (same pattern):**

```ts
case "/observability/shadow.html":
case "/observability/shadow.js":
case "/observability/shadow.css": {
  const filename = path.split("/").pop()!;
  const fullPath = join(process.cwd(), "public", "observability", filename);
  try {
    fsStat(fullPath);
    const body = fsReadFile(fullPath, "utf-8");
    const ext = filename.split(".").pop();
    const ct =
      ext === "html" ? "text/html; charset=utf-8" :
      ext === "js"   ? "application/javascript; charset=utf-8" :
      ext === "css"  ? "text/css; charset=utf-8" :
      "application/octet-stream";
    res.writeHead(200, { "Content-Type": ct, "Cache-Control": "no-store" });
    res.end(body);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" });
    res.end("not found");
  }
  break;
}
```

---

## CHANGE 5 — Update 404 endpoint list (cosmetic)

Append to the `endpoints` array in the `default:` 404 branch:

```ts
"/api/observability/shadow",
"/observability/shadow.html",
```

---

## Verification on VPS (post-apply)

```bash
# 1. Confirm schema migrated
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && \
  sqlite3 nox-mem.db ".schema shadow_runs"'

# Expected: table + 2 triggers + 2 indexes

# 2. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 2 && systemctl is-active nox-mem-api'

# 3. Smoke test endpoint (initially empty when no shadow feature is enabled)
curl -s 'http://127.0.0.1:18802/api/observability/shadow?window=24h' | jq '.'
# Expected: { features: [], latest_runs: [], window: {hours:24,...} }

# 4. Smoke test with explicit feature filter
curl -s 'http://127.0.0.1:18802/api/observability/shadow?feature=temporal-spike-v2&window=24h' | jq '.features[0].count'
# Expected: 0 (zero-filled aggregate)

# 5. Enable one shadow feature in /root/.openclaw/.env, restart, run a few searches
echo 'NOX_SHADOW_TEMPORAL_SPIKE_V2=1' >> /root/.openclaw/.env
ssh root@187.77.234.79 'systemctl restart nox-mem-api'
curl -s 'http://127.0.0.1:18802/api/search?q=last+week+meeting' >/dev/null
curl -s 'http://127.0.0.1:18802/api/search?q=action+items' >/dev/null

# 6. Confirm the shadow tracker captured the comparison
curl -s 'http://127.0.0.1:18802/api/observability/shadow?feature=temporal-spike-v2&window=1h' | jq '.features[0].count'
# Expected: 2

# 7. Confirm append-only triggers fire
sqlite3 nox-mem.db "DELETE FROM shadow_runs;"
# Expected: Runtime error near DELETE: shadow_runs is append-only: DELETE blocked

# 8. Open dashboard
# http://nox-vps.tailnet:18802/observability/shadow.html
```

---

## Rollback

1. Remove the 5 wire-up changes above (revert imports, endpoint case, static
   block, optional `/api/search` hook, env flags).
2. Restart `nox-mem-api`.
3. The `shadow_runs` table remains in the DB — it is append-only research data,
   intentionally preserved. If table removal is needed:
   - Stop the service.
   - `sqlite3 nox-mem.db "DROP TRIGGER trg_shadow_runs_block_delete; DROP TRIGGER trg_shadow_runs_block_update; DROP TABLE shadow_runs;"`
   - Restart.

No data-loss risk on rollback: the in-memory ring buffer is reset on every
process restart anyway; the SQLite table is additive.

---

## Closure of F10 observability suite

After this Phase D ships, F10 observability suite is complete:

| Phase | Endpoint | Surface |
|-------|----------|---------|
| A | `/api/observability/health`, `/recent-ops`, `/canary-tail` | Prod health + audit |
| B | `/observability/eval-browser.html` | Eval result browser |
| C | `/api/observability/telemetry` | Per-request latency + ranking path mix |
| D | `/api/observability/shadow` | Shadow-mode A/B comparisons |

Next observability work (out of scope here): export to Prometheus via the
`staged-prometheus` adapters once the shadow/telemetry signal stabilises.
