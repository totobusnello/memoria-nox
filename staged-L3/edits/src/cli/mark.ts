/**
 * src/cli/mark.ts — CLI front-end for L3 mark workflow.
 *
 * Usage:
 *   nox-mem mark <chunk-id> --canonical          → confidence=1.0  + provenance=user-marked
 *   nox-mem mark <chunk-id> --refuted            → confidence=0.05 + provenance=user-marked
 *   nox-mem mark <chunk-id> --stale              → provenance=user-marked (confidence unchanged)
 *   nox-mem mark <chunk-id> --supersede-by <id>  → set superseded_by FK, mark stale
 *   nox-mem mark <chunk-id> --notes "..."        → optional free text → ops_audit
 *
 * Returns JSON to stdout. Non-zero exit on error.
 *
 * Append-only audit guarantee preserved: all ops emit an ops_audit row via
 * mark.ts core; this CLI layer only parses argv + dispatches.
 */

import type { Db } from "../lib/confidence/db-shim.js";
import {
  markChunk,
  supersedeChunk,
} from "../lib/confidence/mark.js";
import type { MarkKind, MarkResult } from "../lib/confidence/types.js";
import { resolveConfig } from "../lib/confidence/config.js";

export interface ParsedArgs {
  chunk_id: number;
  kind?: MarkKind;
  supersede_by?: number;
  notes?: string;
}

export class CliError extends Error {
  constructor(
    public readonly code: string,
    message: string
  ) {
    super(message);
  }
}

/** Parses `mark <id> [--canonical|--refuted|--stale] [--supersede-by N] [--notes "..."]`. */
export function parseMarkArgs(argv: string[]): ParsedArgs {
  // argv expected to start at first arg after "mark"
  if (argv.length === 0) {
    throw new CliError("usage", "missing chunk_id");
  }
  const idStr = argv[0];
  if (idStr === undefined) {
    throw new CliError("usage", "missing chunk_id");
  }
  const chunk_id = parseInt(idStr, 10);
  if (!Number.isFinite(chunk_id) || chunk_id <= 0) {
    throw new CliError("usage", `invalid chunk_id: ${idStr}`);
  }

  let kind: MarkKind | undefined;
  let supersede_by: number | undefined;
  let notes: string | undefined;

  for (let i = 1; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--canonical") kind = "canonical";
    else if (arg === "--refuted") kind = "refuted";
    else if (arg === "--stale") kind = "stale";
    else if (arg === "--supersede-by") {
      const next = argv[++i];
      if (next === undefined) {
        throw new CliError("usage", "--supersede-by requires an id");
      }
      const n = parseInt(next, 10);
      if (!Number.isFinite(n) || n <= 0) {
        throw new CliError("usage", `invalid supersede-by id: ${next}`);
      }
      supersede_by = n;
    } else if (arg === "--notes") {
      const next = argv[++i];
      if (next === undefined) {
        throw new CliError("usage", "--notes requires a string");
      }
      notes = next;
    } else if (arg !== undefined) {
      throw new CliError("usage", `unknown flag: ${arg}`);
    }
  }

  if (!kind && supersede_by === undefined) {
    throw new CliError(
      "usage",
      "must specify one of --canonical, --refuted, --stale, --supersede-by"
    );
  }

  return { chunk_id, kind, supersede_by, notes };
}

/** Runs the parsed CLI op against `db`. Returns the MarkResult JSON. */
export function runMark(db: Db, args: ParsedArgs): MarkResult {
  const cfg = resolveConfig();

  if (args.supersede_by !== undefined) {
    // Supersede implies stale; run supersede first then mark stale for audit.
    const supersedeResult = supersedeChunk({
      db,
      chunk_id: args.chunk_id,
      by_chunk_id: args.supersede_by,
      notes: args.notes,
      cfg,
    });
    if (args.kind && args.kind !== "stale") {
      // Caller explicitly combined supersede + canonical/refuted — apply mark.
      return markChunk({
        db,
        chunk_id: args.chunk_id,
        kind: args.kind,
        notes: args.notes,
        cfg,
      });
    }
    return supersedeResult;
  }

  if (!args.kind) {
    // Should be unreachable due to parseMarkArgs validation.
    throw new CliError("usage", "no kind specified");
  }

  return markChunk({
    db,
    chunk_id: args.chunk_id,
    kind: args.kind,
    notes: args.notes,
    cfg,
  });
}

/** Top-level CLI entry: argv slice + db handle → printable JSON string. */
export function markCommand(db: Db, argv: string[]): string {
  try {
    const parsed = parseMarkArgs(argv);
    const result = runMark(db, parsed);
    return JSON.stringify(result, null, 2);
  } catch (err) {
    if (err instanceof CliError) {
      return JSON.stringify({ ok: false, code: err.code, error: err.message });
    }
    return JSON.stringify({
      ok: false,
      code: "runtime",
      error: err instanceof Error ? err.message : String(err),
    });
  }
}
