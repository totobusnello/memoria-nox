/**
 * staged-1.7a/edits/ingest-entity.patch.ts
 *
 * audit #20 fix — Adds `checkLargeDbIngestGuard()` to `ingestEntityFile()` in
 * src/ingest-entity.ts (VPS canonical path:
 * /root/.openclaw/workspace/tools/nox-mem/src/ingest-entity.ts).
 *
 * This is a **patch reference** — apply the diff below to the existing
 * ingest-entity.ts. Full deploy steps in DEPLOY-AUDIT20-FIXES.md.
 *
 * ─── PATCH (apply to existing ingest-entity.ts) ───────────────────────────
 *
 * BEFORE (at top of `ingestEntityFile()`, before the INSERT loop):
 *
 *   export async function ingestEntityFile(
 *     filePath: string,
 *     externalDb?: Database,
 *   ): Promise<{ chunks: number }> {
 *     const db = externalDb ?? getDb();
 *     // ... existing parse logic
 *     // INSERT loop runs here
 *   }
 *
 * AFTER:
 *
 *   import { getDb, checkLargeDbIngestGuard } from "./db.js";
 *   // ...
 *   export async function ingestEntityFile(
 *     filePath: string,
 *     externalDb?: Database,
 *   ): Promise<{ chunks: number }> {
 *     const db = externalDb ?? getDb();
 *     // audit #20 fix — Large-DB ingest guard (defense-in-depth).
 *     // Abort if DB has >10k chunks and NOX_ALLOW_PROD_INGEST !== "1".
 *     // Even when called via ingestFile() router, the entity path now also
 *     // runs the guard. Override at caller-side (--allow-prod or env).
 *     checkLargeDbIngestGuard(db, "ingest-entity");
 *     // ... existing parse logic
 *     // INSERT loop runs here
 *   }
 *
 * ─── WHY ──────────────────────────────────────────────────────────────────
 *
 * Audit #20 found that `ingestEntityFile()` had no large-DB guard. The
 * `ingestFile()` router calls into `ingestEntityFile()` for entity files
 * (memory/entities/*.md); without this guard, a misrouted entity ingest into
 * prod (e.g., from a watcher misconfig or batch script) would silently
 * mutate prod even if the user expected to write to an eval DB.
 *
 * The check is **idempotent and cheap** (COUNT(*) FROM chunks, ~1ms even on
 * 70k chunks given the index). Adding it at the head of `ingestEntityFile`
 * means *every* entity ingest path runs through the guard:
 *
 *   1. nox-mem ingest-entity <file>          — direct CLI
 *   2. nox-mem ingest <file>                 — generic ingest → router → entity
 *   3. nox-mem watch                         — watcher → router → entity
 *   4. nox-mem reindex                       — reindex → router → entity
 *   5. graphify-ingest                       — separate flow (guarded too)
 *
 * The override is the same `NOX_ALLOW_PROD_INGEST=1` env or `--allow-prod`
 * flag at the top-level CLI command (already wired in PR #145).
 *
 * ─── TEST ─────────────────────────────────────────────────────────────────
 *
 * staged-1.7a/tests/audit20-ingest-entity-guard.test.ts asserts:
 *   - DB with >10k chunks + no override → process.exit(1) with abort message
 *   - DB with >10k chunks + NOX_ALLOW_PROD_INGEST=1 → passes guard
 *   - DB with <10k chunks → passes guard (no-op)
 */

export {};
