/**
 * staged-1.7a/tests/backfill-source-type.test.ts
 *
 * Unit tests for classifyPath() — pure function mapping source_file path
 * to source_type. No DB touched.
 *
 * Companion to PR Task F (source_type backfill migration).
 * See docs/audits/2026-05-19-source-type-backfill-mapping.md.
 *
 * Run: node --test dist/tests/backfill-source-type.test.js
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

// ── Inline copy of classifyPath (mirrors backfill-source-type.ts) ─────────────
// Isolated so test is self-contained.

const PATTERNS: Array<[RegExp, string]> = [
  [/\/entities\//, "entity"],
  [/\/cache\/ocr\//, "ocr-cache"],
  [/\/sessions\//, "session"],
  [/\/shared\/imports\/Claude\/skills\//, "skill"],
  [/\/shared\/imports\/Claude\/commands\//, "command"],
  [/\/shared\/lex-biblioteca\//, "legal-template"],
  [/\/Claude\/Projetos\//, "project-doc"],
  [/\/memory\/mac-docs\//, "personal-doc"],
  [/\/memory\/lessons\/|-lessons\.md$/, "lesson"],
  [/\.md$/, "note"],
];
const FALLBACK_TYPE = "other";

function classifyPath(sourceFile: string): string {
  if (!sourceFile) return FALLBACK_TYPE;
  for (const [rx, type] of PATTERNS) {
    if (rx.test(sourceFile)) return type;
  }
  return FALLBACK_TYPE;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("classifyPath", () => {
  describe("entity", () => {
    it("matches /entities/ in nox-mem memory path", () => {
      assert.equal(
        classifyPath("memory/entities/person/toto-busnello.md"),
        "entity",
      );
    });
    it("matches /entities/ deep in path", () => {
      assert.equal(
        classifyPath("/some/long/path/memory/entities/decision/d48.md"),
        "entity",
      );
    });
  });

  describe("ocr-cache", () => {
    it("matches OCR cache files (no .md extension)", () => {
      assert.equal(
        classifyPath("tools/nox-mem/cache/ocr/49c416b41b02dd5f.md"),
        "ocr-cache",
      );
    });
    it("does NOT match cache outside ocr/", () => {
      assert.notEqual(
        classifyPath("tools/nox-mem/cache/other/file.md"),
        "ocr-cache",
      );
    });
  });

  describe("session", () => {
    it("matches cipher session checkpoint", () => {
      assert.equal(
        classifyPath("sessions/cipher/cipher:650b0642.checkpoint"),
        "session",
      );
    });
    it("matches atlas session file", () => {
      assert.equal(
        classifyPath("memory/sessions/atlas/2026-05-19.md"),
        "session",
      );
    });
  });

  describe("skill / command", () => {
    it("matches Claude skill SKILL.md", () => {
      assert.equal(
        classifyPath("shared/imports/Claude/skills/engineering/architecture/SKILL.md"),
        "skill",
      );
    });
    it("matches Claude command md", () => {
      assert.equal(
        classifyPath("shared/imports/Claude/commands/setup/setup-monorepo.md"),
        "command",
      );
    });
  });

  describe("legal-template", () => {
    it("matches lex-biblioteca legal template", () => {
      assert.equal(
        classifyPath("shared/lex-biblioteca/templates/06_disputes/penalty_notice.md"),
        "legal-template",
      );
    });
  });

  describe("project-doc", () => {
    it("matches Claude/Projetos path", () => {
      assert.equal(
        classifyPath("Claude/Projetos/memoria-nox/docs/HANDOFF.md"),
        "project-doc",
      );
    });
  });

  describe("personal-doc", () => {
    it("matches memory/mac-docs path (Toto financial docs)", () => {
      assert.equal(
        classifyPath("memory/mac-docs/PPR/SELJ/Paralimpico/Faturamento/Fat1454.md"),
        "personal-doc",
      );
    });
  });

  describe("lesson", () => {
    it("matches /memory/lessons/ path", () => {
      assert.equal(
        classifyPath("memory/lessons/agent-stall-2026-05-19.md"),
        "lesson",
      );
    });
    it("matches *-lessons.md suffix outside /lessons/ dir", () => {
      assert.equal(
        classifyPath("memory/2026-04-05-discord-lessons.md"),
        "lesson",
      );
    });
  });

  describe("note (catch-all .md)", () => {
    it("matches generic .md not caught by earlier patterns", () => {
      assert.equal(
        classifyPath("memory/some-random-note.md"),
        "note",
      );
    });
    it("matches root-level .md", () => {
      assert.equal(classifyPath("README.md"), "note");
    });
  });

  describe("other (fallback)", () => {
    it("returns 'other' for non-md file with no pattern match", () => {
      assert.equal(classifyPath("data/some-file.json"), "other");
    });
    it("returns 'other' for empty string", () => {
      assert.equal(classifyPath(""), "other");
    });
  });

  describe("specificity ordering (most-specific wins)", () => {
    it("entities path takes precedence over .md catch-all", () => {
      // Both /entities/ and .md match — entity must win because it's earlier
      assert.equal(
        classifyPath("memory/entities/lesson/legacy.md"),
        "entity",
      );
    });
    it("ocr-cache takes precedence over .md catch-all", () => {
      assert.equal(
        classifyPath("tools/nox-mem/cache/ocr/abc.md"),
        "ocr-cache",
      );
    });
    it("session takes precedence over note", () => {
      assert.equal(
        classifyPath("memory/sessions/cipher/session.md"),
        "session",
      );
    });
    it("lesson -lessons.md suffix takes precedence over note .md catch-all", () => {
      assert.equal(
        classifyPath("memory/foo-lessons.md"),
        "lesson",
      );
    });
  });
});
