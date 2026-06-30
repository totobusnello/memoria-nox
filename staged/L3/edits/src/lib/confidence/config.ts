/**
 * src/lib/confidence/config.ts — Defaults + env overrides for L3.
 *
 * All confidence values clamped to [0, 1] (DB CHECK constraint).
 * Ranking mode defaults to "disabled" — CLAUDE.md regra #5 (no ranking
 * change without ≥+1.0pp nDCG@10 lift over R01a baseline + 7d shadow).
 *
 * Env overrides honoured:
 *   NOX_CONFIDENCE_OBSERVED            — default 0.95
 *   NOX_CONFIDENCE_DECLARED            — default 0.90
 *   NOX_CONFIDENCE_INFERRED            — default 0.65
 *   NOX_CONFIDENCE_DERIVED             — default 0.75
 *   NOX_CONFIDENCE_GRAPHIFY            — default 0.70
 *   NOX_CONFIDENCE_USER_CANONICAL      — default 1.00
 *   NOX_CONFIDENCE_USER_REFUTED        — default 0.05
 *   NOX_CONFIDENCE_ACTIVE_FLOOR        — default 0.30  (chunks below are skipped when active)
 *   NOX_RANKING_CONFIDENCE             — 'disabled' | 'shadow' | 'active' (default 'disabled')
 *   NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS — default -1 (disabled in v1)
 */

import type { ConfidenceConfig, RankingMode } from "./types.js";

export const DEFAULT_OBSERVED = 0.95;
export const DEFAULT_DECLARED = 0.9;
export const DEFAULT_INFERRED = 0.65;
export const DEFAULT_DERIVED = 0.75;
export const DEFAULT_GRAPHIFY = 0.7;
export const DEFAULT_USER_CANONICAL = 1.0;
export const DEFAULT_USER_REFUTED = 0.05;
export const DEFAULT_ACTIVE_FLOOR = 0.3;
export const DEFAULT_RANKING_MODE: RankingMode = "disabled";
export const DEFAULT_DECAY_HALFLIFE_DAYS = -1; // disabled in v1

function clamp01(v: number): number {
  if (Number.isNaN(v)) return 0;
  if (v === Infinity) return 1;
  if (v === -Infinity) return 0;
  return Math.min(1, Math.max(0, v));
}

function parseEnvFloat(name: string, fallback: number, lo = 0, hi = 1): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = parseFloat(raw);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(hi, Math.max(lo, parsed));
}

function parseEnvInt(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) return fallback;
  const parsed = parseInt(raw, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return parsed;
}

function parseRankingMode(raw: string | undefined): RankingMode {
  if (!raw) return DEFAULT_RANKING_MODE;
  const norm = raw.trim().toLowerCase();
  if (norm === "disabled" || norm === "off") return "disabled";
  if (norm === "shadow") return "shadow";
  if (norm === "active" || norm === "on") return "active";
  return DEFAULT_RANKING_MODE;
}

/**
 * resolveConfig() — env-overridable defaults.
 * Caller may pass partial overrides which take precedence over env.
 */
export function resolveConfig(
  overrides: Partial<ConfidenceConfig> = {}
): ConfidenceConfig {
  const cfg: ConfidenceConfig = {
    default_observed:
      overrides.default_observed ??
      parseEnvFloat("NOX_CONFIDENCE_OBSERVED", DEFAULT_OBSERVED),
    default_declared:
      overrides.default_declared ??
      parseEnvFloat("NOX_CONFIDENCE_DECLARED", DEFAULT_DECLARED),
    default_inferred:
      overrides.default_inferred ??
      parseEnvFloat("NOX_CONFIDENCE_INFERRED", DEFAULT_INFERRED),
    default_derived:
      overrides.default_derived ??
      parseEnvFloat("NOX_CONFIDENCE_DERIVED", DEFAULT_DERIVED),
    default_graphify:
      overrides.default_graphify ??
      parseEnvFloat("NOX_CONFIDENCE_GRAPHIFY", DEFAULT_GRAPHIFY),
    user_marked_canonical:
      overrides.user_marked_canonical ??
      parseEnvFloat("NOX_CONFIDENCE_USER_CANONICAL", DEFAULT_USER_CANONICAL),
    user_marked_refuted:
      overrides.user_marked_refuted ??
      parseEnvFloat("NOX_CONFIDENCE_USER_REFUTED", DEFAULT_USER_REFUTED),
    active_floor:
      overrides.active_floor ??
      parseEnvFloat("NOX_CONFIDENCE_ACTIVE_FLOOR", DEFAULT_ACTIVE_FLOOR),
    ranking_mode:
      overrides.ranking_mode ??
      parseRankingMode(process.env.NOX_RANKING_CONFIDENCE),
    decay_halflife_days:
      overrides.decay_halflife_days ??
      parseEnvInt(
        "NOX_CONFIDENCE_DECAY_HALFLIFE_DAYS",
        DEFAULT_DECAY_HALFLIFE_DAYS
      ),
  };

  // Defensive clamp on all confidence-value fields (DB CHECK is final guard).
  cfg.default_observed = clamp01(cfg.default_observed);
  cfg.default_declared = clamp01(cfg.default_declared);
  cfg.default_inferred = clamp01(cfg.default_inferred);
  cfg.default_derived = clamp01(cfg.default_derived);
  cfg.default_graphify = clamp01(cfg.default_graphify);
  cfg.user_marked_canonical = clamp01(cfg.user_marked_canonical);
  cfg.user_marked_refuted = clamp01(cfg.user_marked_refuted);
  cfg.active_floor = clamp01(cfg.active_floor);

  return cfg;
}

export { clamp01 };
