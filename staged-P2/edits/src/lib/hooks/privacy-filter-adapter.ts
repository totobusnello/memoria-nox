/**
 * src/lib/hooks/privacy-filter-adapter.ts — T3: Layer 3 of pipeline.
 *
 * Wraps staged-A1 `redact()` (13 patterns, 68 tests, 1.7% FP) so the
 * pipeline (T6) can call a stable local interface even if the upstream
 * A1 contract evolves.
 *
 * Contract (locked, mirrors staged-privacy/edits/privacy/filter.ts):
 *
 *   redact(rawText: string): {
 *     text: string;            // potentially with `<private>` markers replacing PII
 *     redactionCount: number;  // total matches replaced
 *     kinds: string[];         // deduped pattern names
 *   }
 *
 * Layer 3 ALWAYS redacts (default policy). If NOX_HOOK_PII_POLICY=drop,
 * the pipeline (T6) will reject when redaction_count > 0 — but THIS module
 * never drops; it only transforms.
 *
 * Telemetry: this module emits ZERO content; it returns metadata so the
 * pipeline can log layer name + reason + counts.
 */

import type { CaptureDecision, HookContext } from "./types.js";

/** Shape of the upstream A1 redact() result (locked). */
export interface A1RedactResult {
  text: string;
  redactionCount: number;
  kinds: string[];
}

/** Pluggable redact() signature — defaults to staged-A1 import at wire-up. */
export type RedactFn = (rawText: string) => A1RedactResult;

/**
 * Default redact() — identity function pre-T11 swap.
 * Production wiring imports the real `redact` from staged-A1
 * (see staged-privacy/edits/privacy/filter.ts).
 *
 * The pipeline (T6) accepts a custom RedactFn via DI so tests don't need
 * the real regex pack.
 */
export const identityRedact: RedactFn = (rawText: string): A1RedactResult => ({
  text: rawText,
  redactionCount: 0,
  kinds: [],
});

export interface PrivacyAdapterOpts {
  /** Redact implementation. Default = identityRedact. */
  redact?: RedactFn;
  /** When true, treat any redaction_count>0 as a drop signal. Default false. */
  dropOnDetect?: boolean;
}

/**
 * Apply Layer 3 to a HookContext.
 * Mutates ctx.redacted with the result.
 *
 * Returns:
 *   capture=true  → forward to Layer 4 with redacted text
 *   capture=false → drop (only when dropOnDetect && redactionCount > 0)
 */
export function applyPrivacyFilter(
  ctx: HookContext,
  opts: PrivacyAdapterOpts = {},
): CaptureDecision {
  const redact = opts.redact ?? identityRedact;
  const dropOnDetect = opts.dropOnDetect ?? false;

  let result: A1RedactResult;
  try {
    result = redact(ctx.event.content);
  } catch (e) {
    // Defensive: if A1 throws, drop the event to fail closed.
    return {
      capture: false,
      reason: `A1 redact threw: ${(e as Error).message || "unknown"}`,
      layer: "privacy-filter",
    };
  }

  ctx.redacted = {
    text: result.text,
    redaction_count: result.redactionCount,
    kinds: result.kinds.slice(),
  };

  if (dropOnDetect && result.redactionCount > 0) {
    return {
      capture: false,
      reason: `pii_detected redactions=${result.redactionCount} kinds=[${result.kinds.join("|")}] policy=drop`,
      layer: "privacy-filter",
    };
  }

  if (result.redactionCount > 0) {
    // Log redaction in trace but continue.
    return {
      capture: true,
      reason: `redacted=${result.redactionCount} kinds=[${result.kinds.join("|")}] policy=redact`,
      layer: "privacy-filter",
    };
  }

  return {
    capture: true,
    reason: "no_pii_detected",
    layer: "privacy-filter",
  };
}
