/**
 * observability-evals.test.ts — F10 Phase B unit tests
 *
 * Covers:
 *   - inferDbSource (entity-eval / entity-eval-v2 / g5db / g9 / unknown)
 *   - gateBucketFromDir
 *   - parseAuditFile shape sniff (summary | aggregate | per-query array)
 *   - parseAuditFile graceful failure on missing/malformed JSON
 *   - buildEvalRows sort by ran_at ASC
 *   - matchAnnotations by UTC day
 *   - handleObsEvals: filter by db_source, limit, cache TTL respect, force flag
 *   - empty-data handling (no audit dirs)
 *
 * Cross-link: staged-1.7a/edits/evals.ts
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §"P1 EVAL DASHBOARD"
 */

import { test, describe, beforeEach, afterEach } from "node:test";
import assert from "node:assert/strict";
import { writeFileSync, mkdtempSync, mkdirSync, rmSync, utimesSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";

import {
  inferDbSource,
  gateBucketFromDir,
  isoDay,
  matchAnnotations,
  parseAuditFile,
  collectAuditFiles,
  loadAnnotations,
  buildEvalRows,
  handleObsEvals,
  _resetEvalsCache,
} from "../evals.js";

import type { GateAnnotation } from "../evals.js";

// ── Fixture helpers ───────────────────────────────────────────────────────────

function makeTmpDir(): string {
  return mkdtempSync(join(tmpdir(), "evals-test-"));
}

function writeJson(path: string, obj: unknown, mtimeSec?: number): void {
  writeFileSync(path, JSON.stringify(obj));
  if (mtimeSec !== undefined) {
    utimesSync(path, mtimeSec, mtimeSec);
  }
}

const SUMMARY_FIXTURE = {
  summary: {
    label: "a8_off_control",
    toggles: {},
    n_queries: 100,
    fixture_dir: "/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20",
    endpoint: "http://127.0.0.1:18803/api/search",
    ndcg_at_10: 0.5438,
    mrr: 0.5973,
    recall_at_10: 0.615,
    precision_at_5: 0.178,
    mean_latency_ms: 1529.6,
    p95_latency_ms: 2551.65,
    n_valid_queries: 100,
    wallclock_s: 152.99,
  },
  per_category: { "single-hop": { n: 20, ndcg_at_10: 0.57 } },
};

const AGG_FIXTURE = {
  aggregate: {
    active: {
      label: "mutex_active",
      toggles: {},
      n_queries: 100,
      fixture_dir: "/root/.openclaw/workspace/eval-data/entity-eval-v2",
      ndcg_at_10: 0.55,
      mrr: 0.59,
      recall_at_10: 0.62,
      precision_at_5: 0.18,
    },
    disabled: {
      label: "mutex_disabled",
      toggles: {},
      n_queries: 100,
      fixture_dir: "/root/.openclaw/workspace/eval-data/entity-eval-v2",
      ndcg_at_10: 0.54,
      mrr: 0.58,
      recall_at_10: 0.61,
      precision_at_5: 0.17,
    },
  },
};

// ── inferDbSource ─────────────────────────────────────────────────────────────

describe("inferDbSource", () => {
  test("entity-eval-v2 wins over entity-eval", () => {
    assert.equal(
      inferDbSource("/foo/eval-data/entity-eval-v2"),
      "entity-eval-v2.db",
    );
  });

  test("entity-eval base case", () => {
    assert.equal(
      inferDbSource("/foo/eval-data/entity-eval"),
      "entity-eval.db",
    );
  });

  test("g9-g5db pattern maps to g5.db (canonical post-G6)", () => {
    assert.equal(
      inferDbSource("/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20"),
      "g5.db",
    );
  });

  test("plain g9 fixture maps to g9.db", () => {
    assert.equal(
      inferDbSource("/foo/eval-data/g9"),
      "g9.db",
    );
  });

  test("null fixture → unknown.db", () => {
    assert.equal(inferDbSource(null), "unknown.db");
  });

  test("unmatched fixture → unknown.db", () => {
    assert.equal(inferDbSource("/foo/eval-data/bogus-2099"), "unknown.db");
  });

  test("trailing slash tolerated", () => {
    assert.equal(inferDbSource("/foo/eval-data/g5db/"), "g5.db");
  });
});

// ── gateBucketFromDir ─────────────────────────────────────────────────────────

describe("gateBucketFromDir", () => {
  test("standard naming", () => {
    assert.equal(gateBucketFromDir("/x/audits/data-g10b"), "g10b");
    assert.equal(gateBucketFromDir("/x/audits/data-g10d"), "g10d");
  });

  test("trailing slash tolerated", () => {
    assert.equal(gateBucketFromDir("/x/audits/data-g5/"), "g5");
  });

  test("non-matching leaf returns leaf", () => {
    assert.equal(gateBucketFromDir("/x/audits/legacy"), "legacy");
  });
});

// ── isoDay + matchAnnotations ─────────────────────────────────────────────────

describe("isoDay + matchAnnotations", () => {
  test("isoDay returns YYYY-MM-DD UTC", () => {
    const ms = Date.UTC(2026, 4, 21, 14, 0, 0);
    assert.equal(isoDay(ms), "2026-05-21");
  });

  test("matchAnnotations picks same-day labels", () => {
    const ann: GateAnnotation[] = [
      { date: "2026-05-20", label: "G6 reverse" },
      { date: "2026-05-21", label: "G10b" },
      { date: "2026-05-21", label: "G10c" },
    ];
    const ms = Date.UTC(2026, 4, 21, 17, 0, 0);
    assert.deepEqual(matchAnnotations(ms, ann), ["G10b", "G10c"]);
  });

  test("matchAnnotations returns [] when no match", () => {
    const ann: GateAnnotation[] = [{ date: "2026-05-19", label: "G5 V3" }];
    const ms = Date.UTC(2026, 4, 21, 0, 0, 0);
    assert.deepEqual(matchAnnotations(ms, ann), []);
  });
});

// ── parseAuditFile shape sniff ────────────────────────────────────────────────

describe("parseAuditFile", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = makeTmpDir();
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("summary shape emits ONE row with parsed fields", () => {
    const p = join(tmpDir, "summary.json");
    writeJson(p, SUMMARY_FIXTURE);
    const rows = parseAuditFile(p, 1_700_000_000_000, "g10d", []);
    assert.equal(rows.length, 1);
    const r = rows[0]!;
    assert.equal(r.config_id, "a8_off_control");
    assert.equal(r.db_source, "g5.db");
    assert.equal(r.ndcg_at_10, 0.5438);
    assert.equal(r.mrr, 0.5973);
    assert.equal(r.n_queries, 100);
    assert.equal(r.run_id, "g10d::a8_off_control");
  });

  test("aggregate shape emits TWO rows (one per agg key)", () => {
    const p = join(tmpDir, "derived.json");
    writeJson(p, AGG_FIXTURE);
    const rows = parseAuditFile(p, 1_700_000_000_000, "g10c", []);
    assert.equal(rows.length, 2);
    const ids = rows.map((r) => r.config_id).sort();
    assert.deepEqual(ids, ["mutex_active::active", "mutex_disabled::disabled"]);
    for (const r of rows) {
      assert.equal(r.db_source, "entity-eval-v2.db");
    }
  });

  test("per-query array (g10e shape) is skipped", () => {
    const p = join(tmpDir, "g10e.json");
    writeJson(p, [{ qid: "ad-001", rank_active: 2, rank_disabled: 1 }]);
    const rows = parseAuditFile(p, 1_700_000_000_000, "g10e", []);
    assert.deepEqual(rows, []);
  });

  test("missing file returns [] and does not throw", () => {
    const rows = parseAuditFile(join(tmpDir, "nope.json"), 1, "x", []);
    assert.deepEqual(rows, []);
  });

  test("malformed JSON returns [] and does not throw", () => {
    const p = join(tmpDir, "bad.json");
    writeFileSync(p, "{not json");
    const rows = parseAuditFile(p, 1, "x", []);
    assert.deepEqual(rows, []);
  });

  test("annotations attached to matching UTC day", () => {
    const p = join(tmpDir, "summary.json");
    writeJson(p, SUMMARY_FIXTURE);
    const ms = Date.UTC(2026, 4, 21, 12, 0, 0);
    const ann: GateAnnotation[] = [
      { date: "2026-05-21", label: "G10b per-category mutex" },
      { date: "2026-05-20", label: "G10 mutex validated" },
    ];
    const rows = parseAuditFile(p, ms, "g10b", ann);
    assert.equal(rows.length, 1);
    assert.deepEqual(rows[0]!.annotations, ["G10b per-category mutex"]);
  });

  test("summary with non-numeric ndcg coerces to null (does not crash)", () => {
    const p = join(tmpDir, "weird.json");
    writeJson(p, { summary: { label: "weird", ndcg_at_10: "n/a" } });
    const rows = parseAuditFile(p, 1, "wave-bogus", []);
    assert.equal(rows.length, 1);
    assert.equal(rows[0]!.ndcg_at_10, null);
  });
});

// ── collectAuditFiles + buildEvalRows ─────────────────────────────────────────

describe("collectAuditFiles + buildEvalRows", () => {
  let tmpDir: string;
  let auditsRoot: string;
  let annotationsPath: string;

  beforeEach(() => {
    tmpDir = makeTmpDir();
    auditsRoot = join(tmpDir, "audits");
    mkdirSync(auditsRoot, { recursive: true });
    // bucket 1
    const dirA = join(auditsRoot, "data-g10b");
    mkdirSync(dirA);
    writeJson(join(dirA, "mutex_active.json"), SUMMARY_FIXTURE, 1_700_000_001);
    writeJson(join(dirA, "mutex_disabled.json"), {
      summary: { ...SUMMARY_FIXTURE.summary, label: "mutex_disabled" },
    }, 1_700_000_002);
    // bucket 2 — older
    const dirB = join(auditsRoot, "data-g10c");
    mkdirSync(dirB);
    writeJson(join(dirB, "derived.json"), AGG_FIXTURE, 1_700_000_000);
    // non-audit dir should be ignored
    mkdirSync(join(auditsRoot, "ignore-me"));
    // annotations
    annotationsPath = join(tmpDir, "gates.json");
    writeFileSync(annotationsPath, JSON.stringify([
      { date: "2023-11-14", label: "Test gate" },
    ]));
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("collectAuditFiles only walks data-* dirs", () => {
    const files = collectAuditFiles(auditsRoot);
    const names = files.map((f) => f.file.split("/").slice(-2).join("/")).sort();
    assert.deepEqual(names, [
      "data-g10b/mutex_active.json",
      "data-g10b/mutex_disabled.json",
      "data-g10c/derived.json",
    ]);
  });

  test("buildEvalRows sorts by ran_at ASC", () => {
    const rows = buildEvalRows({ auditsRoot, annotationsPath });
    // mtimes: g10c=1_700_000_000, g10b active=...001, g10b disabled=...002
    // agg fixture emits 2 rows, summary emits 1 each → 4 total
    assert.equal(rows.length, 4);
    const tsList = rows.map((r) => r.ran_at_ms);
    for (let i = 1; i < tsList.length; i++) {
      assert.ok(tsList[i]! >= tsList[i - 1]!, `row ${i} out of order`);
    }
    // first row should belong to g10c bucket (oldest mtime)
    assert.equal(rows[0]!.run_id.startsWith("g10c::"), true);
  });

  test("buildEvalRows handles missing audits dir gracefully", () => {
    const rows = buildEvalRows({ auditsRoot: join(tmpDir, "nonexistent") });
    assert.deepEqual(rows, []);
  });
});

// ── loadAnnotations ──────────────────────────────────────────────────────────

describe("loadAnnotations", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = makeTmpDir();
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("returns [] on missing file", () => {
    assert.deepEqual(loadAnnotations(join(tmpDir, "nope.json")), []);
  });

  test("returns [] on malformed JSON", () => {
    const p = join(tmpDir, "bad.json");
    writeFileSync(p, "{not json");
    assert.deepEqual(loadAnnotations(p), []);
  });

  test("filters out invalid rows but keeps valid ones", () => {
    const p = join(tmpDir, "ann.json");
    writeFileSync(p, JSON.stringify([
      { date: "2026-05-21", label: "Good" },
      { date: "2026-05-21" }, // no label → skip
      { label: "Missing date" }, // no date → skip
      "not an object",
      { date: "2026-05-20", label: "Also good", description: "desc" },
    ]));
    const r = loadAnnotations(p);
    assert.equal(r.length, 2);
    assert.equal(r[0]!.label, "Good");
    assert.equal(r[1]!.description, "desc");
  });

  test("returns [] when JSON is not an array", () => {
    const p = join(tmpDir, "obj.json");
    writeFileSync(p, JSON.stringify({ not: "array" }));
    assert.deepEqual(loadAnnotations(p), []);
  });
});

// ── handleObsEvals: filter + limit + cache ───────────────────────────────────

describe("handleObsEvals (endpoint)", () => {
  let tmpDir: string;
  let auditsRoot: string;
  let annotationsPath: string;

  beforeEach(() => {
    _resetEvalsCache();
    tmpDir = makeTmpDir();
    auditsRoot = join(tmpDir, "audits");
    mkdirSync(auditsRoot, { recursive: true });
    const dirA = join(auditsRoot, "data-g10b");
    mkdirSync(dirA);
    writeJson(join(dirA, "a.json"), SUMMARY_FIXTURE); // g5.db
    writeJson(join(dirA, "b.json"), AGG_FIXTURE);     // entity-eval-v2.db x2
    annotationsPath = join(tmpDir, "gates.json");
    writeFileSync(annotationsPath, "[]");
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  test("default returns all rows sorted ASC", () => {
    const rows = handleObsEvals({}, { auditsRoot, annotationsPath });
    assert.equal(rows.length, 3);
    for (let i = 1; i < rows.length; i++) {
      assert.ok(rows[i]!.ran_at_ms >= rows[i - 1]!.ran_at_ms);
    }
  });

  test("db_source filter narrows results", () => {
    const rows = handleObsEvals(
      { dbSource: "g5.db" },
      { auditsRoot, annotationsPath },
    );
    assert.equal(rows.length, 1);
    assert.equal(rows[0]!.db_source, "g5.db");
  });

  test("db_source 'all' returns everything", () => {
    const rows = handleObsEvals(
      { dbSource: "all" },
      { auditsRoot, annotationsPath },
    );
    assert.equal(rows.length, 3);
  });

  test("limit caps the array", () => {
    const rows = handleObsEvals({ limit: 2 }, { auditsRoot, annotationsPath });
    assert.equal(rows.length, 2);
  });

  test("limit is clamped to [1, 2000]", () => {
    const r1 = handleObsEvals({ limit: 0 }, { auditsRoot, annotationsPath });
    assert.equal(r1.length, 1);
    const r2 = handleObsEvals({ limit: 999_999 }, { auditsRoot, annotationsPath });
    assert.equal(r2.length, 3);
  });

  test("cache hit within TTL skips disk reread", () => {
    let now = 1_000_000_000_000;
    const opts = {
      auditsRoot,
      annotationsPath,
      ttlMs: 5 * 60 * 1000,
      now: () => now,
    };
    const first = handleObsEvals({}, opts);
    assert.equal(first.length, 3);

    // Delete one fixture file — cache hit should still return 3
    rmSync(join(auditsRoot, "data-g10b", "a.json"));
    now += 1000; // 1s later
    const second = handleObsEvals({}, opts);
    assert.equal(second.length, 3, "cache should serve stale data within TTL");

    // Force flag bypasses cache
    const third = handleObsEvals({ force: true }, opts);
    assert.equal(third.length, 2, "force should reread");
  });

  test("cache expires after TTL", () => {
    let now = 1_000_000_000_000;
    const opts = {
      auditsRoot,
      annotationsPath,
      ttlMs: 60_000,
      now: () => now,
    };
    handleObsEvals({}, opts);
    rmSync(join(auditsRoot, "data-g10b", "a.json"));
    now += 60_001;
    const r = handleObsEvals({}, opts);
    assert.equal(r.length, 2, "post-TTL should reread");
  });

  test("empty audits root yields empty array", () => {
    rmSync(auditsRoot, { recursive: true, force: true });
    mkdirSync(auditsRoot);
    const r = handleObsEvals(
      { force: true },
      { auditsRoot, annotationsPath },
    );
    assert.deepEqual(r, []);
  });
});
