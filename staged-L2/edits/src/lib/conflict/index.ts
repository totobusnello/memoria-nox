/**
 * L2 conflict-detection — public re-exports.
 *
 * Consumers (CLI, HTTP, MCP, daemon) should import from here, not from
 * sibling modules directly. This is the stable surface.
 */

export type {
  Conflict,
  ConflictAuditRow,
  ConflictEvidence,
  ConflictKind,
  ConflictMode,
  ConflictStatus,
  DetectorOptions,
  EvidenceChunk,
  ExtractionMethod,
  ResolutionInput,
  ResolutionKind,
  VariantEvidence,
  VariantRelation,
} from "./types.js";

export {
  DEFAULT_CONFLICT_MODE,
  DEFAULT_EVIDENCE_SNIPPET_LEN,
  DEFAULT_MIN_CONFIDENCE,
  DEFAULT_SCAN_LIMIT,
} from "./types.js";

export { detectDirectConflicts } from "./detector-direct.js";
export { collectEvidence } from "./evidence.js";
export {
  recordConflict,
  updateConflictStatus,
  getConflictById,
  listConflicts,
  statusCounts,
  type RecordOptions,
  type RecordResult,
} from "./audit-writer.js";
export {
  resolveMode,
  runConflictPass,
  annotateRelations,
  getShadowTelemetry,
  getConflictsForRelations,
  makeConflictContext,
  type ConflictContext,
  type PassResult,
  type ShadowTelemetry,
} from "./shadow.js";
export {
  parseCronExpression,
  nextRunAfter,
  shouldRunScan,
  runScheduledScan,
  type ParsedCron,
  type SchedulerOptions,
  type ScheduledRunResult,
} from "./scheduler.js";

export type { DBHandle, PreparedStatement, RunResult } from "./db.js";
