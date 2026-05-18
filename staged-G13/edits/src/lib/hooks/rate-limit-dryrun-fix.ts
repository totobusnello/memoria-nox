/**
 * G13 — Rate limit for `POST /api/hooks/dryrun` (Wave G)
 *
 * Background:
 *   `POST /api/hooks/dryrun` intentionally bypasses the capture rate limit
 *   (a separate token bucket for actual ingestion). This lets ops/dev test
 *   classifier output freely.
 *
 *   But: it also lets an attacker probe the classifier filter (privacy
 *   patterns, PII detection, redaction layers) at unlimited speed — an
 *   oracle that can be used to fingerprint or evade A1 patterns.
 *
 * Fix:
 *   Per-IP token bucket sized via `NOX_HOOK_DRYRUN_RATE_LIMIT` (default
 *   10 req/min). Refills at `rate / 60` tokens per second. Buckets are
 *   process-local (no shared state — single-tenant assumption per
 *   `THREAT-MODEL.md §12.1`).
 *
 * Does NOT affect:
 *   - The capture rate-limit token bucket (separate, configured via
 *     `HookConfig.rateLimitPerMin`).
 *   - GET endpoints (status, recent) — those are read-only metadata.
 *
 * Refs:
 *   - PR #58 §14 G13.
 *   - THREAT-MODEL.md §7.7 T-P2-2.
 */

export interface DryrunRateLimitConfig {
  /** Requests per minute per IP. Default 10. */
  perMinute: number;
  /** Override: bucket capacity (defaults to perMinute). */
  burstCapacity?: number;
}

export function readDryrunRateLimitConfig(
  env: NodeJS.ProcessEnv = process.env,
): DryrunRateLimitConfig {
  const raw = env.NOX_HOOK_DRYRUN_RATE_LIMIT;
  const n = raw ? Number.parseInt(raw, 10) : NaN;
  const perMinute = Number.isFinite(n) && n > 0 ? n : 10;
  return { perMinute };
}

// ── token bucket ────────────────────────────────────────────────────────────

interface Bucket {
  tokens: number;
  lastRefillMs: number;
}

export interface DryrunRateLimiter {
  /** Attempt to consume 1 token. Returns true if allowed. */
  tryConsume(ip: string, nowMs?: number): boolean;
  /** Refill all buckets up to `nowMs`. Pure helper for tests. */
  refillAll(nowMs?: number): void;
  /** Snapshot for telemetry. */
  snapshot(): Array<{ ip: string; tokens: number; lastRefillMs: number }>;
  /** Reset (test helper). */
  clear(): void;
}

export function createDryrunRateLimiter(
  cfg: DryrunRateLimitConfig = readDryrunRateLimitConfig(),
): DryrunRateLimiter {
  const buckets = new Map<string, Bucket>();
  const capacity = cfg.burstCapacity ?? cfg.perMinute;
  const refillPerMs = cfg.perMinute / 60_000;

  const refill = (b: Bucket, nowMs: number): void => {
    const elapsed = Math.max(0, nowMs - b.lastRefillMs);
    if (elapsed === 0) return;
    const add = elapsed * refillPerMs;
    if (add <= 0) return;
    b.tokens = Math.min(capacity, b.tokens + add);
    b.lastRefillMs = nowMs;
  };

  return {
    tryConsume(ip: string, nowMs: number = Date.now()): boolean {
      let b = buckets.get(ip);
      if (!b) {
        b = { tokens: capacity, lastRefillMs: nowMs };
        buckets.set(ip, b);
      } else {
        refill(b, nowMs);
      }
      if (b.tokens >= 1) {
        b.tokens -= 1;
        return true;
      }
      return false;
    },
    refillAll(nowMs: number = Date.now()): void {
      for (const b of buckets.values()) refill(b, nowMs);
    },
    snapshot() {
      return Array.from(buckets.entries()).map(([ip, b]) => ({
        ip,
        tokens: b.tokens,
        lastRefillMs: b.lastRefillMs,
      }));
    },
    clear(): void {
      buckets.clear();
    },
  };
}

// ── handler integration helper ──────────────────────────────────────────────

export interface DryrunGateResult {
  allowed: boolean;
  /** HTTP response when rejected. */
  rejectResponse?: {
    status: 429;
    headers: Record<string, string>;
    body: { error: "rate_limited"; reason: "dryrun_per_ip"; retry_after_seconds: number };
  };
}

/**
 * Gate helper for `POST /api/hooks/dryrun`. Caller (hooks API handler)
 * wraps the existing dryrun branch with:
 *
 *   const gate = checkDryrunGate(limiter, req.ip);
 *   if (!gate.allowed) return gate.rejectResponse;
 *   // ... existing dryrun logic ...
 */
export function checkDryrunGate(
  limiter: DryrunRateLimiter,
  ip: string,
  cfg: DryrunRateLimitConfig = readDryrunRateLimitConfig(),
): DryrunGateResult {
  if (limiter.tryConsume(ip)) {
    return { allowed: true };
  }
  // Retry-After: roughly time to next token (60s / perMinute).
  const retryAfterSeconds = Math.max(1, Math.ceil(60 / cfg.perMinute));
  return {
    allowed: false,
    rejectResponse: {
      status: 429,
      headers: {
        "Content-Type": "application/json; charset=utf-8",
        "Retry-After": String(retryAfterSeconds),
        "Cache-Control": "no-store",
      },
      body: {
        error: "rate_limited",
        reason: "dryrun_per_ip",
        retry_after_seconds: retryAfterSeconds,
      },
    },
  };
}
