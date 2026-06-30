/**
 * src/providers/types.ts — Shared types + errors (T1).
 *
 * `HealthStatus` shape is consumed by both EmbeddingProvider.healthCheck()
 * and LLMProvider.healthCheck() — same contract on both sides keeps the
 * registry-level boot probe (T8) uniform.
 *
 * Errors are typed so the registry (T2) can surface clear messages and so
 * callers can distinguish "user config bug" from "transient backend issue"
 * without parsing error strings.
 */

/** Health probe shape. `ok=false` MUST also fill `error`. */
export interface HealthStatus {
  ok: boolean;
  /** Round-trip latency for the probe call. Optional when ok=false + no call made. */
  latencyMs?: number;
  /** Human-readable error message. REQUIRED when ok=false. Never contains API keys. */
  error?: string;
}

/** Thrown when an env API key is missing for the selected provider. */
export class MissingKeyError extends Error {
  public readonly providerName: string;
  public readonly envVar: string;
  constructor(providerName: string, envVar: string) {
    super(
      `MissingKeyError: provider "${providerName}" requires env var ${envVar} ` +
        `(currently unset or empty). Refusing to construct provider without credentials.`,
    );
    this.name = "MissingKeyError";
    this.providerName = providerName;
    this.envVar = envVar;
  }
}

/** Thrown when an unknown provider name is requested via env or factory arg. */
export class UnknownProviderError extends Error {
  public readonly requested: string;
  public readonly known: readonly string[];
  constructor(requested: string, known: readonly string[]) {
    super(
      `UnknownProviderError: provider "${requested}" not in known set ` +
        `[${known.join(", ")}]. Check NOX_*_PROVIDER env var.`,
    );
    this.name = "UnknownProviderError";
    this.requested = requested;
    this.known = known;
  }
}

/** Thrown by stub providers when actual work is invoked (vs healthCheck). */
export class NotImplementedError extends Error {
  public readonly providerName: string;
  constructor(providerName: string, op: string) {
    super(
      `NotImplementedError: provider "${providerName}" is a stub. ` +
        `Operation "${op}" is not implemented — interface conformance only. ` +
        `Implement when first user activates this provider (A3.1 follow-up).`,
    );
    this.name = "NotImplementedError";
    this.providerName = providerName;
  }
}

/** Thrown when a provider's healthCheck fails at boot AND fail-fast is enabled. */
export class ProviderHealthError extends Error {
  public readonly providerName: string;
  public readonly cause?: string;
  constructor(providerName: string, cause: string | undefined) {
    super(
      `ProviderHealthError: provider "${providerName}" failed health check at boot` +
        (cause ? ` (${cause})` : "") +
        `. Set NOX_PROVIDER_HEALTH_FAIL_FAST=0 to soft-warn instead.`,
    );
    this.name = "ProviderHealthError";
    this.providerName = providerName;
    this.cause = cause;
  }
}
