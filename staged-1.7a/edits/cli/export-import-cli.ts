// export-import-cli.ts — A2 Tier 1 + Tier 2 CLI wrapper for nox-mem export/import.
//
// Subcommands:
//   nox-mem export --output <path> --passphrase-env <ENV_VAR>
//                  [--tier 1|2] (default: 2)
//                  [--tables chunks,kg_entities,kg_relations] (default: all; v2 only)
//   nox-mem import --input <path>  --passphrase-env <ENV_VAR>
//                  [--strategy merge|replace] (default: merge)
//                  [--tables chunks,kg_entities] (default: all-in-bundle; v2 only)
//                  [--dry-run]
//
// IMPORT IS AUTO-DETECTING: it routes v1 bundles to the v1 importer and v2
// bundles to the v2 importer transparently. --tables is ignored for v1.
//
// HARD RULES (D41 #2, memory [[no-secrets-in-git]] / [[no-hardcoded-secrets]]):
//   - Passphrase NEVER passed via argv (visible in `ps aux`). We REFUSE
//     `--passphrase=`, `--passphrase <value>`, and `-p <value>` shorthand.
//   - Only `--passphrase-env <ENV_VAR_NAME>` is accepted. The env var must be set;
//     we read its value at runtime and pass to the lib.
//   - Empty or absent env var = fail-closed with exit code 2.
//
// Exit codes (script-friendly):
//   0 — success
//   1 — system error (DB lock, disk full, bundle corrupted, etc.)
//   2 — user error (bad flag, refused passphrase flag, missing env var)
//
// This module is callable from production (CLI bin) and tests
// (`runCli(argv, { db, env, stdout, stderr })`).

import type Database from "better-sqlite3";
import {
  exportEncrypted,
  exportEncryptedV2,
  importEncryptedAuto,
  ExportImportError,
  type ImportV2Options,
} from "../lib/export-import.js";

export interface CliEnv {
  argv: string[];
  env: Record<string, string | undefined>;
  db: Database.Database;
  stdout?: (msg: string) => void;
  stderr?: (msg: string) => void;
}

export interface CliResult {
  exitCode: 0 | 1 | 2;
}

export class CliUsageError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CliUsageError";
  }
}

interface ExportArgs {
  output: string;
  passphraseEnv: string;
  tier: 1 | 2;
  tables?: string[]; // v2 only
}

interface ImportArgs {
  input: string;
  passphraseEnv: string;
  strategy: "merge" | "replace";
  tables?: string[]; // v2 only — ignored for v1 bundles
  dryRun: boolean;
}

const USAGE = `Usage:
  nox-mem export --output <path>          --passphrase-env <ENV_VAR>
                 [--tier 1|2]                 (default: 2 — per-table encryption)
                 [--tables chunks,kg_entities,kg_relations]   (v2 only; default: all)
  nox-mem import --input  <bundle.json>   --passphrase-env <ENV_VAR>
                 [--strategy merge|replace]   (default: merge)
                 [--tables chunks,kg_entities]                (v2 only; default: all-in-bundle)
                 [--dry-run]
`;

function parseTablesArg(raw: string): string[] {
  const list = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
  if (list.length === 0) {
    throw new CliUsageError("--tables value cannot be empty (expected comma-separated table names)");
  }
  return list;
}

/** Pure argv parser. Rejects argv-borne passphrase flags. */
function parseExport(argv: string[]): ExportArgs {
  rejectArgvPassphrase(argv);
  const args: Partial<ExportArgs> = { tier: 2 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    switch (a) {
      case "--output":
      case "-o":
        args.output = requireValue(argv, ++i, a);
        break;
      case "--passphrase-env":
        args.passphraseEnv = requireValue(argv, ++i, a);
        break;
      case "--tier": {
        const v = requireValue(argv, ++i, a);
        if (v !== "1" && v !== "2") {
          throw new CliUsageError(`--tier must be '1' or '2', got '${v}'`);
        }
        args.tier = v === "1" ? 1 : 2;
        break;
      }
      case "--tables": {
        const v = requireValue(argv, ++i, a);
        args.tables = parseTablesArg(v);
        break;
      }
      default:
        if (a.startsWith("--output=")) args.output = a.slice("--output=".length);
        else if (a.startsWith("--passphrase-env="))
          args.passphraseEnv = a.slice("--passphrase-env=".length);
        else if (a.startsWith("--tier=")) {
          const v = a.slice("--tier=".length);
          if (v !== "1" && v !== "2") {
            throw new CliUsageError(`--tier must be '1' or '2', got '${v}'`);
          }
          args.tier = v === "1" ? 1 : 2;
        } else if (a.startsWith("--tables=")) {
          args.tables = parseTablesArg(a.slice("--tables=".length));
        } else throw new CliUsageError(`Unknown export flag: ${a}`);
    }
  }
  if (!args.output) throw new CliUsageError("--output is required");
  if (!args.passphraseEnv) throw new CliUsageError("--passphrase-env <ENV_VAR> is required");
  if (args.tier === 1 && args.tables) {
    throw new CliUsageError("--tables is only valid with --tier 2 (V2 supports selective subset)");
  }
  return args as ExportArgs;
}

function parseImport(argv: string[]): ImportArgs {
  rejectArgvPassphrase(argv);
  const args: Partial<ImportArgs> & { dryRun?: boolean } = {
    strategy: "merge",
    dryRun: false,
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i]!;
    switch (a) {
      case "--input":
      case "-i":
        args.input = requireValue(argv, ++i, a);
        break;
      case "--passphrase-env":
        args.passphraseEnv = requireValue(argv, ++i, a);
        break;
      case "--strategy":
      case "-s": {
        const v = requireValue(argv, ++i, a);
        if (v !== "merge" && v !== "replace") {
          throw new CliUsageError(`--strategy must be 'merge' or 'replace', got '${v}'`);
        }
        args.strategy = v;
        break;
      }
      case "--tables": {
        const v = requireValue(argv, ++i, a);
        args.tables = parseTablesArg(v);
        break;
      }
      case "--dry-run":
        args.dryRun = true;
        break;
      default:
        if (a.startsWith("--input=")) args.input = a.slice("--input=".length);
        else if (a.startsWith("--passphrase-env="))
          args.passphraseEnv = a.slice("--passphrase-env=".length);
        else if (a.startsWith("--strategy=")) {
          const v = a.slice("--strategy=".length);
          if (v !== "merge" && v !== "replace") {
            throw new CliUsageError(`--strategy must be 'merge' or 'replace', got '${v}'`);
          }
          args.strategy = v;
        } else if (a.startsWith("--tables=")) {
          args.tables = parseTablesArg(a.slice("--tables=".length));
        } else throw new CliUsageError(`Unknown import flag: ${a}`);
    }
  }
  if (!args.input) throw new CliUsageError("--input is required");
  if (!args.passphraseEnv) throw new CliUsageError("--passphrase-env <ENV_VAR> is required");
  return args as ImportArgs;
}

function requireValue(argv: string[], i: number, flag: string): string {
  const v = argv[i];
  if (v === undefined || v.startsWith("--")) {
    throw new CliUsageError(`Flag ${flag} requires a value`);
  }
  return v;
}

/** Hard refuse any argv pattern that carries a passphrase value directly. */
function rejectArgvPassphrase(argv: string[]): void {
  for (const a of argv) {
    if (
      a === "--passphrase" ||
      a === "-p" ||
      a.startsWith("--passphrase=") ||
      a.startsWith("-p=")
    ) {
      throw new CliUsageError(
        "REFUSED: passphrase must never be passed via argv (it leaks in `ps aux`). " +
          "Use --passphrase-env <ENV_VAR_NAME> instead.",
      );
    }
  }
}

function resolvePassphrase(envVarName: string, env: Record<string, string | undefined>): string {
  // Env var name itself must be sane — uppercase + underscores + digits.
  if (!/^[A-Z_][A-Z0-9_]*$/.test(envVarName)) {
    throw new CliUsageError(
      `Invalid env var name '${envVarName}' for --passphrase-env (expected [A-Z_][A-Z0-9_]*)`,
    );
  }
  const value = env[envVarName];
  if (!value || value.length === 0) {
    throw new CliUsageError(
      `Env var ${envVarName} is not set or empty. Set it before invoking the CLI.`,
    );
  }
  return value;
}

/** Programmatic entry point — used by both bin and tests. */
export function runCli(opts: CliEnv): CliResult {
  const stdout = opts.stdout ?? ((m: string): void => void process.stdout.write(m + "\n"));
  const stderr = opts.stderr ?? ((m: string): void => void process.stderr.write(m + "\n"));

  const [subcommand, ...rest] = opts.argv;
  if (!subcommand || subcommand === "--help" || subcommand === "-h") {
    stdout(USAGE);
    return { exitCode: 0 };
  }

  try {
    if (subcommand === "export") {
      const a = parseExport(rest);
      const passphrase = resolvePassphrase(a.passphraseEnv, opts.env);
      if (a.tier === 1) {
        const result = exportEncrypted(opts.db, passphrase, a.output);
        stdout(
          JSON.stringify({
            ok: true,
            op: "export",
            tier: 1,
            bundle_path: result.bundlePath,
            // V1 flat fields (backward compat with T1 callers)
            chunks_exported: result.chunksExported,
            entities_exported: result.entitiesExported,
            relations_exported: result.relationsExported,
            // V2-shaped echo for unified consumers
            tables_exported: [
              { name: "chunks", rows: result.chunksExported },
              { name: "kg_entities", rows: result.entitiesExported },
              { name: "kg_relations", rows: result.relationsExported },
            ],
            bundle_bytes: result.bundleBytes,
          }),
        );
      } else {
        const result = exportEncryptedV2(opts.db, passphrase, a.output, { tables: a.tables });
        // Derive v1-shape flat fields too (0 if table absent from subset) so
        // legacy consumers calling .chunks_exported don't break.
        const byName = Object.fromEntries(result.tablesExported.map((t) => [t.name, t.rows]));
        stdout(
          JSON.stringify({
            ok: true,
            op: "export",
            tier: 2,
            bundle_path: result.bundlePath,
            tables_exported: result.tablesExported,
            chunks_exported: byName.chunks ?? 0,
            entities_exported: byName.kg_entities ?? 0,
            relations_exported: byName.kg_relations ?? 0,
            bundle_bytes: result.bundleBytes,
          }),
        );
      }
      return { exitCode: 0 };
    }

    if (subcommand === "import") {
      const a = parseImport(rest);
      const passphrase = resolvePassphrase(a.passphraseEnv, opts.env);
      const importOptions: ImportV2Options = {
        strategy: a.strategy,
        dryRun: a.dryRun,
        tables: a.tables,
      };
      // Auto-detect v1 vs v2 from the bundle header.
      const result = importEncryptedAuto(opts.db, passphrase, a.input, importOptions);
      // Derive v1-shape flat fields from the v2 result for backward compat.
      const byName = Object.fromEntries(result.tablesImported.map((t) => [t.name, t.rows]));
      stdout(
        JSON.stringify({
          ok: true,
          op: "import",
          strategy: a.strategy,
          dry_run: a.dryRun,
          tables_imported: result.tablesImported,
          // V1 flat fields (backward compat with T1 callers)
          chunks_imported: byName.chunks ?? 0,
          entities_imported: byName.kg_entities ?? 0,
          relations_imported: byName.kg_relations ?? 0,
          conflicts: result.conflicts,
        }),
      );
      return { exitCode: 0 };
    }

    throw new CliUsageError(`Unknown subcommand: '${subcommand}'\n${USAGE}`);
  } catch (e) {
    if (e instanceof CliUsageError) {
      stderr(`ERROR: ${e.message}`);
      return { exitCode: 2 };
    }
    if (e instanceof ExportImportError) {
      stderr(`ERROR [${e.code}]: ${e.message}`);
      return { exitCode: 1 };
    }
    stderr(`FATAL: ${(e as Error).message}`);
    return { exitCode: 1 };
  }
}
