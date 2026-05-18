/**
 * T13 — HTTP `POST /api/import` handler (framework-agnostic).
 *
 * Accepts JSON body `{ archive_b64: string, passphrase?: string, mode?: 'merge'|'replace',
 * dry_run?: bool, verify_only?: bool }`. Caller is responsible for adapting to
 * multipart/form-data on the host server side (we keep the contract pure JSON
 * here to avoid pulling a multipart parser dependency into staged-A2).
 *
 * Returns summary JSON: counts, conflicts, duration.
 */

import {
  runImport,
  ImportRequest,
  ProgressEvent,
} from "../lib/archive/orchestrator.js";
import { ChunkRow, KgEntityRow, KgRelationRow, OpsAuditRow, BadPassphraseError, TamperedArchiveError } from "../lib/archive/types.js";

export interface HttpImportBody {
  /** Base64-encoded gzipped tar archive. */
  archive_b64?: string;
  passphrase?: string;
  mode?: "merge" | "replace";
  dry_run?: boolean;
  verify_only?: boolean;
}

export interface HttpResponse {
  status: number;
  headers: Record<string, string>;
  body: Buffer | string;
}

export interface HttpImportDeps {
  loadExisting: () => Promise<{
    chunks: ChunkRow[];
    kg_entities: KgEntityRow[];
    kg_relations: KgRelationRow[];
    ops_audit: OpsAuditRow[];
  }>;
  currentSchemaVersion: () => Promise<number>;
  persist?: (
    resolved: import("../lib/archive/orchestrator.js").ImportResult["resolved"],
  ) => Promise<void>;
  signal?: AbortSignal;
  onProgress?: (ev: ProgressEvent) => void;
}

export async function handleImport(
  body: HttpImportBody,
  deps: HttpImportDeps,
): Promise<HttpResponse> {
  if (!body.archive_b64) {
    return jsonResponse(400, { error: "archive_b64 required" });
  }
  let archive: Buffer;
  try {
    archive = Buffer.from(body.archive_b64, "base64");
    if (archive.length === 0) {
      return jsonResponse(400, { error: "archive_b64 decoded to empty buffer" });
    }
  } catch (err) {
    return jsonResponse(400, { error: `bad base64: ${(err as Error).message}` });
  }

  const existing = await deps.loadExisting();
  const currentSchemaVersion = await deps.currentSchemaVersion();
  const req: ImportRequest = {
    archive,
    passphrase: body.passphrase,
    mode: body.mode ?? "merge",
    dry_run: body.dry_run === true,
    verify_only: body.verify_only === true,
    current_schema_version: currentSchemaVersion,
    existing,
    signal: deps.signal,
    onProgress: deps.onProgress,
  };

  let result;
  try {
    result = await runImport(req);
  } catch (err) {
    if (err instanceof BadPassphraseError) {
      return jsonResponse(401, { error: "bad passphrase" });
    }
    if (err instanceof TamperedArchiveError) {
      return jsonResponse(409, { error: "archive tampered" });
    }
    const msg = (err as Error).message;
    if (/encrypted/.test(msg) && !body.passphrase) {
      return jsonResponse(401, { error: "passphrase required" });
    }
    if (/cancel/i.test(msg)) {
      return jsonResponse(499, { error: "cancelled" });
    }
    return jsonResponse(500, { error: msg });
  }

  if (!body.dry_run && !body.verify_only && deps.persist) {
    try {
      await deps.persist(result.resolved);
    } catch (err) {
      return jsonResponse(500, {
        error: `persist failed: ${(err as Error).message}`,
      });
    }
  }

  return jsonResponse(200, {
    mode: body.mode ?? "merge",
    dry_run: body.dry_run === true,
    verify_only: body.verify_only === true,
    encrypted: result.manifest.encryption.enabled,
    schema_version_archive: result.manifest.schema_version,
    schema_version_target: currentSchemaVersion,
    stats: result.stats,
    duration_ms: result.duration_ms,
  });
}

function jsonResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}
