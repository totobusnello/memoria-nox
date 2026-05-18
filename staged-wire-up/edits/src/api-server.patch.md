# Patch: src/api-server.ts — mount Wave A→K wire-up router

> APPLIES ON TOP OF: prod `src/api-server.ts` (post-deploy Wave A→K, schema v20).
> Baseline reference: `staged-1.6/edits/api-server.ts` (lines 1–312) + `staged-P3/edits/api-server.ts` (search handler patch).

## Change 1 — import statement (add near top, after existing imports)

```ts
import { registerWireUpRoutes } from "./api/wire-up.js";
```

Insert at line ~14 (after the `execFileSync` import, before the `const PORT = …` line).

## Change 2 — dispatch inside `handleRequest()`

Find the existing `switch (path) { … default: json(res, { error: "Not found", …}, 404); }` block.

**BEFORE** the `default:` arm, insert a `default:` body that first delegates to the wire-up router:

```ts
default: {
  // Wave A→K handlers — mount post-deploy.
  if (await registerWireUpRoutes(req, res)) break;
  json(res, {
    error: "Not found",
    endpoints: [
      "/api/health", "/api/agents", "/api/kg", "/api/kg/path",
      "/api/search", "/api/cross-kg", "/api/reflect",
      "/api/procedures", "/api/crystallize", "/api/crystallize/validate",
      // Wave A→K
      "POST /api/answer",
      "POST /api/export", "POST /api/import",
      "GET /api/events/stream", "GET /viewer/*",
      "GET /api/conflict", "GET /api/conflict/:id",
      "POST /api/conflict/:id/resolve",
      "POST /api/chunk/:id/mark", "POST /api/chunk/:id/supersede",
      "GET /api/health/confidence",
      "GET /api/hooks/status", "GET /api/hooks/recent",
      "POST /api/hooks/dryrun",
    ],
  }, 404);
}
```

(Existing prod has a non-block `default:` followed by `json(...)`. Convert to block syntax `default: { … }` so `await` is valid inside.)

## Change 3 — none for top-level catch

The top-level `try { switch(...) } catch (err) { json(res, { error: String(err) }, 500); }` already exists. The wire-up router emits its OWN sanitized error (via G5) before returning `true`, so it never re-raises into this catch. Leave the catch untouched.

## Why the wire-up does NOT live in api-server.ts directly

1. **Separation of concerns** — api-server.ts holds the canonical routes that
   ship with v1.6 and are stable. Wave A→K adds 14 new routes from 7 staged
   patch dirs; embedding them inline would 5x the file and merge-conflict
   with every future wave.
2. **Lazy imports** — handlers depend on staged-A2/L2/L3/P2/P5 lib modules.
   If a staged dir hasn't been rsync'd, the wire-up returns 503 (not crash
   on require). Inline imports would prevent the API from booting.
3. **Single test surface** — `wire-up.test.ts` covers all 14 endpoints
   without booting the full server.

## Validation post-patch

```bash
# Sanity: file still parses
node --check /root/.openclaw/workspace/tools/nox-mem/dist/api-server.js

# Live health (unchanged behaviour for existing endpoints)
curl -sf http://127.0.0.1:18802/api/health | jq .chunks.total

# New endpoint smoke tests
curl -sf -X POST http://127.0.0.1:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"smoke"}' | jq .trace_id
# Expect 200 (or 503 with reason if lib/answer not built)

curl -sf http://127.0.0.1:18802/api/conflict | jq .count
# Expect 200 { count: N, rows: [...] } if L2 db deployed
# Expect 503 { error: "not_implemented" } otherwise

curl -sf http://127.0.0.1:18802/viewer | head -c 200
# Expect 200 text/html OR 404 if staged-P5 viewer/ not on disk
```

## Rollback

Revert this PR (`git revert`), restart `nox-mem-api`:

```bash
systemctl restart nox-mem-api
```

Wave A→K endpoints go back to 404 (same as pre-deploy). All existing
endpoints unaffected.
