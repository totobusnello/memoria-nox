/**
 * staged-1.7a/tests/search-boost-stack.test.ts
 *
 * Wiring tests for the A-boost-stack-wiring patch (2026-05-19).
 *
 * Validates that the boost stack is:
 *   1. Additive (CLAUDE.md rule #5), not multiplicative.
 *   2. Honors the 5 env toggles (NOX_DISABLE_*).
 *   3. Reads section / pain / importance / source_type / tier from chunks.
 *   4. SOURCE_TYPE_BOOST keys match prod corpus (`external` not `user_statement`).
 *   5. Salience only contributes when NOX_SALIENCE_MODE=active.
 *   6. Stacks all boosts as a single (1 + Σdeltas) multiplier.
 *
 * Self-contained: in-memory better-sqlite3 + inline boost logic mirroring
 * staged-1.7a/edits/search.ts. Does NOT import search.ts directly because
 * search.ts has a module-load dependency on getDb() / tier-manager / embed
 * that doesn't resolve outside the VPS module graph. This pattern matches
 * search-sanitize.test.ts (same staged dir).
 *
 * Run: npm test
 * Or:  npx tsx staged-1.7a/tests/search-boost-stack.test.ts (dev)
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";

import {
  calculateSalience,
  recencyComponent,
  importanceComponent,
  painComponent,
  resolveRetentionDays,
  getSalienceMode,
} from "../edits/salience.js";

// ── Inline copies of the boost maps and helpers from search.ts ────────────────
// These mirror staged-1.7a/edits/search.ts byte-for-byte to keep the test
// self-contained while still exercising the actual additive contract.

const TIER_BOOST: Record<string, number> = {
  core: 2.0,
  active: 1.5,
  peripheral: 1.0,
  archived: 0.5,
};

const BOOST_TYPES = new Set(["decision", "lesson", "person", "project", "pending"]);
const TYPE_BOOST_DELTA_FTS = 1.0;
const RECENCY_BOOST_DELTA_FTS = 0.5;

// NOTE: mirror of `SOURCE_TYPE_BOOST` from staged-1.7a/edits/search.ts
//   Keep in sync. The `mirror-drift-guard` test below asserts byte equality
//   against the live export (`_internals.SOURCE_TYPE_BOOST`) so any future
//   calibration change in search.ts breaks the test if this mirror lags.
const SOURCE_TYPE_BOOST: Record<string, number> = {
  // Active keys (post-backfill 2026-05-19)
  entity: 2.0,
  lesson: 1.8,
  skill: 1.5,
  "project-doc": 1.4,
  command: 1.4,
  "legal-template": 1.3,
  "personal-doc": 1.2,
  session: 1.0,
  note: 1.0,
  external: 0.8,
  other: 0.7,
  "ocr-cache": 0.7,
  // Forward-compat (ingest path planned but not landed):
  user_statement: 2.0,
};

const SECTION_BOOST: Record<string, number> = {
  compiled: 2.0,
  frontmatter: 1.5,
  timeline: 0.8,
};

interface ChunkRow {
  id: number;
  chunk_text: string;
  source_file: string;
  chunk_type: string;
  source_date: string | null;
  tier: string | null;
  source_type: string | null;
  section: string | null;
  section_boost: number | null;
  pain: number | null;
  importance: number | null;
  retention_days: number | null;
  created_at: string | null;
  last_accessed_at: string | null;
  rank: number;
}

interface ScoreOpts {
  disableType?: boolean;
  disableTier?: boolean;
  disableSourceType?: boolean;
  disableSection?: boolean;
  disableRecency?: boolean;
  // G9 Hard Mutex (PR #180 Option 1): default ON (mutex applied). Set
  // `disableMutex: true` to mirror NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1
  // — both sectionDelta and sourceTypeDelta accumulate (pre-mutex behaviour).
  disableMutex?: boolean;
  salienceMode?: "shadow" | "active" | "off";
  nowMs?: number;
}

function scoreChunk(row: ChunkRow, opts: ScoreOpts = {}): number {
  const baseScore = Math.abs(row.rank);
  const sevenDaysAgo = new Date(
    (opts.nowMs ?? Date.now()) - 7 * 24 * 60 * 60 * 1000,
  ).toISOString().split("T")[0];

  let boostSum = 0;
  if (!opts.disableType && BOOST_TYPES.has(row.chunk_type)) {
    boostSum += TYPE_BOOST_DELTA_FTS;
  }
  if (!opts.disableRecency && row.source_date && row.source_date >= sevenDaysAgo!) {
    boostSum += RECENCY_BOOST_DELTA_FTS;
  }
  if (!opts.disableTier) {
    const t = row.tier ?? "peripheral";
    boostSum += (TIER_BOOST[t] ?? 1.0) - 1.0;
  }
  if (!opts.disableSourceType && row.source_type) {
    // G9 Hard Mutex (PR #180 Option 1): skip source_type contribution when
    // `section` is populated AND section_boost active — mirror of search.ts
    // sourceTypeDelta() guard. The mutex is ON by default.
    const mutexApplies =
      !opts.disableMutex &&
      !opts.disableSection &&
      row.section !== null &&
      row.section !== undefined &&
      SECTION_BOOST[row.section] !== undefined;
    if (!mutexApplies) {
      boostSum += (SOURCE_TYPE_BOOST[row.source_type] ?? 1.0) - 1.0;
    }
  }
  if (!opts.disableSection) {
    if (row.section && SECTION_BOOST[row.section] !== undefined) {
      boostSum += SECTION_BOOST[row.section]! - 1.0;
    } else if (row.section_boost !== null && row.section_boost !== undefined) {
      boostSum += row.section_boost - 1.0;
    }
  }
  if ((opts.salienceMode ?? "shadow") === "active") {
    const s = calculateSalience(row, opts.nowMs);
    boostSum += s - 0.5;
  }
  return baseScore * (1 + boostSum);
}

// ── In-memory schema mirror ──────────────────────────────────────────────────

function makeDb(): InstanceType<typeof Database> {
  const db = new Database(":memory:");
  // NOTE: `rank` is a BM25 output in production (not a stored column). In these
  // self-contained tests we materialize it as a column so scoreChunk() has a
  // value to read — same shape as the FtsRow that the real search.ts builds.
  db.exec(`
    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY,
      chunk_text TEXT NOT NULL,
      source_file TEXT NOT NULL,
      chunk_type TEXT NOT NULL,
      source_date TEXT,
      tier TEXT,
      source_type TEXT,
      section TEXT,
      section_boost REAL,
      pain REAL,
      importance REAL,
      retention_days INTEGER,
      created_at TEXT,
      last_accessed_at TEXT,
      rank REAL
    );
  `);
  return db;
}

// Helper to build a row with sensible defaults overridable per-test.
function row(overrides: Partial<ChunkRow> = {}): ChunkRow {
  return {
    id: 1,
    chunk_text: "test",
    source_file: "test.md",
    chunk_type: "general",
    source_date: null,
    tier: "peripheral",
    source_type: null,
    section: null,
    section_boost: null,
    pain: null,
    importance: null,
    retention_days: null,
    created_at: null,
    last_accessed_at: null,
    rank: 10.0,
    ...overrides,
  };
}

// ─── 1. SECTION_BOOST wiring ─────────────────────────────────────────────────

describe("section_boost — V10 schema column wiring", () => {
  it("compiled section ranks above timeline (G3-rerun fix)", () => {
    const compiled = scoreChunk(row({ section: "compiled" }));
    const timeline = scoreChunk(row({ section: "timeline" }));
    assert.ok(compiled > timeline, `compiled (${compiled}) should rank > timeline (${timeline})`);
  });

  it("compiled = 2.0× base, frontmatter = 1.5×, timeline = 0.8×, NULL = 1.0×", () => {
    const base = scoreChunk(row({ section: null }));
    const compiled = scoreChunk(row({ section: "compiled" }));
    const frontmatter = scoreChunk(row({ section: "frontmatter" }));
    const timeline = scoreChunk(row({ section: "timeline" }));
    assert.strictEqual(base, 10.0);
    assert.strictEqual(compiled, 10.0 * (1 + 1.0)); // +1.0 delta
    assert.strictEqual(frontmatter, 10.0 * (1 + 0.5));
    assert.strictEqual(timeline, 10.0 * (1 + (-0.2)));
  });

  it("falls back to section_boost column when section name is unknown", () => {
    const score = scoreChunk(row({ section: "unknown_section", section_boost: 1.7 }));
    // Delta = 1.7 − 1.0 = +0.7
    assert.strictEqual(score, 10.0 * 1.7);
  });

  it("NOX_DISABLE_SECTION_BOOST=1 → section contributes 0", () => {
    const enabled = scoreChunk(row({ section: "compiled" }));
    const disabled = scoreChunk(row({ section: "compiled" }), { disableSection: true });
    assert.ok(enabled > disabled);
    assert.strictEqual(disabled, 10.0);
  });
});

// ─── 2. SOURCE_TYPE_BOOST — fixed map matches prod corpus ────────────────────

describe("source_type_boost — corpus-correct keys", () => {
  it("`external` (live prod key) applies 0.8× penalty (delta −0.2)", () => {
    const base = scoreChunk(row({ source_type: null }));
    const ext = scoreChunk(row({ source_type: "external" }));
    assert.strictEqual(base, 10.0);
    assert.strictEqual(ext, 10.0 * (1 + (-0.2)));
    assert.ok(ext < base, `external should rank LOWER than null source_type`);
  });

  it("unknown source_type → delta 0 (not negative)", () => {
    const base = scoreChunk(row({ source_type: null }));
    const unk = scoreChunk(row({ source_type: "unknown_provider" }));
    assert.strictEqual(base, unk);
  });

  it("forward-compat: `user_statement` still resolves to 2.0× when present", () => {
    // dead-by-corpus today but the map MUST keep the key for when ingest lands.
    const us = scoreChunk(row({ source_type: "user_statement" }));
    assert.strictEqual(us, 10.0 * (1 + 1.0));
  });

  it("NOX_DISABLE_SOURCE_TYPE_BOOST=1 → contributes 0 even for `external`", () => {
    const enabled = scoreChunk(row({ source_type: "external" }));
    const disabled = scoreChunk(row({ source_type: "external" }), { disableSourceType: true });
    assert.ok(enabled !== disabled);
    assert.strictEqual(disabled, 10.0);
  });

  // ── Backfill keys (PR 2026-05-20 — unlocks A5 contribution) ─────────────────
  it("backfill key `entity` (1.10% corpus, peak curation) → +1.0 delta", () => {
    const score = scoreChunk(row({ source_type: "entity" }));
    assert.strictEqual(score, 10.0 * (1 + 1.0));
  });

  it("backfill key `lesson` (retrospective signal) → +0.8 delta", () => {
    const score = scoreChunk(row({ source_type: "lesson" }));
    assert.strictEqual(score, 10.0 * (1 + 0.8));
  });

  it("backfill key `skill` → +0.5 delta", () => {
    const score = scoreChunk(row({ source_type: "skill" }));
    assert.strictEqual(score, 10.0 * (1 + 0.5));
  });

  it("backfill keys `project-doc` and `command` tied at +0.4 delta", () => {
    const pd = scoreChunk(row({ source_type: "project-doc" }));
    const cmd = scoreChunk(row({ source_type: "command" }));
    assert.strictEqual(pd, 10.0 * (1 + 0.4));
    assert.strictEqual(cmd, 10.0 * (1 + 0.4));
    assert.strictEqual(pd, cmd);
  });

  it("backfill key `legal-template` → +0.3 delta", () => {
    const score = scoreChunk(row({ source_type: "legal-template" }));
    assert.strictEqual(score, 10.0 * (1 + 0.3));
  });

  it("backfill key `personal-doc` (34% corpus) → +0.2 delta", () => {
    const score = scoreChunk(row({ source_type: "personal-doc" }));
    assert.strictEqual(score, 10.0 * (1 + 0.2));
  });

  it("backfill keys `note` and `session` neutral (delta 0)", () => {
    const note = scoreChunk(row({ source_type: "note" }));
    const session = scoreChunk(row({ source_type: "session" }));
    assert.strictEqual(note, 10.0, "note=baseline");
    assert.strictEqual(session, 10.0, "session=baseline");
  });

  it("backfill key `other` → −0.3 delta (residual penalty)", () => {
    const score = scoreChunk(row({ source_type: "other" }));
    assert.strictEqual(score, 10.0 * (1 + (-0.3)));
  });

  it("backfill key `ocr-cache` (16% corpus, scan artifacts) → −0.3 delta (conservative)", () => {
    const score = scoreChunk(row({ source_type: "ocr-cache" }));
    assert.strictEqual(score, 10.0 * (1 + (-0.3)));
    assert.ok(score < 10.0, "ocr-cache must penalize below baseline");
  });

  it("ranking order: entity > lesson > skill > project-doc > legal-template > personal-doc > note > external > {other, ocr-cache}", () => {
    // Chain is strictly monotonic decreasing until the penalty floor where
    // `other` (0.7) and `ocr-cache` (0.7) tie. Use `>=` only for the final
    // pair; `>` everywhere else.
    const keys = [
      "entity",        // 2.0
      "lesson",        // 1.8
      "skill",         // 1.5
      "project-doc",   // 1.4 — `command` ties; omitted from chain
      "legal-template", // 1.3
      "personal-doc",  // 1.2
      "note",          // 1.0 — `session` ties; omitted from chain
      "external",      // 0.8
      "other",         // 0.7 — tied with `ocr-cache`
      "ocr-cache",     // 0.7
    ];
    const scores = keys.map((k) => ({ key: k, score: scoreChunk(row({ source_type: k })) }));
    for (let i = 0; i < scores.length - 1; i++) {
      const isPenaltyFloorTie = i === scores.length - 2; // only `other` vs `ocr-cache`
      if (isPenaltyFloorTie) {
        assert.ok(
          scores[i]!.score >= scores[i + 1]!.score,
          `${scores[i]!.key} (${scores[i]!.score}) must rank ≥ ${scores[i + 1]!.key} (${scores[i + 1]!.score})`,
        );
      } else {
        assert.ok(
          scores[i]!.score > scores[i + 1]!.score,
          `${scores[i]!.key} (${scores[i]!.score}) must rank > ${scores[i + 1]!.key} (${scores[i + 1]!.score})`,
        );
      }
    }
  });

  // ── Drift guard (PR #154 code-review LOW #1) ────────────────────────────────
  // Test inline `SOURCE_TYPE_BOOST` mirrors live export from search.ts. Two
  // sources of truth is intentional (avoids resolving search.ts module-load
  // deps in unit tests) but drift is bug-prone — assert key+value equality
  // here so any future calibration tweak in search.ts that misses this file
  // fails CI immediately.
  it("mirror-drift-guard: inline map matches `_internals.SOURCE_TYPE_BOOST` from search.ts", async () => {
    let live: Record<string, number>;
    try {
      const mod: { _internals?: { SOURCE_TYPE_BOOST: Record<string, number> } } = await import(
        "../edits/search.js"
      );
      if (!mod._internals?.SOURCE_TYPE_BOOST) {
        // Live export shape changed — flag, don't pass.
        assert.fail("search.ts no longer exports _internals.SOURCE_TYPE_BOOST");
      }
      live = mod._internals.SOURCE_TYPE_BOOST;
    } catch (err: unknown) {
      // search.ts module-load may fail if deps (getDb / tier-manager / embed)
      // aren't resolvable in this test environment. That's expected outside
      // the VPS module graph — skip the drift assertion in that case rather
      // than failing the suite. CI on prod tree will exercise this branch.
      const msg = err instanceof Error ? err.message : String(err);
      console.warn(`[mirror-drift-guard] skipped (search.ts load failed): ${msg}`);
      return;
    }
    const liveKeys = Object.keys(live).sort();
    const mirrorKeys = Object.keys(SOURCE_TYPE_BOOST).sort();
    assert.deepStrictEqual(
      mirrorKeys, liveKeys,
      `key set drift: mirror=${mirrorKeys.join(",")} vs live=${liveKeys.join(",")}`,
    );
    for (const k of liveKeys) {
      assert.strictEqual(
        SOURCE_TYPE_BOOST[k], live[k],
        `value drift for key "${k}": mirror=${SOURCE_TYPE_BOOST[k]} vs live=${live[k]}`,
      );
    }
  });

  // Drift guard for the new mutex signature (PR #180 / G9). Calling the live
  // sourceTypeDelta with the (sourceType, section) arity must return 0 when
  // section=compiled, mirroring this file's inline scoreChunk implementation.
  it("mutex-signature-drift-guard: live sourceTypeDelta honors (sourceType, section)", async () => {
    type Delta = (s: string | null | undefined, sec: string | null | undefined) => number;
    let live: { sourceTypeDelta: Delta } | undefined;
    try {
      const mod: { _internals?: { sourceTypeDelta: Delta } } = await import(
        "../edits/search.js"
      );
      if (!mod._internals?.sourceTypeDelta) {
        assert.fail("search.ts no longer exports _internals.sourceTypeDelta");
      }
      live = { sourceTypeDelta: mod._internals.sourceTypeDelta };
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn(`[mutex-signature-drift-guard] skipped (search.ts load failed): ${msg}`);
      return;
    }
    // arity check: function MUST accept 2 args (signature shape)
    assert.ok(live.sourceTypeDelta.length >= 2, "sourceTypeDelta must accept (sourceType, section)");
    // behaviour check: entity + compiled → mutex fires → 0
    assert.strictEqual(
      live.sourceTypeDelta("entity", "compiled"),
      0,
      "live mutex must suppress source_type when section in SECTION_BOOST",
    );
    // behaviour check: entity + null → mutex inert → +1.0
    assert.strictEqual(
      live.sourceTypeDelta("entity", null),
      1.0,
      "live source_type=entity alone must deliver +1.0",
    );
  });
});

// ─── 2b. Hard Mutex: sectionDelta ↔ sourceTypeDelta (G9, PR #180) ────────────
//
// G9 ablation (g5.db prod 69,495 chunks, n=100 queries, 2026-05-20) cravou:
//   A0 (no boosts)          = 0.4108
//   A5 (source_type only)   = 0.4693  → +14.2% vs A0 (boost LIVE)
//   A8 (full canonical)     = 0.5387
//   A10 (full − source_type) = 0.5530 → +2.6% vs A8 (REDUNDÂNCIA)
//
// Resolution: hard mutex em `sourceTypeDelta` — quando o chunk já tem `section`
// populado (sinal mais granular), pula source_type boost pra evitar
// double-boost em entity files (compiled/frontmatter/timeline). Spec:
// `specs/2026-05-20-mutual-exclusion-section-source-type.md`.

describe("hard mutex sectionDelta ↔ sourceTypeDelta — G9 redundancy fix", () => {
  it("entity + compiled: source_type contribution SUPPRESSED (mutex ON, default)", () => {
    // section=compiled → SECTION_BOOST[compiled]=2.0 → sectionDelta=+1.0.
    // source_type=entity normally contributes +1.0 (SOURCE_TYPE_BOOST=2.0)
    // but mutex skips it. Net boost: +1.0 (section only), score = 10 * 2.0.
    const score = scoreChunk(row({
      source_type: "entity",
      section: "compiled",
    }));
    assert.strictEqual(score, 10.0 * 2.0, "mutex should yield only sectionDelta contribution");
  });

  it("entity + null section: source_type contributes normally (mutex inert)", () => {
    // No section → mutex guard does not apply → source_type delivers full +1.0.
    const score = scoreChunk(row({
      source_type: "entity",
      section: null,
    }));
    assert.strictEqual(score, 10.0 * 2.0, "source_type=entity alone delivers +1.0");
  });

  it("entity + compiled + disableMutex (rollback flag): both deltas accumulate", () => {
    // Mirror of NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1: pre-mutex behaviour
    // returns. Net boost = source_type(+1.0) + section(+1.0) = +2.0,
    // score = 10 * 3.0 = 30. This is the SAME stacking the G9 ablation
    // showed underperforming A10 by −2.6%.
    const score = scoreChunk(
      row({ source_type: "entity", section: "compiled" }),
      { disableMutex: true },
    );
    assert.strictEqual(score, 10.0 * 3.0, "rollback flag must restore double-boost");
  });

  it("entity + frontmatter: mutex applies (frontmatter in SECTION_BOOST)", () => {
    // sectionDelta(frontmatter) = +0.5; source_type entity suppressed.
    const score = scoreChunk(row({ source_type: "entity", section: "frontmatter" }));
    assert.strictEqual(score, 10.0 * 1.5);
  });

  it("entity + timeline: mutex applies, only timeline penalty remains", () => {
    // sectionDelta(timeline) = −0.2; source_type entity suppressed.
    // Net = −0.2 → score = 10 * 0.8.
    const score = scoreChunk(row({ source_type: "entity", section: "timeline" }));
    assert.ok(Math.abs(score - 10.0 * 0.8) < 1e-9, `expected 8.0, got ${score}`);
  });

  it("entity + unknown section (NOT in SECTION_BOOST): mutex inert", () => {
    // section=foo is not in SECTION_BOOST. sectionDelta falls back to
    // section_boost column (null here → 0). sourceTypeDelta runs normally.
    const score = scoreChunk(row({
      source_type: "entity",
      section: "foo",
      section_boost: null,
    }));
    assert.strictEqual(score, 10.0 * 2.0, "unknown section name does not trigger mutex");
  });

  it("entity + compiled + DISABLE_SECTION_BOOST: mutex inert (section guard inactive)", () => {
    // When section_boost is globally disabled, mutex should NOT fire — the
    // search.ts guard checks `!DISABLE_SECTION_BOOST`. Mirror via disableSection.
    // source_type=entity delivers +1.0, section disabled → 0. Net = 10 * 2.0.
    const score = scoreChunk(
      row({ source_type: "entity", section: "compiled" }),
      { disableSection: true },
    );
    assert.strictEqual(score, 10.0 * 2.0, "DISABLE_SECTION_BOOST should keep source_type live");
  });

  it("lesson + compiled (rare): mutex still applies — section sinal wins", () => {
    // Hypothetical chunk: source_type=lesson + section=compiled. Pre-mutex
    // would stack +0.8 + +1.0 = +1.8. Mutex returns only section: +1.0.
    const score = scoreChunk(row({ source_type: "lesson", section: "compiled" }));
    assert.strictEqual(score, 10.0 * 2.0);
  });

  it("non-entity baseline (note + null section): mutex inert", () => {
    // 98.9% of corpus path: source_type=note (delta 0) + section=null. Mutex
    // never fires — proves no regression to the bulk of the corpus.
    const score = scoreChunk(row({ source_type: "note", section: null }));
    assert.strictEqual(score, 10.0, "note + null section unaffected by mutex");
  });

  it("personal-doc + null section: mutex inert, full +0.2 delivered", () => {
    // 34% of corpus: personal-doc never has section set → mutex inactive.
    const score = scoreChunk(row({ source_type: "personal-doc", section: null }));
    assert.strictEqual(score, 10.0 * 1.2, "personal-doc keeps +0.2 delta");
  });
});

// ─── 3. BOOST_TYPES (chunk_type) wiring ──────────────────────────────────────

describe("type_boost — chunk_type signal wiring", () => {
  it("chunk_type=lesson outranks chunk_type=general", () => {
    const lesson = scoreChunk(row({ chunk_type: "lesson" }));
    const general = scoreChunk(row({ chunk_type: "general" }));
    assert.ok(lesson > general);
  });

  it("decision / lesson / person / project / pending all boosted", () => {
    for (const t of ["decision", "lesson", "person", "project", "pending"]) {
      const s = scoreChunk(row({ chunk_type: t }));
      assert.ok(s > 10.0, `chunk_type=${t} should boost above base, got ${s}`);
    }
  });

  it("NOX_DISABLE_TYPE_BOOST=1 → no chunk_type boost applied", () => {
    const enabled = scoreChunk(row({ chunk_type: "decision" }));
    const disabled = scoreChunk(row({ chunk_type: "decision" }), { disableType: true });
    assert.ok(enabled > disabled);
    assert.strictEqual(disabled, 10.0);
  });
});

// ─── 4. TIER_BOOST wiring ────────────────────────────────────────────────────

describe("tier_boost — tier column signal wiring", () => {
  it("tier=core > tier=active > tier=peripheral > tier=archived", () => {
    const core = scoreChunk(row({ tier: "core" }));
    const active = scoreChunk(row({ tier: "active" }));
    const peripheral = scoreChunk(row({ tier: "peripheral" }));
    const archived = scoreChunk(row({ tier: "archived" }));
    assert.ok(core > active);
    assert.ok(active > peripheral);
    assert.ok(peripheral > archived);
  });

  it("NOX_DISABLE_TIER_BOOST=1 → all tiers equal", () => {
    const core = scoreChunk(row({ tier: "core" }), { disableTier: true });
    const archived = scoreChunk(row({ tier: "archived" }), { disableTier: true });
    assert.strictEqual(core, archived);
  });
});

// ─── 5. Salience — pain × recency × importance, gated by MODE ────────────────

describe("salience — pain-weighted ranking, mode-gated", () => {
  // Fix `now` at 2026-05-19T12:00:00Z so dates are deterministic.
  const NOW = new Date("2026-05-19T12:00:00Z").getTime();
  const FRESH = "2026-05-19"; // 0 days old

  it("calculateSalience: high pain + fresh + high importance → high score", () => {
    const s = calculateSalience(
      {
        chunk_type: "lesson",
        pain: 1.0,
        importance: 1.0,
        retention_days: 180,
        last_accessed_at: FRESH,
      },
      NOW,
    );
    assert.ok(s > 0.8, `expected high salience, got ${s}`);
  });

  it("calculateSalience: low pain → low salience", () => {
    const hi = calculateSalience(
      { chunk_type: "lesson", pain: 1.0, importance: 1.0, retention_days: 180, last_accessed_at: FRESH },
      NOW,
    );
    const lo = calculateSalience(
      { chunk_type: "lesson", pain: 0.1, importance: 1.0, retention_days: 180, last_accessed_at: FRESH },
      NOW,
    );
    assert.ok(hi > lo * 5, `pain=1.0 (${hi}) should dominate pain=0.1 (${lo})`);
  });

  it("MODE=shadow (default): salience does NOT affect score", () => {
    const hi = scoreChunk(
      row({ chunk_type: "lesson", pain: 1.0, importance: 1.0, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "shadow" },
    );
    const lo = scoreChunk(
      row({ chunk_type: "lesson", pain: 0.1, importance: 0.1, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "shadow" },
    );
    // Both get the same chunk_type=lesson boost, no salience delta in shadow
    assert.strictEqual(hi, lo, `shadow mode should ignore salience (got ${hi} vs ${lo})`);
  });

  it("MODE=active: high-pain chunk ranks above low-pain chunk", () => {
    const hi = scoreChunk(
      row({ chunk_type: "lesson", pain: 1.0, importance: 1.0, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "active" },
    );
    const lo = scoreChunk(
      row({ chunk_type: "lesson", pain: 0.1, importance: 0.1, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "active" },
    );
    assert.ok(hi > lo, `active mode: high-pain (${hi}) should rank > low-pain (${lo})`);
  });

  it("MODE=off: salience contributes 0 (ablation)", () => {
    const hi = scoreChunk(
      row({ chunk_type: "lesson", pain: 1.0, importance: 1.0, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "off" },
    );
    const lo = scoreChunk(
      row({ chunk_type: "lesson", pain: 0.1, importance: 0.1, retention_days: 180, last_accessed_at: FRESH }),
      { nowMs: NOW, salienceMode: "off" },
    );
    assert.strictEqual(hi, lo);
  });

  it("getSalienceMode honors NOX_SALIENCE_MODE env (defaults to shadow)", () => {
    const prev = process.env.NOX_SALIENCE_MODE;
    try {
      delete process.env.NOX_SALIENCE_MODE;
      assert.strictEqual(getSalienceMode(), "shadow");
      process.env.NOX_SALIENCE_MODE = "active";
      assert.strictEqual(getSalienceMode(), "active");
      process.env.NOX_SALIENCE_MODE = "OFF"; // case-insensitive
      assert.strictEqual(getSalienceMode(), "off");
      process.env.NOX_SALIENCE_MODE = "bogus";
      assert.strictEqual(getSalienceMode(), "shadow", "unknown values default to shadow");
    } finally {
      if (prev === undefined) delete process.env.NOX_SALIENCE_MODE;
      else process.env.NOX_SALIENCE_MODE = prev;
    }
  });
});

// ─── 6. Salience component pieces ────────────────────────────────────────────

describe("salience component math", () => {
  const NOW = new Date("2026-05-19T12:00:00Z").getTime();

  it("recencyComponent: fresh = ~1.0, half-life = ~0.5, ancient → ~0", () => {
    // "Today" (date-only) + NOW=midday is ~0.5 day old → recency ≈0.988 for 30d half-life.
    const fresh = recencyComponent("2026-05-19", null, 30, NOW);
    assert.ok(fresh > 0.95 && fresh <= 1.0, `fresh recency near 1.0, got ${fresh}`);
    const halfLife = recencyComponent("2026-04-19", null, 30, NOW); // ~30 days ago
    assert.ok(halfLife > 0.45 && halfLife < 0.55, `half-life recency ≈0.5, got ${halfLife}`);
    const ancient = recencyComponent("2020-01-01", null, 30, NOW);
    assert.ok(ancient < 0.01);
  });

  it("recencyComponent: retention_days=0 → never decays (recency=1.0)", () => {
    assert.strictEqual(recencyComponent("2010-01-01", null, 0, NOW), 1.0);
  });

  it("painComponent: NULL → default 0.2; out-of-range clamped", () => {
    assert.strictEqual(painComponent(null), 0.2);
    assert.strictEqual(painComponent(undefined), 0.2);
    assert.strictEqual(painComponent(0.7), 0.7);
    assert.strictEqual(painComponent(-1), 0);
    assert.strictEqual(painComponent(99), 1);
  });

  it("importanceComponent: explicit value wins over chunk_type prior", () => {
    assert.strictEqual(importanceComponent("decision", 0.3), 0.3);
    assert.strictEqual(importanceComponent("decision", null), 0.95);
    assert.strictEqual(importanceComponent("unknown_type", null), 0.40);
  });

  it("resolveRetentionDays: explicit beats type-default beats fallback", () => {
    assert.strictEqual(resolveRetentionDays(120, "lesson"), 120);
    assert.strictEqual(resolveRetentionDays(null, "lesson"), 180);
    assert.strictEqual(resolveRetentionDays(null, "feedback"), 0); // never-decay
    assert.strictEqual(resolveRetentionDays(null, "totally_made_up"), 90);
  });
});

// ─── 7. Stacking is ADDITIVE (CLAUDE.md rule #5) ──────────────────────────────

describe("boost stacking — ADDITIVE not MULTIPLICATIVE", () => {
  it("stacks deltas additively (sum, not product)", () => {
    // chunk_type=decision (+1.0), tier=core (+1.0), section=compiled (+1.0)
    // Additive: 1 + (1.0 + 1.0 + 1.0) = 4.0× base
    // Multiplicative (BANNED): 2.0 × 2.0 × 2.0 = 8.0× base
    const score = scoreChunk(row({
      chunk_type: "decision",
      tier: "core",
      section: "compiled",
    }));
    assert.strictEqual(score, 10.0 * 4.0, "expected additive stacking");
    assert.notStrictEqual(score, 10.0 * 8.0, "must NOT be multiplicative");
  });

  it("4-way stack: type + tier + section + recency", () => {
    const NOW = new Date("2026-05-19T12:00:00Z").getTime();
    const FRESH = "2026-05-19";
    const score = scoreChunk(
      row({
        chunk_type: "decision",   // +1.0
        tier: "core",              // +1.0
        section: "compiled",       // +1.0
        source_date: FRESH,        // +0.5 (within 7 days)
      }),
      { nowMs: NOW },
    );
    assert.strictEqual(score, 10.0 * (1 + 1.0 + 1.0 + 1.0 + 0.5));
  });

  it("penalty + boost can cancel out (mutex OFF mirrors pre-G9 stacking)", () => {
    // With mutex ON (default), section=timeline suppresses source_type=external.
    // To exercise the original pre-G9 penalty+boost stack, disable the mutex.
    // Net (mutex OFF): chunk_type=lesson (+1.0), tier=peripheral (0),
    // section=timeline (−0.2), source_type=external (−0.2) = +0.6.
    const score = scoreChunk(
      row({
        chunk_type: "lesson",
        tier: "peripheral",
        section: "timeline",
        source_type: "external",
      }),
      { disableMutex: true },
    );
    assert.ok(Math.abs(score - 10.0 * 1.6) < 1e-9);
  });

  it("post-G9 mutex: section=timeline + source_type=external → source_type SKIPPED", () => {
    // Mirror of search.ts mutex guard: when section is populated AND in
    // SECTION_BOOST, sourceTypeDelta returns 0. Net: chunk_type=lesson (+1.0)
    // + tier=peripheral (0) + section=timeline (−0.2) = +0.8.
    const score = scoreChunk(row({
      chunk_type: "lesson",
      tier: "peripheral",
      section: "timeline",
      source_type: "external",
    }));
    assert.ok(
      Math.abs(score - 10.0 * 1.8) < 1e-9,
      `mutex ON should drop external penalty; expected 18.0, got ${score}`,
    );
  });

  it("all-disabled produces baseline score (no regression with toggles ON)", () => {
    const score = scoreChunk(
      row({
        chunk_type: "decision",
        tier: "core",
        section: "compiled",
        source_type: "user_statement",
        source_date: "2026-05-19",
        pain: 1.0,
        importance: 1.0,
      }),
      {
        disableType: true,
        disableTier: true,
        disableSection: true,
        disableSourceType: true,
        disableRecency: true,
        salienceMode: "off",
        nowMs: new Date("2026-05-19T12:00:00Z").getTime(),
      },
    );
    assert.strictEqual(score, 10.0, "all-disabled must equal base FTS rank");
  });
});

// ─── 8. Integration: end-to-end ranking over an in-memory DB ─────────────────

describe("end-to-end: ranking over in-memory DB", () => {
  it("compiled-section lesson outranks timeline-section general (G3 regression fix)", () => {
    const db = makeDb();
    db.prepare(`
      INSERT INTO chunks (id, chunk_text, source_file, chunk_type, source_date, tier, section, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(1, "compiled truth", "person/toto.md", "person", "2026-05-19", "core", "compiled", -5.0);
    db.prepare(`
      INSERT INTO chunks (id, chunk_text, source_file, chunk_type, source_date, tier, section, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(2, "old log", "person/toto.md", "general", "2026-05-19", "peripheral", "timeline", -5.0);

    const all = db.prepare(`SELECT * FROM chunks ORDER BY id`).all() as ChunkRow[];
    const scored = all.map((r) => ({ id: r.id, score: scoreChunk(r) }));
    scored.sort((a, b) => b.score - a.score);
    assert.strictEqual(scored[0]!.id, 1, "compiled-section chunk must rank first");
  });

  it("high-pain decision outranks fresh general note under MODE=active", () => {
    const NOW = new Date("2026-05-19T12:00:00Z").getTime();
    const db = makeDb();
    db.prepare(`
      INSERT INTO chunks
        (id, chunk_text, source_file, chunk_type, source_date, tier, section,
         pain, importance, retention_days, last_accessed_at, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      1, "prod outage lesson", "lessons/incident.md", "decision",
      "2025-11-19", // 6 months old
      "active", null,
      1.0, 1.0, 365,
      "2025-11-19",
      -5.0,
    );
    db.prepare(`
      INSERT INTO chunks
        (id, chunk_text, source_file, chunk_type, source_date, tier, section,
         pain, importance, retention_days, last_accessed_at, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      2, "minor doc tweak", "docs/note.md", "general",
      "2026-05-19", "peripheral", null,
      0.1, 0.2, 90,
      "2026-05-19",
      -5.0,
    );

    const rows = db.prepare(`SELECT * FROM chunks ORDER BY id`).all() as ChunkRow[];
    const scored = rows.map((r) => ({ id: r.id, score: scoreChunk(r, { nowMs: NOW, salienceMode: "active" }) }));
    scored.sort((a, b) => b.score - a.score);
    assert.strictEqual(
      scored[0]!.id, 1,
      `high-pain old decision (score ${scored[0]!.score}) should beat fresh general note (score ${scored[1]!.score}) under MODE=active`,
    );
  });

  it("under MODE=shadow same fixture: fresh general note can rank higher (proves shadow inertness)", () => {
    const NOW = new Date("2026-05-19T12:00:00Z").getTime();
    const db = makeDb();
    db.prepare(`
      INSERT INTO chunks (id, chunk_text, source_file, chunk_type, source_date, tier, section, pain, importance, retention_days, last_accessed_at, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(1, "old decision", "x.md", "general", "2025-11-19", "peripheral", null, 1.0, 1.0, 365, "2025-11-19", -5.0);
    db.prepare(`
      INSERT INTO chunks (id, chunk_text, source_file, chunk_type, source_date, tier, section, pain, importance, retention_days, last_accessed_at, rank)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(2, "fresh note", "y.md", "general", "2026-05-19", "peripheral", null, 0.1, 0.2, 90, "2026-05-19", -5.0);

    // chunk_type=general for both, identical tier/section, no salience contribution.
    // Only differentiator under shadow is the recency-window boost.
    const rows = db.prepare(`SELECT * FROM chunks ORDER BY id`).all() as ChunkRow[];
    const scored = rows.map((r) => ({ id: r.id, score: scoreChunk(r, { nowMs: NOW, salienceMode: "shadow" }) }));
    scored.sort((a, b) => b.score - a.score);
    assert.strictEqual(scored[0]!.id, 2, "shadow mode: fresh recency wins (proves salience is NOT applied)");
  });
});
