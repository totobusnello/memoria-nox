#!/usr/bin/env node
// sprint-empates-salience-producao.mjs — recompute of TIEBREAK-EXPOSURE (§5.7.1) on the key the
// coverage comparator actually uses: (last_served truncated, calculateSalience), with
// calculateSalience IMPORTED from the deposited serving-salience.ts (rule 5 of §3.2).
//
// Why (REVIEW-A-rc3-2026-10-04.md, finding #4, Grok#6, confirmed):
//   measurement/empates-por-granularidade.py counts ties on the SQL pre-rank expression
//   0.55*COALESCE(importance,0.5) + 0.10*COALESCE(pain,0.2) + 0.1*(access_count>0),
//   which in serving-brief.ts is only the ORDER BY that cuts the eligible set to
//   FRESH_CANDIDATE_POOL = 400 (:731-737, and its JS replica :689-702). With 108 eligible it
//   excludes nobody. The comparator then re-sorts by
//   coverageCompare(lastServedMs, calculateSalience(r, nowMs) + boost) (:708-712, :747-751,
//   ordenarCobertura :605-616). Two candidates are indistinguishable to the comparator iff they
//   share lastServedMs AND calculateSalience exactly (coverageCompare returns
//   bSalience - aSalience, which is 0 only on exact equality); the JS sort is stable, so such a
//   pair keeps the SQL input order.
//
// Input: the same read-only extract as sprint-contrafactual-salience-producao.mjs (gzip JSON from
//   a COPY of e20260907T060001Z.db: all 67,187 chunks with the salience fields, and the brief_log
//   rows of [2026-08-20, 2026-08-27)). The extract stays outside the repo (it lists private
//   source paths); this script writes only aggregates and integer ids.
//
// Instants: the extract's brief_log ends 2026-08-26 23:52:09, so the original instant of the
//   2026-08-29 run (live DB, julianday('now') at run time, not recorded) cannot be rebuilt. We pin
//   instants inside the 350-state replay window that the extract covers (it starts 2026-08-26
//   20:37Z) and on the two preceding days, and compute BOTH keys at each instant, so old and new are
//   compared at the same instant. last_served(T) = MAX(served_at <= T) over the window; this equals
//   the full-history value for every chunk served in [2026-08-20, T], which is all 108 (100% of the
//   pool served each day, POOL-ELEGIVEL-2026-08-26-to-29.json); the script aborts otherwise.
//
// Limits (declared in the output): importance, pain, access_count and last_accessed_at are as stored
//   at the 2026-09-07 copy. last_accessed_at after T is bracketed (kept / dropped), as in the
//   counterfactual script. Ties are counted, not resolved; how much of 127/281/348 the arbitrary
//   order decides is still not measured.
//
// Usage: node sprint-empates-salience-producao.mjs --extract X.json.gz --ref COVERAGE-SET.json --out out/....json
//        add --shared-plus 1 for out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json (D-A3)
import fs from "node:fs";
import zlib from "node:zlib";
import { calculateSalience } from "../serving-salience.ts";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? [...acc, [v.slice(2), a[i + 1]]] : acc), []),
);
if (!args.extract || !args.ref) { console.error("--extract and --ref required"); process.exit(2); }
// --shared-plus 1 (added 2026-10-05, CHECK-A-rc4-B-rc4.md D-A3): also emit last_accessed_at, created_at and a
// source-file CLASS in each tie group's `shared`, so the §5.7.1 sentence on what the remaining ties share is
// checkable from the artifact. Off by default: without it the output is byte-identical to
// out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json. With it, write to a NEW file; never overwrite that one.
const SHARED_PLUS = args["shared-plus"] === "1";
const raw = JSON.parse(zlib.gunzipSync(fs.readFileSync(args.extract)).toString("utf8"));
const refIds = new Set(JSON.parse(fs.readFileSync(args.ref, "utf8")).reference_ids);

// predicate verbatim from serving-brief.ts:638-645 with GLOBAL_FRESH_PATTERNS (:135) and the
// defaults of brief-diversity.ts:59-62 (freshMinImp 0.7, freshMinPain 0.7, freshGlobalMaxAgeDays 30)
const like = (s, pat) => (pat.endsWith("%") ? (s ?? "").startsWith(pat.slice(0, -1)) : s === pat);
const PATTERNS = ["memory/entities/%", "memory/lessons.md"];
const julianMs = (s) => Date.parse(s.length === 10 ? s + "T00:00:00Z" : s.replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? "" : "Z"));
const sqlKey = (c) => 0.55 * (c.importance ?? 0.5) + 0.10 * (c.pain ?? 0.2) + ((c.access_count ?? 0) > 0 ? 0.1 : 0);
const GRAN = { seg: 19, min: 16, hora: 13, dia: 10 };

const bl = raw.brief_log_window;
function pool(Tms) {
  return raw.chunks.filter((c) =>
    PATTERNS.some((p) => like(c.source_file, p)) &&
    ((c.importance ?? 0) >= 0.7 || (c.pain ?? 0) >= 0.7) &&
    (Tms - julianMs(c.source_date ?? c.created_at)) / 86400000 <= 30);
}
function lastServed(ids, Tms) {
  const m = new Map();
  for (const r of bl) {
    if (!ids.has(r.chunk_id) || julianMs(r.served_at) > Tms) continue;
    if (!m.has(r.chunk_id) || r.served_at > m.get(r.chunk_id)) m.set(r.chunk_id, r.served_at);
  }
  return m;
}
const dropFuture = (c, Tms) => (c.last_accessed_at && Date.parse(c.last_accessed_at) > Tms ? { ...c, last_accessed_at: null } : c);
function census(P, ls, score) {
  const n = P.length, total = (n * (n - 1)) / 2;
  const rows = [];
  for (const [g, k] of Object.entries(GRAN)) {
    const groups = new Map();
    for (const c of P) {
      const l = ls.get(c.id);
      const key = (l === undefined ? "NULL" : l.slice(0, k)) + "|" + score(c);
      groups.set(key, (groups.get(key) ?? 0) + 1);
    }
    let pairs = 0, big = 0;
    for (const v of groups.values()) { pairs += (v * (v - 1)) / 2; big = Math.max(big, v); }
    rows.push({ granularidade: g, pares_indistinguiveis: pairs, maior_bloco_indistinguivel: big,
      pct_dos_pares: +(100 * pairs / total).toFixed(2) });
  }
  const distinct = new Set(P.map(score)).size;
  return { valores_distintos_de_salience: distinct, por_granularidade: rows };
}

const INSTANTS = ["2026-08-26T20:37:00Z", "2026-08-26T22:00:00Z", "2026-08-26T23:52:09Z",
  "2026-08-25T23:59:59Z", "2026-08-24T23:59:59Z"];
const rounds = [];
for (const iso of INSTANTS) {
  const T = Date.parse(iso);
  const P = pool(T);
  const ids = new Set(P.map((c) => c.id));
  const sameAsRef = ids.size === refIds.size && [...ids].every((i) => refIds.has(i));
  if (!sameAsRef) { console.error(`ABORT ${iso}: pool ${ids.size} is not the 108 reference ids`); process.exit(1); }
  const ls = lastServed(ids, T);
  if (ls.size !== P.length) { console.error(`ABORT ${iso}: ${P.length - ls.size} pool chunks unserved inside the window; last_served would be wrong`); process.exit(1); }
  const keys = {
    sql_prerank_expression: (c) => sqlKey(c),
    calculateSalience: (c) => calculateSalience(c, T),
    calculateSalience_drop_future_access: (c) => calculateSalience(dropFuture(c, T), T),
  };
  const r = { instant: iso, pool: P.length, pares_possiveis: (P.length * (P.length - 1)) / 2 };
  for (const [k, f] of Object.entries(keys)) r[k] = census(P, ls, f);
  // mechanism of the remaining ties: what the tied candidates share
  const groups = new Map();
  for (const c of P) {
    const key = ls.get(c.id) + "|" + calculateSalience(c, T);
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(c);
  }
  const tied = [...groups.values()].filter((g) => g.length > 1);
  r.ties_at_second_with_calculateSalience = tied.map((g) => ({
    size: g.length,
    ids: g.map((c) => c.id).sort((a, b) => a - b),
    same_source_file: new Set(g.map((c) => c.source_file)).size === 1,
    shared: { importance: [...new Set(g.map((c) => c.importance))], pain: [...new Set(g.map((c) => c.pain))],
      access_count: [...new Set(g.map((c) => c.access_count))], retention_days: [...new Set(g.map((c) => c.retention_days))],
      ...(SHARED_PLUS ? {
        last_accessed_at: [...new Set(g.map((c) => c.last_accessed_at))],
        created_at: [...new Set(g.map((c) => c.created_at))],
        // class only, never the path: entity slugs can name people (the repo is public)
        source_file_class: [...new Set(g.map((c) => (c.source_file === "memory/lessons.md" ? "memory/lessons.md" : (c.source_file ?? "").startsWith("memory/entities/") ? "memory/entities/*" : "other")))],
      } : {}) },
  }));
  rounds.push(r);
}

const out = {
  script: "measurement/sprint-empates-salience-producao.mjs",
  scoring_function: "serving-salience.ts::calculateSalience (imported; sha256 083399fc... per SERVING-CODE-MANIFEST.md)",
  supersedes_key_of: "TIEBREAK-EXPOSURE-2026-08-29.json (measured on the SQL pre-rank expression)",
  input_db_sha256: raw.db_sha256,
  reference_pool: "A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json reference_ids (108)",
  original_instant_not_rebuildable: "the 2026-08-29 run read a live DB with julianday('now') at run time, not recorded; the extract's brief_log ends 2026-08-26 23:52:09",
  limits: [
    "importance, pain, access_count, last_accessed_at as stored at the 2026-09-07 copy",
    "last_accessed_at later than the instant: kept (calculateSalience) and dropped (calculateSalience_drop_future_access)",
    "ties are counted, not resolved: how much of 127/281/348 the arbitrary order decides is not measured",
  ],
  rounds,
};
const s = JSON.stringify(out, null, 1);
if (args.out) fs.writeFileSync(args.out, s + "\n");
console.log(s);
