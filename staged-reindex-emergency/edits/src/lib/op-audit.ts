// op-audit.ts — STAGED STUB.
// Real implementation lives at src/lib/op-audit.ts on the VPS — DO NOT replace.
// This stub exists only so reindex.ts compiles in isolation inside this staged dir.
export interface OpResult {
  affected_rows?: number;
  notes?: string;
}
export type DbSource = "main" | "shadow" | "isolated" | "test";
export interface WithOpAuditOptions {
  db_source: DbSource;
}

export async function withOpAudit<T extends OpResult>(
  opName: string,
  _options: WithOpAuditOptions,
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
