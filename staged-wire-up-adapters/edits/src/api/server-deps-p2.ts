/**
 * src/api/server-deps-p2.ts — Wave O T5: P2 (hooks) wire-up adapter.
 *
 * Companion to `src/lib/hooks/server-deps.ts`. This module is the public
 * entry the api/ layer + tests import from. It re-exports `buildHooksDeps`
 * and adds two convenience helpers:
 *
 *   - `getRecentMetadataOnly()` — direct DB query for the recent rows the
 *     wire-up + dashboard surface. Sanitization is identical to the inline
 *     code in staged-P2's `handleHooksRequest` (drops payload_json).
 *
 *   - `dryRunHook(text, role, source)` — runs the 5-layer pipeline with
 *     dryRun=true and returns the trace. Mirrors the POST /api/hooks/dryrun
 *     handler but callable in-process for tests/dashboards.
 */

import { buildHooksDeps as buildHooksDepsImpl } from "../lib/hooks/server-deps.js";

export {
  buildHooksDeps,
  __setQueueProbeForTests,
  __resetHooksDepsForTests,
  type HooksApiDeps,
  type HookRecentRow,
  type HookTelemetryRow,
} from "../lib/hooks/server-deps.js";

// ─── Convenience helpers ─────────────────────────────────────────────────────

export interface DryRunResult {
  result: unknown;
  trace: Array<{
    layer: string;
    reason: string;
    redaction_count: number;
    kind: string;
  }>;
}

/**
 * In-process dry-run for the hook pipeline. Lazy-loads staged-P2 modules.
 * Returns null when staged-P2 is not deployed.
 */
export async function dryRunHook(
  text: string,
  role: "user" | "assistant" | "system" | "tool" | "unknown" = "user",
  source: "openclaw" | "cli" | "manual" | "mcp" | "api" | "unknown" = "api",
): Promise<DryRunResult | null> {
  // String indirection — files live in the staged-P2 tree, not co-located
  // here. Production rsync places them at `src/lib/hooks/{config,pipeline}.js`.
  const CONFIG_SPEC = "../lib/hooks/config.js";
  const PIPELINE_SPEC = "../lib/hooks/pipeline.js";
  let configMod: any;
  let pipelineMod: any;
  try {
    configMod = await import(CONFIG_SPEC);
    pipelineMod = await import(PIPELINE_SPEC);
  } catch {
    return null;
  }
  if (!configMod?.loadConfig || !pipelineMod?.createPipeline) return null;

  const base = configMod.loadConfig();
  const forced = {
    ...base,
    enabled: true,
    dryRun: true,
    allowedSources: new Set([...(base.allowedSources ?? []), "api", "cli"]),
  };
  const trace: any[] = [];
  const pipeline = pipelineMod.createPipeline({
    config: forced,
    telemetry: (row: any) => {
      trace.push(row);
    },
  });
  const event = {
    event_id: `dr_${Math.random().toString(36).slice(2)}`,
    source,
    role,
    content: text,
    session_id: "api-dryrun",
    project_slug: "api",
    ts: new Date().toISOString(),
  };
  const result = await pipeline.run(event);
  return {
    result,
    trace: trace.map((t) => {
      let parsed: { layer?: string; reason?: string } = {};
      try {
        parsed = JSON.parse(t.payload_json ?? "{}");
      } catch {
        /* ignore */
      }
      return {
        layer: parsed.layer ?? "unknown",
        reason: parsed.reason ?? "unknown",
        redaction_count: t.redaction_count ?? 0,
        kind: t.kind ?? "unknown",
      };
    }),
  };
}

/** Force the deps builder to load (used by `await Promise.all` warmup). */
export async function warmupHooksDeps(): Promise<void> {
  await buildHooksDepsImpl();
}
