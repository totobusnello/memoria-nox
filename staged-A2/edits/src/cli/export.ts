/**
 * T11 — CLI `nox-mem export` (framework-agnostic argv parser + runner).
 *
 * D41 #2: encrypt-by-default. `--unencrypted` is the opt-out flag. `--passphrase`
 * is REJECTED at argv parse time (CLI argv leaks via `ps aux`); passphrase
 * comes from `--passphrase-env <ENV>` (env var name) or an interactive prompt.
 *
 * Output path default: `~/nox-mem-export-<YYYY-MM-DD>.tgz`.
 *
 * Exit codes:
 *   0 — success
 *   1 — system error (disk, DB lock, archive write failure)
 *   2 — user cancellation (Ctrl-C / passphrase prompt aborted / explicit
 *       missing-required-flag) — distinguished from system error for scripts.
 *
 * Progress reporting: prints "chunks: X/Y" every 500 rows OR every 1s wall.
 *
 * This module is callable from production (CLI bin) and from tests (mock
 * `dbReader` + `fs` + `prompt`).
 */

import { writeFile } from "node:fs/promises";
import * as path from "node:path";
import * as os from "node:os";
import {
  runExport,
  ExportRequest,
  ProgressEvent,
} from "../lib/archive/orchestrator.js";
import { getPassphrase } from "../lib/archive/encryption.js";

export interface CliExportArgs {
  out?: string;
  unencrypted?: boolean;
  passphraseEnv?: string;
  project?: string;
  since?: string;
  until?: string;
  excludeEmbeddings?: boolean;
  /** When non-TTY scripts opt-out: require `NOX_EXPORT_UNENCRYPTED_ACK=1`. */
  ackUnencrypted?: boolean;
}

/** Pure argv parser. Throws on `--passphrase` flag (security hard rule). */
export function parseExportArgs(argv: string[]): CliExportArgs {
  const args: CliExportArgs = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i]!;
    // SECURITY: reject any flag carrying passphrase value in argv. ps aux leak.
    if (
      arg === "--passphrase" ||
      arg.startsWith("--passphrase=") ||
      arg === "-p"
    ) {
      throw new CliError(
        "REFUSED: passphrase must never be passed via argv (visible in `ps aux`). " +
          "Use --passphrase-env <ENV_VAR_NAME> or interactive prompt.",
        2,
      );
    }
    switch (arg) {
      case "--out":
        args.out = requireNext(argv, i++, "--out");
        break;
      case "--unencrypted":
        args.unencrypted = true;
        break;
      case "--passphrase-env":
        args.passphraseEnv = requireNext(argv, i++, "--passphrase-env");
        break;
      case "--project":
        args.project = requireNext(argv, i++, "--project");
        break;
      case "--since":
        args.since = requireNext(argv, i++, "--since");
        break;
      case "--until":
        args.until = requireNext(argv, i++, "--until");
        break;
      case "--exclude-embeddings":
        args.excludeEmbeddings = true;
        break;
      case "--help":
      case "-h":
        throw new CliHelpRequest();
      default:
        throw new CliError(`Unknown flag: ${arg}`, 2);
    }
  }
  return args;
}

function requireNext(argv: string[], i: number, name: string): string {
  const v = argv[i + 1];
  if (!v || v.startsWith("--")) {
    throw new CliError(`${name} requires a value`, 2);
  }
  return v;
}

export interface RunCliExportDeps {
  /** Inject a corpus reader. Production wires this to better-sqlite3. */
  dbReader: () => Promise<Omit<ExportRequest, "passphrase" | "unencrypted" | "signal" | "onProgress">>;
  /** Inject for test isolation. */
  writeArchive?: (path: string, buf: Buffer) => Promise<void>;
  /** Inject for test isolation. */
  promptPassphrase?: () => Promise<string>;
  /** Inject env for test isolation. */
  env?: NodeJS.ProcessEnv;
  /** Inject log sink. */
  log?: (msg: string) => void;
  /** Inject cancellation. */
  signal?: AbortSignal;
  /** Inject TTY detection. */
  isTTY?: boolean;
}

export interface CliExportOutcome {
  exitCode: number;
  archivePath?: string;
  manifest?: import("../lib/archive/types.js").ManifestV1;
  bytes?: number;
  duration_ms?: number;
}

export async function runCliExport(
  argv: string[],
  deps: RunCliExportDeps,
): Promise<CliExportOutcome> {
  const env = deps.env ?? process.env;
  const log = deps.log ?? ((m: string) => process.stdout.write(m + "\n"));

  let parsed: CliExportArgs;
  try {
    parsed = parseExportArgs(argv);
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

  // Resolve output path
  const outPath = parsed.out ?? defaultExportPath();

  // Resolve passphrase (D41 #2)
  let passphrase: string | undefined;
  if (!parsed.unencrypted) {
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
  } else {
    // --unencrypted: belt + suspenders. In non-TTY, require ACK env var.
    const ack = env.NOX_EXPORT_UNENCRYPTED_ACK === "1";
    const isTTY = deps.isTTY ?? Boolean(process.stdin.isTTY);
    if (!isTTY && !ack) {
      log(
        "error: --unencrypted in non-TTY context requires " +
          "NOX_EXPORT_UNENCRYPTED_ACK=1 (D41 #2 safety net).",
      );
      return { exitCode: 2 };
    }
  }

  const corpus = await deps.dbReader();
  if (parsed.excludeEmbeddings) {
    corpus.embeddings = undefined;
  }

  // Progress: print every 500 rows OR every 1s
  let lastPrint = Date.now();
  let lastTotal = 0;
  const onProgress = (ev: ProgressEvent): void => {
    const now = Date.now();
    switch (ev.phase) {
      case "export.start":
        log(`[export] starting (${ev.total ?? "?"} chunks total)`);
        break;
      case "export.chunks":
        if (
          ev.emitted - lastTotal >= 500 ||
          now - lastPrint > 1000 ||
          ev.emitted === ev.total
        ) {
          log(`[export] chunks: ${ev.emitted}/${ev.total}`);
          lastPrint = now;
          lastTotal = ev.emitted;
        }
        break;
      case "export.embeddings":
        log(`[export] embeddings: ${ev.emitted}/${ev.total}`);
        break;
      case "export.kg":
        log(`[export] kg: ${ev.emitted}/${ev.total}`);
        break;
      case "export.encrypt":
        log(`[export] encrypting ${ev.files} files (AES-256-GCM)…`);
        break;
      case "export.pack":
        log(`[export] packing ${ev.entries} entries into tar.gz…`);
        break;
      case "export.done":
        log(
          `[export] done — ${ev.size_bytes} bytes in ${ev.duration_ms} ms → ${outPath}`,
        );
        break;
    }
  };

  let result;
  try {
    result = await runExport({
      ...corpus,
      filters: {
        project: parsed.project ?? null,
        since: parsed.since ?? null,
        until: parsed.until ?? null,
      },
      unencrypted: parsed.unencrypted === true,
      passphrase,
      signal: deps.signal,
      onProgress,
    });
  } catch (err) {
    const msg = (err as Error).message;
    if (/cancel/i.test(msg)) {
      log(`[export] cancelled: ${msg}`);
      return { exitCode: 2 };
    }
    log(`error: ${msg}`);
    return { exitCode: 1 };
  }

  const writer = deps.writeArchive ?? defaultWriter;
  try {
    await writer(outPath, result.archive);
  } catch (err) {
    log(`error: failed to write archive: ${(err as Error).message}`);
    return { exitCode: 1 };
  }

  return {
    exitCode: 0,
    archivePath: outPath,
    manifest: result.manifest,
    bytes: result.size_bytes,
    duration_ms: result.duration_ms,
  };
}

async function defaultWriter(p: string, buf: Buffer): Promise<void> {
  await writeFile(p, buf, { mode: 0o600 });
}

function defaultExportPath(): string {
  const date = new Date().toISOString().slice(0, 10);
  return path.join(os.homedir(), `nox-mem-export-${date}.tgz`);
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
nox-mem export — archive memory state to a portable .tgz

Usage:
  nox-mem export [options]

Options:
  --out <path>              Output archive path (default ~/nox-mem-export-<YYYY-MM-DD>.tgz)
  --unencrypted             Opt-out of encryption (D41 #2 default = encrypted)
  --passphrase-env <ENV>    Read passphrase from env var (preferred for automation)
  --project <name>          Filter to a single project
  --since <iso8601>         Only include chunks created on/after this date
  --until <iso8601>         Only include chunks created on/before this date
  --exclude-embeddings      Skip embeddings.bin/idx (smaller archive)
  -h, --help                Show this help

Security:
  Passphrase is NEVER read from argv. Use --passphrase-env or interactive prompt.
  Output file is written with mode 0600 (owner read/write only).

Examples:
  nox-mem export                                    # encrypted, prompt for pass
  NOX_EXPORT_PASSPHRASE=hunter2 nox-mem export      # encrypted, env passphrase
  nox-mem export --unencrypted --out /tmp/dev.tgz   # plaintext (requires TTY or ACK env)
`.trim();
