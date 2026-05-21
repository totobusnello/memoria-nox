/**
 * regex-extract.test.ts — node:test suite for regex-first KG extraction (L4).
 *
 * Coverage: extractEntityRefsRegex, extractFrontmatterRelations, extractCodeRefs,
 * regexExtract, isAmbiguous.
 *
 * Design: zero IO, zero network. All fixtures are inline strings.
 * Run: node --experimental-strip-types __tests__/regex-extract.test.ts
 *      OR via staged-1.7a npm test script.
 *
 * Spec: specs/2026-05-18-L4-regex-first-extraction.md §3-§7.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";

import {
  extractEntityRefsRegex,
  extractFrontmatterRelations,
  extractCodeRefs,
  regexExtract,
  isAmbiguous,
  NOX_ENTITY_TYPES,
} from "../regex-extract.js";

// ─── 1. Person / entity extraction — positive ─────────────────────────────────

describe("extractEntityRefsRegex — markdown links", () => {
  it("extracts person entity from markdown link", () => {
    const text = `See [Toto](person/toto_busnello) for context.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "person");
    assert.equal(refs[0]?.slug, "toto_busnello");
    assert.equal(refs[0]?.key, "person/toto_busnello");
    assert.equal(refs[0]?.source, "markdown_link");
    assert.equal(refs[0]?.display, "Toto");
  });

  it("extracts project entity from markdown link with entities/ prefix", () => {
    const text = `Deployed to [nox-mem](entities/project/nox_mem).`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "project");
    assert.equal(refs[0]?.slug, "nox_mem");
  });

  it("strips .md extension from slug", () => {
    const text = `[Decision D48](decision/d48.md) was approved.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.slug, "d48");
  });

  it("strips tooltip from markdown link", () => {
    const text = `[Audit](audit/2026-04-25 "tooltip text") completed.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "audit");
  });
});

// ─── 2. Wikilink extraction ───────────────────────────────────────────────────

describe("extractEntityRefsRegex — wikilinks", () => {
  it("extracts entity from bare wikilink", () => {
    const text = `Cross-ref: [[feedback/no_secrets_in_git]].`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "feedback");
    assert.equal(refs[0]?.slug, "no_secrets_in_git");
    assert.equal(refs[0]?.source, "wikilink");
  });

  it("extracts entity from wikilink with display text", () => {
    const text = `See [[decision/d41|D41 gbrain analysis]] for rationale.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.display, "D41 gbrain analysis");
  });

  it("extracts entity from wikilink with entities/ prefix", () => {
    const text = `Recall [[entities/agent/atlas]] is active.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "agent");
    assert.equal(refs[0]?.slug, "atlas");
  });

  it("ignores generic wikilink without entity type", () => {
    const text = `Read [[some-file.md]] for details.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 0);
  });
});

// ─── 3. Bare ref extraction ───────────────────────────────────────────────────

describe("extractEntityRefsRegex — bare refs", () => {
  it("extracts bare slug ref from line start", () => {
    const text = `feedback/no_secrets is a hard rule.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "feedback");
    assert.equal(refs[0]?.source, "bare_ref");
  });

  it("extracts bare slug ref from mid-sentence", () => {
    const text = `See decision/d48 for pain-weighted ranking.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "decision");
    assert.equal(refs[0]?.slug, "d48");
  });

  it("does NOT match URL path containing entity type (false-positive guard)", () => {
    const text = `See https://example.com/feedback/foo for context.`;
    const refs = extractEntityRefsRegex(text);
    // URL has / before "feedback" — lookbehind should prevent match.
    assert.equal(refs.length, 0);
  });
});

// ─── 4. Decision reference patterns ─────────────────────────────────────────

describe("extractEntityRefsRegex — decision patterns", () => {
  it("extracts decision D48 from bare ref", () => {
    const text = `This resolves decision/d48 and decision/d49.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 2);
    const slugs = refs.map((r) => r.slug).sort();
    assert.deepEqual(slugs, ["d48", "d49"]);
  });

  it("extracts decision from markdown link with D-prefix slug", () => {
    const text = `[D41](decision/d41) motivates the gbrain approach.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs[0]?.slug, "d41");
  });
});

// ─── 5. Multiple entities in one chunk ───────────────────────────────────────

describe("extractEntityRefsRegex — multi-entity", () => {
  it("extracts multiple entities from mixed content", () => {
    const text = [
      `[Toto](person/toto) reviewed [[decision/d48]] and confirmed feedback/no_secrets.`,
      `Also see [nox-mem](project/nox_mem) status.`,
    ].join("\n");
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 4);
    const types = refs.map((r) => r.entityType).sort();
    assert.deepEqual(types, ["decision", "feedback", "person", "project"]);
  });

  it("deduplicates the same entity referenced twice", () => {
    const text = `[D48](decision/d48) and also [[decision/d48]] same thing.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1); // dedup by key
    assert.equal(refs[0]?.key, "decision/d48");
  });

  it("prefers markdown_link display over bare_ref for same key", () => {
    const text = `[Pain weights](decision/d48) are in decision/d48.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.display, "Pain weights");
    assert.equal(refs[0]?.source, "markdown_link");
  });
});

// ─── 6. Code fence stripping ─────────────────────────────────────────────────

describe("extractEntityRefsRegex — code fence stripping", () => {
  it("ignores entity refs inside fenced code blocks", () => {
    const text = "Before fence.\n```typescript\nconst x = feedback/no_secrets;\n```\nAfter fence.";
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 0);
  });

  it("extracts entity refs outside fenced code blocks", () => {
    const text = "```\ncode block here\n```\n\nReal ref: [[decision/d48]].";
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.slug, "d48");
  });

  it("ignores inline code containing entity-like patterns", () => {
    const text = "The value `feedback/no_secrets` is a slug, not a link.";
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 0);
  });
});

// ─── 7. Frontmatter relation extraction ──────────────────────────────────────

describe("extractFrontmatterRelations", () => {
  it("extracts agent relation from scalar frontmatter", () => {
    const text = `---\nagent: atlas\n---\n\nContent here.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 1);
    assert.equal(rels[0]?.relationType, "is_agent_of");
    assert.equal(rels[0]?.target, "atlas");
  });

  it("extracts references array from flow YAML", () => {
    const text = `---\nreferences: [feedback/no_secrets, decision/d48]\n---\n\nContent.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 2);
    assert.equal(rels[0]?.relationType, "references");
    const targets = rels.map((r) => r.target).sort();
    assert.deepEqual(targets, ["decision/d48", "feedback/no_secrets"]);
  });

  it("extracts references from block YAML array", () => {
    const text = `---\nreferences:\n  - feedback/foo\n  - lesson/bar\n---\n\nBody.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 2);
    assert.equal(rels[1]?.target, "lesson/bar");
  });

  it("extracts supersedes relation", () => {
    const text = `---\nsupersedes: decision/d40\n---\nNew decision content.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 1);
    assert.equal(rels[0]?.relationType, "supersedes");
    assert.equal(rels[0]?.target, "decision/d40");
  });

  it("extracts decided_by relation", () => {
    const text = `---\ndecided_by: person/toto_busnello\n---\nDecision content.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 1);
    assert.equal(rels[0]?.relationType, "decided_by");
  });

  it("returns empty array when no frontmatter present", () => {
    const text = `No frontmatter here. Just plain text.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 0);
  });

  it("ignores non-typed frontmatter fields", () => {
    const text = `---\ntitle: My Document\ndate: 2026-05-21\nauthor: Toto\n---\nContent.`;
    const rels = extractFrontmatterRelations(text);
    assert.equal(rels.length, 0);
  });
});

// ─── 8. Code ref extraction ───────────────────────────────────────────────────

describe("extractCodeRefs", () => {
  it("extracts TypeScript source file reference", () => {
    const text = `See src/lib/op-audit.ts:42 for the snapshot logic.`;
    const refs = extractCodeRefs(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.root, "src");
    assert.equal(refs[0]?.line, 42);
    assert.ok(refs[0]?.key.startsWith("codepath/src/"));
  });

  it("extracts spec markdown reference", () => {
    const text = `Spec: specs/2026-05-18-L4-regex-first-extraction.md covers the design.`;
    const refs = extractCodeRefs(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.root, "specs");
  });

  it("extracts audit ref without line number", () => {
    const text = `See audits/2026-04-25-A1-A2-review.md for incident details.`;
    const refs = extractCodeRefs(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.root, "audits");
    assert.equal(refs[0]?.line, undefined);
  });

  it("deduplicates same code ref mentioned twice", () => {
    const text = `src/db.ts is important. Again: src/db.ts.`;
    const refs = extractCodeRefs(text);
    assert.equal(refs.length, 1);
  });

  it("ignores code refs inside fenced code blocks", () => {
    const text = "```\n// src/lib/foo.ts:10 — example\n```\nReal ref: src/db.ts.";
    const refs = extractCodeRefs(text);
    // Only the outside ref should be matched.
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.path, "db.ts");
  });
});

// ─── 9. regexExtract aggregated ─────────────────────────────────────────────

describe("regexExtract — aggregated result", () => {
  it("returns all three categories in one pass", () => {
    const text = `---\nagent: forge\n---\n\n[[decision/d48]] updated via src/lib/op-audit.ts.`;
    const result = regexExtract(text);
    assert.equal(result.entityRefs.length, 1);        // decision/d48
    assert.equal(result.frontmatterRelations.length, 1); // agent: forge
    assert.equal(result.codeRefs.length, 1);           // src/lib/op-audit.ts
    assert.equal(result.totalCount, 3);
  });

  it("returns totalCount=0 for empty input", () => {
    const result = regexExtract("");
    assert.equal(result.totalCount, 0);
  });

  it("marks hadCodeFences=true when input has code blocks", () => {
    const text = "```\nsome code\n```\nContent.";
    const result = regexExtract(text);
    assert.equal(result.hadCodeFences, true);
  });

  it("marks hadCodeFences=false when no code blocks", () => {
    const text = "Plain markdown [[decision/d48]].";
    const result = regexExtract(text);
    assert.equal(result.hadCodeFences, false);
  });
});

// ─── 10. isAmbiguous — Gemini fallback signal ────────────────────────────────

describe("isAmbiguous", () => {
  it("returns true for conversation type regardless of refs", () => {
    const text = "[[decision/d48]] mentioned.";
    const result = regexExtract(text);
    assert.equal(isAmbiguous(text, result, "conversation"), true);
  });

  it("returns true for daily_log type", () => {
    const text = "Today I reviewed [[decision/d48]].";
    const result = regexExtract(text);
    assert.equal(isAmbiguous(text, result, "daily_log"), true);
  });

  it("returns true for empty regex result on substantial content", () => {
    const text = "This is a long paragraph with no structured references to any entity. More text here.";
    const result = regexExtract(text);
    assert.equal(isAmbiguous(text, result), true);
  });

  it("returns false for compiled entity section with refs", () => {
    const text = "[[decision/d48]] and [[feedback/no_secrets]] clearly reference entities.";
    const result = regexExtract(text);
    // Has entity refs, is not conversation/daily_log.
    assert.equal(isAmbiguous(text, result, "entity"), false);
  });

  it("returns false for short content with no refs (below 50-char threshold)", () => {
    const text = "OK.";
    const result = regexExtract(text);
    assert.equal(isAmbiguous(text, result), false);
  });
});

// ─── 11. PascalCase non-entity rejection ─────────────────────────────────────

describe("extractEntityRefsRegex — PascalCase false positive guard", () => {
  it("does NOT match standalone PascalCase words as entities", () => {
    // DIR_PATTERN requires entity_type/ prefix — bare PascalCase is not matched.
    const text = "Toto Busnello reviewed the code. Atlas ran the analysis.";
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 0);
  });
});

// ─── 12. NOX_ENTITY_TYPES completeness ───────────────────────────────────────

describe("NOX_ENTITY_TYPES", () => {
  it("contains all 17 canonical entity types (16 original + `system` added in plural normalisation round)", () => {
    assert.equal(NOX_ENTITY_TYPES.length, 17);
  });

  it("includes critical types: feedback, decision, person, agent", () => {
    const set = new Set<string>(NOX_ENTITY_TYPES);
    assert.ok(set.has("feedback"));
    assert.ok(set.has("decision"));
    assert.ok(set.has("person"));
    assert.ok(set.has("agent"));
  });
});

// ─── 13. Audit reference pattern ─────────────────────────────────────────────

describe("extractEntityRefsRegex — audit refs", () => {
  it("extracts audit entity via wikilink", () => {
    const text = `See [[audit/2026-04-25-a1-a2-review]] for incident details.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "audit");
  });

  it("extracts audit entity via markdown link", () => {
    const text = `[Audit A1](audit/a1-review) was completed.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "audit");
  });
});

// ─── 14. Date/ISO8601 patterns in frontmatter (non-relation, no match) ────────

describe("extractFrontmatterRelations — date field is property not relation", () => {
  it("does NOT create a relation for incident_date field", () => {
    const text = `---\nincident_date: 2026-04-25\ncaused_by: incident/wipe_2026\n---\nContent.`;
    const rels = extractFrontmatterRelations(text);
    // Only caused_by maps to a relation; incident_date is a property (spec §5).
    assert.equal(rels.length, 1);
    assert.equal(rels[0]?.relationType, "caused_by");
  });
});

// ─── 15. Unicode handling ────────────────────────────────────────────────────

describe("extractEntityRefsRegex — Unicode boundary", () => {
  it("handles slug with accented characters in surrounding text without false match", () => {
    // Slugs are ASCII-normalized; accented words in surrounding text should not break matching.
    const text = `Análise: [[decision/d48]] foi aprovada com sucesso.`;
    const refs = extractEntityRefsRegex(text);
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.slug, "d48");
  });
});

// ─── 16. Plural filesystem dir normalisation (PR #210 follow-up) ─────────────

describe("extractEntityRefsRegex — plural filesystem dir forms", () => {
  it("normalises plural `agents/` to canonical singular `agent`", () => {
    const refs = extractEntityRefsRegex("see [[agents/nox]] for chief-of-staff role");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "agent", "plural agents → singular agent");
    assert.equal(refs[0]?.slug, "nox");
    assert.equal(refs[0]?.key, "agent/nox", "key uses singular canonical form");
  });

  it("normalises plural `decisions/` via markdown link", () => {
    const refs = extractEntityRefsRegex("[D48 verdict](decisions/d48-mutex-active-t2)");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "decision");
    assert.equal(refs[0]?.slug, "d48-mutex-active-t2");
  });

  it("normalises plural `lessons/` via bare ref", () => {
    const refs = extractEntityRefsRegex("já vimos esse padrão em lessons/sqlite-affinity hoje");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "lesson");
    assert.equal(refs[0]?.slug, "sqlite-affinity");
  });

  it("normalises plural `projects/`", () => {
    const refs = extractEntityRefsRegex("[[projects/area-campolim]] is parked");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "project");
    assert.equal(refs[0]?.slug, "area-campolim");
  });

  it("normalises plural `systems/` to new canonical `system`", () => {
    const refs = extractEntityRefsRegex("see [[systems/nox-mem]] for core schema");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "system");
    assert.equal(refs[0]?.slug, "nox-mem");
  });

  it("dedups when same key reached via both singular and plural", () => {
    // Both `[[agent/nox]]` and `[[agents/nox]]` resolve to key `agent/nox`.
    // The second occurrence is a no-op (first wins, just like other dedup paths).
    const refs = extractEntityRefsRegex("[[agent/nox]] vs [[agents/nox]] are same entity");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.key, "agent/nox");
  });

  it("rejects unknown plural form not in NOX_ENTITY_DIRS_PLURAL", () => {
    // `teams` is NOT on the filesystem and was never added to the plural list.
    // Should not match (no canonical mapping).
    const refs = extractEntityRefsRegex("see [[teams/granix]] for context");
    assert.equal(refs.length, 0, "teams/ not in plural whitelist");
  });

  it("preserves singular forms untouched", () => {
    // Sanity guard — the plural support should never break existing singular behavior.
    const refs = extractEntityRefsRegex("[[feedback/no-secrets]] still works");
    assert.equal(refs.length, 1);
    assert.equal(refs[0]?.entityType, "feedback");
    assert.equal(refs[0]?.slug, "no-secrets");
  });
});

// ─── 17. system canonical (new type) ─────────────────────────────────────────

describe("NOX_ENTITY_TYPES — system canonical added", () => {
  it("includes `system` as a canonical entity type", () => {
    const set = new Set<string>(NOX_ENTITY_TYPES);
    assert.ok(set.has("system"), "system added pra canonicalise systems/ filesystem dir");
  });

  it("now has 17 canonical types (was 16 pre-PR #210 follow-up)", () => {
    assert.equal(NOX_ENTITY_TYPES.length, 17);
  });
});
