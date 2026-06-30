/**
 * src/api/hooks.ts — T12: HTTP endpoints for hooks inspection + dryrun.
 *
 * Routes (mounted under /api/hooks):
 *
 *   GET  /api/hooks/status   → 200 { config, queueDepth, rateLimitTokens }
 *   GET  /api/hooks/recent   → 200 { rows: [...metadata only...] }
 *   POST /api/hooks/dryrun   → 200 { result, trace } — accepts { text } body
 *
 * Output sanitization:
 *   - status returns config + counters; never raw events
 *   - recent returns only metadata fields (event_uuid, ts, redaction_count,
 *     kind, session_id, project_slug); NEVER payload content
 *   - dryrun returns per-layer trace (layer + reason) and the redacted
 *     output preview (truncated to 200 chars)
 */

import { randomUUID } from "node:crypto";

import { createPipeline, type TelemetrySink } from "../lib/hooks/pipeline.js";
import { loadConfig, type HookConfig } from "../lib/hooks/config.js";
import type { HookEvent, HookTelemetryRow } from "../lib/hooks/types.js";

export interface HttpRequest {
  method: string;
  path: string;
  query?: Record<string, string>;
  body?: unknown;
}

export interface HttpResponse {
  status: number;
  body: Record<string, unknown>;
}

export interface HooksApiDeps {
  readRecent: (limit: number) => Promise<Array<{
    event_uuid: string;
    session_id: string;
    project_slug: string;
    kind: string;
    timestamp: string;
    redaction_count: number;
  }>>;
  config?: HookConfig;
  telemetry?: TelemetrySink;
  /** Inject queue inspector (e.g., from plugin handle). Default returns 0. */
  inspectQueue?: () => { queueDepth: number; rateLimitTokens?: number };
}

/**
 * Route a single HTTP request. Returns an HttpResponse.
 * No Express/Fastify dep — host wires this into whichever framework.
 */
export async function handleHooksRequest(
  req: HttpRequest,
  deps: HooksApiDeps,
): Promise<HttpResponse> {
  const { method, path } = req;

  if (method === "GET" && path === "/api/hooks/status") {
    const config = deps.config ?? loadConfig();
    const inspect = deps.inspectQueue ? deps.inspectQueue() : { queueDepth: 0 };
    return {
      status: 200,
      body: {
        config: {
          enabled: config.enabled,
          allowed_sources: Array.from(config.allowedSources),
          rate_limit_per_min: config.rateLimitPerMin,
          dedup_threshold: config.dedupThreshold,
          llm_classify: config.llmClassify,
          dry_run: config.dryRun,
          queue_size: config.queueSize,
          min_length: config.minLength,
          pii_policy: config.piiPolicy,
        },
        queueDepth: inspect.queueDepth,
        rateLimitTokens: inspect.rateLimitTokens ?? null,
      },
    };
  }

  if (method === "GET" && path === "/api/hooks/recent") {
    const limit = Math.max(1, Math.min(100, Number.parseInt(req.query?.["limit"] ?? "20", 10) || 20));
    try {
      const rows = await deps.readRecent(limit);
      // Sanitize: drop payload_json entirely
      const sanitized = rows.map((r) => ({
        event_uuid: r.event_uuid,
        session_id: r.session_id,
        project_slug: r.project_slug,
        kind: r.kind,
        timestamp: r.timestamp,
        redaction_count: r.redaction_count,
      }));
      return { status: 200, body: { rows: sanitized } };
    } catch (e) {
      return { status: 500, body: { error: (e as Error).message } };
    }
  }

  if (method === "POST" && path === "/api/hooks/dryrun") {
    const body = (req.body ?? {}) as { text?: unknown; source?: unknown; role?: unknown };
    if (typeof body.text !== "string" || body.text.length === 0) {
      return { status: 400, body: { error: "missing required field: text (non-empty string)" } };
    }
    const role = typeof body.role === "string" ? body.role : "user";
    const source = typeof body.source === "string" ? body.source : "api";

    const base = deps.config ?? loadConfig();
    const forced: HookConfig = {
      ...base,
      enabled: true,
      dryRun: true,
      allowedSources: new Set([...base.allowedSources, "api", "cli"]),
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
      source: source as HookEvent["source"],
      role: role as HookEvent["role"],
      content: body.text,
      session_id: "api-dryrun",
      project_slug: "api",
      ts: new Date().toISOString(),
    };
    const result = await pipeline.run(event);
    return {
      status: 200,
      body: {
        result,
        trace: trace.map((t) => {
          const p = JSON.parse(t.payload_json) as { layer: string; reason: string };
          return {
            layer: p.layer,
            reason: p.reason,
            redaction_count: t.redaction_count,
            kind: t.kind,
          };
        }),
      },
    };
  }

  return { status: 404, body: { error: `no route for ${method} ${path}` } };
}
