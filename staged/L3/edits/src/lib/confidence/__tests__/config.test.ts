/**
 * T2 — Config tests (8 tests).
 * Validates env override behaviour, defaults, clamping.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  resolveConfig,
  DEFAULT_OBSERVED,
  DEFAULT_INFERRED,
  DEFAULT_RANKING_MODE,
  clamp01,
} from "../config.js";

function withEnv<T>(vars: Record<string, string | undefined>, fn: () => T): T {
  const prev: Record<string, string | undefined> = {};
  for (const k of Object.keys(vars)) {
    prev[k] = process.env[k];
    const v = vars[k];
    if (v === undefined) delete process.env[k];
    else process.env[k] = v;
  }
  try {
    return fn();
  } finally {
    for (const k of Object.keys(prev)) {
      const v = prev[k];
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  }
}

test("T2.1 resolveConfig with no env returns spec defaults", () => {
  const cfg = withEnv(
    {
      NOX_CONFIDENCE_OBSERVED: undefined,
      NOX_CONFIDENCE_INFERRED: undefined,
      NOX_RANKING_CONFIDENCE: undefined,
    },
    () => resolveConfig()
  );
  assert.equal(cfg.default_observed, DEFAULT_OBSERVED);
  assert.equal(cfg.default_inferred, DEFAULT_INFERRED);
  assert.equal(cfg.ranking_mode, DEFAULT_RANKING_MODE);
});

test("T2.2 NOX_CONFIDENCE_OBSERVED overrides default", () => {
  const cfg = withEnv({ NOX_CONFIDENCE_OBSERVED: "0.88" }, () =>
    resolveConfig()
  );
  assert.equal(cfg.default_observed, 0.88);
});

test("T2.3 NOX_RANKING_CONFIDENCE accepts disabled/shadow/active and synonyms", () => {
  const disabled = withEnv({ NOX_RANKING_CONFIDENCE: "off" }, () =>
    resolveConfig()
  );
  assert.equal(disabled.ranking_mode, "disabled");
  const shadow = withEnv({ NOX_RANKING_CONFIDENCE: "shadow" }, () =>
    resolveConfig()
  );
  assert.equal(shadow.ranking_mode, "shadow");
  const active = withEnv({ NOX_RANKING_CONFIDENCE: "ACTIVE" }, () =>
    resolveConfig()
  );
  assert.equal(active.ranking_mode, "active");
});

test("T2.4 unrecognised ranking mode falls back to disabled (safe default)", () => {
  const cfg = withEnv({ NOX_RANKING_CONFIDENCE: "yolo" }, () => resolveConfig());
  assert.equal(cfg.ranking_mode, "disabled");
});

test("T2.5 explicit overrides win over env", () => {
  const cfg = withEnv({ NOX_CONFIDENCE_OBSERVED: "0.5" }, () =>
    resolveConfig({ default_observed: 0.42 })
  );
  assert.equal(cfg.default_observed, 0.42);
});

test("T2.6 invalid env values fall back to default (NaN safe)", () => {
  const cfg = withEnv({ NOX_CONFIDENCE_INFERRED: "not-a-number" }, () =>
    resolveConfig()
  );
  assert.equal(cfg.default_inferred, DEFAULT_INFERRED);
});

test("T2.7 confidence values are clamped to [0,1]", () => {
  const cfg = withEnv(
    { NOX_CONFIDENCE_OBSERVED: "2.5", NOX_CONFIDENCE_USER_REFUTED: "-3" },
    () => resolveConfig()
  );
  assert.equal(cfg.default_observed, 1.0);
  assert.equal(cfg.user_marked_refuted, 0.0);
});

test("T2.8 clamp01 helper clamps NaN to 0, +Inf to 1", () => {
  assert.equal(clamp01(NaN), 0);
  assert.equal(clamp01(Infinity), 1);
  assert.equal(clamp01(-Infinity), 0);
  assert.equal(clamp01(0.42), 0.42);
});
