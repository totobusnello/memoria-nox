/**
 * T13 — HTTP `POST /api/export` handler (framework-agnostic).
 *
 * Returns a `{ status, headers, body }` shape so the host server (express,
 * fastify, plain http.Server) can adapt without coupling. The actual streaming
 * write happens in the caller; we return the archive Buffer plus suggested
 * headers (Content-Type, Content-Disposition, Content-Length).
 *
 * Body schema:
 *   { unencrypted?: bool,
 *     passphrase?: string,        // accepted ONLY over POST body (TLS-protected)
 *     project?: string,
 *     since?: string,
 *     until?: string,
 *     exclude_embeddings?: bool }
 *
 * Auth: the parent API layer enforces middleware (regra #4 — port 18802 +
 * existing auth). This module is unauthenticated by design; never expose it
 * directly.
 */

import {
  runExport,
  ExportRequest,
  ProgressEvent,
} from "../lib/archive/orchestrator.js";

export interface HttpExportBody {
  unencrypted?: boolean;
  passphrase?: string;
  project?: string;
  since?: string;
  until?: string;
  exclude_embeddings?: boolean;
}

export interface HttpResponse {
  status: number;
  headers: Record<string, string>;
  body: Buffer | string;
}

export interface HttpExportDeps {
  dbReader: () => Promise<Omit<ExportRequest, "passphrase" | "unencrypted" | "signal" | "onProgress">>;
  signal?: AbortSignal;
  onProgress?: (ev: ProgressEvent) => void;
  /** Optional max archive size guard (defaults to 5 GiB). */
  maxBytes?: number;
}

const DEFAULT_MAX_BYTES = 5 * 1024 * 1024 * 1024;

export async function handleExport(
  body: HttpExportBody,
  deps: HttpExportDeps,
): Promise<HttpResponse> {
  // Validate
  if (
    !body.unencrypted &&
    (typeof body.passphrase !== "string" || body.passphrase.length === 0)
  ) {
    return jsonResponse(400, {
      error:
        "passphrase required when not unencrypted (D41 #2 encrypt-by-default)",
    });
  }

  const corpus = await deps.dbReader();
  if (body.exclude_embeddings) {
    corpus.embeddings = undefined;
  }

  let result;
  try {
    result = await runExport({
      ...corpus,
      filters: {
        project: body.project ?? null,
        since: body.since ?? null,
        until: body.until ?? null,
      },
      unencrypted: body.unencrypted === true,
      passphrase: body.passphrase,
      signal: deps.signal,
      onProgress: deps.onProgress,
    });
  } catch (err) {
    const msg = (err as Error).message;
    if (/cancel/i.test(msg)) {
      return jsonResponse(499, { error: "client closed request" });
    }
    return jsonResponse(500, { error: msg });
  }

  const max = deps.maxBytes ?? DEFAULT_MAX_BYTES;
  if (result.archive.length > max) {
    return jsonResponse(413, {
      error: `archive too large: ${result.archive.length} > ${max} bytes`,
      hint: "use --project / --since filters or split via multiple exports",
    });
  }

  const date = new Date().toISOString().slice(0, 10);
  const fileName = `nox-mem-export-${date}.tgz`;
  return {
    status: 200,
    headers: {
      "Content-Type": "application/gzip",
      "Content-Disposition": `attachment; filename="${fileName}"`,
      "Content-Length": String(result.archive.length),
      "X-Archive-Encrypted": String(result.manifest.encryption.enabled),
      "X-Archive-Chunks": String(result.manifest.counts.chunks),
      "X-Archive-Duration-Ms": String(result.duration_ms),
    },
    body: result.archive,
  };
}

function jsonResponse(status: number, payload: unknown): HttpResponse {
  return {
    status,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
}
