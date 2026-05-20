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

// PATTERNS order matters: first match wins. Most specific first.
// `(?:^|\/)` matches start-of-string OR path separator — handles relative
// AND nested paths (empirical fix from dry-run 2026-05-19 22:36 BRT).
const PATTERNS: Array<[RegExp, string]> = [
  [/(?:^|\/)entities\//, "entity"],
  [/(?:^|\/)cache\/ocr\//, "ocr-cache"],
  [/(?:^|\/)sessions\//, "session"],
  [/(?:^|\/)shared\/imports\/Claude\/skills\//, "skill"],
  [/(?:^|\/)shared\/imports\/Claude\/commands\//, "command"],
  [/(?:^|\/)shared\/lex-biblioteca\//, "legal-template"],
  [/(?:^|\/)Claude\/Projetos\//, "project-doc"],
  [/(?:^|\/)memory\/mac-docs\//, "personal-doc"],
  [/(?:^|\/)memory\/lessons\//, "lesson"],
  [/-lessons\.md$/, "lesson"],
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

  describe("edge cases (review LOW)", () => {
    it("handles non-md extensions (json/txt/html/pptx)", () => {
      assert.equal(classifyPath("data/config.json"), "other");
      assert.equal(classifyPath("notes/draft.txt"), "other");
      assert.equal(classifyPath("page.html"), "other");
      assert.equal(classifyPath("slide.pptx"), "other");
    });
    it("handles unicode (PT-BR) in file names", () => {
      assert.equal(classifyPath("memory/lições-aprendidas.md"), "note");
      assert.equal(classifyPath("memory/mac-docs/relação.md"), "personal-doc");
    });
    it("handles absolute paths starting with /", () => {
      assert.equal(
        classifyPath("/root/.openclaw/workspace/tools/nox-mem/memory/entities/foo.md"),
        "entity",
      );
    });
    it("handles paths with trailing slashes", () => {
      assert.equal(classifyPath("memory/entities/"), "entity");
    });
  });
});

// ── parseArgs tests (review MEDIUM #4) ────────────────────────────────────────
// Inline copy mirrors backfill-source-type.ts:148+ to keep test self-contained.

interface TestOpts {
  dryRun?: boolean;
  limit?: number;
  batchSize?: number;
  force?: boolean;
}

function parseArgs(argv: string[]): TestOpts {
  const opts: TestOpts = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--dry-run") opts.dryRun = true;
    else if (a === "--force") opts.force = true;
    else if (a === "--limit" && argv[i + 1]) {
      const raw = argv[++i]!;
      const n = Number.parseInt(raw, 10);
      if (!Number.isFinite(n) || n <= 0) {
        throw new Error(`--limit requires positive integer, got: '${raw}'`);
      }
      opts.limit = n;
    } else if (a === "--batch-size" && argv[i + 1]) {
      const raw = argv[++i]!;
      const n = Number.parseInt(raw, 10);
      if (!Number.isFinite(n) || n <= 0) {
        throw new Error(`--batch-size requires positive integer, got: '${raw}'`);
      }
      opts.batchSize = n;
    }
  }
  return opts;
}

describe("parseArgs", () => {
  it("parses --dry-run flag", () => {
    assert.deepEqual(parseArgs(["--dry-run"]), { dryRun: true });
  });
  it("parses --force flag", () => {
    assert.deepEqual(parseArgs(["--force"]), { force: true });
  });
  it("parses --limit with valid integer", () => {
    assert.deepEqual(parseArgs(["--limit", "100"]), { limit: 100 });
  });
  it("parses --batch-size with valid integer", () => {
    assert.deepEqual(parseArgs(["--batch-size", "500"]), { batchSize: 500 });
  });
  it("throws on --limit NaN ('foo')", () => {
    assert.throws(() => parseArgs(["--limit", "foo"]), /--limit requires positive integer/);
  });
  it("throws on --limit zero", () => {
    assert.throws(() => parseArgs(["--limit", "0"]), /--limit requires positive integer/);
  });
  it("throws on --limit negative", () => {
    assert.throws(() => parseArgs(["--limit", "-5"]), /--limit requires positive integer/);
  });
  it("throws on --batch-size NaN ('bar')", () => {
    assert.throws(() => parseArgs(["--batch-size", "bar"]), /--batch-size requires positive integer/);
  });
  it("throws on --batch-size zero", () => {
    assert.throws(() => parseArgs(["--batch-size", "0"]), /--batch-size requires positive integer/);
  });
  it("combines multiple flags", () => {
    assert.deepEqual(
      parseArgs(["--dry-run", "--limit", "10", "--batch-size", "5", "--force"]),
      { dryRun: true, force: true, limit: 10, batchSize: 5 },
    );
  });
  it("ignores unknown flags", () => {
    assert.deepEqual(parseArgs(["--unknown", "--dry-run"]), { dryRun: true });
  });
  it("empty argv returns empty opts", () => {
    assert.deepEqual(parseArgs([]), {});
  });
});

// ── formatResult tests (review MEDIUM #7) ─────────────────────────────────────

interface TestResult {
  totalChunks: number;
  processed: number;
  byType: Record<string, number>;
  durationMs: number;
  dryRun: boolean;
}

function formatResult(r: TestResult): string {
  if (r.processed === 0) {
    return `${r.dryRun ? "[DRY-RUN] " : ""}No chunks to process (totalChunks=${r.totalChunks})`;
  }
  const lines: string[] = [];
  lines.push(
    `${r.dryRun ? "[DRY-RUN] " : ""}Backfill complete: ${r.processed}/${r.totalChunks} chunks in ${(r.durationMs / 1000).toFixed(1)}s`,
  );
  lines.push("");
  lines.push("Distribution:");
  const entries = Object.entries(r.byType).sort((a, b) => b[1] - a[1]);
  if (entries.length === 0) {
    lines.push("  (empty)");
    return lines.join("\n");
  }
  const maxLabel = Math.max(...entries.map(([k]) => k.length));
  for (const [type, count] of entries) {
    const pct = ((count * 100) / r.processed).toFixed(2);
    lines.push(`  ${type.padEnd(maxLabel)}  ${String(count).padStart(7)}  (${pct}%)`);
  }
  return lines.join("\n");
}

describe("formatResult", () => {
  it("returns 'No chunks to process' when processed=0 (zero-guard, no divide-by-zero)", () => {
    const r: TestResult = { totalChunks: 100, processed: 0, byType: {}, durationMs: 50, dryRun: false };
    const out = formatResult(r);
    assert.match(out, /No chunks to process/);
    assert.match(out, /totalChunks=100/);
    assert.doesNotMatch(out, /Infinity/);
    assert.doesNotMatch(out, /NaN/);
  });
  it("returns 'No chunks to process' under --dry-run with processed=0", () => {
    const r: TestResult = { totalChunks: 0, processed: 0, byType: {}, durationMs: 5, dryRun: true };
    const out = formatResult(r);
    assert.match(out, /^\[DRY-RUN\] No chunks to process/);
  });
  it("formats normal result with byType distribution", () => {
    const r: TestResult = {
      totalChunks: 100, processed: 100,
      byType: { note: 50, entity: 30, lesson: 20 },
      durationMs: 1234, dryRun: false,
    };
    const out = formatResult(r);
    assert.match(out, /Backfill complete: 100\/100 chunks in 1\.2s/);
    assert.match(out, /note\s+50\s+\(50\.00%\)/);
    assert.match(out, /entity\s+30\s+\(30\.00%\)/);
    assert.match(out, /lesson\s+20\s+\(20\.00%\)/);
  });
  it("handles empty byType with non-zero processed (edge case)", () => {
    const r: TestResult = { totalChunks: 10, processed: 10, byType: {}, durationMs: 100, dryRun: false };
    const out = formatResult(r);
    assert.match(out, /\(empty\)/);
  });
});
