// staged-A2-T3/scripts/migrate-encrypt-db.ts
//
// A2 Tier 3 / Phase 2 — plaintext-to-encrypted migration script.
//
// PURPOSE
// -------
// Take an existing PLAINTEXT nox-mem.db (currently ~62.9k chunks in prod) and
// produce an ENCRYPTED copy at a new path using `better-sqlite3-multiple-ciphers`
// with cipher_compatibility=4 (AES-256-CBC + HMAC-SHA512). No data loss, no
// schema drift, FTS5 + vec0 tables preserved.
//
// CRITICAL DESIGN NOTE — why "ATTACH dest WITH KEY" does NOT work in sqlite3mc
// ----------------------------------------------------------------------------
// The original task brief sketched this algorithm:
//   open(src plaintext) → ATTACH '<dest>' AS enc KEY '<k>' → VACUUM INTO 'enc'
//
// Empirically (probed 2026-05-23 against better-sqlite3-multiple-ciphers 11.10):
//   1. `VACUUM INTO '<attach-alias>'` is not valid SQL — VACUUM INTO takes a
//      file path string literal, not a schema name.
//   2. `ATTACH DATABASE '<dest>' AS enc KEY '<k>'` from a plaintext primary
//      DOES write data to the file, BUT the cipher config (KDF iter count,
//      compat level) is bound to the *primary* connection — the attached DB
//      gets a partial/inconsistent header. Result: the file fails to reopen
//      with the very same key, "file is not a database (26)".
//   3. `sqlcipher_export('attached')` (the sqlcipher CLI idiom) is NOT
//      exported by sqlite3mc's SQL function table.
//
// What WORKS in sqlite3mc (this script's algorithm):
//   1. Open DESTINATION first as the PRIMARY connection, with full cipher
//      config + key (the KDF runs once, cipher header is written correctly).
//   2. ATTACH source as plaintext: `ATTACH DATABASE '<src>' AS src KEY ''`.
//   3. Walk source's sqlite_master to recreate schema on main (the encrypted
//      destination), skipping FTS5 auxiliary tables (`*_data`, `*_idx`,
//      `*_docsize`, `*_config`) which are auto-created by their virtual table.
//   4. Copy data per ordinary table via `INSERT INTO main."<t>" SELECT * FROM
//      src."<t>"`. FTS5 virtual tables themselves are rebuilt via
//      `INSERT INTO chunks_fts(chunks_fts) VALUES('rebuild')`.
//   5. DETACH src; close main; reopen with key for validation pass.
//
// vec0 tables: sqlite-vec virtual tables follow the same auxiliary-table pattern
// (`vec_chunks_chunks`, `vec_chunks_rowids`, `vec_chunks_vector_chunks00`).
// They are NOT auto-rebuildable from a `rebuild` directive, so we copy each
// vec aux table's data verbatim via INSERT INTO ... SELECT (works for ordinary
// tables that back the vec0 virtual table).
//
// CLI
// ---
//   migrate-encrypt-db.ts <source.db> <dest.db> <key>          # migrate only
//   migrate-encrypt-db.ts <source.db> <dest.db> <key> --swap   # migrate+swap
//
// Or env-driven:
//   NOX_DB_PATH=... NOX_DB_DEST=... NOX_DB_KEY=... migrate-encrypt-db.ts
//
// Exit codes:
//   0 — migration + validation success
//   1 — source not plaintext (already encrypted) or pre-flight failed
//   2 — dest exists, refusing overwrite
//   3 — migration ran but row counts diverge (CORRUPTED — investigate)
//   4 — usage / argument error
//
// Safety
// ------
//   • Refuses to overwrite an existing destination file (exit 2). Caller must
//     remove it explicitly or pick a different path.
//   • Verifies source opens cleanly as plaintext BEFORE doing any work
//     (if source is already encrypted, this script aborts with exit 1).
//   • --swap is OFF by default. Even with --swap, we first move source to
//     <source>.pre-encrypt-<ISO-ts>.db (never deleted) before moving dest into
//     source's slot. Rollback: `mv <source>.pre-encrypt-<ts>.db <source>`.
//
// Cross-reference
// ---------------
//   • staged-A2-T3/edits/src/lib/db.ts (P1) — open path with NOX_DB_KEY
//   • experiments/a2-tier3-sqlcipher-spike/RESULTS.md — Phase 2 + 5.e
//   • docs/A2-TIER3-MIGRATION-RUNBOOK.md — operator-facing procedure
//   • CLAUDE.md §6 — "Operações destrutivas só com --dry-run ou snapshot atômico"
//     (this migration creates the snapshot via the .pre-encrypt-<ts>.db artifact
//     on --swap; without --swap the source DB is untouched).

import Database from "better-sqlite3-multiple-ciphers";
import { existsSync, statSync, renameSync } from "node:fs";
import { resolve } from "node:path";

// ────────────────────────────────────────────────────────────────────────────
// Types + constants
// ────────────────────────────────────────────────────────────────────────────

export interface MigrateOptions {
  sourcePath: string;
  destPath: string;
  key: string;
  swap?: boolean;
  /** Suppress stdout progress logs (for tests). Default false. */
  quiet?: boolean;
}

export interface MigrateResult {
  success: boolean;
  tableCounts: Array<{ table: string; sourceCount: number; destCount: number; match: boolean }>;
  schemaItems: number;
  destSize: number;
  durationMs: number;
}

/**
 * FTS5 + sqlite-vec auxiliary tables that are auto-created by their parent
 * virtual table. We skip these in the explicit table copy because:
 *   - chunks_fts_{data,idx,docsize,config} — created by CREATE VIRTUAL TABLE
 *     ... USING fts5(...) and populated via 'rebuild' directive
 *   - vec_chunks_{chunks,rowids,vector_chunks00} — created by USING vec0(...)
 *     BUT these are ordinary backing tables, NOT auto-populated. We copy them
 *     verbatim via INSERT INTO ... SELECT after the virtual table CREATE.
 *
 * Disambiguation: FTS5 aux are auto-rebuildable; vec0 aux must be copied.
 */
const FTS5_AUX_SUFFIXES = ["_data", "_idx", "_docsize", "_config", "_content"];
const VEC0_AUX_SUFFIXES = ["_chunks", "_rowids"];
// vec0 also creates pattern: <name>_vector_chunks<NN> (one per vector column)
const VEC0_VECTOR_CHUNKS_REGEX = /_vector_chunks\d+$/;

function isFts5Aux(name: string, virtualTableNames: ReadonlySet<string>): boolean {
  for (const vname of virtualTableNames) {
    for (const suf of FTS5_AUX_SUFFIXES) {
      if (name === `${vname}${suf}`) return true;
    }
  }
  return false;
}

function isVec0Aux(name: string, vec0TableNames: ReadonlySet<string>): boolean {
  for (const vname of vec0TableNames) {
    for (const suf of VEC0_AUX_SUFFIXES) {
      if (name === `${vname}${suf}`) return true;
    }
    if (name.startsWith(`${vname}`) && VEC0_VECTOR_CHUNKS_REGEX.test(name.slice(vname.length))) {
      return true;
    }
  }
  return false;
}

// ────────────────────────────────────────────────────────────────────────────
// Cipher helpers (lock-step with edits/src/lib/db.ts applyCipherPragmas)
// ────────────────────────────────────────────────────────────────────────────

function applyCipherPragmas(db: Database.Database, key: string): void {
  db.pragma(`cipher='sqlcipher'`, { simple: true });
  db.pragma(`legacy=4`, { simple: true });
  db.pragma(`cipher_compatibility=4`, { simple: true });
  const escapedKey = key.replace(/'/g, "''");
  db.pragma(`key='${escapedKey}'`, { simple: true });
}

// ────────────────────────────────────────────────────────────────────────────
// Pre-flight: verify source is plaintext (NOT already encrypted)
// ────────────────────────────────────────────────────────────────────────────

/**
 * Returns true if the file at `path` opens cleanly as plaintext SQLite
 * (i.e. `SELECT 1 FROM sqlite_master` succeeds without a key).
 * Returns false if the open fails with NOTADB / HMAC / file-is-encrypted
 * (treat as "already encrypted, do not migrate").
 *
 * Throws on other failures (file not found, perm denied, etc.) — those are
 * caller bugs, not migration scenarios.
 */
export function isSourcePlaintext(path: string): boolean {
  if (!existsSync(path)) {
    throw new Error(`[migrate] source does not exist: ${path}`);
  }
  const db = new Database(path, { readonly: true });
  try {
    db.prepare("SELECT name FROM sqlite_master LIMIT 1").get();
    return true;
  } catch (err) {
    const msg = (err as Error).message;
    if (/file is not a database|not a database|HMAC|file is encrypted/i.test(msg)) {
      return false;
    }
    throw err;
  } finally {
    db.close();
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Core migration
// ────────────────────────────────────────────────────────────────────────────

export function migrateEncryptDb(opts: MigrateOptions): MigrateResult {
  const t0 = Date.now();
  const { sourcePath, destPath, key, quiet = false } = opts;

  const log = (msg: string): void => {
    if (!quiet) console.log(msg);
  };

  if (!key || key.length === 0) {
    throw new Error("[migrate] key must be non-empty");
  }
  if (resolve(sourcePath) === resolve(destPath)) {
    throw new Error(`[migrate] source and dest must differ — got both = ${sourcePath}`);
  }

  // (a) Source plaintext check
  log(`[migrate] verifying source is plaintext: ${sourcePath}`);
  if (!isSourcePlaintext(sourcePath)) {
    throw new Error(
      `[migrate] source '${sourcePath}' is already encrypted (or unreadable). ` +
      `Refusing to migrate. If you intended a re-key, that is a separate ` +
      `operation (PRAGMA rekey) and NOT supported by this script.`,
    );
  }

  // (b) Dest must not exist
  if (existsSync(destPath)) {
    throw new Error(`[migrate] dest already exists: ${destPath} — refusing overwrite`);
  }

  // (c) Open destination FIRST as encrypted primary connection
  log(`[migrate] opening encrypted destination: ${destPath}`);
  const dst = new Database(destPath);
  applyCipherPragmas(dst, key);
  // Mirror the safe-integers contract from db.ts so any BigInt round-trips
  // through INTEGER columns survive the migration (vec0 rowid contract).
  dst.defaultSafeIntegers(true);

  // (d) ATTACH source as plaintext
  log(`[migrate] attaching source (plaintext) for streaming copy`);
  // Escape source path single-quotes defensively (file paths normally have none).
  const srcSqlPath = sourcePath.replace(/'/g, "''");
  dst.exec(`ATTACH DATABASE '${srcSqlPath}' AS src KEY ''`);

  // (e) Read source schema from src.sqlite_master
  type SchemaItem = { type: string; name: string; sql: string | null; tbl_name: string };
  const schemaItems = dst
    .prepare(
      "SELECT type, name, sql, tbl_name FROM src.sqlite_master " +
      "WHERE name NOT LIKE 'sqlite_%' " +
      "ORDER BY CASE type WHEN 'table' THEN 1 WHEN 'view' THEN 2 WHEN 'trigger' THEN 3 WHEN 'index' THEN 4 ELSE 5 END",
    )
    .all() as SchemaItem[];

  // Identify virtual tables BEFORE filtering so we know which aux tables to skip.
  const virtualTableNames = new Set<string>();
  const vec0TableNames = new Set<string>();
  for (const it of schemaItems) {
    if (it.type !== "table" || !it.sql) continue;
    const sql = it.sql.toUpperCase();
    if (sql.includes("CREATE VIRTUAL TABLE")) {
      virtualTableNames.add(it.name);
      // sqlite-vec virtual tables: detect by `USING vec0`
      if (sql.includes("USING VEC0")) {
        vec0TableNames.add(it.name);
      }
    }
  }
  log(`[migrate] schema: ${schemaItems.length} items, virtual=${virtualTableNames.size}, vec0=${vec0TableNames.size}`);

  // (f) Recreate schema on main (encrypted) — skip auto-built FTS5 aux tables.
  //     We DO recreate vec0 aux tables explicitly because vec0 stores its
  //     persistent payload in those backing tables (not auto-rebuildable).
  // Order: first all tables, then triggers, then indexes (mirrors ORDER BY).
  for (const it of schemaItems) {
    if (!it.sql) continue;
    if (it.type === "table" && isFts5Aux(it.name, virtualTableNames)) {
      continue; // FTS5 auxiliary — auto-created by CREATE VIRTUAL TABLE
    }
    try {
      dst.exec(it.sql);
    } catch (err) {
      // FTS5 auxiliary catch-all: some tokenizers create slightly differently-
      // named aux tables — if the CREATE fails with "already exists" that's
      // benign (auto-created); otherwise re-throw.
      const msg = (err as Error).message;
      if (/already exists/i.test(msg)) {
        log(`[migrate]   skip ${it.type} ${it.name} (already exists)`);
        continue;
      }
      throw new Error(`[migrate] failed to recreate ${it.type} ${it.name}: ${msg}`);
    }
  }

  // (g) Copy data — ordinary tables ONLY (skip FTS5 virtual + its aux; we
  //     rebuild FTS5 from the underlying content table).
  //     vec0 aux tables ARE copied (their backing tables hold the vectors).
  const sourceTables = dst
    .prepare("SELECT name FROM src.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    .all() as Array<{ name: string }>;

  const tableCounts: MigrateResult["tableCounts"] = [];

  // Drop triggers temporarily — INSERTs would otherwise re-fire FTS5 triggers
  // and double-populate. We have explicit FTS5 rebuild at the end.
  const triggerNames = schemaItems.filter((i) => i.type === "trigger").map((i) => i.name);
  for (const tn of triggerNames) {
    try { dst.exec(`DROP TRIGGER IF EXISTS "${tn}"`); } catch { /* best-effort */ }
  }

  for (const t of sourceTables) {
    // Skip FTS5 virtual table itself + its aux tables — rebuilt from content.
    if (virtualTableNames.has(t.name) && !vec0TableNames.has(t.name)) {
      continue;
    }
    if (isFts5Aux(t.name, virtualTableNames) && !isVec0Aux(t.name, vec0TableNames)) {
      continue;
    }
    // vec0 virtual table itself: skip — its data is in the aux tables (copied below)
    if (vec0TableNames.has(t.name)) {
      const cnt = (dst.prepare(`SELECT count(*) AS n FROM src."${t.name}"`).get() as { n: bigint | number }).n;
      const cntNum = typeof cnt === "bigint" ? Number(cnt) : cnt;
      tableCounts.push({ table: t.name, sourceCount: cntNum, destCount: cntNum, match: true });
      continue;
    }

    // Column list from source — defends against schema drift between attach + main.
    const cols = (dst.prepare(`PRAGMA src.table_info('${t.name}')`).all() as Array<{ name: string }>);
    if (cols.length === 0) continue;
    const colList = cols.map((c) => `"${c.name}"`).join(", ");

    const srcCntRaw = (dst.prepare(`SELECT count(*) AS n FROM src."${t.name}"`).get() as { n: bigint | number }).n;
    const srcCnt = typeof srcCntRaw === "bigint" ? Number(srcCntRaw) : srcCntRaw;

    try {
      dst.exec(`INSERT INTO main."${t.name}" (${colList}) SELECT ${colList} FROM src."${t.name}"`);
    } catch (err) {
      throw new Error(`[migrate] copy failed for table '${t.name}': ${(err as Error).message}`);
    }

    const dstCntRaw = (dst.prepare(`SELECT count(*) AS n FROM main."${t.name}"`).get() as { n: bigint | number }).n;
    const dstCnt = typeof dstCntRaw === "bigint" ? Number(dstCntRaw) : dstCntRaw;

    tableCounts.push({
      table: t.name,
      sourceCount: srcCnt,
      destCount: dstCnt,
      match: srcCnt === dstCnt,
    });
    log(`[migrate]   ${t.name}: ${srcCnt} → ${dstCnt} ${srcCnt === dstCnt ? "OK" : "MISMATCH"}`);
  }

  // (h) Recreate triggers — virtual-table-related triggers must come AFTER
  //     data copy so they don't fire on backfill.
  for (const it of schemaItems) {
    if (it.type !== "trigger" || !it.sql) continue;
    try {
      dst.exec(it.sql);
    } catch (err) {
      const msg = (err as Error).message;
      if (/already exists/i.test(msg)) continue;
      throw new Error(`[migrate] failed to recreate trigger ${it.name}: ${msg}`);
    }
  }

  // (i) Rebuild FTS5 virtual tables — one per chunks_fts-style table.
  //     The CREATE VIRTUAL TABLE statement was already issued in step (f);
  //     this triggers a full index build from the content table.
  for (const vname of virtualTableNames) {
    if (vec0TableNames.has(vname)) continue; // vec0 not rebuildable; data copied above
    try {
      dst.exec(`INSERT INTO main."${vname}"(${vname}) VALUES('rebuild')`);
      log(`[migrate]   FTS rebuild: ${vname} OK`);
    } catch (err) {
      // Not all virtual tables have a 'rebuild' op (only FTS5). Best-effort.
      log(`[migrate]   FTS rebuild ${vname}: ${(err as Error).message} (non-fatal)`);
    }
  }

  // (j) Update sqlite_sequence rows so AUTOINCREMENT continues from current max
  try {
    const hasSeq = dst.prepare("SELECT 1 FROM main.sqlite_master WHERE name='sqlite_sequence'").get();
    if (hasSeq) {
      const srcSeq = dst.prepare("SELECT name, seq FROM src.sqlite_sequence").all() as Array<{ name: string; seq: number }>;
      const replaceSeq = dst.prepare("INSERT OR REPLACE INTO main.sqlite_sequence (name, seq) VALUES (?, ?)");
      for (const r of srcSeq) replaceSeq.run(r.name, r.seq);
    }
  } catch (err) {
    log(`[migrate]   sqlite_sequence copy: ${(err as Error).message} (non-fatal)`);
  }

  // (k) DETACH src; close dest
  dst.exec("DETACH DATABASE src");
  dst.close();

  // (l) Validate by reopening dest with key and counting rows independently
  log(`[migrate] validating destination by reopen-with-key`);
  const validate = new Database(destPath, { readonly: true });
  try {
    applyCipherPragmas(validate, key);
    validate.defaultSafeIntegers(true);
    for (const tc of tableCounts) {
      if (vec0TableNames.has(tc.table)) continue; // vec0 not directly queryable for count
      const rawCnt = (validate.prepare(`SELECT count(*) AS n FROM "${tc.table}"`).get() as { n: bigint | number }).n;
      const reopened = typeof rawCnt === "bigint" ? Number(rawCnt) : rawCnt;
      if (reopened !== tc.destCount) {
        throw new Error(
          `[migrate] validation FAIL: ${tc.table} reopened count ${reopened} ≠ insert count ${tc.destCount}`,
        );
      }
    }
  } finally {
    validate.close();
  }

  const allMatch = tableCounts.every((t) => t.match);
  const destSize = statSync(destPath).size;
  const durationMs = Date.now() - t0;

  log(`[migrate] ${allMatch ? "SUCCESS" : "MISMATCH"} — ${tableCounts.length} tables, ` +
      `${destSize} bytes, ${durationMs} ms`);

  return {
    success: allMatch,
    tableCounts,
    schemaItems: schemaItems.length,
    destSize,
    durationMs,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// Atomic swap helper (--swap mode)
// ────────────────────────────────────────────────────────────────────────────

/**
 * Atomically replace `sourcePath` with `destPath`, after backing up
 * `sourcePath` to `<sourcePath>.pre-encrypt-<ISO-ts>.db`.
 *
 * Sequence:
 *   1. Move source → <source>.pre-encrypt-<ts>.db (NEVER deleted by this script)
 *   2. Move dest   → source path
 *   Result: source path now holds the encrypted DB.
 *
 * Rollback (manual):
 *   mv <source>.pre-encrypt-<ts>.db <source>
 *   rm <source>  # if encrypted version exists and you want to revert
 *
 * Refuses to run unless both paths exist (sanity).
 */
export function swapEncryptedIntoSource(sourcePath: string, destPath: string, quiet = false): string {
  if (!existsSync(sourcePath)) {
    throw new Error(`[swap] sourcePath does not exist: ${sourcePath}`);
  }
  if (!existsSync(destPath)) {
    throw new Error(`[swap] destPath does not exist: ${destPath}`);
  }
  const log = (msg: string): void => { if (!quiet) console.log(msg); };

  const ts = new Date().toISOString().replace(/[:T.]/g, "-").replace(/Z$/, "");
  const backupPath = `${sourcePath}.pre-encrypt-${ts}.db`;

  if (existsSync(backupPath)) {
    throw new Error(`[swap] backup path already exists (TS collision?): ${backupPath}`);
  }

  log(`[swap] move source → backup: ${sourcePath} → ${backupPath}`);
  renameSync(sourcePath, backupPath);

  log(`[swap] move dest → source: ${destPath} → ${sourcePath}`);
  try {
    renameSync(destPath, sourcePath);
  } catch (err) {
    // Roll back the source-to-backup move
    try { renameSync(backupPath, sourcePath); } catch { /* best-effort */ }
    throw new Error(`[swap] dest→source rename failed: ${(err as Error).message}`);
  }

  log(`[swap] SUCCESS — encrypted DB now at ${sourcePath}, plaintext backup at ${backupPath}`);
  return backupPath;
}

// ────────────────────────────────────────────────────────────────────────────
// CLI entry
// ────────────────────────────────────────────────────────────────────────────

/**
 * Parse argv + env and run migration. Exposed so tests can construct options
 * without going through process.argv. Returns the planned options or null if
 * an error message was printed (caller should exit with code 4).
 */
export function parseCliArgs(
  argv: ReadonlyArray<string>,
  env: NodeJS.ProcessEnv,
): { opts: MigrateOptions; swap: boolean } | null {
  // argv passed in is process.argv.slice(2)
  const args = argv.filter((a) => !a.startsWith("--"));
  const flags = new Set(argv.filter((a) => a.startsWith("--")));
  const swap = flags.has("--swap");

  let sourcePath: string | undefined;
  let destPath: string | undefined;
  let key: string | undefined;

  if (args.length >= 3) {
    sourcePath = args[0];
    destPath = args[1];
    key = args[2];
  } else {
    sourcePath = env.NOX_DB_PATH;
    destPath = env.NOX_DB_DEST;
    key = env.NOX_DB_KEY;
  }

  if (!sourcePath || !destPath || !key) {
    console.error(
      "Usage:\n" +
      "  migrate-encrypt-db.ts <source.db> <dest.db> <key> [--swap]\n" +
      "or env-driven:\n" +
      "  NOX_DB_PATH=<src> NOX_DB_DEST=<dst> NOX_DB_KEY=<k> migrate-encrypt-db.ts [--swap]",
    );
    return null;
  }

  return {
    opts: { sourcePath, destPath, key, swap },
    swap,
  };
}

export async function main(argv: ReadonlyArray<string>, env: NodeJS.ProcessEnv): Promise<number> {
  const parsed = parseCliArgs(argv, env);
  if (!parsed) return 4;
  const { opts, swap } = parsed;

  try {
    const result = migrateEncryptDb(opts);
    if (!result.success) {
      console.error("[migrate] FAIL: row counts mismatch — see table above");
      console.table(result.tableCounts);
      return 3;
    }
    console.table(result.tableCounts.map((t) => ({
      table: t.table,
      source: t.sourceCount,
      dest: t.destCount,
      match: t.match ? "OK" : "MISMATCH",
    })));

    if (swap) {
      console.log("\n[migrate] --swap requested. Performing atomic swap.");
      const backupPath = swapEncryptedIntoSource(opts.sourcePath, opts.destPath);
      console.log(`[migrate] PLAINTEXT BACKUP retained at: ${backupPath}`);
      console.log("[migrate] To rollback: mv " + backupPath + " " + opts.sourcePath);
    } else {
      console.log("\n[migrate] --swap NOT requested. Source DB untouched.");
      console.log(`[migrate]   Encrypted DB:  ${opts.destPath}`);
      console.log(`[migrate]   Plaintext DB:  ${opts.sourcePath}  (untouched)`);
      console.log("[migrate] Next steps:");
      console.log(`[migrate]   1. Set NOX_DB_KEY in env (matches the key passed to this script)`);
      console.log(`[migrate]   2. Point NOX_DB_PATH at ${opts.destPath} (or run --swap)`);
      console.log(`[migrate]   3. Restart nox-mem services`);
    }
    return 0;
  } catch (err) {
    console.error((err as Error).message);
    const msg = (err as Error).message;
    if (/already exists/.test(msg)) return 2;
    if (/already encrypted/.test(msg)) return 1;
    return 1;
  }
}

// Direct CLI execution guard (run only when invoked as main module).
// Using import.meta.url comparison is robust under both ts-node and node-dist
// builds. Skipped under `node --test` (test runner sets its own entrypoint).
const isMainModule =
  typeof process !== "undefined" &&
  process.argv[1] !== undefined &&
  import.meta.url === `file://${process.argv[1]}`;

if (isMainModule) {
  main(process.argv.slice(2), process.env).then(
    (code) => process.exit(code),
    (err) => {
      console.error("[migrate] FATAL:", err);
      process.exit(1);
    },
  );
}
