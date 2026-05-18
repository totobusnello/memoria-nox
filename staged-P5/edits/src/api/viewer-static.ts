/**
 * T7 — Static file serving for /viewer/*
 *
 * Framework-agnostic helper: caller invokes `serveViewerFile(req.path)` and
 * receives a `StaticResponse` it can write to whatever HTTP layer is in use.
 *
 * Path resolution:
 *  /viewer            → index.html
 *  /viewer/           → index.html
 *  /viewer/app.js     → app.js
 *  /viewer/style.css  → style.css
 *  /viewer/<path traversal attempt> → 404 (never escape /viewer dir)
 */

import { readFileSync, statSync } from "node:fs";
import { join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = fileURLToPath(new URL(".", import.meta.url));
// edits/src/api/ -> edits/src/viewer/
const DEFAULT_ROOT = resolve(HERE, "..", "viewer");

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".png": "image/png",
  ".woff2": "font/woff2",
};

export interface StaticResponse {
  status: 200 | 304 | 404;
  headers: Record<string, string>;
  body: Buffer | string;
}

export interface ServeOptions {
  /** Override the document root (mostly for tests). */
  root?: string;
  /** Cache-Control max-age in seconds. Default 300 (5 minutes). */
  cacheSeconds?: number;
}

function extensionOf(p: string): string {
  const i = p.lastIndexOf(".");
  return i >= 0 ? p.slice(i).toLowerCase() : "";
}

function safeJoin(root: string, rel: string): string | null {
  // Reject explicit `..` traversal pre-normalize so /viewer/../etc/passwd
  // does not silently collapse to /etc/passwd (Node's normalize would
  // resolve the .. against a root-relative path and drop it).
  if (/(^|[\\/])\.\.([\\/]|$)/.test(rel)) return null;
  const stripped = rel.replace(/^([\\/]+)/, "");
  const normalized = normalize(stripped);
  if (normalized.includes("..")) return null;
  const full = join(root, normalized);
  const fullResolved = resolve(full);
  const rootResolved = resolve(root);
  if (
    !fullResolved.startsWith(rootResolved + "/") &&
    fullResolved !== rootResolved
  ) {
    return null;
  }
  return fullResolved;
}

/**
 * Resolve a request path under `/viewer` to a file on disk.
 * Returns null when the path is outside the viewer root or attempts traversal.
 */
export function resolveViewerPath(
  requestPath: string,
  root: string = DEFAULT_ROOT
): string | null {
  // Strip optional leading `/viewer`
  let rel = requestPath;
  if (rel.startsWith("/viewer")) rel = rel.slice("/viewer".length);
  if (rel === "" || rel === "/") rel = "/index.html";
  // Reject query/hash leftovers.
  rel = rel.split("?")[0]!.split("#")[0]!;
  return safeJoin(root, rel);
}

export function serveViewerFile(
  requestPath: string,
  opts: ServeOptions = {}
): StaticResponse {
  const root = opts.root ?? DEFAULT_ROOT;
  const cacheSeconds = opts.cacheSeconds ?? 300;
  const resolved = resolveViewerPath(requestPath, root);
  if (!resolved) {
    return notFound();
  }
  try {
    const st = statSync(resolved);
    if (!st.isFile()) return notFound();
    const ext = extensionOf(resolved);
    const contentType = CONTENT_TYPES[ext] ?? "application/octet-stream";
    const body = readFileSync(resolved);
    return {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": `public, max-age=${cacheSeconds}`,
        "X-Content-Type-Options": "nosniff",
      },
      body,
    };
  } catch {
    return notFound();
  }
}

function notFound(): StaticResponse {
  return {
    status: 404,
    headers: { "Content-Type": "text/plain; charset=utf-8" },
    body: "Not Found",
  };
}
