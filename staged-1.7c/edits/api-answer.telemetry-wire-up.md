# Wire-up patch — F10 Phase C Phase 2: /api/answer telemetry hook

**Target file on VPS:** `src/api/wire-up.ts`  
**Prerequisite:** F10 Phase C Phase 1 deployed (telemetry-collector.js live)  
**PR:** feat/f10-phase-c-phase2-answer-wireup  

**Context:** The `/api/answer` handler lives in `src/api/wire-up.ts` (not `api-server.ts`).  
PR #274 deploy audit flagged CHANGE 3 (answer hook in `api-server.ts`) as N/A because the  
handler was already refactored to `wire-up.ts`. This patch closes that gap surgically.

---

## CHANGE 1 — Add lazy telemetry import block

**FIND** (the existing Node.js import at the top of `src/api/wire-up.ts`):

```ts
import { IncomingMessage, ServerResponse } from "node:http";
```

**ADD IMMEDIATELY AFTER** (paste the full block below):

```ts
// ─── F10 Phase C Phase 2: telemetry-collector hook ───────────────────────────
// Lazy import — falls back silently if telemetry-collector is not yet deployed.
// recordRequest is fire-and-forget synchronous; zero async overhead.
let _recordRequest:
  | ((
      path: "search" | "answer",
      startMs: number,
      endMs: number,
      resultCount: number,
      pathUsed: string,
      semanticUsed: boolean,
      statusCode?: number,
    ) => void)
  | null
  | undefined = undefined; // undefined = not yet resolved; null = not available

async function getRecordRequest(): Promise<typeof _recordRequest> {
  if (_recordRequest !== undefined) return _recordRequest;
  try {
    const mod: any = await import("../lib/telemetry-collector.js");
    _recordRequest = mod.recordRequest ?? null;
  } catch {
    _recordRequest = null; // telemetry-collector not deployed — degrade gracefully
  }
  return _recordRequest;
}
```

---

## CHANGE 2 — Wrap /api/answer handler with timing + recordRequest call

**FIND** the existing `POST /api/answer` block (currently ~10 lines):

```ts
  // ── P1: POST /api/answer ────────────────────────────────────────────────
  if (method === "POST" && path === "/api/answer") {
    await safeHandle(req, res, async () => {
      const body = await readJsonBody(req);
      const mod: any = await import("./answer.js");
      const out = await mod.handleAnswerRequest({
        body,
        headers: req.headers,
      });
      writeJson(res, out.body, out.status, out.headers ?? {});
    });
    return true;
  }
```

**REPLACE WITH:**

```ts
  // ── P1: POST /api/answer ────────────────────────────────────────────────
  // F10 Phase C Phase 2: wrapped with telemetry timing.
  if (method === "POST" && path === "/api/answer") {
    await safeHandle(req, res, async () => {
      const _t0 = Date.now();
      const body = await readJsonBody(req);
      const mod: any = await import("./answer.js");
      const out = await mod.handleAnswerRequest({
        body,
        headers: req.headers,
      });
      const _t1 = Date.now();
      // Fire-and-forget telemetry — non-blocking, degrades gracefully if not deployed.
      // /api/answer always runs the full semantic pipeline (Gemini embed + LLM synthesis).
      // result_count = 1: one synthesized answer per call (not a ranked list).
      const rec = await getRecordRequest();
      rec?.("answer", _t0, _t1, 1, "answer-pipeline", true, out.status);
      writeJson(res, out.body, out.status, out.headers ?? {});
    });
    return true;
  }
```

---

## Notes

- `_t0` captured **before** `readJsonBody` — measures full request latency including body parse.
- `_t1` captured **after** `handleAnswerRequest` resolves — includes retrieval + LLM synthesis.
- `out.status` propagated as `statusCode` — telemetry will show 503 (retrieval_empty) vs 200.
- `path_used: "answer-pipeline"` is a fixed label (no sub-path variants for the answer route).
- `semantic_used: true` always — answer always runs Gemini embedding for retrieval.
- `getRecordRequest()` is memoized: first call does dynamic import, subsequent calls are synchronous.
- If telemetry-collector is not deployed (file missing), `_recordRequest` is set to `null` and the `?.()` no-ops silently. Zero risk of breaking answer path.

---

## Deploy sequence

```bash
# 1. SCP the patched wire-up.ts to VPS
scp staged-wire-up/edits/src/api/wire-up.ts root@187.77.234.79:/root/.openclaw/workspace/tools/nox-mem/src/api/wire-up.ts

# 2. Rebuild (if TypeScript compilation step exists on VPS)
# If VPS runs dist/ compiled: rebuild needed.
# If VPS runs ts-node or tsx: restart is enough.
ssh root@187.77.234.79 'cd /root/.openclaw/workspace/tools/nox-mem && npm run build 2>&1 | tail -5'

# 3. Restart service
ssh root@187.77.234.79 'systemctl restart nox-mem-api && sleep 2 && systemctl is-active nox-mem-api'

# 4. Smoke: trigger an answer call
curl -s -X POST http://127.0.0.1:18802/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"question":"test telemetry hook"}' | jq '.answer | .[0:60]'

# 5. Wait ~5s then check telemetry
curl -s 'http://127.0.0.1:18802/api/observability/telemetry?window=1h' | \
  jq '{count: .aggregate.count, by_path: .aggregate.by_path}'
# Expected: by_path.answer >= 1
```

---

## Rollback

Remove CHANGE 1 and revert CHANGE 2 to original. The telemetry module is in-memory only;  
process restart resets all data. No DB migration required. No data loss risk.

---

## Verification criteria

Post-deploy, within 1h of a `/api/answer` call:

```bash
curl -s 'http://127.0.0.1:18802/api/observability/telemetry?window=1h' | \
  jq '.aggregate.by_path.answer'
# Must return >= 1 (not 0 or null)
```

And the telemetry dashboard at `/observability/telemetry.html` should show answer-path  
entries in the by_path breakdown.
