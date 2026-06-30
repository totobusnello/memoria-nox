/**
 * A2.1 T5 — Entropy estimator tests (27 cases).
 *
 * Coverage:
 *   - empty / non-string             (2)
 *   - known-weak common passwords    (8)
 *   - known-strong long mixed pass   (3)
 *   - keyboard patterns / sequences  (4)
 *   - repeated chars                 (2)
 *   - digit-only PIN cap             (2)
 *   - unicode / emoji / long pass    (3)
 *   - tier mapping basics            (3)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { estimateEntropyBits } from "../entropy.js";
import {
  meetsMinimumStrength,
  renderStrengthMeter,
  strengthFromBits,
  strengthOfPassphrase,
} from "../strength.js";

describe("entropy / strength", () => {
  // — empties / non-strings —
  it("returns 0 for empty string", () => {
    assert.equal(estimateEntropyBits(""), 0);
  });

  it("returns 0 for non-string input", () => {
    // @ts-expect-error - guarding runtime misuse
    assert.equal(estimateEntropyBits(null), 0);
  });

  // — known-weak (must all map to `weak` tier) —
  for (const pw of [
    "a",
    "password",
    "123456",
    "qwerty",
    "senha",
    "iloveyou",
    "admin",
    "letmein",
  ]) {
    it(`rejects known-weak "${pw}" → weak tier`, () => {
      const { tier } = strengthOfPassphrase(pw);
      assert.equal(tier, "weak", `expected weak for "${pw}"`);
    });
  }

  // — known-strong (must map to `strong` tier) —
  it("accepts 24-char mixed pass as `strong`", () => {
    const pw = "Tr0ub4dor&3-Quantum#X9zP";
    const { bits, tier } = strengthOfPassphrase(pw);
    assert.ok(bits >= 70, `expected >=70 bits, got ${bits}`);
    assert.equal(tier, "strong");
  });

  it("accepts 30-char diceware-style pass as `strong`", () => {
    // No common substrings, diverse chars
    const pw = "Xy7!Qz3#Vp9@Mw5$Lr8*Nh2&Ka6%Bc4";
    const { bits, tier } = strengthOfPassphrase(pw);
    assert.ok(bits >= 70, `expected >=70 bits, got ${bits}`);
    assert.equal(tier, "strong");
  });

  it("accepts long random ascii as `strong`", () => {
    const pw = "K9!mX#vL@4nQ$pZ%8wY^bR&3jT";
    const { tier } = strengthOfPassphrase(pw);
    assert.equal(tier, "strong");
  });

  // — keyboard patterns / sequences —
  it("penalises keyboard row 'qwertyuiop'", () => {
    const bits = estimateEntropyBits("qwertyuiop");
    assert.ok(bits < 30, `expected weak, got ${bits} bits`);
  });

  it("penalises ascending sequence 'abcdefgh'", () => {
    const bits = estimateEntropyBits("abcdefgh");
    assert.ok(bits < 30, `expected weak, got ${bits} bits`);
  });

  it("penalises descending sequence '987654321'", () => {
    const bits = estimateEntropyBits("987654321");
    assert.ok(bits < 30, `expected weak, got ${bits} bits`);
  });

  it("penalises 'Password123' (substring + sequence)", () => {
    const bits = estimateEntropyBits("Password123");
    assert.ok(bits < 50, `expected <fair, got ${bits} bits`);
  });

  // — repeated chars —
  it("penalises 'aaaaaaaaaa' (all same)", () => {
    const bits = estimateEntropyBits("aaaaaaaaaa");
    assert.ok(bits < 20, `expected weak, got ${bits} bits`);
  });

  it("penalises 'AaaaaaaaB' (>60% one char)", () => {
    const bits = estimateEntropyBits("Aaaaaaaab");
    assert.ok(bits < 30, `expected <fair, got ${bits} bits`);
  });

  // — digit-only cap —
  it("caps 8-digit PIN to <=~26.6 bits regardless of seq", () => {
    const bits = estimateEntropyBits("83746291"); // no seq
    assert.ok(bits <= 27, `expected ≤27 bits for 8-digit PIN, got ${bits}`);
  });

  it("does NOT cap 12-digit numeric (length > 8)", () => {
    const bits = estimateEntropyBits("837462910583");
    // 12 digits × log2(10) ≈ 39.86 bits
    assert.ok(bits >= 30, `expected ≥30 bits for 12-digit, got ${bits}`);
  });

  // — unicode / emoji / very long —
  it("handles emoji passphrase", () => {
    const pw = "🌟✨🎵🚀🌈💫🔥🌊🌀🍀";
    const bits = estimateEntropyBits(pw);
    assert.ok(bits > 0, "emoji pass should yield non-zero bits");
  });

  it("counts code-points (not UTF-16 units) for length", () => {
    // Each emoji is one code point > BMP (surrogate pair); JS .length would
    // return 20 but Array.from() length is 10.
    const pw = "🌟✨🎵🚀🌈💫🔥🌊🌀🍀";
    assert.equal(Array.from(pw).length, 10);
    // Bits should reflect the 10-cp length scaled by non-ascii pool ≥2560.
    const bits = estimateEntropyBits(pw);
    assert.ok(bits >= 60, `expected ≥60 bits for 10 emoji cps, got ${bits}`);
  });

  it("handles unicode latin (ç, ã, é)", () => {
    const pw = "MãeQueriaCafézinhoÀs7h45ÇãoBrasília";
    const { tier } = strengthOfPassphrase(pw);
    assert.equal(tier, "strong");
  });

  // — tier mapping basics —
  it("strengthFromBits 0 → weak, 50 → good, 100 → strong", () => {
    assert.equal(strengthFromBits(0), "weak");
    assert.equal(strengthFromBits(29.9), "weak");
    assert.equal(strengthFromBits(30), "fair");
    assert.equal(strengthFromBits(49.9), "fair");
    assert.equal(strengthFromBits(50), "good");
    assert.equal(strengthFromBits(69.9), "good");
    assert.equal(strengthFromBits(70), "strong");
    assert.equal(strengthFromBits(120), "strong");
  });

  it("meetsMinimumStrength ordering", () => {
    assert.equal(meetsMinimumStrength("strong", "good"), true);
    assert.equal(meetsMinimumStrength("good", "good"), true);
    assert.equal(meetsMinimumStrength("fair", "good"), false);
    assert.equal(meetsMinimumStrength("weak", "weak"), true);
  });

  it("renderStrengthMeter formats expected width", () => {
    const meter = renderStrengthMeter({ bits: 55, tier: "good" });
    assert.match(meter, /^\[.{8}\] GOOD/);
    assert.match(meter, /\(~55 bits\)/);
  });
});
