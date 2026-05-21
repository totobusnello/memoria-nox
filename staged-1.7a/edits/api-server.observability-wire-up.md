# Wire-up patch — F10 Phase A observability endpoints

**APPLIES ON TOP OF:** VPS `src/api-server.ts` (post-Wave-A-deploy state)
**ADDS:** Three read-only endpoints under `/api/observability/*` + static dir serving for `public/observability/`.

Pattern matches `api-server.patch.ts` — surgical manual FIND/REPLACE, no behavior change to existing endpoints.

---

## CHANGE 1 — Add import (after existing imports near top of file)

**FIND** (last import line before const PORT, varies by deploy):

```ts
import { execFileSync } from "child_process";
```

**ADD BELOW:**

```ts
import {
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
} from "./observability.js";
import { join } from "path";
import { readFileSync as fsReadFile, statSync as fsStat } from "fs";
```

The `path` + `fs` imports are reused for the static-file branch below; if either is already present in the file, skip the duplicate.

---

## CHANGE 2 — Add three switch cases inside `handleRequest`

**FIND** the existing `case "/api/health": { ... break; }` block.

**ADD AFTER IT** (still inside the `switch (path)` block):

```ts
      case "/api/observability/health": {
        const db = getDb();
        json(res, handleObsHealth(db));
        break;
      }

      case "/api/observability/recent-ops": {
        const db = getDb();
        const params = parseQuery(url);
        const n = parseInt(params.n || "10", 10);
        json(res, handleObsRecentOps(db, Number.isFinite(n) ? n : 10));
        break;
      }

      case "/api/observability/canary-tail": {
        const params = parseQuery(url);
        const n = parseInt(params.n || "3", 10);
        json(res, handleObsCanaryTail(Number.isFinite(n) ? n : 3));
        break;
      }
```

These three cases reuse the existing `parseQuery()` helper and the `json()` writer. Handler functions live in `observability.ts` — no DB logic embedded in the router.

---

## CHANGE 3 — Static serving for the dashboard page

The Phase A UI lives at `public/observability/health.{html,js,css}`. Two options:

### Option A (recommended, single deploy target)

Add a fallback branch at the END of the switch statement (just before `default:`) to serve files under `/observability/`:

```ts
      case "/observability/health.html":
      case "/observability/health.js":
      case "/observability/health.css": {
        const filename = path.split("/").pop()!;
        const fullPath = join(process.cwd(), "public", "observability", filename);
        try {
          fsStat(fullPath); // existence check (throws ENOENT otherwise)
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

The three filenames are an explicit allow-list (no path traversal possible — no `..` resolution, `pop()` strips path).

### Option B (separate deploy)

Serve `public/observability/` via nginx/Caddy on the same VPS at a different port, proxying API calls back to `:18802`. More moving parts; only justify if Option A creates noisy logs.

**Recommendation:** Option A for Phase A. Revisit only if static traffic becomes a measurable share of API hits (it won't with one user).

---

## CHANGE 4 — Update the 404 endpoint list (cosmetic)

In the `default:` branch, the `endpoints` array in the 404 response lists all known paths. Append:

```ts
"/api/observability/health",
"/api/observability/recent-ops",
"/api/observability/canary-tail",
"/observability/health.html",
```

---

## Verification on VPS (post-apply)

```bash
# 1. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 2 && systemctl is-active nox-mem-api'

# 2. Smoke test each endpoint
curl -s http://127.0.0.1:18802/api/observability/health | jq '.indicators, .delta_24h'
curl -s http://127.0.0.1:18802/api/observability/recent-ops?n=5 | jq 'length'
curl -s http://127.0.0.1:18802/api/observability/canary-tail?n=3 | jq '.[].timestamp'

# 3. Open dashboard locally via Tailscale tunnel
# http://nox-vps.tailnet:18802/observability/health.html
```

---

## Rollback

Revert the four CHANGES above. Endpoints + static handler are additive — removing them leaves all existing behavior intact. No DB migration required.
