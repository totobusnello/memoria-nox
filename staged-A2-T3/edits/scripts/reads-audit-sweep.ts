#!/usr/bin/env node
// staged-A2-T3/edits/scripts/reads-audit-sweep.ts
//
// A2 Tier 3 / Phase 3 — retention sweeper for reads_audit table.
//
// Decisions:
//   D58 (D-A2T3-5) — env-driven retention default 90d, archive (NOT delete).
//
// Behavior:
//   1. Resolves cutoff = now - retention_days * 86_400_000 ms.
//   2. Opens (or creates) archive DB at --archive-path (default:
//      ${dirname(NOX_DB_PATH)}/nox-mem-audit-archive.db). Same SQLCipher key
//      flows transparently — both DBs are opened with PRAGMA key from
//      NOX_DB_KEY if set.
//   3. Atomic move: in a SINGLE transaction on the main DB —
//        ATTACH '<archive>' AS archive KEY '<key>';
//        BEGIN IMMEDIATE;
//        INSERT INTO archive.reads_audit (...) SELECT ... FROM main.reads_audit WHERE ts < cutoff;
//        -- DELETE from main is BLOCKED by trg_reads_audit_no_delete.
//      The append-only invariant on main is preserved. The archive policy is
//      LOGICAL: rows are duplicated into the archive (idempotent via UNIQUE),
//      not removed from main. Operators who want true purge must do so on a
//      separate archive file (via PRAGMA writable_schema=ON ceremony) outside
//      this CLI.
//
// CAVEAT vs task brief §3:
//   Brief says "DELETE FROM reads_audit WHERE ts < cutoff" inside the txn.
//   That contradicts the append-only invariant (trg_reads_audit_no_delete →
//   RAISE(ABORT)) which is part of the security model (D55 + W2-1 lesson).
//   The implementation here honors the security model: rows are COPIED to
//   archive; main table never shrinks. This matches D58's exact language:
//   "main `reads_audit` table never deletes; archive mechanism is LOGICAL".
//   The CLI is still labeled "sweep" since it moves the *operational* working
//   set off the hot path — queries that JOIN both via the recon §6 UNION
//   pattern get the same logical result.
//
// Idempotent: re-running the sweep with the same cutoff is a no-op (INSERT OR
// IGNORE on the PRIMARY KEY id avoids duplicates in archive).
//
// Usage:
//   tsx edits/scripts/reads-audit-sweep.ts \
//     --retention-days 90 \
//     --archive-path /var/backups/nox-mem/audit-archive.db
//
//   # Cron weekly (recommended per D58):
//   # 0 3 * * 0  /usr/local/bin/node /path/to/reads-audit-sweep.js
//
// Env:
//   NOX_DB_KEY                            — cipher key (if encrypted DB)
//   NOX_READS_AUDIT_RETENTION_DAYS        — default 90
//   NOX_READS_AUDIT_ARCHIVE_PATH          — default sibling of NOX_DB_PATH
//   NOX_DB_PATH                           — main DB path (resolves like db.ts)

import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Database from 'better-sqlite3-multiple-ciphers';

interface SweepArgs {
  retentionDays: number;
  archivePath: string;
  dryRun: boolean;
}

const __dirname = dirname(fileURLToPath(import.meta.url));
// Schema SQL is loaded relative to the LIB folder (sibling location after build:
// dist/edits/scripts/reads-audit-sweep.js → ../../src/lib/reads-audit-schema.sql).
const SCHEMA_PATH = resolve(__dirname, '..', 'src', 'lib', 'reads-audit-schema.sql');

const DEFAULT_RETENTION = Number(process.env.NOX_READS_AUDIT_RETENTION_DAYS ?? '90');

function parseArgs(argv: string[]): SweepArgs {
  const args = argv.slice(2);
  let retentionDays = DEFAULT_RETENTION;
  let archivePath: string | undefined = process.env.NOX_READS_AUDIT_ARCHIVE_PATH;
  let dryRun = false;

  for (let i = 0; i < args.length; i++) {
    const a = args[i];
    if (a === '--retention-days') {
      const v = args[++i];
      if (!v) throw new Error('--retention-days requires a value');
      const n = Number(v);
      if (!Number.isFinite(n) || n <= 0 || !Number.isInteger(n)) {
        throw new Error(`--retention-days must be a positive integer, got '${v}'`);
      }
      retentionDays = n;
    } else if (a === '--archive-path') {
      const v = args[++i];
      if (!v) throw new Error('--archive-path requires a value');
      archivePath = v;
    } else if (a === '--dry-run') {
      dryRun = true;
    } else if (a === '--help' || a === '-h') {
      console.log(
        'Usage: reads-audit-sweep [--retention-days N] [--archive-path PATH] [--dry-run]\n' +
        '  --retention-days N     rows with ts < now-N*86400000ms are archived (default: 90,\n' +
        '                         or NOX_READS_AUDIT_RETENTION_DAYS env)\n' +
        '  --archive-path PATH    archive DB file (default: sibling of NOX_DB_PATH named\n' +
        '                         nox-mem-audit-archive.db, or NOX_READS_AUDIT_ARCHIVE_PATH env)\n' +
        '  --dry-run              report counts without writing\n',
      );
      process.exit(0);
    } else {
      throw new Error(`unknown arg '${a}'`);
    }
  }

  // Resolve archive path default: sibling of main DB.
  if (!archivePath) {
    const dbPath = process.env.NOX_DB_PATH;
    if (!dbPath) {
      throw new Error(
        '--archive-path not given AND NOX_DB_PATH unset AND NOX_READS_AUDIT_ARCHIVE_PATH unset. ' +
        'Provide one of them.',
      );
    }
    archivePath = resolve(dirname(dbPath), 'nox-mem-audit-archive.db');
  }
  return { retentionDays, archivePath: resolve(archivePath), dryRun };
}

function applyCipherPragmas(db: Database.Database, key: string): void {
  // Lock-step with src/lib/db.ts:applyCipherPragmas(). See P1 PR #280.
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const escapedKey = key.replace(/'/g, "''");
  db.pragma(`key='${escapedKey}'`, { simple: true });
}

function ensureArchiveSchema(db: Database.Database, attachAs: string): void {
  // Apply schema DDL to the attached archive DB. We CANNOT simply text-replace
  // "reads_audit" → "<alias>.reads_audit" in the main schema file because
  // SQLite's CREATE TRIGGER syntax differs: the schema qualifier goes on the
  // TRIGGER NAME, not the table name (i.e. CREATE TRIGGER archive.trg_foo ...
  // ON reads_audit; NOT CREATE TRIGGER trg_foo ... ON archive.reads_audit;).
  //
  // Easier + safer: inline the DDL here with explicit `<alias>.` qualification
  // on each schema object. Keep it lock-step with reads-audit-schema.sql —
  // any change there must be mirrored here. The lib-side schema file remains
  // the source-of-truth for the MAIN DB; this function handles the archive
  // attach-time bootstrap only.
  db.exec(`
    CREATE TABLE IF NOT EXISTS ${attachAs}.reads_audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts INTEGER NOT NULL,
      query TEXT,
      k INTEGER,
      n_results INTEGER,
      latency_ms INTEGER,
      user_id TEXT,
      source_app TEXT
    );
    CREATE INDEX IF NOT EXISTS ${attachAs}.idx_reads_audit_ts ON reads_audit(ts);
    CREATE INDEX IF NOT EXISTS ${attachAs}.idx_reads_audit_app_ts ON reads_audit(source_app, ts DESC);
    CREATE TRIGGER IF NOT EXISTS ${attachAs}.trg_reads_audit_no_delete
      BEFORE DELETE ON reads_audit
      BEGIN SELECT RAISE(ABORT, 'archive reads_audit append-only'); END;
    CREATE TRIGGER IF NOT EXISTS ${attachAs}.trg_reads_audit_no_update
      BEFORE UPDATE ON reads_audit
      BEGIN SELECT RAISE(ABORT, 'archive reads_audit rows immutable'); END;
    CREATE TRIGGER IF NOT EXISTS ${attachAs}.trg_reads_audit_ts_must_be_int
      BEFORE INSERT ON reads_audit
      FOR EACH ROW WHEN NEW.ts IS NOT NULL AND typeof(NEW.ts) != 'integer'
      BEGIN SELECT RAISE(ABORT, 'archive reads_audit.ts must be INTEGER epoch ms'); END;
  `);
}

function main(): void {
  const args = parseArgs(process.argv);

  const dbPath = process.env.NOX_DB_PATH;
  if (!dbPath) {
    throw new Error('NOX_DB_PATH env var is required for sweep');
  }
  if (!existsSync(dbPath)) {
    throw new Error(`main DB not found at ${dbPath}`);
  }

  const key = process.env.NOX_DB_KEY;
  const cutoff = Date.now() - args.retentionDays * 86_400_000;

  console.log(
    `[reads-audit-sweep] retention=${args.retentionDays}d cutoff=${cutoff} (` +
    new Date(cutoff).toISOString() +
    `) archive=${args.archivePath} dryRun=${args.dryRun}`,
  );

  const main = new Database(dbPath);
  if (key && key.length > 0) applyCipherPragmas(main, key);
  main.defaultSafeIntegers(true);

  // Ensure reads_audit table exists on main (no-op if previously bootstrapped).
  const schemaSql = readFileSync(SCHEMA_PATH, 'utf8');
  main.exec(schemaSql);

  // Count first (sanity + dry-run path).
  const cntRow = main
    .prepare('SELECT COUNT(*) AS c FROM reads_audit WHERE ts < ?')
    .get(cutoff) as { c: bigint };
  const eligibleCount = Number(cntRow.c);
  console.log(`[reads-audit-sweep] eligible rows for archive: ${eligibleCount}`);

  if (eligibleCount === 0) {
    console.log('[reads-audit-sweep] nothing to archive — exiting clean');
    main.close();
    return;
  }
  if (args.dryRun) {
    console.log(`[reads-audit-sweep] DRY RUN — would archive ${eligibleCount} rows to ${args.archivePath}`);
    main.close();
    return;
  }

  // ATTACH archive DB. If file doesn't exist, sqlite3mc creates it on attach.
  // KEY clause needed only when encrypted (otherwise omit to allow plaintext
  // archive — same posture as the main DB).
  if (key && key.length > 0) {
    const escapedKey = key.replace(/'/g, "''");
    const escapedPath = args.archivePath.replace(/'/g, "''");
    main.exec(`ATTACH DATABASE '${escapedPath}' AS archive KEY '${escapedKey}'`);
  } else {
    const escapedPath = args.archivePath.replace(/'/g, "''");
    main.exec(`ATTACH DATABASE '${escapedPath}' AS archive`);
  }

  try {
    // Apply DDL to archive (idempotent).
    ensureArchiveSchema(main, 'archive');

    // Atomic copy. INSERT OR IGNORE on PRIMARY KEY id makes re-runs safe.
    // We do NOT DELETE from main — append-only trigger enforces that, and
    // D58 explicitly chose "main never deletes; archive is logical UNION".
    const txn = main.transaction(() => {
      const insertResult = main
        .prepare(
          'INSERT OR IGNORE INTO archive.reads_audit ' +
          '(id, ts, query, k, n_results, latency_ms, user_id, source_app) ' +
          'SELECT id, ts, query, k, n_results, latency_ms, user_id, source_app ' +
          'FROM reads_audit WHERE ts < ?',
        )
        .run(cutoff);
      return insertResult.changes;
    });
    const copied = txn();
    console.log(`[reads-audit-sweep] archived ${copied} rows to ${args.archivePath}`);
    console.log(
      '[reads-audit-sweep] NOTE: main.reads_audit retains rows (append-only invariant). ' +
      'For queries spanning archive, UNION main and archive on ts < cutoff. ' +
      'See docs/A2-TIER3-READS-AUDIT-GUIDE.md §Query-across-archive.',
    );
  } finally {
    try { main.exec('DETACH DATABASE archive'); } catch { /* best-effort */ }
    main.close();
  }
}

// Entry-point guard — only run when executed directly (not when imported by
// tests). The classic ESM idiom for "if __name__ == '__main__'".
const isMain = (() => {
  try {
    return import.meta.url === `file://${process.argv[1]}` || import.meta.url.endsWith(process.argv[1] ?? '');
  } catch { return false; }
})();

if (isMain) {
  try {
    main();
  } catch (err) {
    console.error(`[reads-audit-sweep] FAILED: ${(err as Error).message}`);
    process.exit(1);
  }
}

// Export for testing
export { main as runSweep, parseArgs };
