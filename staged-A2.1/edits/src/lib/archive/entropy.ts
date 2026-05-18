/**
 * A2.1 T1 — Lightweight entropy estimator (zxcvbn-inspired, zero-dep).
 *
 * Real zxcvbn(-ts) is the gold standard but adds ~700 KB and a transitive dep.
 * For A2.1 we use a deterministic, fully-local heuristic:
 *
 *   1) Build the effective character set: pools enabled if at least one char
 *      present (lowercase 26, uppercase 26, digits 10, symbols 32, unicode
 *      "other" 256 per non-ASCII char observed up to a cap).
 *   2) Raw entropy = length × log2(poolSize).
 *   3) Penalties:
 *        - exact match in COMMON_PASSWORDS → cap to 10 bits regardless.
 *        - substring match in COMMON_PASSWORDS (length ≥4) → −25 bits.
 *        - >60% repeated chars → −15 bits.
 *        - sequential runs of ≥4 ("1234", "abcd", "qwer") → −10 bits per run.
 *        - keyboard rows ("qwerty", "asdf", "zxcv") of length ≥4 → −10 bits.
 *        - only digits, length ≤8 → cap to log2(10) × length (no bonus).
 *   4) Bonus:
 *        - length ≥20 → +5 bits (proxy for diceware-style passphrases).
 *        - length ≥30 → +10 bits.
 *
 * NOT a security oracle. It's a conservative estimator: when uncertain it
 * UNDER-estimates so that enforcement defaults to safer rejections.
 *
 * Threat-model ref: docs/security/THREAT-MODEL.md §5.2 T-A2-1 / Gap G1.
 */

import {
  containsCommonSubstring,
  isCommonPassword,
} from "./common-passwords.js";

// — Pool sizes (rough char-class counts) —
const POOL_LOWER = 26;
const POOL_UPPER = 26;
const POOL_DIGIT = 10;
// Printable ASCII symbols excluding space (~32 printable special chars).
const POOL_SYMBOL = 32;
// For each unique non-ASCII char we add 256 — this caps at 4096 (16 chars).
const POOL_NON_ASCII_PER_CHAR = 256;
const NON_ASCII_CAP = 16;

const HAS_LOWER = /[a-z]/;
const HAS_UPPER = /[A-Z]/;
const HAS_DIGIT = /[0-9]/;
const HAS_SYMBOL = /[!-/:-@[-`{-~]/; // printable ASCII non-alphanumerics
const NON_ASCII = /[^\x00-\x7f]/;

/** Common keyboard "row" sequences that should not contribute to entropy. */
const KEYBOARD_ROWS: ReadonlyArray<string> = [
  "qwertyuiop",
  "asdfghjkl",
  "zxcvbnm",
  "1234567890",
  "0987654321",
  "qwerty",
  "asdfgh",
  "zxcvbn",
  "azerty",
  "qazwsx",
];

/** Alphabet/sequence runs used to detect ascending/descending tracks. */
const SEQUENCE_RUNS: ReadonlyArray<string> = [
  "abcdefghijklmnopqrstuvwxyz",
  "zyxwvutsrqponmlkjihgfedcba",
  "0123456789",
  "9876543210",
];

/**
 * Estimate entropy bits for `passphrase`. Returns a non-negative number;
 * 0 indicates "essentially predictable".
 *
 * For tests + UX you usually want `strengthFromBits()` (see strength.ts)
 * rather than the raw number.
 */
export function estimateEntropyBits(passphrase: string): number {
  if (typeof passphrase !== "string") return 0;
  if (passphrase.length === 0) return 0;

  // Exact-match shortcut.
  const lower = passphrase.toLowerCase();
  if (isCommonPassword(lower)) {
    // Cap at 10 bits regardless. A long well-known password is still well-known.
    return Math.min(10, passphrase.length);
  }

  // — Build pool —
  let pool = 0;
  if (HAS_LOWER.test(passphrase)) pool += POOL_LOWER;
  if (HAS_UPPER.test(passphrase)) pool += POOL_UPPER;
  if (HAS_DIGIT.test(passphrase)) pool += POOL_DIGIT;
  if (HAS_SYMBOL.test(passphrase)) pool += POOL_SYMBOL;
  if (NON_ASCII.test(passphrase)) {
    const uniqNonAscii = new Set(
      Array.from(passphrase).filter((c) => NON_ASCII.test(c)),
    );
    const n = Math.min(NON_ASCII_CAP, uniqNonAscii.size);
    pool += n * POOL_NON_ASCII_PER_CHAR;
  }
  if (pool === 0) return 0;

  // Code-point length (correct handling of surrogate pairs, emoji, etc).
  const cpLength = Array.from(passphrase).length;
  let bits = cpLength * Math.log2(pool);

  // — Penalties —
  if (containsCommonSubstring(lower)) {
    bits -= 25;
  }

  const repeatPenalty = repeatedCharPenalty(passphrase);
  bits -= repeatPenalty;

  const seqPenalty = sequenceRunPenalty(lower);
  bits -= seqPenalty;

  const kbPenalty = keyboardRowPenalty(lower);
  bits -= kbPenalty;

  // Digit-only cap: short PINs should never be considered strong.
  if (/^[0-9]+$/.test(passphrase) && passphrase.length <= 8) {
    bits = Math.min(bits, Math.log2(POOL_DIGIT) * passphrase.length);
  }

  // — Length bonus —
  if (cpLength >= 20) bits += 5;
  if (cpLength >= 30) bits += 10;

  return Math.max(0, bits);
}

/**
 * Penalty for repeated characters. Returns bits to subtract.
 * Highest single-char fraction; if >60% of the string is one char, penalise.
 */
function repeatedCharPenalty(s: string): number {
  if (s.length === 0) return 0;
  const counts = new Map<string, number>();
  for (const ch of s) {
    counts.set(ch, (counts.get(ch) ?? 0) + 1);
  }
  let maxCount = 0;
  for (const c of counts.values()) {
    if (c > maxCount) maxCount = c;
  }
  const frac = maxCount / s.length;
  if (frac > 0.6) return 15;
  if (frac > 0.4) return 5;
  return 0;
}

/**
 * Penalty for ascending/descending sequence runs of length ≥4.
 * Each such run subtracts 10 bits.
 */
function sequenceRunPenalty(lower: string): number {
  let bits = 0;
  for (const run of SEQUENCE_RUNS) {
    for (let i = 0; i + 4 <= lower.length; i++) {
      const window = lower.slice(i, i + 4);
      if (run.includes(window)) {
        bits += 10;
        break; // count this run once
      }
    }
  }
  return bits;
}

/**
 * Penalty for keyboard-row substrings (≥4 chars).
 * Each distinct keyboard run subtracts 10 bits.
 */
function keyboardRowPenalty(lower: string): number {
  let bits = 0;
  for (const row of KEYBOARD_ROWS) {
    if (row.length < 4) continue;
    // Check any 4-char window of `row` appearing in `lower`.
    for (let i = 0; i + 4 <= row.length; i++) {
      if (lower.includes(row.slice(i, i + 4))) {
        bits += 10;
        break;
      }
    }
  }
  // Cap penalty so we don't go absurdly negative for "qwerty1234".
  return Math.min(30, bits);
}
