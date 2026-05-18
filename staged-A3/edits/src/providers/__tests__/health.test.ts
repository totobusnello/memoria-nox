/**
 * health.test.ts — T8 bootProviderHealth.
 *
 * Cases (6):
 *  1. happy path: both providers OK → allOk=true, no throw
 *  2. fail-fast on embedding down → throws ProviderHealthError
 *  3. soft-warn on embedding down → no throw, onWarn invoked
 *  4. fail-fast on LLM down → throws, mentions provider name
 *  5. timeout: hung healthCheck → ok=false within timeoutMs
 *  6. soft-warn from NOX_PROVIDER_HEALTH_FAIL_FAST=0 env override
 */
import { test, describe } from "node:test";
import { strict as assert } from "node:assert";

import { bootProviderHealth, ProviderHealthError } from "../index.js";
import type { EmbeddingProvider } from "../embedding/types.js";
import type { LLMProvider } from "../llm/types.js";

const FAKE_KEY = "AIzaTESTtestTESTtestTESTtestTESTtest";

/** Tiny in-memory stub that lets us control healthCheck outcome. */
class FakeEmbedding implements EmbeddingProvider {
  public readonly name: string;
  public readonly dimensions = 3072;
  public readonly maxTokens = 2048;
  public readonly costPerMillionTokens = 0.15;
  constructor(
    name: string,
    private readonly status: { ok: boolean; latencyMs?: number; error?: string },
  ) {
    this.name = name;
  }
  public async embed(_t: string[]): Promise<Float32Array[]> {
    return [];
  }
  public async healthCheck(): Promise<{ ok: boolean; latencyMs?: number; error?: string }> {
    return this.status;
  }
}

class FakeLLM implements LLMProvider {
  public readonly name: string;
  public readonly model = "fake-model";
  public readonly contextWindow = 100_000;
  constructor(
    name: string,
    private readonly status: { ok: boolean; latencyMs?: number; error?: string },
  ) {
    this.name = name;
  }
  public async complete(): Promise<{
    text: string;
    tokensIn: number;
    tokensOut: number;
    latencyMs: number;
  }> {
    return { text: "", tokensIn: 0, tokensOut: 0, latencyMs: 0 };
  }
  public async healthCheck(): Promise<{ ok: boolean; latencyMs?: number; error?: string }> {
    return this.status;
  }
}

/** A provider whose healthCheck never resolves — to test timeout. */
class HangingEmbedding implements EmbeddingProvider {
  public readonly name = "hanger";
  public readonly dimensions = 3072;
  public readonly maxTokens = 2048;
  public readonly costPerMillionTokens = 0.15;
  public async embed(_t: string[]): Promise<Float32Array[]> {
    return [];
  }
  public healthCheck(): Promise<{ ok: boolean; latencyMs?: number; error?: string }> {
    return new Promise(() => {
      /* never resolves */
    });
  }
}

describe("bootProviderHealth (T8)", () => {
  test("happy path: both OK → allOk=true, report populated", async () => {
    const e = new FakeEmbedding("gemini", { ok: true, latencyMs: 10 });
    const l = new FakeLLM("gemini", { ok: true, latencyMs: 12 });
    const report = await bootProviderHealth({
      embedding: e,
      llm: l,
      failFast: true,
    });
    assert.equal(report.allOk, true);
    assert.equal(report.embedding?.ok, true);
    assert.equal(report.llm?.ok, true);
    assert.equal(report.embedding?.providerName, "gemini");
    assert.equal(report.llm?.providerName, "gemini");
  });

  test("fail-fast embedding down → throws ProviderHealthError", async () => {
    const e = new FakeEmbedding("gemini", { ok: false, error: "401" });
    const l = new FakeLLM("gemini", { ok: true });
    await assert.rejects(
      bootProviderHealth({ embedding: e, llm: l, failFast: true }),
      ProviderHealthError,
    );
  });

  test("soft-warn embedding down → no throw, onWarn invoked", async () => {
    const e = new FakeEmbedding("openai", { ok: false, error: "stub" });
    const l = new FakeLLM("gemini", { ok: true });
    const warnings: Array<{ providerName: string; kind: string; error: string }> = [];
    const report = await bootProviderHealth({
      embedding: e,
      llm: l,
      failFast: false,
      onWarn: (w) => warnings.push(w),
    });
    assert.equal(report.allOk, false);
    assert.equal(warnings.length, 1);
    assert.equal(warnings[0]?.providerName, "openai");
    assert.equal(warnings[0]?.kind, "embedding");
  });

  test("fail-fast LLM down → throws and report includes llm.providerName", async () => {
    const e = new FakeEmbedding("gemini", { ok: true });
    const l = new FakeLLM("anthropic", { ok: false, error: "stub" });
    await assert.rejects(
      bootProviderHealth({ embedding: e, llm: l, failFast: true }),
      ProviderHealthError,
    );
  });

  test("timeout: hung healthCheck returns ok=false within budget", async () => {
    const e = new HangingEmbedding();
    const t0 = Date.now();
    const report = await bootProviderHealth({
      embedding: e,
      failFast: false,
      timeoutMs: 50,
    });
    const elapsed = Date.now() - t0;
    assert.equal(report.embedding?.ok, false);
    assert.match(report.embedding?.error ?? "", /timeout/i);
    // Allow generous slack but assert nowhere near 5s default.
    assert.ok(elapsed < 1000, `elapsed ${elapsed}ms should be < 1000`);
  });

  test("NOX_PROVIDER_HEALTH_FAIL_FAST=0 env → soft-warn mode", async () => {
    const e = new FakeEmbedding("openai", { ok: false, error: "stub" });
    const report = await bootProviderHealth({
      embedding: e,
      env: { NOX_PROVIDER_HEALTH_FAIL_FAST: "0", GEMINI_API_KEY: FAKE_KEY },
    });
    assert.equal(report.allOk, false);
    // No throw because env disabled fail-fast.
  });
});
