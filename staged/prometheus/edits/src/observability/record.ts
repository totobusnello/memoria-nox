/**
 * src/observability/record.ts — High-level recording API (T6).
 *
 * Convenience wrappers around the metric primitives. Callers in P1/A3/P5
 * should use these — NOT `counter.inc()` directly — so that:
 *   1. Cardinality + privacy guards are applied consistently.
 *   2. Future schema changes only touch one file.
 *   3. The recording is *fire-and-forget*: never throws, never blocks.
 *
 * All functions in this module catch + swallow errors. The hot path must
 * not be affected by observability failures.
 */

import {
  chunksTotal,
  embeddingsTotal,
  kgEntitiesTotal,
  kgRelationsTotal,
  searchRequestsTotal,
  searchDurationSeconds,
  searchResultsReturned,
  answerRequestsTotal,
  answerDurationSeconds,
  answerTokensTotal,
  providerCallsTotal,
  providerDurationSeconds,
  providerCostUsdTotal,
  providerTokensTotal,
  hooksEventsTotal,
  hooksPipelineDurationSeconds,
  viewerConnections,
  viewerEventsTotal,
  viewerDroppedTotal,
  auditRowsTotal,
} from "./metrics.js";
import { guardLabels } from "./privacy-guard.js";

// ─── helpers ─────────────────────────────────────────────────────────────────

function safe<T>(fn: () => T): T | undefined {
  try {
    return fn();
  } catch {
    return undefined;
  }
}

// ─── Search ──────────────────────────────────────────────────────────────────

export type SearchMethod = "cli" | "api" | "mcp";
export type SearchOutcome = "success" | "empty" | "error";

export function recordSearch(opts: {
  method: SearchMethod;
  durationSeconds: number;
  resultsCount: number;
  outcome: SearchOutcome;
}): void {
  safe(() => {
    const reqLabels = guardLabels("nox_search_requests_total", {
      method: opts.method,
      outcome: opts.outcome,
    }).labels;
    if (reqLabels) searchRequestsTotal.inc(reqLabels);
    const durLabels = guardLabels("nox_search_duration_seconds", {
      method: opts.method,
    }).labels;
    if (durLabels) searchDurationSeconds.observe(durLabels, opts.durationSeconds);
    const resLabels = guardLabels("nox_search_results_returned", {
      method: opts.method,
    }).labels;
    if (resLabels) searchResultsReturned.observe(resLabels, opts.resultsCount);
  });
}

// ─── Answer (P1) ─────────────────────────────────────────────────────────────

export type AnswerOutcome =
  | "success"
  | "no_chunks"
  | "llm_failed"
  | "hallucination"
  | "timeout"
  | "cost_cap";

export interface AnswerTiming {
  total?: number;
  retrieve?: number;
  rerank?: number;
  synthesize?: number;
  verify?: number;
}

export function recordAnswer(opts: {
  outcome: AnswerOutcome;
  timing: AnswerTiming;
  tokensIn?: number;
  tokensOut?: number;
}): void {
  safe(() => {
    const reqLabels = guardLabels("nox_answer_requests_total", {
      failure_reason: opts.outcome,
    }).labels;
    if (reqLabels) answerRequestsTotal.inc(reqLabels);

    for (const phase of [
      "total",
      "retrieve",
      "rerank",
      "synthesize",
      "verify",
    ] as const) {
      const v = opts.timing[phase];
      if (typeof v === "number" && Number.isFinite(v)) {
        const lbl = guardLabels("nox_answer_duration_seconds", { phase }).labels;
        if (lbl) answerDurationSeconds.observe(lbl, v);
      }
    }

    if (typeof opts.tokensIn === "number" && opts.tokensIn > 0) {
      const lbl = guardLabels("nox_answer_tokens_total", {
        direction: "input",
      }).labels;
      if (lbl) answerTokensTotal.inc(lbl, opts.tokensIn);
    }
    if (typeof opts.tokensOut === "number" && opts.tokensOut > 0) {
      const lbl = guardLabels("nox_answer_tokens_total", {
        direction: "output",
      }).labels;
      if (lbl) answerTokensTotal.inc(lbl, opts.tokensOut);
    }
  });
}

// ─── Provider (A3) ───────────────────────────────────────────────────────────

export type ProviderOutcome = "success" | "rate_limit" | "error" | "fallback";
export type ProviderKind = "embedding" | "llm";

export function recordProviderCall(opts: {
  provider: string;
  model: string;
  kind: ProviderKind;
  durationSeconds: number;
  outcome: ProviderOutcome;
  costUsd?: number;
  tokensIn?: number;
  tokensOut?: number;
}): void {
  safe(() => {
    const callLabels = guardLabels("nox_provider_calls_total", {
      provider: opts.provider,
      model: opts.model,
      outcome: opts.outcome,
    }).labels;
    if (callLabels) providerCallsTotal.inc(callLabels);

    const durLabels = guardLabels("nox_provider_duration_seconds", {
      provider: opts.provider,
      kind: opts.kind,
    }).labels;
    if (durLabels) providerDurationSeconds.observe(durLabels, opts.durationSeconds);

    if (typeof opts.costUsd === "number" && opts.costUsd > 0) {
      const lbl = guardLabels("nox_provider_cost_usd_total", {
        provider: opts.provider,
        model: opts.model,
      }).labels;
      if (lbl) providerCostUsdTotal.inc(lbl, opts.costUsd);
    }
    if (typeof opts.tokensIn === "number" && opts.tokensIn > 0) {
      const lbl = guardLabels("nox_provider_tokens_total", {
        provider: opts.provider,
        direction: "input",
      }).labels;
      if (lbl) providerTokensTotal.inc(lbl, opts.tokensIn);
    }
    if (typeof opts.tokensOut === "number" && opts.tokensOut > 0) {
      const lbl = guardLabels("nox_provider_tokens_total", {
        provider: opts.provider,
        direction: "output",
      }).labels;
      if (lbl) providerTokensTotal.inc(lbl, opts.tokensOut);
    }
  });
}

// ─── Pipeline ────────────────────────────────────────────────────────────────

export type ProvenanceKind = "fresh" | "stale" | "compiled" | "frontmatter" | "timeline";

export function recordChunkIngest(opts: {
  provenanceKind: ProvenanceKind;
  count?: number;
  redactionsApplied?: number;
}): void {
  safe(() => {
    const lbl = guardLabels("nox_chunks_total", {
      provenance_kind: opts.provenanceKind,
    }).labels;
    if (lbl) chunksTotal.inc(lbl, opts.count ?? 1);
  });
}

export function recordEmbedding(opts: {
  provider: string;
  outcome: "success" | "error";
  count?: number;
}): void {
  safe(() => {
    const lbl = guardLabels("nox_embeddings_total", {
      provider: opts.provider,
      outcome: opts.outcome,
    }).labels;
    if (lbl) embeddingsTotal.inc(lbl, opts.count ?? 1);
  });
}

export function recordKgEntity(opts: { type: string; count?: number }): void {
  safe(() => {
    const lbl = guardLabels("nox_kg_entities_total", {
      type: opts.type,
    }).labels;
    if (lbl) kgEntitiesTotal.inc(lbl, opts.count ?? 1);
  });
}

export function recordKgRelation(opts: { predicate: string; count?: number }): void {
  safe(() => {
    const lbl = guardLabels("nox_kg_relations_total", {
      predicate: opts.predicate,
    }).labels;
    if (lbl) kgRelationsTotal.inc(lbl, opts.count ?? 1);
  });
}

// ─── Hooks (P2) ──────────────────────────────────────────────────────────────

export function recordHookEvent(opts: {
  layer: string;
  reason: "captured" | "filtered" | "redacted" | "error" | "dropped";
  durationSeconds?: number;
}): void {
  safe(() => {
    const evtLabels = guardLabels("nox_hooks_events_total", {
      layer: opts.layer,
      reason: opts.reason,
    }).labels;
    if (evtLabels) hooksEventsTotal.inc(evtLabels);

    if (typeof opts.durationSeconds === "number") {
      const dur = guardLabels("nox_hooks_pipeline_duration_seconds", {
        layer: opts.layer,
      }).labels;
      if (dur) hooksPipelineDurationSeconds.observe(dur, opts.durationSeconds);
    }
  });
}

// ─── Viewer (P5) ─────────────────────────────────────────────────────────────

export function recordViewerConnect(): void {
  safe(() => viewerConnections.inc());
}

export function recordViewerDisconnect(): void {
  safe(() => viewerConnections.dec());
}

export function recordViewerEvent(type: string): void {
  safe(() => {
    const lbl = guardLabels("nox_viewer_events_total", { type }).labels;
    if (lbl) viewerEventsTotal.inc(lbl);
  });
}

export function recordViewerDropped(
  reason: "slow_consumer" | "queue_full" | "client_gone",
): void {
  safe(() => {
    const lbl = guardLabels("nox_viewer_dropped_total", { reason }).labels;
    if (lbl) viewerDroppedTotal.inc(lbl);
  });
}

// ─── Audit ───────────────────────────────────────────────────────────────────

export function recordAuditWrite(table: string, count = 1): void {
  safe(() => {
    const lbl = guardLabels("nox_audit_rows_total", { table }).labels;
    if (lbl) auditRowsTotal.inc(lbl, count);
  });
}

// ─── Timer helper ────────────────────────────────────────────────────────────

/**
 * Start a high-resolution timer that returns elapsed seconds when called.
 * Use:
 *   const end = startTimer();
 *   // ... work
 *   recordSearch({ method: "api", durationSeconds: end(), … });
 */
export function startTimer(): () => number {
  const start = process.hrtime.bigint();
  return () => Number(process.hrtime.bigint() - start) / 1e9;
}
