/**
 * src/lib/hooks/rate-limit.ts — T5: Layer 5 of pipeline.
 *
 * Two protections combined:
 *   1. Token-bucket rate limit (default 30 captures/min, configurable via
 *      NOX_HOOK_RATE_LIMIT). Refills 1 token every (60/N) seconds.
 *   2. Near-duplicate dedup via cosine similarity on a lightweight
 *      character-shingle vector (no embeddings required — keeps Layer 5
 *      independent of embedding provider availability).
 *
 * Dedup keeps a ring buffer of the last 10 redacted texts; if cosine
 * (new vs any in ring) > NOX_HOOK_DEDUP_THRESHOLD (default 0.95), reject.
 *
 * Note on cosine choice: full Gemini embedding cosine would be ideal but
 * Layer 5 must NOT depend on network/embedding latency (it's the last
 * gate before persistence). Char-shingle cosine is fast + decent for
 * near-identical detection (e.g., "rerun the same command" duplicates).
 * Upstream callers can swap the similarity fn via DI if a real embedder
 * is desired (e.g., from cached chunks).
 */

import type { CaptureDecision, HookContext } from "./types.js";

/** Pluggable similarity. Default = char-shingle cosine. */
export type SimilarityFn = (a: string, b: string) => number;

export interface RateLimitState {
  /** Tokens available (float). */
  tokens: number;
  /** Last refill timestamp (ms epoch). */
  lastRefillMs: number;
  /** Ring buffer of recent redacted texts. */
  recent: string[];
}

export interface RateLimitOpts {
  /** Captures-per-minute capacity. Default 30. */
  capacityPerMin?: number;
  /** Cosine threshold for dedup (rejects if >threshold). Default 0.95. */
  dedupThreshold?: number;
  /** Ring buffer size. Default 10. */
  ringSize?: number;
  /** Pluggable similarity. Default charShingleCosine. */
  similarity?: SimilarityFn;
  /** Inject clock for tests. */
  now?: () => number;
}

/**
 * Build a fresh empty state with full bucket.
 */
export function createState(capacity: number, now: () => number = Date.now): RateLimitState {
  return {
    tokens: capacity,
    lastRefillMs: now(),
    recent: [],
  };
}

/** Default: character 3-shingle cosine. */
export function charShingleCosine(a: string, b: string): number {
  if (a.length === 0 || b.length === 0) return 0;
  if (a === b) return 1;
  const shA = shingle(a, 3);
  const shB = shingle(b, 3);
  let dot = 0;
  let magA = 0;
  let magB = 0;
  for (const [k, va] of shA) {
    magA += va * va;
    const vb = shB.get(k) ?? 0;
    if (vb !== 0) dot += va * vb;
  }
  for (const vb of shB.values()) magB += vb * vb;
  if (magA === 0 || magB === 0) return 0;
  return dot / (Math.sqrt(magA) * Math.sqrt(magB));
}

function shingle(s: string, n: number): Map<string, number> {
  const m = new Map<string, number>();
  if (s.length < n) {
    m.set(s, 1);
    return m;
  }
  for (let i = 0; i <= s.length - n; i++) {
    const k = s.slice(i, i + n);
    m.set(k, (m.get(k) ?? 0) + 1);
  }
  return m;
}

/**
 * Refill token bucket based on elapsed wall-clock since last refill.
 */
function refill(state: RateLimitState, capacityPerMin: number, now: () => number): void {
  const t = now();
  const elapsedMs = t - state.lastRefillMs;
  if (elapsedMs <= 0) return;
  const refillRatePerMs = capacityPerMin / 60_000;
  const add = elapsedMs * refillRatePerMs;
  state.tokens = Math.min(capacityPerMin, state.tokens + add);
  state.lastRefillMs = t;
}

/**
 * Evaluate Layer 5 against a HookContext, updating the passed-in state.
 * State must be threaded by the pipeline (singleton per worker).
 */
export function applyRateLimit(
  ctx: HookContext,
  state: RateLimitState,
  opts: RateLimitOpts = {},
): CaptureDecision {
  const capacity = opts.capacityPerMin ?? 30;
  const threshold = opts.dedupThreshold ?? 0.95;
  const ringSize = opts.ringSize ?? 10;
  const sim = opts.similarity ?? charShingleCosine;
  const now = opts.now ?? Date.now;

  refill(state, capacity, now);

  // Dedup check (cosine) before consuming a token — dedup hits should NOT
  // count against rate-limit.
  const text = ctx.redacted?.text ?? ctx.event.content;
  for (const prev of state.recent) {
    const c = sim(text, prev);
    if (c > threshold) {
      return {
        capture: false,
        reason: `dedup_hit cosine=${c.toFixed(3)} threshold=${threshold}`,
        layer: "rate-limit",
        score: c,
      };
    }
  }

  // Rate-limit
  if (state.tokens < 1) {
    return {
      capture: false,
      reason: `rate_limited tokens=${state.tokens.toFixed(2)} capacity=${capacity}/min`,
      layer: "rate-limit",
    };
  }

  // Consume + push to ring
  state.tokens -= 1;
  state.recent.push(text);
  if (state.recent.length > ringSize) state.recent.shift();

  return {
    capture: true,
    reason: `ok tokens_remaining=${state.tokens.toFixed(2)}`,
    layer: "rate-limit",
  };
}
