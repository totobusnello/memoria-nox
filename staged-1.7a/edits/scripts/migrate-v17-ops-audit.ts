/**
 * Schema migration v.17 — ops_audit visibility columns.
 *
 * Wrapper standalone para aplicar migration v.17 com snapshot atômico pré-op
 * via withOpAudit, antes de restart da nox-mem-api (que aplicaria a mesma
 * migration via ensureSchema no boot, mas sem snapshot do main DB de 1.2GB).
 *
 * Pattern: withOpAudit('schema-v17-migration', ...) → VACUUM INTO atômico do
 * main DB → aplica ALTER TABLE → ops_audit row registrada com status='success'.
 *
 * Fase 2 / Gap C-migration (2026-05-15) — plans/2026-05-15-op-audit-gaps-review.md §10.6
 *
 * Uso na VPS:
 *   cd /root/.openclaw/workspace/tools/nox-mem
 *   node dist/scripts/migrate-v17-ops-audit.js
 *
 * Issue #3B (2026-05-21): db_source is now explicit — 'main' (prod nox-mem.db).
 * NOX_DB_SOURCE env no longer needed for this script; db_source is hardcoded 'main'.
 */

import { withOpAudit } from "../lib/op-audit.js";
import { getDb } from "../db.js";

async function main(): Promise<void> {
  console.log("[migrate-v17] starting schema v.17 migration with pre-op snapshot");

  const result = await withOpAudit("schema-v17-migration", { db_source: 'main' }, async () => {
    const db = getDb();
    const before = db
      .prepare("SELECT value FROM meta WHERE key = 'schema_version'")
      .get() as { value: string } | undefined;
    console.log(`[migrate-v17] schema_version before: ${before?.value ?? "unset"}`);

    // Idempotent ALTER TABLE — duplicate column é OK (re-run safe)
    const statements = [
      "ALTER TABLE ops_audit ADD COLUMN db_source TEXT DEFAULT 'unknown'",
      "ALTER TABLE ops_audit ADD COLUMN db_path TEXT DEFAULT 'unknown'",
      "ALTER TABLE ops_audit ADD COLUMN last_heartbeat_at TEXT",
    ];

    let appliedCount = 0;
    for (const stmt of statements) {
      try {
        db.exec(stmt);
        appliedCount++;
        console.log(`[migrate-v17] applied: ${stmt}`);
      } catch (err: any) {
        const msg = String(err?.message ?? err);
        if (msg.includes("duplicate column")) {
          console.log(`[migrate-v17] skipped (already applied): ${stmt}`);
        } else {
          throw err;
        }
      }
    }

    // Update meta + PRAGMA
    db.prepare(
      "INSERT OR REPLACE INTO meta (key, value, updated_at) VALUES ('schema_version', ?, datetime('now'))",
    ).run("17");
    db.exec("PRAGMA user_version = 17;");

    const after = db
      .prepare("SELECT value FROM meta WHERE key = 'schema_version'")
      .get() as { value: string };
    const pragma = (db.prepare("PRAGMA user_version").get() as {
      user_version: number;
    }).user_version;

    console.log(`[migrate-v17] schema_version after: ${after.value}`);
    console.log(`[migrate-v17] PRAGMA user_version: ${pragma}`);

    return {
      affected_rows: appliedCount,
      notes: `v.17 migration: ${appliedCount}/3 cols added (rest already present); meta=${after.value}, PRAGMA=${pragma}`,
    };
  });

  console.log("[migrate-v17] migration complete");
  console.log("[migrate-v17] result:", JSON.stringify(result, null, 2));
}

main().catch((err) => {
  console.error("[migrate-v17] FAILED:", err);
  process.exit(1);
});
