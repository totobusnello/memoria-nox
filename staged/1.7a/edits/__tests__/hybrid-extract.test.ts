/**
 * hybrid-extract.test.ts — node:test suite for L4 hybrid orchestration.
 *
 * Tests the NOX_KG_EXTRACT_MODE routing logic in kg-llm.ts without real
 * Gemini API calls. Gemini path is tested via mocking the GEMINI_API_KEY to
 * empty string + verifying early-return behavior.
 *
 * WARNING: These tests manipulate process.env — each test restores the value
 * in a teardown step. They run serially to avoid race conditions on env state.
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §3, §7, §15.
 */

import { describe, it, before, after } from "node:test";
import assert from "node:assert/strict";
import { regexExtract } from "../regex-extract.js";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function setEnv(key: string, val: string | undefined): void {
  if (val === undefined) {
    delete process.env[key];
  } else {
    process.env[key] = val;
  }
}

function withMode(mode: string, fn: () => Promise<void> | void): () => Promise<void> {
  return async () => {
    const prev = process.env["NOX_KG_EXTRACT_MODE"];
    setEnv("NOX_KG_EXTRACT_MODE", mode);
    try {
      await fn();
    } finally {
      setEnv("NOX_KG_EXTRACT_MODE", prev);
    }
  };
}

// ─── 1. regex_only mode ───────────────────────────────────────────────────────

describe("extractWithLLM — regex_only mode", () => {
  it(
    "returns regex_result without calling Gemini",
    withMode("regex_only", async () => {
      // Ensure no GEMINI_API_KEY so Gemini call would fail visibly if attempted.
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", "SHOULD_NOT_BE_CALLED");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = "[[decision/d48]] was finalized.";
        const result = await extractWithLLM(text);
        assert.equal(result.extract_mode, "regex_only");
        assert.ok(result.regex_result !== undefined);
        assert.ok((result.regex_result?.totalCount ?? 0) >= 1);
        // Gemini entities should be empty (no Gemini call).
        assert.equal(result.entities.length, 0);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );
});

// ─── 2. gemini_only mode ──────────────────────────────────────────────────────

describe("extractWithLLM — gemini_only mode", () => {
  it(
    "returns gemini_only mode without regex_result field",
    withMode("gemini_only", async () => {
      // Clear API key so Gemini returns empty (no-key path).
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", "");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = "[[decision/d48]] and some prose content.";
        const result = await extractWithLLM(text);
        assert.equal(result.extract_mode, "gemini_only");
        // regex_result should NOT be populated in gemini_only mode.
        assert.equal(result.regex_result, undefined);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );

  it(
    "invokes fast-path PT-BR before Gemini in gemini_only mode",
    withMode("gemini_only", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      // Keep key empty — if fast-path triggers, Gemini won't be called.
      setEnv("GEMINI_API_KEY", "");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        // Text with 3+ structured hits (CNPJ + 2 BRL values) — fast-path threshold.
        const text = `Empresa: 12.345.678/0001-99, valor: R$ 500.000 + R$ 200.000 negociado.`;
        const result = await extractWithLLM(text);
        assert.equal(result.fast_path_used, true);
        assert.ok(result.entities.length > 0);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );
});

// ─── 3. hybrid_shadow mode ────────────────────────────────────────────────────

describe("extractWithLLM — hybrid_shadow mode", () => {
  it(
    "runs regex extraction and attaches regex_result",
    withMode("hybrid_shadow", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", ""); // Gemini returns empty — no API call
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = `[[feedback/no_secrets]] and [[decision/d48]] both referenced.`;
        const result = await extractWithLLM(text);
        assert.equal(result.extract_mode, "hybrid_shadow");
        // regex_result must be attached in shadow mode.
        assert.ok(result.regex_result !== undefined);
        assert.ok((result.regex_result?.entityRefs.length ?? 0) >= 2);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );
});

// ─── 4. hybrid_active mode ───────────────────────────────────────────────────

describe("extractWithLLM — hybrid_active mode", () => {
  it(
    "skips Gemini when regex finds refs in entity content",
    withMode("hybrid_active", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", "SHOULD_NOT_BE_CALLED_IF_SKIP");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        // Entity type chunk with structured refs — should skip Gemini.
        const text = `[[decision/d48]] and [[feedback/no_secrets_in_git]] are both active rules.`;
        const result = await extractWithLLM(text, { type: "entity", section: "compiled" });
        assert.equal(result.extract_mode, "hybrid_active");
        assert.ok(result.regex_result !== undefined);
        // Entities are empty because Gemini was skipped.
        assert.equal(result.entities.length, 0);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );

  it(
    "calls Gemini for conversation type regardless of regex hits",
    withMode("hybrid_active", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", ""); // empty → Gemini returns empty (no real call)
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = `[[decision/d48]] came up in the meeting, we should follow up.`;
        // conversation type forces Gemini even with regex hits.
        const result = await extractWithLLM(text, { type: "conversation" });
        // Should have called Gemini (returned empty due to no key).
        assert.equal(result.extract_mode, "hybrid_active");
        // regex_result still populated for telemetry.
        assert.ok(result.regex_result !== undefined);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );
});

// ─── 5. Invalid mode → defaults to hybrid_shadow ─────────────────────────────

describe("extractWithLLM — invalid mode fallback", () => {
  it(
    "defaults to hybrid_shadow on unknown NOX_KG_EXTRACT_MODE value",
    withMode("INVALID_MODE_XYZ", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", "");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = `[[feedback/no_secrets]] is a rule.`;
        const result = await extractWithLLM(text);
        // Should fall back to hybrid_shadow behavior.
        assert.equal(result.extract_mode, "hybrid_shadow");
        assert.ok(result.regex_result !== undefined);
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
      }
    }),
  );
});

// ─── 6. Telemetry integration smoke ──────────────────────────────────────────

describe("hybrid_shadow telemetry", () => {
  it(
    "attaches regex_result to result for downstream telemetry consumers",
    withMode("hybrid_shadow", async () => {
      const prevKey = process.env["GEMINI_API_KEY"];
      setEnv("GEMINI_API_KEY", "");
      // Use a temp dir for telemetry log to avoid polluting /var/log in tests.
      const prevTelDir = process.env["NOX_KG_TELEMETRY_DIR"];
      setEnv("NOX_KG_TELEMETRY_DIR", "/tmp/nox-kg-test");
      try {
        const { extractWithLLM } = await import("../kg-llm.js");
        const text = `---\nagent: forge\n---\n\n[[decision/d48]] confirmed.`;
        const result = await extractWithLLM(text, {
          chunkId: "test-chunk-001",
          section: "compiled",
          type: "entity",
        });
        assert.equal(result.extract_mode, "hybrid_shadow");
        // Telemetry fields on regex_result.
        assert.ok(result.regex_result !== undefined);
        assert.equal(result.regex_result?.frontmatterRelations.length, 1); // agent: forge
        assert.equal(result.regex_result?.entityRefs.length, 1); // decision/d48
      } finally {
        setEnv("GEMINI_API_KEY", prevKey);
        setEnv("NOX_KG_TELEMETRY_DIR", prevTelDir);
      }
    }),
  );
});

// ─── Direct regexExtract unit — fast check ───────────────────────────────────

describe("regexExtract — direct unit test (no env dependency)", () => {
  it("correctly aggregates from a rich entity file", () => {
    const content = `---
agent: atlas
references: [feedback/no_secrets, decision/d48]
decided_by: person/toto_busnello
---

## Summary

This [[project/nox_mem]] spec references src/lib/op-audit.ts:42.
See also [L4 spec](spec/l4_regex_first_extraction).
`;
    const result = regexExtract(content);
    // Frontmatter: agent + 2 references + decided_by = 4
    assert.equal(result.frontmatterRelations.length, 4);
    // Entity refs: project/nox_mem + spec/l4_regex_first_extraction = 2
    assert.ok(result.entityRefs.length >= 2);
    // Code ref: src/lib/op-audit.ts:42
    assert.equal(result.codeRefs.length, 1);
    assert.equal(result.codeRefs[0]?.line, 42);
    assert.ok(result.totalCount >= 7);
  });
});
