# Wire-up patch — F10 Phase B evals endpoint + static assets

**APPLIES ON TOP OF:** VPS `src/api-server.ts` (post-Phase-A-deploy state, i.e. after `api-server.observability-wire-up.md` has been applied).
**ADDS:** One read-only endpoint `/api/observability/evals` + extends the Phase A static-file allow-list with `/observability/evals.{html,js,css}` and `/observability/gate-annotations.json`.

Same surgical FIND/REPLACE pattern as the Phase A doc. Four numbered CHANGE blocks.

---

## CHANGE 1 — Add import (near top of file, next to the Phase A imports)

**FIND** (added in Phase A wire-up):

```ts
import {
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
} from "./observability.js";
```

**REPLACE WITH:**

```ts
import {
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
} from "./observability.js";
import { handleObsEvals } from "./evals.js";
```

The `path` + `fs` imports added in Phase A already cover this change. No other imports needed — the evals module owns its own filesystem reads.

---

## CHANGE 2 — Add the new switch case inside `handleRequest`

**FIND** the existing Phase A block:

```ts
      case "/api/observability/canary-tail": {
        const params = parseQuery(url);
        const n = parseInt(params.n || "3", 10);
        json(res, handleObsCanaryTail(Number.isFinite(n) ? n : 3));
        break;
      }
```

**ADD AFTER IT** (still inside the `switch (path)` block):

```ts
      case "/api/observability/evals": {
        const params = parseQuery(url);
        const limit = parseInt(params.limit || "500", 10);
        const dbSource = params.db_source || params.dbSource || undefined;
        json(res, handleObsEvals({
          dbSource,
          limit: Number.isFinite(limit) ? limit : 500,
        }));
        break;
      }
```

Reuses the existing `parseQuery()` helper and `json()` writer. Handler lives in `evals.ts` — no filesystem or aggregation logic embedded in the router. The 5-min in-memory cache is owned by the handler module.

---

## CHANGE 3 — Extend the static-file allow-list

Phase A added a static-serving branch with an explicit allow-list of three filenames under `/observability/`. Find that block:

```ts
      case "/observability/health.html":
      case "/observability/health.js":
      case "/observability/health.css": {
```

**REPLACE THE THREE CASE LINES WITH:**

```ts
      case "/observability/health.html":
      case "/observability/health.js":
      case "/observability/health.css":
      case "/observability/evals.html":
      case "/observability/evals.js":
      case "/observability/evals.css":
      case "/observability/gate-annotations.json": {
```

The rest of the block (the body that resolves the file, sets the Content-Type, etc.) requires one small extension — the MIME map needs a `.json` branch. Find the `ct` ternary in the body:

```ts
          const ct =
            ext === "html" ? "text/html; charset=utf-8" :
            ext === "js"   ? "application/javascript; charset=utf-8" :
            ext === "css"  ? "text/css; charset=utf-8" :
            "application/octet-stream";
```

**REPLACE WITH:**

```ts
          const ct =
            ext === "html" ? "text/html; charset=utf-8" :
            ext === "js"   ? "application/javascript; charset=utf-8" :
            ext === "css"  ? "text/css; charset=utf-8" :
            ext === "json" ? "application/json; charset=utf-8" :
            "application/octet-stream";
```

No path-traversal risk — the case labels are an explicit allow-list, and the body still uses `path.split("/").pop()!` so no `..` resolution.

---

## CHANGE 4 — Update the 404 endpoint list (cosmetic)

In the `default:` branch, the `endpoints` array in the 404 response lists known paths. Append:

```ts
"/api/observability/evals",
"/observability/evals.html",
"/observability/gate-annotations.json",
```

---

## Verification on VPS (post-apply)

```bash
# 1. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 2 && systemctl is-active nox-mem-api'

# 2. Smoke test the new endpoint
curl -s 'http://127.0.0.1:18802/api/observability/evals?limit=5' | jq 'length, .[0] | {run_id, config_id, db_source, ndcg_at_10}'
curl -s 'http://127.0.0.1:18802/api/observability/evals?db_source=g5.db' | jq 'length'

# 3. Static assets
curl -sI http://127.0.0.1:18802/observability/evals.html | head -3
curl -s  http://127.0.0.1:18802/observability/gate-annotations.json | jq 'length'

# 4. Open dashboard locally via Tailscale tunnel
# http://nox-vps.tailnet:18802/observability/evals.html
```

The endpoint reads `audits/data-G*` relative to `process.cwd()`. On the VPS this resolves under `${OPENCLAW_WORKSPACE}/tools/nox-mem/`, which is the deploy working directory for `nox-mem-api`. If the deploy ever runs from a different cwd, pass an explicit `auditsRoot` to `handleObsEvals` from the api-server wrapper (the handler accepts options).

---

## Rollback

Revert the four CHANGES above. Endpoint + static handler extensions are additive — removing them restores Phase A behavior. No DB migration required.
