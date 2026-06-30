/**
 * src/lib/hooks/source-allowlist.ts — T2: Layer 2 of the privacy pipeline.
 *
 * Filters HookEvent by `source` AND `role`. Only events with:
 *   - source ∈ NOX_HOOK_SOURCES (default {openclaw})
 *   - role   ∈ {user, assistant}  (system/tool/unknown rejected by default)
 *
 * pass through. "unknown" source is ALWAYS rejected (it indicates the
 * event was constructed without explicit channel attribution — risk vector).
 *
 * No content access. No telemetry write here — pipeline (T6) records the
 * decision via the trace mechanism.
 */

import type { HookConfig } from "./config.js";
import type { CaptureDecision, HookEvent, HookRole } from "./types.js";

/** Roles we accept as conversation content. */
const ALLOWED_ROLES: ReadonlySet<HookRole> = new Set<HookRole>(["user", "assistant"]);

export interface SourceAllowlistOpts {
  /** Override allowed roles (tests only). */
  allowedRoles?: ReadonlySet<HookRole>;
}

/**
 * Evaluate Layer 2 against a HookEvent given the active config.
 * Pure function — safe to test in isolation.
 */
export function evaluateSourceAllowlist(
  event: HookEvent,
  config: HookConfig,
  opts: SourceAllowlistOpts = {},
): CaptureDecision {
  const roles = opts.allowedRoles ?? ALLOWED_ROLES;

  // Reject unknown source unconditionally — explicit attribution required.
  if (event.source === "unknown") {
    return {
      capture: false,
      reason: "source=unknown is never allowed (explicit channel attribution required)",
      layer: "source-allowlist",
    };
  }

  if (!config.allowedSources.has(event.source)) {
    return {
      capture: false,
      reason: `source=${event.source} not in NOX_HOOK_SOURCES allowlist`,
      layer: "source-allowlist",
    };
  }

  if (!roles.has(event.role)) {
    return {
      capture: false,
      reason: `role=${event.role} not in {user,assistant}`,
      layer: "source-allowlist",
    };
  }

  return {
    capture: true,
    reason: `source=${event.source} role=${event.role} allowed`,
    layer: "source-allowlist",
  };
}

/** Returns true if a given source string is recognized at all. */
export function isKnownSource(s: string): boolean {
  return ["openclaw", "cli", "manual", "mcp", "api", "unknown"].includes(s);
}
