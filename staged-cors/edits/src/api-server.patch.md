# Patch: src/api-server.ts — CORS support for P7 browser extension

> **Applies on top of:** prod `src/api-server.ts` (baseline: `staged-1.6/edits/api-server.ts` lines 1–312).
> **Depends on:** `staged-cors/edits/src/api/cors.ts` deployed to `src/api/cors.ts` on VPS.
> **Purpose:** Unblocks P7 browser extension (#96) — Chrome/Firefox extensions can now call
> `http://127.0.0.1:18802` without CORS rejection from the browser.

---

## Change 1 — import statement

Add near the top of `src/api-server.ts`, alongside existing imports:

```diff
+ import { applyCorsHeaders, handlePreflight } from "./api/cors.js";
```

Suggested placement: after the last existing `import` line, before `const PORT = …`.

---

## Change 2 — top of handleRequest() body

Inside the `handleRequest(req, res)` function, add **two lines** at the very start
of the function body, **before any routing** (`switch`, `if`, URL parsing, etc.):

```diff
  async function handleRequest(req: IncomingMessage, res: ServerResponse) {
+   if (handlePreflight(req, res)) return;   // OPTIONS preflight → 204, short-circuit
+   applyCorsHeaders(req, res);               // all other methods: set CORS headers if origin matches
    // ... existing URL parsing + switch/case routing ...
  }
```

**Why before routing:**
- `OPTIONS` preflight MUST return 204 immediately (browsers block if it takes too long)
- CORS headers must be present on error responses too (4xx/5xx), so they go on the
  response object before any route handler can call `res.writeHead()` for the first time

---

## Diff summary

Total change to `src/api-server.ts`: **3 lines** (1 import + 2 in handleRequest body).

```diff
  // === existing imports ===
  import { createServer, IncomingMessage, ServerResponse } from "node:http";
  // ... other imports ...
+ import { applyCorsHeaders, handlePreflight } from "./api/cors.js";

  // === inside handleRequest ===
  async function handleRequest(req: IncomingMessage, res: ServerResponse) {
+   if (handlePreflight(req, res)) return;
+   applyCorsHeaders(req, res);
    const url = new URL(req.url ?? "/", `http://localhost`);
    // ...
  }
```

---

## Deploy steps

### Step 1 — Copy cors.ts to VPS

```bash
rsync -av staged-cors/edits/src/api/cors.ts \
  root@<VPS_IP>:/root/.openclaw/workspace/tools/nox-mem/src/api/cors.ts
```

### Step 2 — Apply the 3-line patch to api-server.ts

SSH into VPS and edit `src/api-server.ts` manually or via heredoc:

```bash
# Verify baseline — find the handleRequest function start
grep -n "async function handleRequest" \
  /root/.openclaw/workspace/tools/nox-mem/src/api-server.ts
```

Add the import and the two lines as shown above.

### Step 3 — Build

```bash
cd /root/.openclaw/workspace/tools/nox-mem
set -a; source /root/.openclaw/.env; set +a
npm run build 2>&1 | tail -5
```

Build should complete with no TypeScript errors.

### Step 4 — Restart API

```bash
systemctl restart nox-mem-api
sleep 3
systemctl status nox-mem-api --no-pager | head -10
```

### Step 5 — Smoke test (from extension popup or curl)

```bash
# Test preflight from a chrome-extension origin
curl -si -X OPTIONS http://127.0.0.1:18802/api/health \
  -H "Origin: chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef" \
  -H "Access-Control-Request-Method: GET" | head -15
```

Expected response:

```
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef
Vary: Origin
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
Access-Control-Max-Age: 86400
```

```bash
# Test actual GET request
curl -si http://127.0.0.1:18802/api/health \
  -H "Origin: chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef" | head -15
```

Expected: `HTTP/1.1 200 OK` + `Access-Control-Allow-Origin: chrome-extension://...`.

```bash
# Verify unknown origin is blocked
curl -si http://127.0.0.1:18802/api/health \
  -H "Origin: https://evil.com" | grep -i "access-control"
```

Expected: no `Access-Control-Allow-Origin` header.

### Step 6 — Extension integration test

1. Load the extension unpacked at `chrome://extensions` (`dist/chrome/`)
2. Open popup → click any search or save action
3. Check browser DevTools → Network tab: request to `127.0.0.1:18802` must show `200 OK`
   with `Access-Control-Allow-Origin: chrome-extension://<your-id>`
4. No CORS error in Console

---

## Rollback

If the patch causes a regression:

```bash
# Revert the 3-line edit to api-server.ts (restore original)
cd /root/.openclaw/workspace/tools/nox-mem
git diff src/api-server.ts   # review
git checkout src/api-server.ts   # revert
npm run build
systemctl restart nox-mem-api
```

The `cors.ts` file can remain on disk — it's only active when imported.

---

## Notes

- **No `Access-Control-Allow-Origin: *`** — header echoes matched origin only.
  This is required because browsers refuse `Allow-Credentials: true` when origin is `*`.
- **Vary: Origin** is mandatory alongside the echo-origin pattern to prevent CDN/proxy
  cache serving one user's response to another origin.
- Extra origins can be added without code changes via `NOX_CORS_EXTRA_ORIGINS` env var.
  See `staged-cors/edits/docs/CORS.md` for full documentation.
