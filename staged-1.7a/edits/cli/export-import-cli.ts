// export-import-cli.ts — A2 Tier 1 CLI wrapper for nox-mem export/import.
//
// Two subcommands:
//   nox-mem export --output <path> --passphrase-env <ENV_VAR>
//   nox-mem import --input <path>  --passphrase-env <ENV_VAR> [--strategy merge|replace] [--dry-run]
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
  importEncrypted,
  ExportImportError,
  type ImportOptions,
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
}

interface ImportArgs {
  input: string;
  passphraseEnv: string;
  strategy: "merge" | "replace";
  dryRun: boolean;
}

const USAGE = `Usage:
  nox-mem export --output <path>          --passphrase-env <ENV_VAR>
  nox-mem import --input  <bundle.json>   --passphrase-env <ENV_VAR>
                 [--strategy merge|replace]   (default: merge)
                 [--dry-run]
`;

/** Pure argv parser. Rejects argv-borne passphrase flags. */
function parseExport(argv: string[]): ExportArgs {
  rejectArgvPassphrase(argv);
  const args: Partial<ExportArgs> = {};
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
      default:
        if (a.startsWith("--output=")) args.output = a.slice("--output=".length);
        else if (a.startsWith("--passphrase-env="))
          args.passphraseEnv = a.slice("--passphrase-env=".length);
        else throw new CliUsageError(`Unknown export flag: ${a}`);
    }
  }
  if (!args.output) throw new CliUsageError("--output is required");
  if (!args.passphraseEnv) throw new CliUsageError("--passphrase-env <ENV_VAR> is required");
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
      const result = exportEncrypted(opts.db, passphrase, a.output);
      stdout(
        JSON.stringify({
          ok: true,
          op: "export",
          bundle_path: result.bundlePath,
          chunks_exported: result.chunksExported,
          entities_exported: result.entitiesExported,
          relations_exported: result.relationsExported,
          bundle_bytes: result.bundleBytes,
        }),
      );
      return { exitCode: 0 };
    }

    if (subcommand === "import") {
      const a = parseImport(rest);
      const passphrase = resolvePassphrase(a.passphraseEnv, opts.env);
      const importOptions: ImportOptions = { strategy: a.strategy, dryRun: a.dryRun };
      const result = importEncrypted(opts.db, passphrase, a.input, importOptions);
      stdout(
        JSON.stringify({
          ok: true,
          op: "import",
          strategy: a.strategy,
          dry_run: a.dryRun,
          chunks_imported: result.chunksImported,
          entities_imported: result.entitiesImported,
          relations_imported: result.relationsImported,
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
