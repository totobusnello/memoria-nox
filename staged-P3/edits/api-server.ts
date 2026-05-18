/**
 * src/api-server.ts — P3 temporal queries HTTP API patch
 *
 * APPLIES ON TOP OF: staged-1.6/edits/api-server.ts (current VPS version)
 *
 * Change: extend the /api/search handler to accept as_of and changed_since
 * query parameters (GET) or body fields (POST).
 *
 * Replace the existing "/api/search" case block WITH the version below.
 *
 * Also add this import near the top of api-server.ts:
 *   import { parseFlexibleDate } from "./dates.js";
 */

// ── /api/search handler replacement ──────────────────────────────────────────

// GET  /api/search?q=foo&limit=10&as_of=7d&changed_since=2026-05-01
// POST /api/search  body: { q, limit, as_of, changed_since }

case "/api/search": {
  let q_param: string | undefined;
  let limit_param: string | undefined;
  let as_of_param: string | undefined;
  let changed_since_param: string | undefined;

  if (req.method === "POST") {
    const body = await readJson<{
      q?: string;
      limit?: number | string;
      as_of?: string;
      changed_since?: string;
    }>(req);
    q_param = body.q;
    limit_param = body.limit !== undefined ? String(body.limit) : undefined;
    as_of_param = body.as_of;
    changed_since_param = body.changed_since;
  } else {
    const qs = parseQuery(url);
    q_param = qs.q;
    limit_param = qs.limit;
    as_of_param = qs.as_of;
    changed_since_param = qs.changed_since;
  }

  if (!q_param) { json(res, { error: "q parameter required" }, 400); break; }

  const limit = parseInt(limit_param || "10");
  const { parseFlexibleDate } = await import("./dates.js");

  let asOf: Date | undefined;
  let changedSince: Date | undefined;
  try {
    if (as_of_param) asOf = parseFlexibleDate(as_of_param);
    if (changed_since_param) changedSince = parseFlexibleDate(changed_since_param);
  } catch (err) {
    json(res, { error: (err as Error).message }, 400);
    break;
  }

  const filter = { asOf, changedSince };
  const results = await searchHybrid(q_param, limit, filter);
  json(res, results);
  break;
}
