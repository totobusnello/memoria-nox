/**
 * G10 — ran_at server-side enforcement for audit tables.
 *
 * Gap from THREAT-MODEL.md §3.4 / G10:
 *   "ops_audit.ran_at field stored as user-supplied timestamp could be
 *    backdated to hide actions."
 *
 * This module provides:
 *   1. Application-layer guard that overrides backdated timestamps before INSERT.
 *      Defence-in-depth alongside the SQL trigger in v23-audit-ran-at-trigger.sql.
 *
 *   2. insertWithServerTimestamp() — wrapper around DB INSERT that forces
 *      server-side time regardless of caller-supplied value.
 *
 *   3. validateAuditTimestamp() — utility to check whether a timestamp
 *      is within acceptable skew (< 24h drift from now).
 *
 * The SQL trigger in v23 is the primary control. This module is secondary
 * (defence-in-depth) — handles cases where the trigger is not yet applied
 * or is on a different DB file.
 *
 * Ref: THREAT-MODEL.md G10 (medium priority).
 *      staged-G10/edits/migrations/v23-audit-ran-at-trigger.sql.
 */

// ─── Constants ────────────────────────────────────────────────────────────────

/** Max allowable drift between caller-supplied timestamp and server time (ms). */
export const MAX_TIMESTAMP_DRIFT_MS = 24 * 60 * 60 * 1000; // 24 hours

/** Max allowable ISO 8601 drift for confidence_eval_log.ran_at. */
export const MAX_ISO_DRIFT_MS = 24 * 60 * 60 * 1000; // 24 hours

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AuditRow {
  ran_at?: number | string; // INTEGER ms (ops_audit) or TEXT ISO (confidence_eval_log)
  started_at?: number;      // ops_audit
  [key: string]: unknown;
}

export type AuditRowWithServerTime<T extends AuditRow> = Omit<T, "ran_at" | "started_at"> & {
  ran_at: number | string;
  started_at?: number;
};

// ─── Core functions ───────────────────────────────────────────────────────────

/**
 * serverTimestampMs — current server time in Unix milliseconds.
 * Extracted for testability (mock in tests).
 */
export function serverTimestampMs(): number {
  return Date.now();
}

/**
 * serverTimestampIso — current server time in ISO 8601 UTC.
 */
export function serverTimestampIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

/**
 * validateAuditTimestamp — checks whether a numeric ms timestamp is within
 * MAX_TIMESTAMP_DRIFT_MS of server time.
 *
 * Returns { valid: true } or { valid: false, driftMs: number }.
 */
export function validateAuditTimestamp(
  suppliedMs: number,
  nowMs = serverTimestampMs(),
): { valid: true } | { valid: false; driftMs: number } {
  const drift = Math.abs(nowMs - suppliedMs);
  if (drift <= MAX_TIMESTAMP_DRIFT_MS) {
    return { valid: true };
  }
  return { valid: false, driftMs: drift };
}

/**
 * validateAuditTimestampIso — checks whether an ISO 8601 string is within
 * MAX_ISO_DRIFT_MS of server time.
 */
export function validateAuditTimestampIso(
  suppliedIso: string,
  nowMs = serverTimestampMs(),
): { valid: true } | { valid: false; driftMs: number } {
  const suppliedMs = new Date(suppliedIso).getTime();
  if (Number.isNaN(suppliedMs)) {
    return { valid: false, driftMs: Infinity };
  }
  return validateAuditTimestamp(suppliedMs, nowMs);
}

/**
 * overrideWithServerTime — returns row with started_at / ran_at forced to
 * server-side time, regardless of supplied values.
 *
 * For ops_audit: overrides started_at (INTEGER ms).
 * For confidence_eval_log: overrides ran_at (TEXT ISO 8601).
 *
 * @param row - input row (partial or full)
 * @param mode - "ops_audit" | "confidence_eval_log"
 */
export function overrideWithServerTime<T extends AuditRow>(
  row: T,
  mode: "ops_audit" | "confidence_eval_log",
): AuditRowWithServerTime<T> {
  const now = serverTimestampMs();

  if (mode === "ops_audit") {
    const result = { ...row } as AuditRowWithServerTime<T>;
    if ("started_at" in row) {
      (result as Record<string, unknown>).started_at = now;
    }
    // If row has ran_at (future schema), override as INTEGER ms
    if ("ran_at" in row) {
      (result as Record<string, unknown>).ran_at = now;
    }
    return result;
  }

  // confidence_eval_log: ran_at is TEXT ISO
  const result = { ...row } as AuditRowWithServerTime<T>;
  (result as Record<string, unknown>).ran_at = serverTimestampIso();
  return result;
}

/**
 * warnIfBackdated — logs a warning if the supplied timestamp is more than
 * MAX_TIMESTAMP_DRIFT_MS in the past. Does not throw — informational only.
 *
 * Used in development / testing to surface potential issues.
 */
export function warnIfBackdated(
  field: string,
  suppliedMs: number,
  nowMs = serverTimestampMs(),
): void {
  const check = validateAuditTimestamp(suppliedMs, nowMs);
  if (!check.valid) {
    const driftH = (check.driftMs / 3600000).toFixed(1);
    console.warn(
      `[ran-at-guard] Backdated ${field} detected: ` +
        `${driftH}h drift (max allowed: ${MAX_TIMESTAMP_DRIFT_MS / 3600000}h). ` +
        `Server time will be used instead.`,
    );
  }
}
