/**
 * L2 T10 — Periodic scanner scaffolding (cron pattern).
 *
 * NOT an actual scheduler — daemon-side opt-in cron scaffold. The real
 * nox-mem daemon is `nox-mem-api` (port 18802). This module exposes:
 *   - `parseCronExpression(expr)` — minimal validator + next-run calculator
 *     for the limited set of cron expressions we expect (M H * * *).
 *   - `shouldRunScan(now, lastRunAt, cronExpr, tzOffsetMinutes)` — pure
 *     decision function for "is it time to scan?"
 *   - `runScheduledScan(db, opts)` — idempotent scan wrapper that records
 *     the last-run timestamp.
 *
 * Default cron: `0 3 * * *` (03:00 BRT — after backup-all at 02:00).
 * Env var: `NOX_CONFLICT_SCAN_CRON`.
 *
 * Idempotency: skipping conflicts already open is handled at audit-writer
 * dedupe layer (see audit-writer.recordConflict). This module only handles
 * "should the pass run now?" — not what to do once running.
 */

import type { DBHandle } from "./db.js";
import { runConflictPass, resolveMode } from "./shadow.js";
import type { PassResult } from "./shadow.js";
import type { DetectorOptions, ConflictMode } from "./types.js";

export interface ParsedCron {
  /** Minute 0-59 */
  minute: number;
  /** Hour 0-23 */
  hour: number;
  /** Day-of-month — '*' allowed; v1 only supports '*' */
  dom: "*";
  /** Month — '*' only */
  month: "*";
  /** Day-of-week — '*' only */
  dow: "*";
}

/**
 * Parse a restricted cron expression `M H * * *`. v1 explicitly rejects
 * non-trivial DOM/month/DOW patterns to keep the scheduler boring.
 */
export function parseCronExpression(expr: string): ParsedCron {
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) {
    throw new Error(`cron expression must have 5 fields, got ${parts.length}: '${expr}'`);
  }
  const [m, h, dom, month, dow] = parts;
  const min = Number(m);
  const hr = Number(h);
  if (!Number.isFinite(min) || min < 0 || min > 59) {
    throw new Error(`invalid cron minute: ${m}`);
  }
  if (!Number.isFinite(hr) || hr < 0 || hr > 23) {
    throw new Error(`invalid cron hour: ${h}`);
  }
  if (dom !== "*" || month !== "*" || dow !== "*") {
    throw new Error(
      `cron v1 supports only 'M H * * *' (got dom=${dom}, month=${month}, dow=${dow})`,
    );
  }
  return { minute: min, hour: hr, dom: "*", month: "*", dow: "*" };
}

/**
 * Returns next-run unix-ms timestamp at or after `now`, in local timezone
 * (caller passes tzOffsetMinutes relative to UTC; default -180 = BRT).
 */
export function nextRunAfter(
  now: number,
  cron: ParsedCron,
  tzOffsetMinutes = -180,
): number {
  // Move "now" into local time
  const localNow = new Date(now + tzOffsetMinutes * 60_000);
  const candidate = new Date(localNow);
  candidate.setUTCSeconds(0, 0);
  candidate.setUTCHours(cron.hour, cron.minute, 0, 0);
  if (candidate.getTime() <= localNow.getTime()) {
    candidate.setUTCDate(candidate.getUTCDate() + 1);
  }
  // Translate back to UTC
  return candidate.getTime() - tzOffsetMinutes * 60_000;
}

/**
 * Should we run a scan now? True when `now >= nextRunAfter(lastRunAt)`.
 * On first run (lastRunAt is null), returns true only if the scheduled
 * time has already passed at least once today.
 */
export function shouldRunScan(
  now: number,
  lastRunAt: number | null,
  cron: ParsedCron,
  tzOffsetMinutes = -180,
): boolean {
  if (lastRunAt == null) {
    const next = nextRunAfter(now - 24 * 3600_000, cron, tzOffsetMinutes);
    return next <= now;
  }
  const next = nextRunAfter(lastRunAt, cron, tzOffsetMinutes);
  return now >= next;
}

export interface SchedulerState {
  lastRunAt: number | null;
  cron: ParsedCron;
  tzOffsetMinutes: number;
  mode: ConflictMode;
}

export interface SchedulerOptions {
  cronExpr?: string;
  tzOffsetMinutes?: number;
  modeOverride?: ConflictMode;
  detectorOpts?: DetectorOptions;
  /** Test hook — current time. Defaults to Date.now(). */
  now?: number;
  /** Test hook — last-run timestamp from previous invocation. */
  lastRunAt?: number | null;
}

export interface ScheduledRunResult {
  ran: boolean;
  reason: "first_run" | "due" | "not_due" | "disabled";
  result: PassResult | null;
  nextRunAt: number;
}

/**
 * Decide-then-run scaffold. Caller manages persistence of lastRunAt
 * (DB row, file, in-memory) and threads it through. Idempotent: same
 * (now, lastRunAt) input returns the same decision.
 */
export function runScheduledScan(
  db: DBHandle,
  opts: SchedulerOptions = {},
): ScheduledRunResult {
  const cronExpr =
    opts.cronExpr ?? process.env.NOX_CONFLICT_SCAN_CRON ?? "0 3 * * *";
  const cron = parseCronExpression(cronExpr);
  const tz = opts.tzOffsetMinutes ?? -180;
  const now = opts.now ?? Date.now();
  const lastRun = opts.lastRunAt ?? null;
  const mode = opts.modeOverride ?? resolveMode();

  // Even if scheduler is wired in, conflict mode disabled prevents writes.
  // We still surface 'disabled' so the daemon log shows the explicit gate.
  if (mode === "disabled") {
    return {
      ran: false,
      reason: "disabled",
      result: null,
      nextRunAt: nextRunAfter(now, cron, tz),
    };
  }

  const due = shouldRunScan(now, lastRun, cron, tz);
  if (!due) {
    return {
      ran: false,
      reason: lastRun == null ? "first_run" : "not_due",
      result: null,
      nextRunAt: nextRunAfter(now, cron, tz),
    };
  }
  const result = runConflictPass(db, opts.detectorOpts ?? {}, mode);
  return {
    ran: true,
    reason: lastRun == null ? "first_run" : "due",
    result,
    nextRunAt: nextRunAfter(now, cron, tz),
  };
}
