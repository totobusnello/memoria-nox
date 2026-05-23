# Wire-up patch — F10 Phase C Phase 1 telemetry endpoint

**APPLIES ON TOP OF:** VPS `src/api-server.ts` (post-Phase A + Phase B deploy state)
**ADDS:**
  - Import `recordRequest` + `handleObsTelemetry` from `./lib/telemetry-collector.js`
  - Hook in `/api/search` and `/api/answer` handlers to capture latency + result_count
  - New endpoint `GET /api/observability/telemetry?window=24h&bucket=1h`
  - Static serving for `public/observability/telemetry.{html,js,css}`

Pattern: surgical manual FIND/REPLACE. No behavior change to existing endpoints.

---

## CHANGE 1 — Add import

**FIND** (after existing observability import added in Phase A):

```ts
import {
  handleObsHealth,
  handleObsRecentOps,
  handleObsCanaryTail,
} from "./observability.js";
```

**ADD BELOW:**

```ts
import {
  recordRequest,
  handleObsTelemetry,
} from "./lib/telemetry-collector.js";
```

---

## CHANGE 2 — Hook /api/search handler

**FIND** the existing `/api/search` case. It looks roughly like:

```ts
case "/api/search": {
  const params = parseQuery(url);
  // ... build query ...
  const results = search(db, query, ...);
  json(res, { results });
  break;
}
```

**WRAP with timing:**

```ts
case "/api/search": {
  const _t0 = Date.now();
  const params = parseQuery(url);
  // ... existing logic unchanged ...
  const results = search(db, query, ...);
  const _pathUsed = results.meta?.path_used ?? "unknown";
  const _semantic = results.meta?.semantic_used === true;
  recordRequest("search", _t0, Date.now(), results.results?.length ?? 0, _pathUsed, _semantic);
  json(res, { results });
  break;
}
```

**Notes:**
- `results.meta` shape depends on VPS search.ts version. Use optional chaining.
- If search.ts does not expose `path_used`/`semantic_used`, use `"hybrid"` / `true` as safe defaults.
- The `recordRequest` call is fire-and-forget synchronous — zero async overhead.

---

## CHANGE 3 — Hook /api/answer handler

**FIND** the existing `/api/answer` case.

**WRAP with timing:**

```ts
case "/api/answer": {
  const _t0 = Date.now();
  // ... existing logic unchanged ...
  const answer = await computeAnswer(db, question, ...);
  recordRequest("answer", _t0, Date.now(), 1, "answer-pipeline", true);
  json(res, { answer });
  break;
}
```

**Notes:**
- `/api/answer` always uses semantic (Gemini embed) → `semantic_used: true`.
- `result_count: 1` is correct (one synthesized answer per call).

---

## CHANGE 4 — Add telemetry endpoint case

**FIND** the three Phase A observability cases and ADD AFTER:

```ts
      case "/api/observability/telemetry": {
        const params = parseQuery(url);
        json(res, handleObsTelemetry(params));
        break;
      }
```

---

## CHANGE 5 — Static serving for telemetry dashboard

**FIND** the Phase A static serving block:

```ts
case "/observability/health.html":
case "/observability/health.js":
case "/observability/health.css": {
```

**ADD three more cases above or below:**

```ts
case "/observability/telemetry.html":
case "/observability/telemetry.js":
case "/observability/telemetry.css": {
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

## CHANGE 6 — Update 404 endpoint list (cosmetic)

Append to the `endpoints` array in the `default:` 404 branch:

```ts
"/api/observability/telemetry",
"/observability/telemetry.html",
```

---

## Verification on VPS (post-apply)

```bash
# 1. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 2 && systemctl is-active nox-mem-api'

# 2. Smoke test telemetry endpoint (initially empty)
curl -s 'http://127.0.0.1:18802/api/observability/telemetry?window=24h' | jq '.aggregate'

# 3. Run a search to generate telemetry
curl -s 'http://127.0.0.1:18802/api/search?q=test+query' | jq '.results | length'

# 4. Confirm telemetry captured
curl -s 'http://127.0.0.1:18802/api/observability/telemetry?window=1h' | jq '.aggregate.count'
# Expected: 1 (or more if other searches happened)

# 5. Open dashboard
# http://nox-vps.tailnet:18802/observability/telemetry.html
```

---

## Rollback

Remove the 6 changes above. The telemetry module keeps data in memory — process restart resets all collected data. No DB migration required. No data loss risk.
