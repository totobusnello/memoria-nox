/**
 * src/lib/hooks/pipeline.ts — T6: 5-layer orchestrator.
 *
 * Chains layers in load-bearing order:
 *
 *   Layer 1: env gate         (config.enabled)
 *   Layer 2: source allowlist (source-allowlist.ts)
 *   Layer 3: privacy filter   (privacy-filter-adapter.ts)
 *   Layer 4: classifier       (classifier.ts)
 *   Layer 5: rate-limit+dedup (rate-limit.ts)
 *
 * Decorator overrides (T10):
 *   - "@nox:skip" short-circuits at Layer 1 (before anything else)
 *   - "@nox:capture" bypasses Layer 4 (classifier) but NOT Layers 1/2/3/5
 *
 * Telemetry: emits one row per pipeline run via the injected telemetry
 * sink — captured OR rejected. NEVER includes raw content.
 *
 * Dry-run: when config.dryRun is true, the pipeline still runs through
 * every layer but does NOT call ingestFn at the end. Outcome reports
 * dry_run=true.
 */

import { loadConfig, type HookConfig } from "./config.js";
import { evaluateSourceAllowlist } from "./source-allowlist.js";
import { applyPrivacyFilter, type RedactFn, identityRedact } from "./privacy-filter-adapter.js";
import { applyClassifier } from "./classifier.js";
import { applyRateLimit, createState, type RateLimitState, type SimilarityFn } from "./rate-limit.js";
import { decoratorOverride, attachDecorators } from "./decorators.js";
import type {
  CaptureDecision,
  HookContext,
  HookEvent,
  HookResult,
  HookTelemetryRow,
  RejectionReason,
} from "./types.js";

/** ingestText sink — pipeline writes here on capture. */
export type IngestFn = (params: {
  text: string;
  source: string;
  session_id: string;
  project_slug: string;
  provenance: "hook";
  redaction_count: number;
  ts: string;
  event_id: string;
}) => Promise<{ chunk_id: number } | { chunk_id: null; error: string }>;

/** Telemetry sink — pipeline emits one row per event. */
export type TelemetrySink = (row: HookTelemetryRow) => void | Promise<void>;

export interface PipelineDeps {
  config?: HookConfig;
  redact?: RedactFn;
  similarity?: SimilarityFn;
  ingest?: IngestFn;
  telemetry?: TelemetrySink;
  /** Inject clock (tests). */
  now?: () => number;
  /** Inject llm classify (T4). */
  llmClassify?: (text: string) => { capture: boolean; reason: string };
}

export interface PipelineHandle {
  run(event: HookEvent): Promise<HookResult>;
  /** Reset internal rate-limit/dedup state (tests, manual). */
  resetState(): void;
  /** Exposed for inspection (CLI/HTTP status). */
  inspect(): {
    config: HookConfig;
    rateLimitTokens: number;
    recentBufferSize: number;
  };
}

const DEFAULT_TELEMETRY: TelemetrySink = () => {
  /* no-op */
};

const DEFAULT_INGEST: IngestFn = async () => ({ chunk_id: null, error: "no_ingest_configured" });

/**
 * Build a pipeline handle. Stateful: keeps a RateLimitState across calls.
 *
 * Each invocation runs the 5 layers in order. Every rejection emits ONE
 * telemetry row. A capture emits ONE telemetry row plus the ingest call.
 */
export function createPipeline(deps: PipelineDeps = {}): PipelineHandle {
  const config = deps.config ?? loadConfig();
  const redact = deps.redact ?? identityRedact;
  const ingest = deps.ingest ?? DEFAULT_INGEST;
  const telemetry = deps.telemetry ?? DEFAULT_TELEMETRY;
  const now = deps.now ?? Date.now;

  let rlState: RateLimitState = createState(config.rateLimitPerMin, now);

  async function emit(
    event: HookEvent,
    kind: HookTelemetryRow["kind"],
    layer: string,
    reason: string,
    redaction_count: number,
  ): Promise<void> {
    const row: HookTelemetryRow = {
      event_uuid: event.event_id,
      session_id: event.session_id ?? "unknown",
      project_slug: event.project_slug ?? "unknown",
      kind,
      timestamp: event.ts,
      payload_json: JSON.stringify({ layer, reason }),
      redaction_count,
      retention_days: 30,
    };
    try {
      await telemetry(row);
    } catch {
      /* telemetry errors must NEVER break the pipeline */
    }
  }

  function kindForEvent(_e: HookEvent): HookTelemetryRow["kind"] {
    // P2 spec §6.1 enum. Hook events arrive as user_prompt or tool_use most
    // commonly; pipeline doesn't currently distinguish — default tool_use.
    return "tool_use";
  }

  return {
    async run(rawEvent: HookEvent): Promise<HookResult> {
      const startMs = now();
      const event = attachDecorators(rawEvent);
      const ctx: HookContext = { event, trace: [] };

      function record(layer: string, dec: CaptureDecision): CaptureDecision {
        const t_ms = now() - startMs;
        ctx.trace.push({ layer, decision: { ...dec, layer }, t_ms });
        return dec;
      }

      async function reject(
        reasonCode: RejectionReason,
        layer: string,
        dec: CaptureDecision,
        redaction_count = 0,
      ): Promise<HookResult> {
        await emit(event, kindForEvent(event), layer, dec.reason, redaction_count);
        const result: HookResult = {
          captured: false,
          reason: reasonCode,
          layer,
          duration_ms: now() - startMs,
          dry_run: config.dryRun,
        };
        ctx.outcome = result;
        return result;
      }

      // ── Decorator early-skip (T10) ─────────────────────────────────────
      const override = decoratorOverride(event);
      if (override === "skip") {
        const dec: CaptureDecision = {
          capture: false,
          reason: "decorator @nox:skip",
          layer: "decorator",
        };
        record("decorator", dec);
        return reject("explicit_skip", "decorator", dec, 0);
      }

      // ── Layer 1: env gate ──────────────────────────────────────────────
      if (!config.enabled) {
        const dec: CaptureDecision = {
          capture: false,
          reason: "NOX_HOOKS_ENABLED!=1",
          layer: "env-gate",
        };
        record("env-gate", dec);
        return reject("env_disabled", "env-gate", dec, 0);
      }
      record("env-gate", { capture: true, reason: "enabled", layer: "env-gate" });

      // ── Layer 2: source allowlist ──────────────────────────────────────
      const l2 = evaluateSourceAllowlist(event, config);
      record("source-allowlist", l2);
      if (!l2.capture) return reject("source_not_allowed", "source-allowlist", l2, 0);

      // ── Layer 3: privacy filter ────────────────────────────────────────
      const l3 = applyPrivacyFilter(ctx, {
        redact,
        dropOnDetect: config.piiPolicy === "drop",
      });
      record("privacy-filter", l3);
      if (!l3.capture) {
        return reject("pii_detected_skip", "privacy-filter", l3, ctx.redacted?.redaction_count ?? 0);
      }

      // ── Layer 4: classifier (skippable via @nox:capture) ───────────────
      if (override === "capture") {
        record("classifier", {
          capture: true,
          reason: "decorator @nox:capture bypassed classifier",
          layer: "classifier",
        });
      } else {
        const l4 = applyClassifier(ctx, {
          minLength: config.minLength,
          llmFallback: config.llmClassify,
          ...(deps.llmClassify ? { llmClassify: deps.llmClassify } : {}),
        });
        record("classifier", l4);
        if (!l4.capture) {
          return reject(
            "classifier_low_signal",
            "classifier",
            l4,
            ctx.redacted?.redaction_count ?? 0,
          );
        }
      }

      // ── Layer 5: rate-limit + dedup ────────────────────────────────────
      const l5 = applyRateLimit(ctx, rlState, {
        capacityPerMin: config.rateLimitPerMin,
        dedupThreshold: config.dedupThreshold,
        ...(deps.similarity ? { similarity: deps.similarity } : {}),
        now,
      });
      record("rate-limit", l5);
      if (!l5.capture) {
        const code: RejectionReason = l5.reason.startsWith("dedup_hit") ? "dedup_hit" : "rate_limited";
        return reject(code, "rate-limit", l5, ctx.redacted?.redaction_count ?? 0);
      }

      // ── Persistence (Layer 6 implicit) ────────────────────────────────
      const redaction_count = ctx.redacted?.redaction_count ?? 0;
      if (config.dryRun) {
        await emit(event, kindForEvent(event), "persistence", "dry_run_skip", redaction_count);
        return {
          captured: false,
          reason: "dry_run",
          layer: "persistence",
          duration_ms: now() - startMs,
          dry_run: true,
        };
      }

      const ingestResult = await ingest({
        text: ctx.redacted?.text ?? event.content,
        source: event.source,
        session_id: event.session_id ?? "unknown",
        project_slug: event.project_slug ?? "unknown",
        provenance: "hook",
        redaction_count,
        ts: event.ts,
        event_id: event.event_id,
      });

      if (ingestResult.chunk_id === null) {
        await emit(
          event,
          kindForEvent(event),
          "persistence",
          `ingest_failed:${ingestResult.error}`,
          redaction_count,
        );
        return {
          captured: false,
          reason: "invalid_input",
          layer: "persistence",
          duration_ms: now() - startMs,
          dry_run: false,
        };
      }

      await emit(event, kindForEvent(event), "persistence", "ok", redaction_count);
      const ok: HookResult = {
        captured: true,
        reason: "ok",
        layer: "persisted",
        chunk_id: ingestResult.chunk_id,
        duration_ms: now() - startMs,
        dry_run: false,
      };
      ctx.outcome = ok;
      return ok;
    },

    resetState(): void {
      rlState = createState(config.rateLimitPerMin, now);
    },

    inspect() {
      return {
        config,
        rateLimitTokens: rlState.tokens,
        recentBufferSize: rlState.recent.length,
      };
    },
  };
}
