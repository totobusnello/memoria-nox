/**
 * A2.1 T5 — Enforcement tests (15 cases).
 *
 * Coverage:
 *   - default `good` rejects weak           (3)
 *   - default accepts good/strong           (2)
 *   - --allow-weak / opts.allow_weak bypass (2 + stderr warn)
 *   - env var bypass                        (2 + stderr warn)
 *   - empty passphrase rejected            (1)
 *   - minStrength override                  (2)
 *   - bypass logging never includes pass    (1)
 *   - WeakPassphraseError fields            (2)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  enforcePassphraseStrength,
  WeakPassphraseError,
} from "../enforce-strength.js";

describe("enforcePassphraseStrength", () => {
  it("rejects 'a' under default minStrength=good", () => {
    assert.throws(
      () => enforcePassphraseStrength("a", { env: {} }),
      (err) =>
        err instanceof WeakPassphraseError &&
        err.tier === "weak" &&
        err.required === "good",
    );
  });

  it("rejects 'password' under default minStrength=good", () => {
    assert.throws(
      () => enforcePassphraseStrength("password", { env: {} }),
      WeakPassphraseError,
    );
  });

  it("rejects 'qwerty123' under default minStrength=good", () => {
    assert.throws(
      () => enforcePassphraseStrength("qwerty123", { env: {} }),
      WeakPassphraseError,
    );
  });

  it("accepts a strong 24-char mixed pass", () => {
    const res = enforcePassphraseStrength("Tr0ub4dor&3-Quantum#X9zP", {
      env: {},
    });
    assert.equal(res.bypassed, false);
    assert.equal(res.tier, "strong");
  });

  it("accepts a good ~50-bit pass when min=good", () => {
    // 14-char mixed pass; should clear 50 bits if no penalties trigger.
    const res = enforcePassphraseStrength("MxQ7vR!2pK#wL9", { env: {} });
    assert.equal(res.bypassed, false);
    assert.ok(["good", "strong"].includes(res.tier), `tier=${res.tier}`);
  });

  it("accepts weak pass when allow_weak=true (with stderr warn)", () => {
    const lines: string[] = [];
    const res = enforcePassphraseStrength("a", {
      allow_weak: true,
      env: {},
      log: (m) => lines.push(m),
    });
    assert.equal(res.bypassed, true);
    assert.equal(res.bypass_reason, "cli_flag");
    assert.ok(lines.length === 1, "exactly one warn line");
    assert.match(lines[0]!, /WARN: weak passphrase/);
    assert.match(lines[0]!, /--allow-weak/);
    // Passphrase value MUST NOT appear in the log.
    assert.doesNotMatch(lines[0]!, /\ba\b/);
  });

  it("accepts weak pass when NOX_A2_ALLOW_WEAK_PASSPHRASE=1 (with stderr warn)", () => {
    const lines: string[] = [];
    const res = enforcePassphraseStrength("password", {
      env: { NOX_A2_ALLOW_WEAK_PASSPHRASE: "1" },
      log: (m) => lines.push(m),
    });
    assert.equal(res.bypassed, true);
    assert.equal(res.bypass_reason, "env_var");
    assert.match(lines[0]!, /NOX_A2_ALLOW_WEAK_PASSPHRASE/);
  });

  it("does NOT bypass when env var is '0' / unset", () => {
    assert.throws(
      () =>
        enforcePassphraseStrength("password", {
          env: { NOX_A2_ALLOW_WEAK_PASSPHRASE: "0" },
        }),
      WeakPassphraseError,
    );
    assert.throws(
      () => enforcePassphraseStrength("password", { env: {} }),
      WeakPassphraseError,
    );
  });

  it("rejects empty passphrase even with allow_weak (defensive)", () => {
    assert.throws(
      () =>
        enforcePassphraseStrength("", {
          allow_weak: true,
          env: {},
        }),
      (err) =>
        err instanceof WeakPassphraseError &&
        /empty/i.test(err.message),
    );
  });

  it("rejects non-string passphrase (runtime guard)", () => {
    assert.throws(
      () =>
        // @ts-expect-error - runtime misuse
        enforcePassphraseStrength(null, { env: {} }),
      WeakPassphraseError,
    );
  });

  it("respects minStrength='fair' override (accepts fair-tier pass)", () => {
    // 'M!7vqLpZ' is short but has 4 classes — around fair tier (≥30 bits).
    const res = enforcePassphraseStrength("M!7vqLpZ", {
      env: {},
      minStrength: "fair",
    });
    assert.equal(res.bypassed, false);
    assert.ok(["fair", "good", "strong"].includes(res.tier));
  });

  it("respects minStrength='weak' override (accepts anything non-empty)", () => {
    const res = enforcePassphraseStrength("a", {
      env: {},
      minStrength: "weak",
    });
    assert.equal(res.bypassed, false);
  });

  it("WeakPassphraseError exposes bits/tier/required", () => {
    try {
      enforcePassphraseStrength("a", { env: {} });
      assert.fail("should have thrown");
    } catch (err) {
      assert.ok(err instanceof WeakPassphraseError);
      const wpe = err as WeakPassphraseError;
      assert.equal(typeof wpe.bits, "number");
      assert.ok(wpe.bits < 30, `bits should be <30, got ${wpe.bits}`);
      assert.equal(wpe.tier, "weak");
      assert.equal(wpe.required, "good");
    }
  });

  it("WeakPassphraseError message references --allow-weak", () => {
    try {
      enforcePassphraseStrength("password", { env: {} });
      assert.fail("should have thrown");
    } catch (err) {
      assert.match((err as Error).message, /--allow-weak/);
      assert.match(
        (err as Error).message,
        /NOX_A2_ALLOW_WEAK_PASSPHRASE/,
      );
    }
  });

  it("WARN log NEVER contains the passphrase plaintext", () => {
    const lines: string[] = [];
    enforcePassphraseStrength("hunter2", {
      allow_weak: true,
      env: {},
      log: (m) => lines.push(m),
    });
    for (const ln of lines) {
      assert.doesNotMatch(ln, /hunter2/);
    }
  });

  it("returns numeric bits + tier on success path", () => {
    const res = enforcePassphraseStrength("Tr0ub4dor&3-Quantum#X9zP", {
      env: {},
    });
    assert.equal(typeof res.bits, "number");
    assert.ok(res.bits > 0);
    assert.equal(typeof res.tier, "string");
    assert.equal(res.required, "good");
    assert.equal(res.bypassed, false);
    assert.equal(res.bypass_reason, null);
  });
});
