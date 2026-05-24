// op-audit.ts — STAGED STUB.
// Real implementation lives at src/lib/op-audit.ts on the VPS — DO NOT replace.
// This stub exists only so reindex.ts compiles in isolation inside this staged dir.
//
// Signature MUST match prod: withOpAudit(opName, fn) — 2 args.
// The previous 3-arg stub (with db_source option) caused a TS2554 mismatch
// against prod when reindex.ts was deployed (incident 2026-05-24 smoke).
// Any contextual metadata (db_source, etc) must be logged from INSIDE `fn`
// via result.notes or external logging, never via a withOpAudit options bag.
export interface OpResult {
  affected_rows?: number;
  notes?: string;
}

export async function withOpAudit<T extends OpResult>(
  opName: string,
  fn: () => Promise<T>,
): Promise<T> {
  // Stub: just run the function. Real impl does snapshot + audit row.
  console.log(`[op-audit:stub] ${opName} started`);
  try {
    const result = await fn();
    console.log(`[op-audit:stub] ${opName} success`);
    return result;
  } catch (err) {
    console.error(`[op-audit:stub] ${opName} failed: ${err}`);
    throw err;
  }
}
