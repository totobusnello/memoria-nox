/**
 * A2.1 T2 — Passphrase strength tiers.
 *
 * Maps entropy bits → discrete tier so UX (and policy decisions) can be made
 * without forcing the caller to reason about bit numbers.
 *
 * Thresholds (bits) — calibrated against COMMON_PASSWORDS rejection rates +
 * scrypt N=2^17 brute-force economics (~0.5–1s per guess on a modern laptop):
 *
 *   weak   <30      → 1 GPU × 24h breaks "password123"-class words
 *   fair   30–<50   → 1 GPU × weeks breaks; OK for short-lived secrets only
 *   good   50–<70   → 1 GPU × years; the default required tier
 *   strong ≥70      → 1 GPU × decades; recommended for archives kept >12 mo
 *
 * Threat-model ref: docs/security/THREAT-MODEL.md §5.2 T-A2-1 / Gap G1.
 */

import { estimateEntropyBits } from "./entropy.js";

export type PassphraseStrength = "weak" | "fair" | "good" | "strong";

export interface StrengthThresholds {
  weak_max: number; // exclusive upper bound for `weak`
  fair_max: number;
  good_max: number;
  // anything ≥ good_max is `strong`
}

/** Default strength thresholds — locked unless A2.2 revisits. */
export const DEFAULT_THRESHOLDS: StrengthThresholds = {
  weak_max: 30,
  fair_max: 50,
  good_max: 70,
};

/** Default minimum tier required by enforcement. */
export const DEFAULT_MIN_STRENGTH: PassphraseStrength = "good";

/** Tier order — used for compare. */
const ORDER: Record<PassphraseStrength, number> = {
  weak: 0,
  fair: 1,
  good: 2,
  strong: 3,
};

export function strengthFromBits(
  bits: number,
  thresholds: StrengthThresholds = DEFAULT_THRESHOLDS,
): PassphraseStrength {
  if (bits < thresholds.weak_max) return "weak";
  if (bits < thresholds.fair_max) return "fair";
  if (bits < thresholds.good_max) return "good";
  return "strong";
}

export function strengthOfPassphrase(
  passphrase: string,
  thresholds: StrengthThresholds = DEFAULT_THRESHOLDS,
): { bits: number; tier: PassphraseStrength } {
  const bits = estimateEntropyBits(passphrase);
  const tier = strengthFromBits(bits, thresholds);
  return { bits, tier };
}

/**
 * True when `actual` meets or exceeds `required`.
 * `compareStrength('good', 'fair')`  → true
 * `compareStrength('fair', 'good')`  → false
 */
export function meetsMinimumStrength(
  actual: PassphraseStrength,
  required: PassphraseStrength,
): boolean {
  return ORDER[actual] >= ORDER[required];
}

/**
 * Render a textual strength meter for terminal stderr.
 *
 *   weak   → [=>      ]  WEAK    (bits)
 *   fair   → [==>     ]  FAIR    (bits)
 *   good   → [====>   ]  GOOD    (bits)
 *   strong → [========]  STRONG  (bits)
 */
export function renderStrengthMeter(opts: {
  bits: number;
  tier: PassphraseStrength;
  width?: number;
}): string {
  const width = opts.width ?? 8;
  const filledBy: Record<PassphraseStrength, number> = {
    weak: 1,
    fair: 3,
    good: 5,
    strong: width,
  };
  const filled = filledBy[opts.tier];
  const empty = Math.max(0, width - filled);
  const arrow = opts.tier === "strong" ? "" : ">";
  const bar = "=".repeat(Math.max(0, filled - 1)) + arrow + " ".repeat(empty);
  const label = opts.tier.toUpperCase().padEnd(6, " ");
  return `[${bar}] ${label} (~${opts.bits.toFixed(0)} bits)`;
}
