/**
 * src/lib/viewer/broadcast-singleton.ts — Wave O T3 (part 1).
 *
 * Wire-up.ts (#92, line 312) calls `brMod.getBroadcaster()` SYNCHRONOUSLY.
 * The lazy `await import("../lib/viewer/broadcast.js")` at the route entry
 * resolves the module; after that, `getBroadcaster()` must return the
 * instance immediately.
 *
 * Implementation:
 *   - Top-level await resolves the staged-P5 `Broadcaster` ctor at module
 *     load. Once `import("../lib/viewer/broadcast.js")` finishes in wire-up,
 *     this file (re-exported from `broadcast.js`) is already initialized.
 *   - `getBroadcaster()` is sync — returns the cached instance.
 *   - When the ctor isn't loadable (staged-P5 not deployed), the wire-up's
 *     `if (!brMod || typeof brMod.getBroadcaster !== "function")` branch
 *     handles 503 directly because we throw at module load → outer
 *     `tryImport` swallows → null module → 503 path.
 *
 * After rsync, `broadcast.ts` (staged-P5) gets ONE appended line:
 *
 *   export { getBroadcaster, resetBroadcasterForTests } from "./broadcast-singleton.js";
 *
 * This keeps the wire-up's lazy-import semantics intact.
 */

// Top-level await — ESM allows this. Throws if the file is missing, which
// propagates up to wire-up's `tryImport` (caught, mapped to 503).
// String indirection — `./broadcast.js` is co-located only after staged-P5
// is rsynced. TypeScript can't resolve at compile time; that's intentional.
const BROADCAST_SPEC = "./broadcast.js";
const _mod: any = await import(BROADCAST_SPEC);
const _Broadcaster = _mod.Broadcaster ?? _mod.default?.Broadcaster;
if (typeof _Broadcaster !== "function") {
  throw new Error("broadcast-singleton: Broadcaster class missing from ./broadcast.js");
}

let _instance: any = null;

/**
 * Sync accessor — returns the singleton Broadcaster. Creates on first call.
 * Wire-up.ts calls this without await; do not change the signature.
 */
export function getBroadcaster(opts?: {
  ringCapacity?: number;
  clientCapacity?: number;
}): any {
  if (_instance) return _instance;
  _instance = new _Broadcaster(opts);
  return _instance;
}

/** Drop the singleton — test-only. */
export function resetBroadcasterForTests(): void {
  _instance = null;
}
