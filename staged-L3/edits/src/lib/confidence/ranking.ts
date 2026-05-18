/**
 * src/lib/confidence/ranking.ts — confidence × salience ranking integration.
 *
 * GATED per CLAUDE.md regra #5: ranking changes require ≥+1.0pp nDCG@10 over
 * R01a/R01b baseline + 7d shadow validation. Default mode is "disabled" — the
 * wrapper returns the original salience unchanged, no telemetry collected.
 *
 * Modes:
 *   disabled  → no-op, returns salience as-is
 *   shadow    → computes new salience, logs delta, RETURNS ORIGINAL (no behavior change)
 *   active    → applies multiplier + stale/superseded filter
 *
 * Formula (active mode, per spec §5):
 *   salience' = salience × confidence
 *   clamp to [active_floor, 1.5]
 *
 * Skip rules (active mode):
 *   - chunks with provenance_kind='user-marked' AND confidence < active_floor → SKIP
 *   - chunks with confidence < active_floor (any provenance) → SKIP
 *   - chunks where superseded_by IS NOT NULL → de-prioritized by 0.5 multiplier
 *     (NOT skipped; preserves audit trail per CLAUDE.md regra #6)
 *
 * Test-side: feed a stable seed chunk list + cfg, verify same input/output
 * across modes; verify shadow returns original despite computing delta.
 */

import type {
  ConfidenceConfig,
  RankingMode,
} from "./types.js";
import { resolveConfig } from "./config.js";

export interface RankableChunk {
  chunk_id: number;
  /** Pre-ranking salience score from existing pipeline. */
  salience: number;
  /** Chunk confidence (DB field). Defaults to 0.8 if NULL/missing. */
  confidence?: number | null;
  /** Provenance kind. */
  provenance_kind?: string | null;
  /** Superseded chain — non-null means this chunk has been replaced. */
  superseded_by?: number | null;
}

export interface RankedChunk extends RankableChunk {
  /** Final salience after L3 transformation (may equal input if disabled/shadow). */
  ranked_salience: number;
  /** Delta computed but possibly not applied (always populated in shadow). */
  shadow_delta?: number;
  /** Reason the chunk was skipped (active mode only). */
  skip_reason?: "stale_low_confidence" | "below_floor";
}

export interface RankingResult {
  chunks: RankedChunk[];
  mode: RankingMode;
  /** Stats for telemetry. */
  stats: {
    input_count: number;
    output_count: number;
    skipped: number;
    superseded_deprioritized: number;
    mean_delta: number;
  };
}

const CLAMP_MIN = 0.3;
const CLAMP_MAX = 1.5;
const SUPERSEDED_MULTIPLIER = 0.5;

function clampSalience(v: number): number {
  if (!Number.isFinite(v)) return CLAMP_MIN;
  return Math.min(CLAMP_MAX, Math.max(CLAMP_MIN, v));
}

/**
 * applyConfidenceRanking(chunks, cfgOverride?) → RankingResult
 *
 * Mode is read from cfg.ranking_mode (env-resolved by default).
 */
export function applyConfidenceRanking(
  chunks: RankableChunk[],
  cfgOverride?: ConfidenceConfig
): RankingResult {
  const cfg = cfgOverride ?? resolveConfig();
  const mode = cfg.ranking_mode;

  const stats = {
    input_count: chunks.length,
    output_count: 0,
    skipped: 0,
    superseded_deprioritized: 0,
    mean_delta: 0,
  };

  const out: RankedChunk[] = [];
  let totalDelta = 0;
  let deltaSamples = 0;

  for (const chunk of chunks) {
    const conf =
      typeof chunk.confidence === "number" && Number.isFinite(chunk.confidence)
        ? chunk.confidence
        : 0.8;
    const provenance = chunk.provenance_kind ?? null;
    const superseded =
      chunk.superseded_by !== null &&
      chunk.superseded_by !== undefined;

    // Compute potential new salience (always done; only applied in active mode)
    let newSalience = chunk.salience * conf;
    if (superseded) {
      newSalience *= SUPERSEDED_MULTIPLIER;
    }
    newSalience = clampSalience(newSalience);

    const delta = newSalience - chunk.salience;
    totalDelta += delta;
    deltaSamples++;

    // Skip-detection logic — only acts in active mode
    const stale =
      provenance === "user-marked" && conf < cfg.active_floor;
    const belowFloor = conf < cfg.active_floor;

    if (mode === "active" && (stale || belowFloor)) {
      stats.skipped++;
      // Do NOT push skipped chunks to output (active behaviour).
      continue;
    }

    if (mode === "active" && superseded) {
      stats.superseded_deprioritized++;
    }

    const ranked_salience =
      mode === "active" ? newSalience : chunk.salience;

    const rec: RankedChunk = {
      ...chunk,
      ranked_salience,
    };

    if (mode === "shadow") {
      rec.shadow_delta = delta;
    }

    out.push(rec);
  }

  stats.output_count = out.length;
  stats.mean_delta = deltaSamples > 0 ? totalDelta / deltaSamples : 0;

  return { chunks: out, mode, stats };
}

/** Pure helper for tests / external callers: compute one chunk's new salience. */
export function computeRankedSalience(
  salience: number,
  confidence: number,
  superseded: boolean
): number {
  let v = salience * confidence;
  if (superseded) v *= SUPERSEDED_MULTIPLIER;
  return clampSalience(v);
}

export { CLAMP_MIN, CLAMP_MAX, SUPERSEDED_MULTIPLIER };
