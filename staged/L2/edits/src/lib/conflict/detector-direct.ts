/**
 * L2 T3 — Direct conflict detector (Type 1).
 *
 * Algorithm (spec §4.1):
 *   1. Group active kg_relations by (source_entity_id, predicate)
 *   2. Flag groups where COUNT(DISTINCT target_entity_id) > 1
 *   3. Hydrate each group with per-variant metadata (confidence, extraction
 *      method, evidence chunk, created_at)
 *   4. Apply allowlist/blocklist + extraction_method weight bias
 *
 * v1 scope: produces `kind='direct'` conflicts only. Type 3 (temporal
 * supersession) is a downstream refinement — left for L2.1 ranking phase.
 *
 * Defensive checks (spec §3 regra de ouro #4 — confidence threshold gate):
 *   - min_confidence default 0.5 (filtered in SQL via parameter)
 *   - superseded relations (superseded_by_relation_id IS NOT NULL) excluded
 *     by SQL clause; this preserves discoverability but keeps detector quiet
 */

import type { DBHandle } from "./db.js";
import {
  DEFAULT_MIN_CONFIDENCE,
  DEFAULT_SCAN_LIMIT,
  type Conflict,
  type DetectorOptions,
  type ExtractionMethod,
  type VariantRelation,
} from "./types.js";

interface DetectorRow {
  source_entity_id: number;
  predicate: string;
  distinct_targets: number;
  relation_ids_csv: string;
}

interface VariantRow {
  id: number;
  target_entity_id: number;
  confidence: number;
  extraction_method: ExtractionMethod | null;
  evidence_chunk_id: number | null;
  created_at: number;
  user_marked: 0 | 1;
}

interface EntityRow {
  id: number;
  name: string;
}

const DETECTOR_SQL = `
  SELECT
    source_entity_id,
    predicate,
    COUNT(DISTINCT target_entity_id) AS distinct_targets,
    GROUP_CONCAT(id) AS relation_ids_csv
  FROM kg_relations
  WHERE confidence >= ?
    AND superseded_by_relation_id IS NULL
  GROUP BY source_entity_id, predicate
  HAVING COUNT(DISTINCT target_entity_id) > 1
`.trim();

const HYDRATE_SQL = `
  SELECT id, target_entity_id, confidence, extraction_method, evidence_chunk_id, created_at, user_marked
  FROM kg_relations
  WHERE source_entity_id = ? AND predicate = ? AND confidence >= ? AND superseded_by_relation_id IS NULL
`.trim();

const ENTITY_LABEL_SQL = `SELECT id, name FROM kg_entities WHERE id = ?`;

export function detectDirectConflicts(
  db: DBHandle,
  opts: DetectorOptions = {},
): Conflict[] {
  const minConf = opts.min_confidence ?? DEFAULT_MIN_CONFIDENCE;
  const limit = opts.limit ?? DEFAULT_SCAN_LIMIT;
  const scanTs = opts.scan_ts ?? Date.now();

  // Confidence threshold validation — protect against pathological inputs.
  if (minConf < 0 || minConf > 1) {
    throw new RangeError(`min_confidence out of range [0..1]: ${minConf}`);
  }

  const allow = opts.predicate_allowlist?.length
    ? new Set(opts.predicate_allowlist)
    : null;
  const block = opts.predicate_blocklist?.length
    ? new Set(opts.predicate_blocklist)
    : null;
  const weights = opts.extraction_method_weights ?? {};

  const groups = db.prepare(DETECTOR_SQL).all(minConf) as DetectorRow[];

  const conflicts: Conflict[] = [];
  for (const g of groups) {
    if (allow && !allow.has(g.predicate)) continue;
    if (block && block.has(g.predicate)) continue;

    const variantRows = db
      .prepare(HYDRATE_SQL)
      .all(g.source_entity_id, g.predicate, minConf) as VariantRow[];

    // Apply extraction_method weighting — annotate confidence with bias.
    // Weight is multiplicative; default 1.0 (no bias).
    const variants: VariantRelation[] = variantRows.map((r) => {
      const w = (r.extraction_method && weights[r.extraction_method]) ?? 1.0;
      // Clamp adjusted confidence to [0,1] — weighted bias must never push
      // outside the canonical CHECK constraint range.
      const adjusted = Math.max(0, Math.min(1, r.confidence * w));
      return {
        relation_id: r.id,
        target_entity_id: r.target_entity_id,
        confidence: adjusted,
        extraction_method: r.extraction_method,
        evidence_chunk_id: r.evidence_chunk_id,
        created_at: r.created_at,
        user_marked: Boolean(r.user_marked),
      };
    });

    // Distinct-target invariant after weighting: a group might collapse if
    // weighting pulled all variants below minConf — re-check.
    const distinctTargets = new Set(variants.map((v) => v.target_entity_id));
    if (distinctTargets.size < 2) continue;

    // Try to resolve subject label (cheap join — single row per conflict).
    let subjectLabel: string | undefined;
    const entRow = db
      .prepare(ENTITY_LABEL_SQL)
      .get(g.source_entity_id) as EntityRow | undefined;
    if (entRow?.name) subjectLabel = entRow.name;

    const kind = distinctTargets.size > 2 ? "multi_target" : "direct";

    conflicts.push({
      kind,
      subject_entity_id: g.source_entity_id,
      subject_label: subjectLabel,
      predicate: g.predicate,
      variants,
      detected_at: scanTs,
    });

    if (limit > 0 && conflicts.length >= limit) break;
  }

  return conflicts;
}
