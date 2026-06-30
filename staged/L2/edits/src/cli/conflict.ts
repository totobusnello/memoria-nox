/**
 * L2 T7 — CLI subcommands.
 *
 * Top-level: `nox-mem conflict <action>`. Actions:
 *   - scan                    runs detector + audit-writer; prints summary
 *   - list  [--status ...]    lists audit rows
 *   - show  <id>              prints one row + evidence
 *   - resolve <id> --pick <relation_id>
 *   - resolve <id> --merge "<new_target>"
 *   - resolve <id> --dismiss [--notes "..."]
 *
 * Output formats:
 *   - default: human-friendly table-ish
 *   - --json:  machine-readable
 *
 * Implementation: pure functions that take a DBHandle + parsed argv.
 * The runtime entrypoint (`dist/index.js` in production) wires these to
 * the singleton sqlite handle. Tests pass FakeDB.
 */

import type { DBHandle } from "../lib/conflict/db.js";
import {
  recordConflict,
  updateConflictStatus,
  getConflictById,
  listConflicts,
} from "../lib/conflict/audit-writer.js";
import { detectDirectConflicts } from "../lib/conflict/detector-direct.js";
import { collectEvidence } from "../lib/conflict/evidence.js";
import { resolveMode, runConflictPass } from "../lib/conflict/shadow.js";
import type { ConflictStatus, ResolutionInput } from "../lib/conflict/types.js";

export interface CliResult {
  /** Exit code. 0 = success, 1 = usage error, 2 = runtime error. */
  code: number;
  /** Lines to print to stdout (newline-joined). */
  stdout: string[];
  /** Lines to print to stderr. */
  stderr: string[];
  /** Machine-readable result (when --json). */
  json?: unknown;
}

export interface CliEnv {
  /** Override resolveMode() — primarily for tests. */
  mode_override?: string;
  /** ISO actor id (e.g. user name) for resolve writes. */
  actor?: string;
}

/** Entry point — dispatch on action verb. */
export function runConflictCli(
  db: DBHandle,
  argv: readonly string[],
  env: CliEnv = {},
): CliResult {
  const [action, ...rest] = argv;
  switch (action) {
    case "scan":
      return cmdScan(db, rest, env);
    case "list":
      return cmdList(db, rest, env);
    case "show":
      return cmdShow(db, rest);
    case "resolve":
      return cmdResolve(db, rest, env);
    case undefined:
    case "":
      return { code: 1, stdout: [], stderr: [usage()] };
    default:
      return {
        code: 1,
        stdout: [],
        stderr: [`unknown action: ${action}`, usage()],
      };
  }
}

function usage(): string {
  return [
    "nox-mem conflict <action> [options]",
    "  scan                                run detector pass + record audit rows",
    "  list  [--status <s>] [--limit N]   list audit rows (default status=open)",
    "  show  <id>                          show one row + evidence",
    "  resolve <id> --pick <relation_id>   mark as resolved_pick_one",
    "  resolve <id> --merge \"<target>\"     mark as resolved_merged",
    "  resolve <id> --dismiss              mark as dismissed",
    "  [--notes \"...\"]                     attach analyst note",
    "  [--json]                            machine-readable output",
    "  [--min-confidence 0.5]              scan threshold",
    "  [--predicate ...] (repeatable)      restrict scan to predicate(s)",
  ].join("\n");
}

// ─── scan ────────────────────────────────────────────────────────────────────

function cmdScan(db: DBHandle, args: readonly string[], env: CliEnv): CliResult {
  const opts = parseArgs(args);
  if (opts.error) return { code: 1, stdout: [], stderr: [opts.error] };

  const mode = resolveMode(env.mode_override);
  // CLI scan must work even in 'disabled' mode — operator opt-in by explicit
  // CLI call counts as run-once. We bypass the env gate by forcing shadow.
  const effectiveMode = mode === "disabled" ? "shadow" : mode;

  const result = runConflictPass(
    db,
    {
      min_confidence: opts.minConfidence,
      predicate_allowlist: opts.predicates.length > 0 ? opts.predicates : undefined,
    },
    effectiveMode,
  );

  if (opts.json) {
    return { code: 0, stdout: [JSON.stringify(result)], stderr: [], json: result };
  }
  const out = [
    `mode: ${result.mode}`,
    `scanned_at: ${new Date(result.scanned_at).toISOString()}`,
    `detected: ${result.detected}`,
    `recorded: ${result.recorded}`,
    `deduplicated: ${result.deduplicated}`,
  ];
  if (result.audit_ids.length > 0) {
    out.push(`new audit ids: ${result.audit_ids.join(", ")}`);
  }
  return { code: 0, stdout: out, stderr: [], json: result };
}

// ─── list ────────────────────────────────────────────────────────────────────

function cmdList(db: DBHandle, args: readonly string[], _env: CliEnv): CliResult {
  const opts = parseArgs(args);
  if (opts.error) return { code: 1, stdout: [], stderr: [opts.error] };
  const status = (opts.status ?? "open") as ConflictStatus;
  const rows = listConflicts(db, status, opts.limit ?? 20);
  if (opts.json) {
    return { code: 0, stdout: [JSON.stringify(rows)], stderr: [], json: rows };
  }
  const out: string[] = [];
  out.push(`status=${status}  rows=${rows.length}`);
  for (const r of rows) {
    out.push(`  [${r.id}] ${r.kind}  subject=${r.subject_entity_id}  predicate=${r.predicate}  relations=[${r.target_relation_ids.join(",")}]  shadow=${r.shadow_mode}`);
  }
  return { code: 0, stdout: out, stderr: [], json: rows };
}

// ─── show ────────────────────────────────────────────────────────────────────

function cmdShow(db: DBHandle, args: readonly string[]): CliResult {
  const idStr = args[0];
  if (!idStr) return { code: 1, stdout: [], stderr: ["show: missing <id>"] };
  const id = Number(idStr);
  if (!Number.isFinite(id) || id <= 0) {
    return { code: 1, stdout: [], stderr: ["show: invalid <id>"] };
  }
  const json = args.includes("--json");
  const row = getConflictById(db, id);
  if (!row) {
    return { code: 2, stdout: [], stderr: [`conflict ${id} not found`] };
  }

  // Reconstruct a Conflict shape from the audit row to drive collectEvidence().
  const conflict = {
    kind: row.kind,
    subject_entity_id: row.subject_entity_id,
    predicate: row.predicate,
    variants: row.variants,
  };
  const evidence = collectEvidence(db, conflict);
  if (json) {
    const payload = { row, evidence };
    return { code: 0, stdout: [JSON.stringify(payload)], stderr: [], json: payload };
  }
  const out: string[] = [];
  out.push(`conflict ${row.id}  kind=${row.kind}  status=${row.status}  shadow=${row.shadow_mode}`);
  out.push(`subject_entity_id=${row.subject_entity_id}  predicate=${row.predicate}`);
  out.push(`target_relation_ids: ${row.target_relation_ids.join(", ")}`);
  if (row.notes) out.push(`notes: ${row.notes}`);
  out.push("variants:");
  for (const ve of evidence.variants) {
    out.push(`  rel ${ve.variant.relation_id} → target ${ve.variant.target_entity_id}  conf=${ve.variant.confidence.toFixed(2)}  method=${ve.variant.extraction_method ?? "n/a"}  weight=${ve.weighted_score.toFixed(2)}`);
    for (const c of ve.chunks) {
      out.push(`    chunk ${c.chunk_id}: ${c.snippet}`);
    }
  }
  return { code: 0, stdout: out, stderr: [], json: { row, evidence } };
}

// ─── resolve ─────────────────────────────────────────────────────────────────

function cmdResolve(db: DBHandle, args: readonly string[], env: CliEnv): CliResult {
  const idStr = args[0];
  if (!idStr) return { code: 1, stdout: [], stderr: ["resolve: missing <id>"] };
  const id = Number(idStr);
  if (!Number.isFinite(id) || id <= 0) {
    return { code: 1, stdout: [], stderr: ["resolve: invalid <id>"] };
  }
  const opts = parseArgs(args.slice(1));
  if (opts.error) return { code: 1, stdout: [], stderr: [opts.error] };

  const actor = env.actor ?? "cli-user";

  let resolution: ResolutionInput;
  if (opts.pick != null) {
    resolution = {
      status: "resolved_pick_one",
      resolved_by: actor,
      resolution_kind: "pick_one",
      picked_relation_id: opts.pick,
      notes: opts.notes,
    };
  } else if (opts.merge != null) {
    resolution = {
      status: "resolved_merged",
      resolved_by: actor,
      resolution_kind: "merged",
      merge_target: opts.merge,
      notes: opts.notes,
    };
  } else if (opts.dismiss) {
    resolution = {
      status: "dismissed",
      resolved_by: actor,
      resolution_kind: "dismissed",
      notes: opts.notes,
    };
  } else if (opts.bothValid) {
    resolution = {
      status: "resolved_both_valid",
      resolved_by: actor,
      resolution_kind: "both_valid",
      notes: opts.notes,
    };
  } else {
    return {
      code: 1,
      stdout: [],
      stderr: ["resolve: one of --pick, --merge, --dismiss, --both-valid required"],
    };
  }

  try {
    updateConflictStatus(db, id, resolution);
  } catch (err) {
    return {
      code: 2,
      stdout: [],
      stderr: [`resolve failed: ${(err as Error).message}`],
    };
  }
  const row = getConflictById(db, id);
  if (opts.json) {
    return { code: 0, stdout: [JSON.stringify(row)], stderr: [], json: row };
  }
  return {
    code: 0,
    stdout: [`conflict ${id} → ${resolution.status} (by ${actor})`],
    stderr: [],
    json: row,
  };
}

// ─── argv parser ─────────────────────────────────────────────────────────────

interface ParsedArgs {
  status?: string;
  limit?: number;
  minConfidence?: number;
  predicates: string[];
  pick?: number;
  merge?: string;
  dismiss: boolean;
  bothValid: boolean;
  notes?: string;
  json: boolean;
  error?: string;
}

function parseArgs(args: readonly string[]): ParsedArgs {
  const out: ParsedArgs = { predicates: [], dismiss: false, bothValid: false, json: false };
  for (let i = 0; i < args.length; i++) {
    const a = args[i]!;
    switch (a) {
      case "--status":
        out.status = args[++i];
        break;
      case "--limit": {
        const n = Number(args[++i]);
        if (!Number.isFinite(n) || n <= 0) {
          out.error = `invalid --limit: ${args[i]}`;
          return out;
        }
        out.limit = n;
        break;
      }
      case "--min-confidence": {
        const n = Number(args[++i]);
        if (!Number.isFinite(n) || n < 0 || n > 1) {
          out.error = `invalid --min-confidence: ${args[i]}`;
          return out;
        }
        out.minConfidence = n;
        break;
      }
      case "--predicate":
        out.predicates.push(args[++i] ?? "");
        break;
      case "--pick": {
        const n = Number(args[++i]);
        if (!Number.isFinite(n) || n <= 0) {
          out.error = `invalid --pick: ${args[i]}`;
          return out;
        }
        out.pick = n;
        break;
      }
      case "--merge":
        out.merge = args[++i];
        break;
      case "--dismiss":
        out.dismiss = true;
        break;
      case "--both-valid":
        out.bothValid = true;
        break;
      case "--notes":
        out.notes = args[++i];
        break;
      case "--json":
        out.json = true;
        break;
      default:
        // ignore positional args (handled by callers)
        break;
    }
  }
  return out;
}
