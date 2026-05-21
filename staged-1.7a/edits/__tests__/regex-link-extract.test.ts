/**
 * regex-link-extract.test.ts — L4 unit tests for foundational extraction
 *
 * Covers spec §11 T3 "30+ test cases" requirement for extractEntityRefsRegex,
 * stripCodeBlocks code-fence handling, and edge cases from §6.4.
 *
 * Cross-link: staged-1.7a/edits/regex-link-extract.ts
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md
 */

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import {
  stripCodeBlocks,
  extractEntityRefsRegex,
  type ExtractedRef,
  _internals,
} from "../regex-link-extract.js";

// ── Helpers ───────────────────────────────────────────────────────────────────

function keys(refs: ExtractedRef[]): string[] {
  return refs.map((r) => r.key).sort();
}

function bySrc(refs: ExtractedRef[], src: ExtractedRef["source"]): ExtractedRef[] {
  return refs.filter((r) => r.source === src);
}

// ── stripCodeBlocks ───────────────────────────────────────────────────────────

describe("stripCodeBlocks — fenced blocks", () => {
  test("removes content inside triple-backtick fences", () => {
    const input = "before\n```ts\nlet x = [[agents/nox]]\n```\nafter";
    const out = stripCodeBlocks(input);
    assert.ok(!out.includes("[[agents/nox]]"), "wikilink inside fence must be stripped");
    assert.ok(out.includes("before"));
    assert.ok(out.includes("after"));
  });

  test("preserves newlines inside fences for line-number alignment", () => {
    const input = "a\n```\nb\nc\nd\n```\ne";
    const out = stripCodeBlocks(input);
    const inputLines = input.split("\n").length;
    const outLines = out.split("\n").length;
    assert.equal(outLines, inputLines, "line count must be preserved");
  });

  test("handles fenced block with language tag", () => {
    const input = "```typescript\nimport { foo } from '[[agents/nox]]';\n```";
    const out = stripCodeBlocks(input);
    assert.ok(!out.includes("[[agents/nox]]"));
  });

  test("leaves prose around fences untouched", () => {
    const input = "see [[agents/nox]]\n```\nignore me\n```\nand [[decisions/foo]]";
    const out = stripCodeBlocks(input);
    assert.ok(out.includes("[[agents/nox]]"));
    assert.ok(out.includes("[[decisions/foo]]"));
    assert.ok(!out.includes("ignore me"));
  });
});

describe("stripCodeBlocks — inline code", () => {
  test("removes content inside single backticks", () => {
    const input = "see `[[agents/nox]]` for details";
    const out = stripCodeBlocks(input);
    assert.ok(!out.includes("[[agents/nox]]"));
    assert.ok(out.includes("see"));
    assert.ok(out.includes("for details"));
  });

  test("does not span newlines", () => {
    const input = "`unclosed\nseparate `closed` line";
    const out = stripCodeBlocks(input);
    // The prose word "unclosed" survives — single backtick at line start was
    // never closed before \n, so the regex couldn't match across.
    assert.ok(out.includes("unclosed"), "unmatched backtick should stay");
    // The matched inline pair `closed` (with surrounding backticks) was
    // stripped — check the literal sequence with delimiters, NOT the substring
    // "closed" alone (which also appears inside "unclosed").
    assert.ok(!out.includes("`closed`"), "matched backtick pair was stripped");
  });
});

// ── extractEntityRefsRegex — wikilinks ────────────────────────────────────────

describe("extractEntityRefsRegex — wikilinks", () => {
  test("matches bare wikilink form [[agents/nox]]", () => {
    const refs = extractEntityRefsRegex("intro [[agents/nox]] end");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "agents");
    assert.equal(refs[0]!.slug, "nox");
    assert.equal(refs[0]!.source, "wikilink");
  });

  test("matches fully-qualified [[entities/decisions/foo-bar]]", () => {
    const refs = extractEntityRefsRegex("[[entities/decisions/foo-bar]]");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "decisions");
    assert.equal(refs[0]!.slug, "foo-bar");
  });

  test("rejects wikilink with non-entity dir", () => {
    const refs = extractEntityRefsRegex("see [[notes/random]]");
    assert.equal(refs.length, 0);
  });

  test("rejects generic markdown wikilink [[file.md]]", () => {
    const refs = extractEntityRefsRegex("see [[file.md]]");
    assert.equal(refs.length, 0);
  });

  test("multiple wikilinks dedup to first source", () => {
    const refs = extractEntityRefsRegex("[[agents/nox]] then [[agents/nox]] again");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.source, "wikilink");
  });

  test("captures all five live dirs", () => {
    const text = "[[agents/a]] [[decisions/b]] [[lessons/c]] [[projects/d]] [[systems/e]]";
    const refs = extractEntityRefsRegex(text);
    assert.deepEqual(keys(refs), ["agents/a", "decisions/b", "lessons/c", "projects/d", "systems/e"]);
  });

  test("slug normalization is case-insensitive", () => {
    const refs = extractEntityRefsRegex("[[agents/Nox]] vs [[agents/nox]]");
    assert.equal(refs.length, 1, "case-folded keys should dedup");
    assert.equal(refs[0]!.slug, "nox");
  });
});

// ── extractEntityRefsRegex — markdown links ───────────────────────────────────

describe("extractEntityRefsRegex — markdown links", () => {
  test("matches inline markdown link [Display](agents/nox)", () => {
    const refs = extractEntityRefsRegex("see [Display](agents/nox) doc");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "agents");
    assert.equal(refs[0]!.slug, "nox");
    assert.equal(refs[0]!.source, "markdown");
  });

  test("strips .md extension on slug", () => {
    const refs = extractEntityRefsRegex("[X](decisions/foo.md)");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.slug, "foo");
  });

  test("handles markdown link with tooltip [X](path \"tt\")", () => {
    const refs = extractEntityRefsRegex('[X](agents/nox "tooltip text")');
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.slug, "nox");
  });

  test("rejects external https URLs even if path contains entity dir", () => {
    const refs = extractEntityRefsRegex("[X](https://example.com/agents/nox)");
    assert.equal(refs.length, 0);
  });

  test("rejects mailto: and other schemes", () => {
    const refs = extractEntityRefsRegex("[X](mailto:foo@bar.com)");
    assert.equal(refs.length, 0);
  });

  test("handles relative path with memory/entities/ prefix", () => {
    const refs = extractEntityRefsRegex("[X](memory/entities/lessons/some-lesson.md)");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "lessons");
    assert.equal(refs[0]!.slug, "some-lesson");
  });

  test("rejects sub-path slugs (no markdown match)", () => {
    const refs = extractEntityRefsRegex("[X](agents/nox/notes.md)");
    // No markdown source match (sub-path) and BARE_REF lookahead requires
    // [\\s.,;:!?)] after the slug — the `/` between `nox` and `notes` blocks it.
    const md = bySrc(refs, "markdown");
    assert.equal(md.length, 0, "no markdown source for sub-path");
  });

  test("strips fragment and query string", () => {
    const refs = extractEntityRefsRegex("[X](agents/nox.md#section?v=1)");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.slug, "nox");
  });

  test("malformed markdown link still catches ref via bare-ref fallback", () => {
    // Markdown regex won't match (space breaks the pattern), but BARE_REF
    // catches `(agents/nox ` because `(` lookbehind + ` ` lookahead are valid.
    // This is intentional — semantically the text DOES reference agents/nox.
    const refs = extractEntityRefsRegex("[X](agents/nox with space)");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.source, "bare");
  });
});

// ── extractEntityRefsRegex — bare refs ────────────────────────────────────────

describe("extractEntityRefsRegex — bare refs", () => {
  test("matches bare ref after whitespace", () => {
    const refs = extractEntityRefsRegex("see decisions/brave-search for context");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "decisions");
    assert.equal(refs[0]!.slug, "brave-search");
    assert.equal(refs[0]!.source, "bare");
  });

  test("matches bare ref at start of string", () => {
    const refs = extractEntityRefsRegex("lessons/foo is canonical");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.dir, "lessons");
  });

  test("matches bare ref before punctuation", () => {
    assert.equal(extractEntityRefsRegex("ref projects/alpha.").length, 1);
    assert.equal(extractEntityRefsRegex("ref projects/alpha, more").length, 1);
    assert.equal(extractEntityRefsRegex("see (projects/alpha)").length, 1);
  });

  test("rejects path component inside URL", () => {
    const refs = extractEntityRefsRegex("https://example.com/lessons/foo bar");
    assert.equal(refs.length, 0, "slash before dir is path, not whitespace");
  });

  test("dedup keeps higher-priority source (wikilink > bare)", () => {
    const refs = extractEntityRefsRegex("[[agents/nox]] later agents/nox bare");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.source, "wikilink", "wikilink wins over bare on same key");
  });

  test("bare ref preferred over second bare ref (first wins)", () => {
    const refs = extractEntityRefsRegex("see agents/nox then agents/nox");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.source, "bare");
  });
});

// ── Integration with stripCodeBlocks ──────────────────────────────────────────

describe("integration — stripCodeBlocks + extractEntityRefsRegex", () => {
  test("ignores refs inside code fences after stripping", () => {
    const text = "live [[agents/nox]]\n```\nfake [[decisions/foo]]\n```";
    const refs = extractEntityRefsRegex(stripCodeBlocks(text));
    assert.deepEqual(keys(refs), ["agents/nox"]);
  });

  test("ignores refs inside inline code", () => {
    const text = "see `[[agents/nox]]` example but real is [[decisions/foo]]";
    const refs = extractEntityRefsRegex(stripCodeBlocks(text));
    assert.deepEqual(keys(refs), ["decisions/foo"]);
  });

  test("captures refs adjacent to but outside code fences", () => {
    const text = "[[agents/alpha]]\n```\nstuff\n```\n[[agents/beta]]";
    const refs = extractEntityRefsRegex(stripCodeBlocks(text));
    assert.deepEqual(keys(refs), ["agents/alpha", "agents/beta"]);
  });
});

// ── Edge cases (spec §6.4) ────────────────────────────────────────────────────

describe("edge cases", () => {
  test("URL with query string containing slash", () => {
    const refs = extractEntityRefsRegex("see https://example.com/q?path=foo/lessons/bar");
    assert.equal(refs.length, 0);
  });

  test("Unicode prose with accented words around ref", () => {
    const refs = extractEntityRefsRegex("vê a lição [[lessons/atenção]] sobre acentos");
    // slug constraint allows only a-z0-9_-, so accented slugs fail.
    // Real-world VPS slugs are ASCII-only — this is intentional.
    assert.equal(refs.length, 0);
  });

  test("Unicode prose surrounding ASCII slug works", () => {
    const refs = extractEntityRefsRegex("decisão registrada em [[decisions/foo-bar]] hoje");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.slug, "foo-bar");
  });

  test("multiple refs in one line", () => {
    const refs = extractEntityRefsRegex("blame [[agents/a]] and [Display](decisions/b) per lessons/c");
    assert.equal(refs.length, 3);
    assert.deepEqual(keys(refs), ["agents/a", "decisions/b", "lessons/c"]);
  });

  test("empty text returns []", () => {
    assert.deepEqual(extractEntityRefsRegex(""), []);
  });

  test("text with no refs returns []", () => {
    assert.deepEqual(extractEntityRefsRegex("just plain prose without any refs"), []);
  });

  test("slug with underscore and digits", () => {
    const refs = extractEntityRefsRegex("[[lessons/lesson_42-revisited]]");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]!.slug, "lesson_42-revisited");
  });
});

// ── _internals smoke ──────────────────────────────────────────────────────────

describe("_internals", () => {
  test("DIR_PATTERN matches all five live dirs", () => {
    const re = new RegExp(`^${_internals.DIR_PATTERN}$`);
    for (const d of _internals.NOX_ENTITY_DIRS) {
      assert.ok(re.test(d), `${d} should match DIR_PATTERN`);
    }
    assert.ok(!re.test("feedback"), "spec-only singular type should not match");
  });

  test("parseMarkdownTarget returns null for unrelated paths", () => {
    assert.equal(_internals.parseMarkdownTarget("foo/bar"), null);
    assert.equal(_internals.parseMarkdownTarget("agents/"), null);
    assert.equal(_internals.parseMarkdownTarget(""), null);
  });

  test("stripMdExt handles uppercase extension", () => {
    assert.equal(_internals.stripMdExt("foo.MD"), "foo");
    assert.equal(_internals.stripMdExt("foo.Markdown"), "foo");
    assert.equal(_internals.stripMdExt("foo"), "foo");
  });
});
