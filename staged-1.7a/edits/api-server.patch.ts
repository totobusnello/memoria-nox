/**
 * staged-1.7a/edits/api-server.patch.ts
 *
 * PATCH: pre-existing tsc errors in src/api-server.ts (VPS)
 *
 * CONTEXT:
 *   The VPS api-server.ts was patched in 2026-04-23 to expose a `salience`
 *   block inside the /api/health handler (see MASTER-HANDOFF-2026-04-23.md §4).
 *   That patch imported from `./lib/salience.js` where:
 *     - SalienceMode was "shadow" | "active" (no "off")
 *     - computeSalience(chunk, nowMs, mode) accepted 3 args (mode was gating-arg)
 *
 *   Wave A deployed `staged-1.7a/edits/salience.ts` as `src/salience.ts` on the
 *   VPS. The new module has:
 *     - SalienceMode = "shadow" | "active" | "off"       ← "off" added
 *     - computeSalience(chunk, nowMs?)                   ← mode arg removed
 *       (mode gating moved to salienceDelta() in search.ts)
 *
 *   This created TWO pre-existing tsc errors in the VPS api-server.ts:
 *     Line ~221: narrow `if (mode === "off")` → TS2367 "off" not in old union
 *     Line ~305: `computeSalience(chunk, nowMs, mode)` → TS2554 3 args, expects 2
 *
 * APPLIES ON TOP OF:
 *   VPS src/api-server.ts (post-Wave-A-deploy state)
 *   Reference baseline: staged-1.6/edits/api-server.ts (lines 1–311)
 *
 * HOW TO APPLY (on VPS):
 *   Manual FIND/REPLACE — two surgical changes. No behavior change.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * CHANGE 1 — Fix import: use new src/salience.ts (not src/lib/salience.ts)
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * FIND (near top of file, after other imports):
 *
 *   import { getSalienceMode, computeSalience, classifySalience, type SalienceMode } from "./lib/salience.js";
 *
 * REPLACE WITH:
 *
 *   import { getSalienceMode, computeSalience, classifySalience, type SalienceMode } from "./salience.js";
 *
 * NOTE: the new salience.ts exports all four names used here. The only diff is
 * the path: `./salience.js` (Wave A drop-in) instead of `./lib/salience.js`
 * (old module). SalienceMode in the new module is "shadow" | "active" | "off"
 * which fixes the TS2367 at line ~221.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * CHANGE 2 — Fix call site: remove mode as 3rd arg to computeSalience
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * The old lib/salience.ts had:
 *   computeSalience(chunk: SalienceInput, nowMs: number, mode: SalienceMode): number
 *
 * The new salience.ts (alias of calculateSalience) has:
 *   computeSalience(chunk: SalienceInput, nowMs?: number): number
 * Mode gating is the caller's responsibility (done in search.ts salienceDelta).
 * api-server.ts only calls computeSalience for /api/health observability — it
 * should pass the score through regardless of mode and let classifySalience
 * categorize it for the health payload. Remove the mode arg.
 *
 * FIND (inside the /api/health salience block, line ~305):
 *
 *   const score = computeSalience(row, Date.now(), mode);
 *
 * REPLACE WITH:
 *
 *   const score = computeSalience(row, Date.now());
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * VERIFICATION (on VPS, after applying both changes)
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * cd /root/.openclaw/workspace/tools/nox-mem
 * npx tsc -p tsconfig.json --noEmit 2>&1 | grep "api-server"
 * # Expected: zero lines (no errors on api-server.ts lines)
 *
 * # Full build + smoke:
 * npm run build && systemctl restart nox-mem-api && sleep 2
 * curl -s http://127.0.0.1:18802/api/health | jq '.salience.mode'
 * # Expected: "active" (or "shadow" if NOX_SALIENCE_MODE not set to active)
 */

// ─── Annotated snippets for apply reference ───────────────────────────────────
//
// The two lines that change (exact text may vary slightly by VPS patch history;
// match by context if line numbers have drifted):

// BEFORE (line ~1, import block):
// import { getSalienceMode, computeSalience, classifySalience, type SalienceMode } from "./lib/salience.js";

// AFTER:
// import { getSalienceMode, computeSalience, classifySalience, type SalienceMode } from "./salience.js";

// ─────────────────────────────────────────────────────────────────────────────

// BEFORE (line ~305, inside /api/health case):
// const score = computeSalience(row, Date.now(), mode);

// AFTER:
// const score = computeSalience(row, Date.now());
