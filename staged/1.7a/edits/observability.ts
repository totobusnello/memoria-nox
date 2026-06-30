/**
 * observability.ts — F10 Phase A endpoints (Prod Health)
 *
 * Adds three read-only endpoints under `/api/observability/*`:
 *
 *   GET /api/observability/health
 *     Same shape as /api/health PLUS delta vs ~24h ago for key metrics
 *     (chunks.total, dbSizeMB, knowledgeGraph.entities, knowledgeGraph.relations).
 *     The 24h snapshot is cached in-memory and refreshed once per call when older
 *     than ~24h; first call after process start has no delta available.
 *
 *   GET /api/observability/recent-ops?n=10
 *     Last N rows from ops_audit WHERE status IN ('failed','crashed') ORDER BY
 *     started_at DESC. Default n=10, max n=50.
 *
 *   GET /api/observability/canary-tail?n=3
 *     Last N entries from /var/log/nox-schema-invariants.log (F05 cron output).
 *     Default n=3, max n=20. Empty list if file missing.
 *
 * Spec: specs/2026-05-01-F10-observability-dashboard.md (refresh 2026-05-21)
 * Status: Phase A implementation-ready
 *
 * Module design:
 *   - Exports three handler functions invoked from the api-server.ts switch.
 *   - Handlers do NOT touch ServerResponse directly; they return plain objects
 *     and a status code. Caller (api-server.ts) wraps with the existing json()
 *     helper. This keeps boundary thin and unit-testable.
 *   - The 24h snapshot cache lives at module scope (single-process server),
 *     reset on import. Test harness imports a fresh module via cache-bust to
 *     reset state.
 */

import type { Database } from "better-sqlite3";
import { readFileSync, statSync } from "fs";

// ── 24h snapshot cache ────────────────────────────────────────────────────────
//
// Lightweight in-memory snapshot. Single dashboard user means we can afford to
// refresh on read when stale; no separate cron needed. Snapshot stores enough
// to compute deltas for the dashboard's P0 metrics.

interface HealthSnapshot {
  taken_at_ms: number;
  chunks_total: number;
  db_size_mb: number;
  kg_entities: number;
  kg_relations: number;
}

const SNAPSHOT_TTL_MS = 24 * 60 * 60 * 1000; // 24h

let cachedSnapshot: HealthSnapshot | null = null;

/** Read live metrics from DB into a snapshot shape. */
function takeSnapshot(db: Database): HealthSnapshot {
  const chunksTotal = (db.prepare("SELECT COUNT(*) AS c FROM chunks").get() as { c: number }).c;
  const dbSizeBytes = (db.prepare(
    "SELECT page_count * page_size AS s FROM pragma_page_count(), pragma_page_size()",
  ).get() as { s: number }).s;
  let kgEntities = 0;
  let kgRelations = 0;
  try {
    kgEntities = (db.prepare("SELECT COUNT(*) AS c FROM kg_entities").get() as { c: number }).c;
    kgRelations = (db.prepare("SELECT COUNT(*) AS c FROM kg_relations").get() as { c: number }).c;
  } catch {
    // KG tables may not exist on dev / minimal envs
  }
  return {
    taken_at_ms: Date.now(),
    chunks_total: chunksTotal,
    db_size_mb: Math.round((dbSizeBytes / 1024 / 1024) * 10) / 10,
    kg_entities: kgEntities,
    kg_relations: kgRelations,
  };
}

/**
 * Returns current snapshot AND the most recent snapshot that is older than
 * `minAgeMs` (default 24h). When no qualifying historical snapshot exists,
 * `historical` is null and dashboard renders deltas as "—".
 *
 * Cache logic: keep one snapshot at module scope. When the cached snapshot is
 * older than minAgeMs, return it as `historical` and replace it with `current`
 * for next time. This converges to a rolling 24h window without a separate cron.
 */
export function snapshotPair(
  db: Database,
  minAgeMs: number = SNAPSHOT_TTL_MS,
): { current: HealthSnapshot; historical: HealthSnapshot | null } {
  const current = takeSnapshot(db);
  let historical: HealthSnapshot | null = null;
  if (cachedSnapshot && current.taken_at_ms - cachedSnapshot.taken_at_ms >= minAgeMs) {
    historical = cachedSnapshot;
    cachedSnapshot = current;
  } else if (!cachedSnapshot) {
    cachedSnapshot = current;
  }
  return { current, historical };
}

/** Exposed for tests — reset the snapshot cache between cases. */
export function _resetSnapshotCache(): void {
  cachedSnapshot = null;
}

// ── Health threshold logic ────────────────────────────────────────────────────

export type HealthLevel = "green" | "yellow" | "red";

export interface HealthIndicators {
  vector: HealthLevel;
  canary: HealthLevel;
  recentOps: HealthLevel;
}

/**
 * Vector coverage health:
 *   green  — embedded == total AND orphans == 0
 *   yellow — embedded < total by <= 5 chunks OR orphans <= 5
 *   red    — anything worse
 */
export function vectorHealth(embedded: number, total: number, orphans: number): HealthLevel {
  if (embedded === total && orphans === 0) return "green";
  const gap = total - embedded;
  if (gap <= 5 && orphans <= 5) return "yellow";
  return "red";
}

/**
 * Canary log health based on age of last entry:
 *   green  — last entry < 20 minutes ago (cron runs every 15min)
 *   yellow — 20 < age < 60 minutes
 *   red    — age >= 60 minutes OR no log present
 */
export function canaryHealth(lastEntryAgeMs: number | null): HealthLevel {
  if (lastEntryAgeMs == null) return "red";
  const minutes = lastEntryAgeMs / 60000;
  if (minutes < 20) return "green";
  if (minutes < 60) return "yellow";
  return "red";
}

/**
 * Recent ops health:
 *   green  — zero failed/crashed in last 24h
 *   yellow — 1–3 failed/crashed (transient)
 *   red    — 4+ failed/crashed (pattern)
 */
export function recentOpsHealth(failedCount: number): HealthLevel {
  if (failedCount === 0) return "green";
  if (failedCount <= 3) return "yellow";
  return "red";
}

// ── /api/observability/health ─────────────────────────────────────────────────

export interface ObsHealthResponse {
  current: HealthSnapshot & {
    vector_coverage: { embedded: number; total: number; orphans: number };
    salience_mode: string;
  };
  delta_24h: {
    chunks: number | null;
    db_size_mb: number | null;
    kg_entities: number | null;
    kg_relations: number | null;
  };
  indicators: HealthIndicators;
  generated_at_ms: number;
}

export function handleObsHealth(
  db: Database,
  opts: { canaryLogPath?: string; lastFailedOps24h?: number } = {},
): ObsHealthResponse {
  const { current, historical } = snapshotPair(db);

  // Vector coverage — best-effort; falls back to 0/0 if vec extension missing
  let embedded = 0;
  let total = current.chunks_total;
  let orphans = 0;
  try {
    const row = db.prepare(
      "SELECT COUNT(DISTINCT m.chunk_id) AS c FROM vec_chunk_map m INNER JOIN chunks c ON c.id = m.chunk_id",
    ).get() as { c: number };
    embedded = row.c;
    const totalMap = (db.prepare("SELECT COUNT(*) AS c FROM vec_chunk_map").get() as { c: number }).c;
    orphans = Math.max(0, totalMap - embedded);
  } catch {
    // vec tables may not exist in test fixtures
  }

  // Salience mode (env-driven; tolerate missing var)
  const salienceMode = process.env.NOX_SALIENCE_MODE ?? "off";

  // Canary age
  let canaryAgeMs: number | null = null;
  const canaryPath = opts.canaryLogPath ?? "/var/log/nox-schema-invariants.log";
  try {
    const st = statSync(canaryPath);
    canaryAgeMs = Date.now() - st.mtimeMs;
  } catch {
    canaryAgeMs = null;
  }

  // Recent ops count (24h, failed/crashed)
  let failedCount = opts.lastFailedOps24h ?? 0;
  if (opts.lastFailedOps24h === undefined) {
    try {
      const since = Date.now() - 24 * 60 * 60 * 1000;
      const row = db.prepare(
        "SELECT COUNT(*) AS c FROM ops_audit WHERE status IN ('failed','crashed') AND started_at >= ?",
      ).get(since) as { c: number };
      failedCount = row.c;
    } catch {
      failedCount = 0;
    }
  }

  const delta_24h = {
    chunks: historical ? current.chunks_total - historical.chunks_total : null,
    db_size_mb: historical
      ? Math.round((current.db_size_mb - historical.db_size_mb) * 10) / 10
      : null,
    kg_entities: historical ? current.kg_entities - historical.kg_entities : null,
    kg_relations: historical ? current.kg_relations - historical.kg_relations : null,
  };

  return {
    current: {
      ...current,
      vector_coverage: { embedded, total, orphans },
      salience_mode: salienceMode,
    },
    delta_24h,
    indicators: {
      vector: vectorHealth(embedded, total, orphans),
      canary: canaryHealth(canaryAgeMs),
      recentOps: recentOpsHealth(failedCount),
    },
    generated_at_ms: Date.now(),
  };
}

// ── /api/observability/recent-ops ─────────────────────────────────────────────

export interface RecentOpRow {
  id: number;
  op_name: string;
  status: string;
  db_source: string;
  started_at_ms: number;
  duration_ms: number | null;
  error_message: string | null;
}

export function handleObsRecentOps(db: Database, n: number = 10): RecentOpRow[] {
  const limit = Math.max(1, Math.min(50, Math.floor(n)));
  try {
    const rows = db.prepare(
      `SELECT id, op_name, status, db_source, started_at, duration_ms, error_message
       FROM ops_audit
       WHERE status IN ('failed','crashed')
       ORDER BY started_at DESC
       LIMIT ?`,
    ).all(limit) as Array<{
      id: number;
      op_name: string;
      status: string;
      db_source: string;
      started_at: number;
      duration_ms: number | null;
      error_message: string | null;
    }>;
    return rows.map((r) => ({
      id: r.id,
      op_name: r.op_name,
      status: r.status,
      db_source: r.db_source,
      started_at_ms: r.started_at,
      duration_ms: r.duration_ms,
      error_message: r.error_message,
    }));
  } catch {
    return [];
  }
}

// ── /api/observability/canary-tail ────────────────────────────────────────────

export interface CanaryLine {
  raw: string;
  timestamp: string | null;
  ok: boolean;
}

const CANARY_TS_RE = /^\[?(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:?\d{2})?)\]?/;

/** Parse a single canary log line; returns null fields on best-effort failure. */
export function parseCanaryLine(raw: string): CanaryLine {
  const tsMatch = CANARY_TS_RE.exec(raw);
  const timestamp = tsMatch && tsMatch[1] ? tsMatch[1] : null;
  // Heuristic: "OK" / "PASS" / "all 4 invariants OK" → ok=true; else false
  const ok = /\b(OK|PASS|✓|all .* invariants OK)\b/i.test(raw) && !/\b(FAIL|ERROR|✗)\b/i.test(raw);
  return { raw: raw.trim(), timestamp, ok };
}

export function handleObsCanaryTail(
  n: number = 3,
  opts: { canaryLogPath?: string } = {},
): CanaryLine[] {
  const limit = Math.max(1, Math.min(20, Math.floor(n)));
  const canaryPath = opts.canaryLogPath ?? "/var/log/nox-schema-invariants.log";
  try {
    const raw = readFileSync(canaryPath, "utf-8");
    const lines = raw.split("\n").filter((l) => l.trim().length > 0);
    return lines.slice(-limit).map(parseCanaryLine);
  } catch {
    return [];
  }
}

// ── _internals for tests ──────────────────────────────────────────────────────

export const _internals = {
  SNAPSHOT_TTL_MS,
  takeSnapshot,
  CANARY_TS_RE,
};
