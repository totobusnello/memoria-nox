// reindex-errors.ts — error classes for reindex.ts, extracted so the canary
// test can import them without pulling getDb / op-audit / ingest-router deps.

export const MIN_RETENTION_RATIO = Number(
  process.env.NOX_REINDEX_MIN_RETENTION_RATIO ?? "0.90",
);

export class ReindexWipeDetectedError extends Error {
  readonly preCount: number;
  readonly postCount: number;
  readonly ratio: number;
  constructor(preCount: number, postCount: number, ratio: number) {
    super(
      `[reindex] WIPE DETECTED: post-reindex chunks=${postCount} < ${(ratio * 100).toFixed(1)}% of pre=${preCount} ` +
        `(threshold=${(ratio * 100).toFixed(1)}%). ` +
        `Aborting via thrown error so withOpAudit() runs the failure path and preserves the pre-op snapshot. ` +
        `Recover via safeRestore() from /var/backups/nox-mem/pre-op/reindex-main-<ts>-*.db. ` +
        `Set NOX_REINDEX_ALLOW_WIPE=1 ONLY if intentional content removal is expected.`,
    );
    this.name = "ReindexWipeDetectedError";
    this.preCount = preCount;
    this.postCount = postCount;
    this.ratio = ratio;
  }
}
