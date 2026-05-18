/**
 * T12 — CLI `nox-mem import` (framework-agnostic argv parser + runner).
 *
 * Detects encryption via `manifest.encryption.enabled` (always plaintext in
 * the archive — D41 #2). Reads passphrase via env or interactive prompt.
 *
 * Args:
 *   <archive-path>           positional, required
 *   --passphrase-env <ENV>   read passphrase from env (preferred)
 *   --merge | --replace      conflict mode (default: merge)
 *   --target-db <path>       optional override (used by production wiring)
 *   --dry-run                preview JSON, no DB writes
 *   --verify                 integrity check only, no decrypt-to-DB
 *
 * Exit codes: 0 ok, 1 system, 2 user (cancel/bad-args/cancelled prompt).
 */

import { readFile } from "node:fs/promises";
import {
  runImport,
  ImportRequest,
  ProgressEvent,
} from "../lib/archive/orchestrator.js";
import { getPassphrase } from "../lib/archive/encryption.js";
import { parseManifest } from "../lib/archive/manifest.js";
import { unpackArchive } from "../lib/archive/format.js";
import { ChunkRow, KgEntityRow, KgRelationRow, OpsAuditRow } from "../lib/archive/types.js";

export interface CliImportArgs {
  archivePath: string;
  passphraseEnv?: string;
  mode: "merge" | "replace";
  targetDb?: string;
  dryRun: boolean;
  verifyOnly: boolean;
}

export function parseImportArgs(argv: string[]): CliImportArgs {
  let positional: string | undefined;
  const args: Partial<CliImportArgs> = {
    mode: "merge",
    dryRun: false,
    verifyOnly: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    if (
      arg === "--passphrase" ||
      arg.startsWith("--passphrase=") ||
      arg === "-p"
    ) {
      throw new CliError(
        "REFUSED: passphrase must never be passed via argv (visible in `ps aux`).",
        2,
      );
    }
    switch (arg) {
      case "--passphrase-env":
        args.passphraseEnv = requireNext(argv, i++, "--passphrase-env");
        break;
      case "--merge":
        args.mode = "merge";
        break;
      case "--replace":
        args.mode = "replace";
        break;
      case "--target-db":
        args.targetDb = requireNext(argv, i++, "--target-db");
        break;
      case "--dry-run":
        args.dryRun = true;
        break;
      case "--verify":
        args.verifyOnly = true;
        break;
      case "--help":
      case "-h":
        throw new CliHelpRequest();
      default:
        if (arg.startsWith("--")) {
          throw new CliError(`Unknown flag: ${arg}`, 2);
        }
        if (positional) {
          throw new CliError(
            `Only one positional archive path allowed (got ${positional} and ${arg})`,
            2,
          );
        }
        positional = arg;
    }
  }
  if (!positional) {
    throw new CliError("missing archive path (positional argument)", 2);
  }
  return {
    archivePath: positional,
    passphraseEnv: args.passphraseEnv,
    mode: args.mode!,
    targetDb: args.targetDb,
    dryRun: args.dryRun!,
    verifyOnly: args.verifyOnly!,
  };
}

function requireNext(argv: string[], i: number, name: string): string {
  const v = argv[i + 1];
  if (!v || v.startsWith("--")) {
    throw new CliError(`${name} requires a value`, 2);
  }
  return v;
}

export interface RunCliImportDeps {
  /** Inject existing rows for merge planning. Empty for clean imports. */
  loadExisting: () => Promise<{
    chunks: ChunkRow[];
    kg_entities: KgEntityRow[];
    kg_relations: KgRelationRow[];
    ops_audit: OpsAuditRow[];
  }>;
  /** Inject schema version (production wires to PRAGMA user_version). */
  currentSchemaVersion: () => Promise<number>;
  /** Inject for test isolation. */
  readArchive?: (path: string) => Promise<Buffer>;
  /** Inject for test isolation. */
  promptPassphrase?: () => Promise<string>;
  /** Inject persist step (production writes rows back to better-sqlite3). */
  persist?: (
    resolved: import("../lib/archive/orchestrator.js").ImportResult["resolved"],
  ) => Promise<void>;
  env?: NodeJS.ProcessEnv;
  log?: (msg: string) => void;
  signal?: AbortSignal;
  isTTY?: boolean;
}

export interface CliImportOutcome {
  exitCode: number;
  result?: import("../lib/archive/orchestrator.js").ImportResult;
}

export async function runCliImport(
  argv: string[],
  deps: RunCliImportDeps,
): Promise<CliImportOutcome> {
  const env = deps.env ?? process.env;
  const log = deps.log ?? ((m: string) => process.stdout.write(m + "\n"));

  let parsed: CliImportArgs;
  try {
    parsed = parseImportArgs(argv);
  } catch (err) {
    if (err instanceof CliHelpRequest) {
      log(HELP_TEXT);
      return { exitCode: 0 };
    }
    if (err instanceof CliError) {
      log(`error: ${err.message}`);
      return { exitCode: err.exitCode };
    }
    throw err;
  }

  // Read archive
  const reader = deps.readArchive ?? defaultReader;
  let archive: Buffer;
  try {
    archive = await reader(parsed.archivePath);
  } catch (err) {
    log(`error: failed to read ${parsed.archivePath}: ${(err as Error).message}`);
    return { exitCode: 1 };
  }

  // Peek manifest BEFORE any decryption attempt — to know if passphrase is
  // needed AND to validate signature shape early (fail fast).
  let needsPassphrase = false;
  try {
    const entries = unpackArchive(archive);
    const manifestEntry = entries.find((e) => e.name === "manifest.json");
    if (!manifestEntry) {
      throw new Error("manifest.json missing from archive");
    }
    const manifest = parseManifest(manifestEntry.content);
    needsPassphrase = manifest.encryption.enabled === true;
  } catch (err) {
    log(`error: invalid archive: ${(err as Error).message}`);
    return { exitCode: 1 };
  }

  let passphrase: string | undefined;
  if (needsPassphrase) {
    if (parsed.passphraseEnv) {
      const v = env[parsed.passphraseEnv];
      if (typeof v !== "string" || v.length === 0) {
        log(`error: env var ${parsed.passphraseEnv} is not set`);
        return { exitCode: 2 };
      }
      passphrase = v;
    } else {
      const prompt = deps.promptPassphrase ?? (() =>
        getPassphrase({ envOverride: env, isTTY: deps.isTTY }));
      try {
        passphrase = await prompt();
      } catch (err) {
        log(`error: ${(err as Error).message}`);
        return { exitCode: 2 };
      }
    }
  }

  const currentSchemaVersion = await deps.currentSchemaVersion();
  const existing = parsed.verifyOnly
    ? { chunks: [], kg_entities: [], kg_relations: [], ops_audit: [] }
    : await deps.loadExisting();

  let lastPrint = Date.now();
  const onProgress = (ev: ProgressEvent): void => {
    const now = Date.now();
    switch (ev.phase) {
      case "import.start":
        log("[import] starting");
        break;
      case "import.unpack":
        log(`[import] unpacked ${ev.entries} entries`);
        break;
      case "import.decrypt":
        log(`[import] decrypting ${ev.files} files…`);
        break;
      case "import.migrate":
        log(
          `[import] migrating schema v${ev.from} → v${ev.to} (${ev.steps} steps)`,
        );
        break;
      case "import.chunks":
        if (now - lastPrint > 500 || ev.imported === ev.total) {
          log(`[import] chunks: ${ev.imported}/${ev.total}`);
          lastPrint = now;
        }
        break;
      case "import.kg":
        log(`[import] kg: ${ev.imported}/${ev.total}`);
        break;
      case "import.done":
        log(`[import] done — ${ev.duration_ms} ms`);
        break;
    }
  };

  const req: ImportRequest = {
    archive,
    passphrase,
    mode: parsed.mode,
    dry_run: parsed.dryRun,
    verify_only: parsed.verifyOnly,
    current_schema_version: currentSchemaVersion,
    existing,
    signal: deps.signal,
    onProgress,
  };

  let result: import("../lib/archive/orchestrator.js").ImportResult;
  try {
    result = await runImport(req);
  } catch (err) {
    const msg = (err as Error).message;
    if (/cancel/i.test(msg)) {
      log(`[import] cancelled: ${msg}`);
      return { exitCode: 2 };
    }
    log(`error: ${msg}`);
    return { exitCode: 1 };
  }

  // Persist (or skip for dry-run / verify_only)
  if (!parsed.dryRun && !parsed.verifyOnly) {
    if (deps.persist) {
      try {
        await deps.persist(result.resolved);
      } catch (err) {
        log(`error: persist failed: ${(err as Error).message}`);
        return { exitCode: 1 };
      }
    }
  }

  // Summary
  log("--- import summary ---");
  log(JSON.stringify(
    {
      mode: parsed.mode,
      dry_run: parsed.dryRun,
      verify_only: parsed.verifyOnly,
      target_db: parsed.targetDb ?? "<default>",
      stats: result.stats,
      duration_ms: result.duration_ms,
    },
    null,
    2,
  ));

  return { exitCode: 0, result };
}

async function defaultReader(p: string): Promise<Buffer> {
  return await readFile(p);
}

class CliError extends Error {
  constructor(
    message: string,
    public exitCode: number,
  ) {
    super(message);
    this.name = "CliError";
  }
}

class CliHelpRequest extends Error {
  constructor() {
    super("help");
    this.name = "CliHelpRequest";
  }
}

const HELP_TEXT = `
nox-mem import — restore memory state from an archive

Usage:
  nox-mem import <archive-path> [options]

Options:
  --passphrase-env <ENV>    Read passphrase from env (required for encrypted archives)
  --merge                   Skip rows that already exist (default)
  --replace                 Wipe target tables before inserting (ops_audit always preserved)
  --target-db <path>        Target DB path (default: current configured DB)
  --dry-run                 Preview JSON, no DB writes
  --verify                  Integrity check only (checksums + GCM tags + FK), no DB writes
  -h, --help                Show this help

Security:
  Passphrase is NEVER read from argv. Use --passphrase-env or interactive prompt.

Examples:
  nox-mem import /backup/nox.tgz                     # interactive passphrase prompt
  NOX_IMPORT_PASS=hunter2 nox-mem import /backup/nox.tgz --passphrase-env NOX_IMPORT_PASS
  nox-mem import /backup/nox.tgz --dry-run           # preview, no writes
  nox-mem import /backup/nox.tgz --verify            # integrity only
`.trim();
