/**
 * src/api/server-deps-a2.ts — Wave O T2: A2 (export/import) wire-up adapter.
 *
 * Companion to `src/lib/archive/server-deps.ts`. This module re-exports the
 * deps builders under the `/api/*` path used by tests + provides convenience
 * helpers for streaming + multipart parsing that the wire-up.ts router
 * intentionally does NOT couple to (keeping wire-up framework-agnostic).
 *
 * Two streaming concerns are handled here:
 *
 *   1. Export response: when the archive size > NOX_EXPORT_STREAM_THRESHOLD
 *      (default 16 MiB), we set `Transfer-Encoding: chunked` and write the
 *      buffer in 1 MiB slices, yielding to the event loop between writes so
 *      we don't starve other requests (regra de ouro #4 — Node single-thread).
 *
 *   2. Import request: the wire-up.ts contract is JSON body with
 *      `archive_b64`. We also accept `multipart/form-data` when
 *      `Content-Type` starts with `multipart/`, parsing the first file part
 *      out as the binary archive (no @types/formidable dep — minimal parser).
 *      This lets curl users `--data-binary @file.tgz` upload directly.
 *
 * Singleton DB resolution stays in deps-registry. This module is pure
 * stream/parsing glue.
 */

import type { ServerResponse, IncomingMessage } from "node:http";

export {
  buildExportDeps,
  buildImportDeps,
  type HttpExportDeps,
  type HttpImportDeps,
} from "../lib/archive/server-deps.js";

// ─── Streaming export response ───────────────────────────────────────────────

const DEFAULT_STREAM_THRESHOLD = 16 * 1024 * 1024; // 16 MiB
const CHUNK_SIZE = 1 * 1024 * 1024; // 1 MiB slices

/**
 * Write a Buffer back to the response. Small payloads get a single `end()`;
 * large payloads stream via `Transfer-Encoding: chunked` to avoid blocking
 * the event loop.
 *
 * Returns a promise that resolves when the response is fully drained.
 */
export async function writeExportResponse(
  res: ServerResponse,
  body: Buffer,
  baseHeaders: Record<string, string>,
  threshold = DEFAULT_STREAM_THRESHOLD,
): Promise<void> {
  if (body.length <= threshold) {
    res.writeHead(200, baseHeaders);
    res.end(body);
    return;
  }
  // Strip Content-Length (chunked encoding requires it absent).
  const { ["Content-Length"]: _drop, ...rest } = baseHeaders;
  const headers = { ...rest, "Transfer-Encoding": "chunked" };
  res.writeHead(200, headers);

  for (let off = 0; off < body.length; off += CHUNK_SIZE) {
    const slice = body.subarray(off, Math.min(off + CHUNK_SIZE, body.length));
    const ok = res.write(slice);
    if (!ok) {
      await new Promise<void>((r) => res.once("drain", r));
    }
    // Yield to the event loop so other requests aren't starved.
    await new Promise<void>((r) => setImmediate(r));
  }
  res.end();
}

// ─── Multipart/form-data parsing (best-effort, dependency-free) ──────────────

export interface MultipartFile {
  name: string;
  filename: string;
  contentType: string;
  content: Buffer;
}

/**
 * Parse a multipart/form-data body. Returns the first file part found.
 * This is a minimal RFC 7578 implementation — no dependency on `busboy` /
 * `formidable`. For payloads <64 MiB (wire-up.ts cap) this is plenty.
 *
 * Returns `null` when the content-type isn't multipart or when no file part
 * is present. Throws on malformed boundary structure.
 */
export function parseMultipartFirstFile(
  rawBody: Buffer,
  contentType: string,
): MultipartFile | null {
  if (!/^multipart\/form-data/i.test(contentType)) return null;
  const m = /boundary=("?)([^";\s]+)\1/.exec(contentType);
  if (!m) throw new Error("missing boundary in multipart Content-Type");
  const boundary = `--${m[2]}`;
  const boundaryBuf = Buffer.from(boundary);
  const closeBuf = Buffer.from(`${boundary}--`);

  let off = 0;
  while (off < rawBody.length) {
    const start = rawBody.indexOf(boundaryBuf, off);
    if (start < 0) return null;
    // Move past boundary + CRLF
    let cursor = start + boundaryBuf.length;
    if (
      rawBody[cursor] === 0x2d /* '-' */ &&
      rawBody[cursor + 1] === 0x2d /* '-' */
    ) {
      return null; // final boundary
    }
    if (rawBody[cursor] === 0x0d /* CR */) cursor += 2;
    // Read part headers until \r\n\r\n
    const headerEnd = rawBody.indexOf(Buffer.from("\r\n\r\n"), cursor);
    if (headerEnd < 0) return null;
    const headerText = rawBody.slice(cursor, headerEnd).toString("utf-8");
    const bodyStart = headerEnd + 4;
    const nextBoundary = rawBody.indexOf(boundaryBuf, bodyStart);
    if (nextBoundary < 0) return null;
    // Strip the trailing CRLF before the next boundary marker.
    const bodyEnd = nextBoundary - 2;
    const partBody = rawBody.subarray(bodyStart, bodyEnd);

    // Inspect headers for filename + name.
    const dispMatch =
      /Content-Disposition:\s*form-data;\s*name="([^"]+)"(?:;\s*filename="([^"]*)")?/i.exec(
        headerText,
      );
    const typeMatch = /Content-Type:\s*([^\r\n]+)/i.exec(headerText);

    if (dispMatch && dispMatch[2]) {
      return {
        name: dispMatch[1] ?? "",
        filename: dispMatch[2] ?? "",
        contentType: typeMatch?.[1]?.trim() ?? "application/octet-stream",
        content: Buffer.from(partBody),
      };
    }
    off = nextBoundary;
    if (rawBody.indexOf(closeBuf, off) === off) return null;
  }
  return null;
}

// ─── Body collector (Buffer-typed, replaces wire-up's string-mode reader) ────

/**
 * Collect the request body as a Buffer (binary-safe). Wire-up's `readBody()`
 * decodes to UTF-8 which mangles archives. Adapter callers must use this
 * helper when the route can receive multipart/binary payloads.
 */
export function readRequestBodyBuffer(
  req: IncomingMessage,
  limit = 64 * 1024 * 1024,
): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on("data", (chunk: Buffer) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error("Payload too large"));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on("end", () => resolve(Buffer.concat(chunks)));
    req.on("error", reject);
  });
}
