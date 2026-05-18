/**
 * A2.1 T3 — Enforce passphrase entropy.
 *
 * Default: throws `WeakPassphraseError` if entropy tier < `good` (≥50 bits).
 *
 * Override paths (require EXPLICIT consent):
 *   - `opts.allow_weak: true` (caller-provided, programmatic)
 *   - `NOX_A2_ALLOW_WEAK_PASSPHRASE=1` env var
 *   - CLI `--allow-weak` flag (wired into export.ts)
 *
 * When the override is active we emit a single-line WARN to stderr (via the
 * injectable `log` sink) so operators in CI logs notice. Silent override is
 * never offered.
 *
 * Threat-model ref: docs/security/THREAT-MODEL.md §5.2 T-A2-1 / Gap G1.
 */

import {
  DEFAULT_MIN_STRENGTH,
  DEFAULT_THRESHOLDS,
  meetsMinimumStrength,
  PassphraseStrength,
  StrengthThresholds,
  strengthOfPassphrase,
} from "./strength.js";

export class WeakPassphraseError extends Error {
  public readonly bits: number;
  public readonly tier: PassphraseStrength;
  public readonly required: PassphraseStrength;

  constructor(opts: {
    bits: number;
    tier: PassphraseStrength;
    required: PassphraseStrength;
    message?: string;
  }) {
    const base =
      opts.message ??
      `Passphrase too weak: ${opts.tier} (~${opts.bits.toFixed(
        0,
      )} bits). Minimum required: ${opts.required}. ` +
        `Pass --allow-weak or NOX_A2_ALLOW_WEAK_PASSPHRASE=1 to override (NOT recommended).`;
    super(base);
    this.name = "WeakPassphraseError";
    this.bits = opts.bits;
    this.tier = opts.tier;
    this.required = opts.required;
  }
}

export interface EnforcePassphraseOpts {
  /** Minimum strength tier required. Default: `good` (≥50 bits). */
  minStrength?: PassphraseStrength;
  /** Programmatic opt-out — caller has already shown the warning. */
  allow_weak?: boolean;
  /** Env source (defaults to process.env). */
  env?: Record<string, string | undefined>;
  /** Log sink for the WARN line. Defaults to console.error. */
  log?: (msg: string) => void;
  /** Custom thresholds (only for tests / advanced calibration). */
  thresholds?: StrengthThresholds;
}

export interface EnforceResult {
  bits: number;
  tier: PassphraseStrength;
  required: PassphraseStrength;
  bypassed: boolean;
  bypass_reason: "cli_flag" | "env_var" | null;
}

/**
 * Throws `WeakPassphraseError` if `passphrase` strength tier is below `minStrength`
 * AND no override is active. Returns the assessed strength on success or bypass.
 *
 * NEVER logs the passphrase — only the tier + bit count.
 */
export function enforcePassphraseStrength(
  passphrase: string,
  opts: EnforcePassphraseOpts = {},
): EnforceResult {
  if (typeof passphrase !== "string" || passphrase.length === 0) {
    throw new WeakPassphraseError({
      bits: 0,
      tier: "weak",
      required: opts.minStrength ?? DEFAULT_MIN_STRENGTH,
      message: "Passphrase is empty.",
    });
  }
  const required = opts.minStrength ?? DEFAULT_MIN_STRENGTH;
  const thresholds = opts.thresholds ?? DEFAULT_THRESHOLDS;
  const { bits, tier } = strengthOfPassphrase(passphrase, thresholds);

  if (meetsMinimumStrength(tier, required)) {
    return { bits, tier, required, bypassed: false, bypass_reason: null };
  }

  const env = opts.env ?? process.env;
  const envOverride = env.NOX_A2_ALLOW_WEAK_PASSPHRASE === "1";
  const log = opts.log ?? ((m: string) => process.stderr.write(m + "\n"));

  if (opts.allow_weak === true) {
    log(
      `WARN: weak passphrase accepted via --allow-weak (tier=${tier}, ` +
        `~${bits.toFixed(0)} bits). Required=${required}. ` +
        `THIS IS NOT RECOMMENDED FOR PRODUCTION ARCHIVES.`,
    );
    return { bits, tier, required, bypassed: true, bypass_reason: "cli_flag" };
  }
  if (envOverride) {
    log(
      `WARN: weak passphrase accepted via NOX_A2_ALLOW_WEAK_PASSPHRASE=1 ` +
        `(tier=${tier}, ~${bits.toFixed(0)} bits). Required=${required}. ` +
        `THIS IS NOT RECOMMENDED FOR PRODUCTION ARCHIVES.`,
    );
    return { bits, tier, required, bypassed: true, bypass_reason: "env_var" };
  }

  throw new WeakPassphraseError({ bits, tier, required });
}
