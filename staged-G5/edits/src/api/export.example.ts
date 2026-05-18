/**
 * G5 T3 — Integration EXAMPLE: A2 `POST /api/export` refactored to use the
 * sanitizer.
 *
 * Diff vs `staged-A2/edits/src/api/export.ts`:
 *
 *   - The current `try/catch` returns `jsonResponse(500, { error: msg })`
 *     where `msg` is the RAW `err.message`. If the underlying error is e.g.
 *     `Error: ENOENT, open '/Users/lab/secret-passphrase.txt'`, that path
 *     LEAKS verbatim. The sanitizer strips it.
 *   - `BadPassphraseError` / `TamperedArchiveError` / `WeakPassphraseError`
 *     get clean 4xx codes via the central map instead of bare 500.
 *   - X-Request-ID emitted for support traceability.
 *
 * Side-by-side example only — Wave G will copy these lines into staged-A2.
 */

import { errorToResponse } from "../lib/error-sanitizer/middleware.js";

// Placeholder types (real refactor uses staged-A2 modules verbatim).
type HttpExportBody = {
  unencrypted?: boolean;
  passphrase?: string;
  project?: string;
  since?: string;
  until?: string;
  exclude_embeddings?: boolean;
};

type HttpResponse = {
  status: number;
  headers: Record<string, string>;
  body: Buffer | string | unknown;
};

interface HttpExportDeps {
  dbReader: () => Promise<{ embeddings?: unknown; chunks: unknown[] }>;
  signal?: AbortSignal;
  maxBytes?: number;
  /** Caller-injected request id (from server middleware). */
  requestId?: string;
}

const DEFAULT_MAX_BYTES = 5 * 1024 * 1024 * 1024;

export async function handleExport(
  body: HttpExportBody,
  deps: HttpExportDeps,
): Promise<HttpResponse> {
  // Validate — known 400 paths still return a clean shape via errorToResponse.
  if (
    !body.unencrypted &&
    (typeof body.passphrase !== "string" || body.passphrase.length === 0)
  ) {
    return errorToResponse(
      new (class extends Error {
        constructor() {
          super("passphrase required (D41 #2 encrypt-by-default)");
          this.name = "InvalidBodyError";
        }
      })(),
      { requestId: deps.requestId },
    );
  }

  try {
    const corpus = await deps.dbReader();
    if (body.exclude_embeddings) {
      corpus.embeddings = undefined;
    }
    // … runExport(corpus, …) — unchanged
    const archive = Buffer.from(""); // placeholder
    const max = deps.maxBytes ?? DEFAULT_MAX_BYTES;
    if (archive.length > max) {
      return errorToResponse(
        new (class extends Error {
          constructor() {
            super(`archive too large: ${archive.length} > ${max} bytes`);
            this.name = "PayloadTooLargeError";
          }
        })(),
        { requestId: deps.requestId },
      );
    }
    return {
      status: 200,
      headers: {
        "Content-Type": "application/gzip",
        "X-Request-ID": deps.requestId ?? "n/a",
      },
      body: archive,
    };
  } catch (err) {
    // Maps BadPassphraseError → 422, TamperedArchiveError → 422,
    // PayloadTooLargeError → 413, WeakPassphraseError → 400, else 500.
    return errorToResponse(err, { requestId: deps.requestId });
  }
}
