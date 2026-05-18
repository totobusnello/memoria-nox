/**
 * src/cli/hooks.ts — T11: CLI subcommands for hooks inspection.
 *
 * Registered as `nox-mem hooks <verb>`:
 *
 *   status         → print current config + queue depth + rate-limit tokens
 *   recent [N]     → print last N captures (default 20) — never raw content,
 *                    only metadata + redaction counts
 *   dryrun <text>  → run text through pipeline with dryRun=true, print
 *                    per-layer decision trace
 *   stats          → print captured/rejected counters by reason
 *
 * No content ever leaves the host process via CLI output unless the user
 * explicitly passes raw text on the command line (dryrun) — and even then,
 * the output shows redacted form, not the original.
 */

import { randomUUID } from "node:crypto";

import { createPipeline, type IngestFn, type TelemetrySink } from "../lib/hooks/pipeline.js";
import { loadConfig, type HookConfig } from "../lib/hooks/config.js";
import type { HookEvent, HookResult, HookTelemetryRow } from "../lib/hooks/types.js";

export interface HooksCliDeps {
  /** Read recent capture rows from agent_events. */
  readRecent: (limit: number) => Promise<Array<{
    event_uuid: string;
    session_id: string;
    project_slug: string;
    kind: string;
    timestamp: string;
    redaction_count: number;
    payload_json: string;
  }>>;
  /** Aggregate counters from agent_events. */
  readStats: () => Promise<{
    last_24h: { captured: number; rejected: number; by_reason: Record<string, number> };
    last_7d: { captured: number; rejected: number };
  }>;
  /** Optional: provide a wired ingest (only used if a non-dry status check needs it). */
  ingest?: IngestFn;
  /** Optional: telemetry sink for dryrun side-effects. */
  telemetry?: TelemetrySink;
  /** Inject config (tests). */
  config?: HookConfig;
}

export interface HooksCliResult {
  ok: boolean;
  output: string;
  data?: unknown;
}

export async function runHooksCommand(
  argv: string[],
  deps: HooksCliDeps,
): Promise<HooksCliResult> {
  const verb = argv[0] ?? "status";
  switch (verb) {
    case "status":
      return statusCmd(deps);
    case "recent":
      return recentCmd(argv.slice(1), deps);
    case "dryrun":
      return dryrunCmd(argv.slice(1).join(" "), deps);
    case "stats":
      return statsCmd(deps);
    default:
      return {
        ok: false,
        output: `unknown verb '${verb}'. valid: status|recent|dryrun|stats`,
      };
  }
}

function statusCmd(deps: HooksCliDeps): HooksCliResult {
  const config = deps.config ?? loadConfig();
  const lines = [
    "nox-mem hooks — status",
    `  enabled         : ${config.enabled}`,
    `  allowed_sources : ${Array.from(config.allowedSources).join(",")}`,
    `  rate_limit_pm   : ${config.rateLimitPerMin}`,
    `  dedup_threshold : ${config.dedupThreshold}`,
    `  llm_classify    : ${config.llmClassify}`,
    `  dry_run         : ${config.dryRun}`,
    `  queue_size      : ${config.queueSize}`,
    `  min_length      : ${config.minLength}`,
    `  pii_policy      : ${config.piiPolicy}`,
  ];
  return { ok: true, output: lines.join("\n"), data: config };
}

async function recentCmd(args: string[], deps: HooksCliDeps): Promise<HooksCliResult> {
  const n = Math.max(1, Math.min(200, Number.parseInt(args[0] ?? "20", 10) || 20));
  try {
    const rows = await deps.readRecent(n);
    const lines = [
      `nox-mem hooks — last ${rows.length} captures`,
      `${"event_uuid".padEnd(40)} ${"kind".padEnd(14)} ${"redacted".padEnd(8)} session/project`,
    ];
    for (const r of rows) {
      lines.push(
        `${r.event_uuid.padEnd(40)} ${r.kind.padEnd(14)} ${String(r.redaction_count).padEnd(8)} ${r.session_id}/${r.project_slug}`,
      );
    }
    return { ok: true, output: lines.join("\n"), data: rows };
  } catch (e) {
    return { ok: false, output: `recent failed: ${(e as Error).message}` };
  }
}

async function dryrunCmd(text: string, deps: HooksCliDeps): Promise<HooksCliResult> {
  if (!text || text.length === 0) {
    return { ok: false, output: "usage: nox-mem hooks dryrun <text>" };
  }
  const base = deps.config ?? loadConfig();
  // Force dryRun + enabled so the pipeline shows full trace
  const forced: HookConfig = {
    ...base,
    enabled: true,
    dryRun: true,
    allowedSources: new Set([...base.allowedSources, "cli"]),
  };
  const trace: HookTelemetryRow[] = [];
  const pipeline = createPipeline({
    config: forced,
    telemetry: (row) => {
      trace.push(row);
    },
  });
  const event: HookEvent = {
    event_id: `dr_${randomUUID()}`,
    source: "cli",
    role: "user",
    content: text,
    session_id: "cli-dryrun",
    project_slug: "cli",
    ts: new Date().toISOString(),
  };
  const result: HookResult = await pipeline.run(event);
  const lines = [
    `nox-mem hooks — dryrun (${text.length} chars)`,
    `  outcome   : captured=${result.captured} reason=${result.reason}`,
    `  layer     : ${result.layer}`,
    `  duration  : ${result.duration_ms}ms`,
    `  dry_run   : ${result.dry_run}`,
    "trace:",
  ];
  for (const row of trace) {
    const p = JSON.parse(row.payload_json);
    lines.push(`  - layer=${p.layer} reason=${p.reason} redactions=${row.redaction_count}`);
  }
  return { ok: true, output: lines.join("\n"), data: { result, trace } };
}

async function statsCmd(deps: HooksCliDeps): Promise<HooksCliResult> {
  try {
    const s = await deps.readStats();
    const lines = [
      "nox-mem hooks — stats",
      `  24h captured : ${s.last_24h.captured}`,
      `  24h rejected : ${s.last_24h.rejected}`,
      `  7d  captured : ${s.last_7d.captured}`,
      `  7d  rejected : ${s.last_7d.rejected}`,
      "by reason (24h):",
    ];
    for (const [k, v] of Object.entries(s.last_24h.by_reason)) {
      lines.push(`  ${k.padEnd(24)} ${v}`);
    }
    return { ok: true, output: lines.join("\n"), data: s };
  } catch (e) {
    return { ok: false, output: `stats failed: ${(e as Error).message}` };
  }
}
