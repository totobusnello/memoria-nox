/**
 * src/lib/hooks/config.ts — T7: Env config loader + validator.
 *
 * Reads the following env vars (all OPT-IN — defaults are most-restrictive):
 *
 *   NOX_HOOKS_ENABLED       → "1" | "0"  (default "0" — Layer 1 gate is OFF)
 *   NOX_HOOK_SOURCES        → CSV of HookSource (default "openclaw")
 *   NOX_HOOK_RATE_LIMIT     → captures/min (default 30, min 1, max 1000)
 *   NOX_HOOK_DEDUP_THRESHOLD→ cosine threshold (default 0.95, range 0.5..0.999)
 *   NOX_HOOK_LLM_CLASSIFY   → "1" | "0" (default "0" — heuristics only)
 *   NOX_HOOK_DRY_RUN        → "1" | "0" (default "0")
 *   NOX_HOOK_QUEUE_SIZE     → worker queue max (default 10000)
 *   NOX_HOOK_MIN_LENGTH     → classifier min chars (default 20)
 *   NOX_HOOK_PII_POLICY     → "redact" | "drop"  (default "redact")
 *
 * Defensive: invalid values fall back to defaults + warn() to telemetry.
 */

import type { HookSource } from "./types.js";

export interface HookConfig {
  enabled: boolean;
  allowedSources: ReadonlySet<HookSource>;
  rateLimitPerMin: number;
  dedupThreshold: number;
  llmClassify: boolean;
  dryRun: boolean;
  queueSize: number;
  minLength: number;
  piiPolicy: "redact" | "drop";
}

export const DEFAULTS: HookConfig = Object.freeze({
  enabled: false,
  allowedSources: new Set<HookSource>(["openclaw"]),
  rateLimitPerMin: 30,
  dedupThreshold: 0.95,
  llmClassify: false,
  dryRun: false,
  queueSize: 10_000,
  minLength: 20,
  piiPolicy: "redact" as const,
});

const VALID_SOURCES = new Set<HookSource>([
  "openclaw",
  "cli",
  "manual",
  "mcp",
  "api",
  "unknown",
]);

/** Parse "1"/"true"/"yes" as true; everything else false. */
function parseBool(v: string | undefined, fallback: boolean): boolean {
  if (v === undefined) return fallback;
  const s = v.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(s)) return true;
  if (["0", "false", "no", "off", ""].includes(s)) return false;
  return fallback;
}

function parseInt0(v: string | undefined, fallback: number, lo: number, hi: number): number {
  if (v === undefined) return fallback;
  const n = Number.parseInt(v.trim(), 10);
  if (!Number.isFinite(n) || Number.isNaN(n)) return fallback;
  if (n < lo || n > hi) return fallback;
  return n;
}

function parseFloat0(v: string | undefined, fallback: number, lo: number, hi: number): number {
  if (v === undefined) return fallback;
  const n = Number.parseFloat(v.trim());
  if (!Number.isFinite(n) || Number.isNaN(n)) return fallback;
  if (n < lo || n > hi) return fallback;
  return n;
}

function parseSources(v: string | undefined, fallback: ReadonlySet<HookSource>): ReadonlySet<HookSource> {
  if (v === undefined || v.trim() === "") return fallback;
  const items = v.split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
  const out = new Set<HookSource>();
  for (const it of items) {
    if (VALID_SOURCES.has(it as HookSource)) out.add(it as HookSource);
  }
  if (out.size === 0) return fallback;
  return out;
}

function parsePolicy(v: string | undefined): "redact" | "drop" {
  if (v === undefined) return DEFAULTS.piiPolicy;
  const s = v.trim().toLowerCase();
  if (s === "drop") return "drop";
  return "redact";
}

/**
 * Build a HookConfig from process.env (or a passed-in env-like object for tests).
 */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): HookConfig {
  return Object.freeze({
    enabled: parseBool(env["NOX_HOOKS_ENABLED"], DEFAULTS.enabled),
    allowedSources: parseSources(env["NOX_HOOK_SOURCES"], DEFAULTS.allowedSources),
    rateLimitPerMin: parseInt0(env["NOX_HOOK_RATE_LIMIT"], DEFAULTS.rateLimitPerMin, 1, 1000),
    dedupThreshold: parseFloat0(env["NOX_HOOK_DEDUP_THRESHOLD"], DEFAULTS.dedupThreshold, 0.5, 0.999),
    llmClassify: parseBool(env["NOX_HOOK_LLM_CLASSIFY"], DEFAULTS.llmClassify),
    dryRun: parseBool(env["NOX_HOOK_DRY_RUN"], DEFAULTS.dryRun),
    queueSize: parseInt0(env["NOX_HOOK_QUEUE_SIZE"], DEFAULTS.queueSize, 100, 1_000_000),
    minLength: parseInt0(env["NOX_HOOK_MIN_LENGTH"], DEFAULTS.minLength, 1, 10_000),
    piiPolicy: parsePolicy(env["NOX_HOOK_PII_POLICY"]),
  });
}

/** Internal helper kept exported for tests. */
export const __test = { parseBool, parseInt0, parseFloat0, parseSources, parsePolicy };
