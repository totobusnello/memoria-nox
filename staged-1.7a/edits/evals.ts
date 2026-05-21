/**
 * evals.ts — F10 Phase B endpoint (Eval Dashboard)
 *
 * Adds one read-only endpoint under `/api/observability/*`:
 *
 *   GET /api/observability/evals?db_source=<filter>&limit=<n>
 *     Returns the historical ablation/gate runs aggregated from `audits/data-G*`
 *     directories on disk. Each row carries enough metric breadth to drive the
 *     dashboard (nDCG@10, MRR, recall@10), the DB it ran against (for the post-G6
 *     fiasco filter — see [[g6-ablation-results-2026-05-20]]), and a list of gate
 *     annotations that match its run date.
 *
 * Source data layer
 * -----------------
 * The audits directory is heterogeneous:
 *
 *   audits/data-g10b/*.json      → {summary, per_category} per run (a8 mutex active/disabled)
 *   audits/data-g10c/*.json      → derived aggregate: {aggregate.active, aggregate.disabled,
 *                                                       per_style_active, per_style_disabled}
 *   audits/data-g10d/*.json      → {summary, per_category} per t-threshold (a8d_t1/t2/baseline/control)
 *   audits/data-g10e/*.json      → derived per-query diff array (NOT a run aggregate — skipped)
 *
 * Each "summary" block has:
 *   { label, toggles, n_queries, fixture_dir, endpoint, ndcg_at_10, mrr,
 *     recall_at_10, precision_at_5, mean_latency_ms, p95_latency_ms,
 *     n_valid_queries, wallclock_s }
 *
 * Adapter strategy:
 *   - Walk `audits/data-<X>/` directories.
 *   - For each .json file, sniff the shape:
 *       (a) `{ summary, per_category, ... }`             → emit one row from summary
 *       (b) `{ aggregate: { active, disabled }, ... }`   → emit two rows (one per agg key)
 *       (c) anything else (e.g. per-query derived array) → skip with a warn to stderr
 *   - `ran_at` = file mtime (UTC ISO), since aggregate JSONs don't carry a wall-clock.
 *   - `db_source` = parsed from `summary.fixture_dir` (last path component → e.g.
 *     "g9-g5db-2026-05-20" → "g5.db"; the convention is documented in
 *     [[g6-ablation-results-2026-05-20]] and [[g10-mutex-validated-2026-05-20]]).
 *   - `config_id` = `summary.label` (already unique per run).
 *   - `run_id` = `<G-bucket>::<label>` for stability across reads.
 *
 * Annotations:
 *   - Loaded from `public/observability/gate-annotations.json` once per process.
 *   - A row gets every annotation whose date falls on the same UTC calendar day.
 *
 * Caching:
 *   - 5-minute in-memory TTL (spec allows). Single-process server, no infra.
 *   - Test harness exposes `_resetEvalsCache()` to clear state between cases.
 *
 * Spec: specs/2026-05-01-F10-observability-dashboard.md §"P1 EVAL DASHBOARD"
 * Status: Phase B implementation-ready
 */

import { readdirSync, readFileSync, statSync } from "fs";
import { join } from "path";

// ── Data shapes ───────────────────────────────────────────────────────────────

export interface EvalRow {
  run_id: string;
  config_id: string;
  db_source: string;
  ndcg_at_10: number | null;
  mrr: number | null;
  recall_at_10: number | null;
  precision_at_5: number | null;
  mean_latency_ms: number | null;
  p95_latency_ms: number | null;
  n_queries: number | null;
  ran_at: string;
  ran_at_ms: number;
  source_path: string;
  annotations: string[];
}

export interface GateAnnotation {
  date: string; // YYYY-MM-DD UTC
  label: string;
  description?: string;
}

interface SummaryShape {
  label?: unknown;
  toggles?: unknown;
  n_queries?: unknown;
  fixture_dir?: unknown;
  endpoint?: unknown;
  ndcg_at_10?: unknown;
  mrr?: unknown;
  recall_at_10?: unknown;
  precision_at_5?: unknown;
  mean_latency_ms?: unknown;
  p95_latency_ms?: unknown;
  n_valid_queries?: unknown;
  wallclock_s?: unknown;
}

// ── DB-source heuristic ───────────────────────────────────────────────────────

/**
 * Maps the fixture_dir leaf to the canonical DB filename, the way the team
 * tracks DBs in audits. The convention (per [[g6-ablation-results-2026-05-20]]
 * and follow-ups) is that a fixture directory contains a substring naming the
 * DB the eval was actually run against.
 *
 * Examples seen on disk:
 *   /root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20  → "g5.db"
 *   /…/eval-data/entity-eval-v2                              → "entity-eval-v2.db"
 *   /…/eval-data/entity-eval                                 → "entity-eval.db"
 *   /…/eval-data/g9                                          → "g9.db"
 *
 * Returns "unknown.db" if no match. Tests must cover the unknown fallback.
 */
export function inferDbSource(fixtureDir: string | null): string {
  if (!fixtureDir) return "unknown.db";
  const leaf = fixtureDir.split("/").filter((s) => s.length > 0).pop() ?? "";
  const lower = leaf.toLowerCase();
  // Specific names first (longest-prefix wins)
  if (lower.includes("entity-eval-v2")) return "entity-eval-v2.db";
  if (lower.includes("entity-eval")) return "entity-eval.db";
  if (lower.includes("g5db") || lower.includes("g5-db") || lower.includes("g5.db")) return "g5.db";
  if (lower.includes("g9-g5db")) return "g5.db";
  if (lower.includes("g9")) return "g9.db";
  if (lower.includes("g10")) return "g10.db";
  return "unknown.db";
}

/**
 * Bucket key derived from the data-Gxx directory name. Used for stable run_ids
 * and as a fallback config grouping in the UI.
 */
export function gateBucketFromDir(dir: string): string {
  // dir like "data-g10b" → "g10b"
  const leaf = dir.split("/").filter((s) => s.length > 0).pop() ?? "";
  const m = /^data-([A-Za-z0-9._-]+)$/.exec(leaf);
  return m && m[1] ? m[1] : leaf;
}

// ── Number coercion ───────────────────────────────────────────────────────────

function toNumOrNull(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  return null;
}

function toStringOrNull(v: unknown): string | null {
  return typeof v === "string" ? v : null;
}

// ── Annotation matching ───────────────────────────────────────────────────────

/**
 * Returns the YYYY-MM-DD UTC calendar string for an ms timestamp. ISO substring
 * is intentional — keeps the implementation portable across Node versions and
 * avoids a Date locale dependency.
 */
export function isoDay(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

/**
 * Picks every annotation whose `date` matches the run's UTC calendar day.
 * Returns label strings (not the full object) — the UI only needs the labels
 * to overlay vertical lines + tooltips, and richer data lives in the gate file.
 */
export function matchAnnotations(
  ranAtMs: number,
  annotations: GateAnnotation[],
): string[] {
  const day = isoDay(ranAtMs);
  const out: string[] = [];
  for (const a of annotations) {
    if (a.date === day) out.push(a.label);
  }
  return out;
}

// ── Adapter: parse one JSON file → 0..N rows ──────────────────────────────────

/**
 * Parses one audit JSON file into a list of normalized EvalRow.
 *
 * Returns `[]` (with stderr warning) when the file is unreadable, malformed,
 * or carries a shape we explicitly do not aggregate (e.g. per-query diff arrays).
 * Never throws — endpoint hardening per spec.
 */
export function parseAuditFile(
  filePath: string,
  fileMtimeMs: number,
  bucket: string,
  annotations: GateAnnotation[],
): EvalRow[] {
  let raw: string;
  try {
    raw = readFileSync(filePath, "utf-8");
  } catch (err) {
    process.stderr.write(`[evals] read failed: ${filePath}: ${String(err)}\n`);
    return [];
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    process.stderr.write(`[evals] JSON parse failed: ${filePath}: ${String(err)}\n`);
    return [];
  }

  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    // Per-query derived arrays (g10e) or other non-object shapes → skip silently.
    return [];
  }

  const obj = parsed as Record<string, unknown>;
  const ranAtMs = fileMtimeMs;
  const ranAt = new Date(ranAtMs).toISOString();
  const matched = matchAnnotations(ranAtMs, annotations);

  // Shape (b): derived aggregate { aggregate: { active, disabled }, ... }
  if (obj["aggregate"] && typeof obj["aggregate"] === "object" && !Array.isArray(obj["aggregate"])) {
    const agg = obj["aggregate"] as Record<string, unknown>;
    const rows: EvalRow[] = [];
    for (const key of Object.keys(agg)) {
      const sub = agg[key];
      if (sub && typeof sub === "object" && !Array.isArray(sub)) {
        const row = rowFromSummary(
          sub as SummaryShape,
          filePath,
          bucket,
          ranAt,
          ranAtMs,
          matched,
          `${key}`,
        );
        if (row) rows.push(row);
      }
    }
    return rows;
  }

  // Shape (a): { summary, per_category, ... }
  if (obj["summary"] && typeof obj["summary"] === "object" && !Array.isArray(obj["summary"])) {
    const row = rowFromSummary(
      obj["summary"] as SummaryShape,
      filePath,
      bucket,
      ranAt,
      ranAtMs,
      matched,
      null,
    );
    return row ? [row] : [];
  }

  // Unknown shape → skip silently.
  return [];
}

function rowFromSummary(
  s: SummaryShape,
  filePath: string,
  bucket: string,
  ranAt: string,
  ranAtMs: number,
  annotations: string[],
  configSuffix: string | null,
): EvalRow | null {
  const label = toStringOrNull(s.label);
  const configIdBase = label ?? "unknown";
  const configId = configSuffix ? `${configIdBase}::${configSuffix}` : configIdBase;
  const fixtureDir = toStringOrNull(s.fixture_dir);
  const dbSource = inferDbSource(fixtureDir);
  const nQueries = toNumOrNull(s.n_queries) ?? toNumOrNull(s.n_valid_queries);

  return {
    run_id: `${bucket}::${configId}`,
    config_id: configId,
    db_source: dbSource,
    ndcg_at_10: toNumOrNull(s.ndcg_at_10),
    mrr: toNumOrNull(s.mrr),
    recall_at_10: toNumOrNull(s.recall_at_10),
    precision_at_5: toNumOrNull(s.precision_at_5),
    mean_latency_ms: toNumOrNull(s.mean_latency_ms),
    p95_latency_ms: toNumOrNull(s.p95_latency_ms),
    n_queries: nQueries,
    ran_at: ranAt,
    ran_at_ms: ranAtMs,
    source_path: filePath,
    annotations,
  };
}

// ── Directory walker ──────────────────────────────────────────────────────────

/**
 * Returns the sorted absolute paths of `audits/data-*` JSON files under the
 * given root. Best-effort: directories that disappear mid-walk are skipped.
 */
export function collectAuditFiles(auditsRoot: string): Array<{
  file: string;
  bucket: string;
  mtimeMs: number;
}> {
  const out: Array<{ file: string; bucket: string; mtimeMs: number }> = [];
  let entries: string[];
  try {
    entries = readdirSync(auditsRoot);
  } catch {
    return out;
  }
  for (const name of entries) {
    if (!name.startsWith("data-")) continue;
    const dir = join(auditsRoot, name);
    let st;
    try {
      st = statSync(dir);
    } catch {
      continue;
    }
    if (!st.isDirectory()) continue;
    const bucket = gateBucketFromDir(dir);

    let files: string[];
    try {
      files = readdirSync(dir);
    } catch {
      continue;
    }
    for (const f of files) {
      if (!f.endsWith(".json")) continue;
      const fp = join(dir, f);
      let fst;
      try {
        fst = statSync(fp);
      } catch {
        continue;
      }
      if (!fst.isFile()) continue;
      out.push({ file: fp, bucket, mtimeMs: fst.mtimeMs });
    }
  }
  return out;
}

// ── Annotations loader ────────────────────────────────────────────────────────

/**
 * Best-effort load of the gate-annotations.json file. Returns `[]` on missing
 * file, parse error, or wrong shape — callers tolerate empty annotation list.
 */
export function loadAnnotations(filePath: string): GateAnnotation[] {
  let raw: string;
  try {
    raw = readFileSync(filePath, "utf-8");
  } catch {
    return [];
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    process.stderr.write(`[evals] annotations JSON parse failed: ${String(err)}\n`);
    return [];
  }
  if (!Array.isArray(parsed)) return [];
  const out: GateAnnotation[] = [];
  for (const item of parsed) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const rec = item as Record<string, unknown>;
    const date = toStringOrNull(rec["date"]);
    const label = toStringOrNull(rec["label"]);
    if (!date || !label) continue;
    const description = toStringOrNull(rec["description"]) ?? undefined;
    const ann: GateAnnotation = description !== undefined
      ? { date, label, description }
      : { date, label };
    out.push(ann);
  }
  return out;
}

// ── Cache layer ───────────────────────────────────────────────────────────────

interface EvalsCache {
  generatedAtMs: number;
  rows: EvalRow[];
}

const DEFAULT_TTL_MS = 5 * 60 * 1000;
let cached: EvalsCache | null = null;

/** Exposed for tests. */
export function _resetEvalsCache(): void {
  cached = null;
}

export interface EvalsQuery {
  /** Filter by db_source (e.g. "g5.db"). "all" or undefined = no filter. */
  dbSource?: string;
  /** Limit (default 500, max 2000). */
  limit?: number;
  /** Force refresh (skip TTL). */
  force?: boolean;
}

export interface EvalsHandlerOptions {
  auditsRoot?: string;
  annotationsPath?: string;
  ttlMs?: number;
  now?: () => number;
}

/**
 * Build the row list from disk (no cache). Useful for tests.
 */
export function buildEvalRows(opts: EvalsHandlerOptions = {}): EvalRow[] {
  const auditsRoot = opts.auditsRoot ?? join(process.cwd(), "..", "audits");
  const annotationsPath = opts.annotationsPath
    ?? join(process.cwd(), "public", "observability", "gate-annotations.json");
  const annotations = loadAnnotations(annotationsPath);
  const files = collectAuditFiles(auditsRoot);
  const rows: EvalRow[] = [];
  for (const f of files) {
    const parsed = parseAuditFile(f.file, f.mtimeMs, f.bucket, annotations);
    for (const r of parsed) rows.push(r);
  }
  rows.sort((a, b) => a.ran_at_ms - b.ran_at_ms);
  return rows;
}

/**
 * Endpoint handler. Returns an array of EvalRow already sorted by ran_at ASC,
 * filtered by db_source if requested, and capped to `limit`.
 */
export function handleObsEvals(
  query: EvalsQuery = {},
  opts: EvalsHandlerOptions = {},
): EvalRow[] {
  const ttlMs = opts.ttlMs ?? DEFAULT_TTL_MS;
  const now = opts.now ? opts.now() : Date.now();
  const fresh = cached && !query.force && now - cached.generatedAtMs < ttlMs;
  if (!fresh) {
    const rows = buildEvalRows(opts);
    cached = { generatedAtMs: now, rows };
  }
  const rows = cached!.rows;
  const dbFilter = query.dbSource && query.dbSource !== "all" ? query.dbSource : null;
  const limit = Math.max(1, Math.min(2000, Math.floor(query.limit ?? 500)));
  const filtered = dbFilter ? rows.filter((r) => r.db_source === dbFilter) : rows;
  return filtered.slice(0, limit);
}

// ── _internals for tests ──────────────────────────────────────────────────────

export const _internals = {
  DEFAULT_TTL_MS,
  toNumOrNull,
  toStringOrNull,
  rowFromSummary,
};
