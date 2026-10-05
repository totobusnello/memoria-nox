#!/usr/bin/env node
// sprint-contrafactual-salience-producao.mjs — re-run of the §4.3.2 access counterfactual
// with the DEPOSITED production salience (serving-salience.ts::calculateSalience), imported,
// not reimplemented (rule 5 of §3.2).
//
// Why (adversarial review of rc3, Codex #2/#3, verified 2026-10-05):
//   measurement/contrafactual-do-topo.py computes recency as max(0, 1 - age/365) from
//   COALESCE(source_date, created_at), and importance as COALESCE(importance, 0.5).
//   Production (serving-salience.ts:58-98, 118-134, 246-264) computes recency as
//   2^(-age/retention), age from last_accessed_at ?? source_date, with retention 0
//   (never-decay, recency = 1.0) when retention_days IS NULL; and importance falls back to a
//   per-type prior, not 0.5. The published 2/3/5 -> 131/129/128 therefore came from a
//   different function than the one that ranks the brief.
//
// Input: --extract  gzip JSON produced read-only from a COPY of the 2026-09-07 trial epoch
//        (e20260907T060001Z.db, sha256 4ec7e182...1fe721345, the DB that reproduced every
//        §4.3 quantity in RECON-52-e-sondas-2026-10-04.json). Fields: chunks(id, source_file,
//        chunk_type, source_type, tier, pain, importance, retention_days, source_date,
//        created_at, updated_at, last_accessed_at, access_count) and brief_log rows with
//        served_at in [2026-08-20, 2026-08-27). The extract stays outside the repo (it lists
//        private source paths); this script writes only aggregates.
//
// What it computes, for several pinned "now" values:
//   A. ranking over the 149 served-and-still-existing chunks of the window (the population of
//      the published counterfactual), under four score functions:
//        legacy      = the published script's function (anchor: must give 2/131, 3/129, 5/128)
//        prod        = calculateSalience as deposited
//        prod_acc0   = calculateSalience with access_count = 0 for every chunk
//        prod_noacc  = calculateSalience with access_count = 0 AND last_accessed_at = null
//                      (no access history at all: access also feeds recency in production)
//   B. the production main-pool path for the scope pool of the brief (scope=global ⇒
//      scopePatterns = [] ⇒ the whole corpus): SQL pre-rank proxy (brief.ts:384-388,
//      access binary term recomputed per variant) -> LIMIT 500 -> calculateSalience re-rank
//      (brief.ts:390-397). Rank of the three inside that pool. Near-duplicate dedup
//      (pickDedup) is NOT replayed: it can only remove items ranked above, so the pool rank
//      is an upper bound (worst case) on the position the dedup leaves.
//
// Usage: node sprint-contrafactual-salience-producao.mjs --extract X.json.gz --out out/....json
import fs from "node:fs";
import zlib from "node:zlib";
import { calculateSalience } from "../serving-salience.ts";

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, v, i, a) => (v.startsWith("--") ? [...acc, [v.slice(2), a[i + 1]]] : acc), []),
);
if (!args.extract) { console.error("--extract required"); process.exit(2); }
const raw = JSON.parse(zlib.gunzipSync(fs.readFileSync(args.extract)).toString("utf8"));
const chunks = raw.chunks;
const byId = new Map(chunks.map((c) => [c.id, c]));
// optional: the 52 chunks deleted on 2026-08-22, restored read-only from the 2026-08-21 06:00 UTC
// daily backup (sha256 40683f8e...8e724ffa), as in RECON-52-e-sondas-2026-10-04.json. Used only for
// the 201-pool variants; never added to the corpus of the scope-pool path (they did not exist at 09-07).
const restored = args.extract52 ? JSON.parse(zlib.gunzipSync(fs.readFileSync(args.extract52)).toString("utf8")) : [];
const byIdPlus = new Map([...byId, ...restored.map((c) => [c.id, c])]);
// probe briefs and probe-only chunks (out/ancora-sondas.json; ORGANICO-e-hashes-2026-10-04.txt)
const PROBE_BRIEFS = new Set(args.sondas ? JSON.parse(fs.readFileSync(args.sondas, "utf8")).procedencia.sondas_excluidas : []);
const THREE = [116467, 112241, 116107];
const CANDIDATE_POOL = 500; // brief.ts:104

// ── window population ────────────────────────────────────────────────────────
const bl = raw.brief_log_window;
const briefs = new Set(bl.map((r) => r.brief_id));
const perChunkBriefs = new Map();
for (const r of bl) {
  if (!perChunkBriefs.has(r.chunk_id)) perChunkBriefs.set(r.chunk_id, new Set());
  perChunkBriefs.get(r.chunk_id).add(r.brief_id);
}
const served = [...perChunkBriefs.keys()];
const servedExisting = served.filter((id) => byId.has(id));
const organicServed = [...new Set(bl.filter((r) => !PROBE_BRIEFS.has(r.brief_id)).map((r) => r.chunk_id))];
const organicExisting = organicServed.filter((id) => byId.has(id));
const served201 = served.filter((id) => byIdPlus.has(id));
const organic196 = organicServed.filter((id) => byIdPlus.has(id));
const ubiquitous = served.filter((id) => perChunkBriefs.get(id).size === briefs.size).sort();
const scopes = {}; const agents = {};
for (const r of bl) { scopes[r.scope] = (scopes[r.scope] ?? 0) + 1; agents[r.agent ?? "null"] = (agents[r.agent ?? "null"] ?? 0) + 1; }

// ── score functions ──────────────────────────────────────────────────────────
const LOG1000 = Math.log(1000);
const julian = (s) => Date.parse(s.length === 10 ? s + "T00:00:00Z" : s.replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(s) ? "" : "Z"));
function legacy(c, nowMs, withAccess) {
  // verbatim port of contrafactual-do-topo.py:68-76
  const imp = c.importance ?? 0.5, pain = c.pain ?? 0.2, acc = c.access_count ?? 0;
  const ref = c.source_date ?? c.created_at;
  const age = ref ? (nowMs - julian(ref)) / 86400000 : 0;
  const rec = Math.max(0, Math.min(1, 1 - (age || 0) / 365));
  const a = !acc || acc <= 0 ? 0 : Math.min(1, Math.log1p(acc) / LOG1000);
  return 0.55 * imp + 0.15 * rec + 0.10 * pain + 0.20 * (withAccess ? a : 0);
}
const variantRow = {
  prod: (c) => c,
  prod_acc0: (c) => ({ ...c, access_count: 0 }),
  prod_noacc: (c) => ({ ...c, access_count: 0, last_accessed_at: null }),
};
// The epoch holds only the LATEST last_accessed_at. For a pinned "now" inside the window, an access
// recorded after "now" gives the chunk recency 1.0 (age <= 0, serving-salience.ts:94), the most
// favourable value for a competitor; dropping it (fallback to source_date) is the least favourable.
// The true in-window value lies between, so the two variants bracket the three's rank.
const dropFuture = (c, now) => (c.last_accessed_at && Date.parse(c.last_accessed_at) > now ? { ...c, last_accessed_at: null } : c);
const scorers = {
  legacy_with: (c, now) => legacy(c, now, true),
  legacy_acc0: (c, now) => legacy(c, now, false),
  prod: (c, now) => calculateSalience(variantRow.prod(c), now),
  prod_acc0: (c, now) => calculateSalience(variantRow.prod_acc0(c), now),
  prod_noacc: (c, now) => calculateSalience(variantRow.prod_noacc(c), now),
  prod_acc0_drop_future_access: (c, now) => calculateSalience(dropFuture(variantRow.prod_acc0(c), now), now),
};

// rank with the published tie-break (Python sorted((score, id), reverse=True) ⇒ id desc on ties),
// plus the tie range, so a tie never hides inside one ordinal.
function rankAll(ids, score) {
  const s = ids.map((id) => [score(byIdPlus.get(id)), id]);
  s.sort((a, b) => (b[0] - a[0]) || (b[1] - a[1]));
  const pos = new Map(s.map(([, id], k) => [id, k + 1]));
  const out = {};
  for (const id of THREE) {
    const v = s.find((x) => x[1] === id)[0];
    const better = s.filter((x) => x[0] > v + 1e-12).length;
    const equal = s.filter((x) => Math.abs(x[0] - v) <= 1e-12).length;
    out[id] = { rank: pos.get(id), tie_range: [better + 1, better + equal], score: +v.toFixed(6) };
  }
  return out;
}

// production scope pool: brief.ts:359-398 with patterns = [] (scope=global, no since)
function proxy(c) {
  return 0.55 * (c.importance ?? 0.5) + 0.10 * (c.pain ?? 0.2) + ((c.access_count ?? 0) > 0 ? 0.1 : 0);
}
function scopePool(variant, nowMs) {
  const rows = chunks.map(variantRow[variant]);
  rows.sort((a, b) => (proxy(b) - proxy(a)) || ((b.updated_at ?? "") < (a.updated_at ?? "") ? -1 : (b.updated_at ?? "") > (a.updated_at ?? "") ? 1 : 0));
  const cut = rows.slice(0, CANDIDATE_POOL);
  const proxyAt500 = proxy(cut[cut.length - 1]);
  const ranked = cut.map((r) => ({ id: r.id, sf: r.source_file, s: calculateSalience(r, nowMs) })).sort((a, b) => b.s - a.s); // stable, as in JS prod
  const res = {};
  for (const id of THREE) {
    const k = ranked.findIndex((x) => x.id === id);
    const r = rows.find((x) => x.id === id);
    res[id] = k >= 0
      ? { in_pool: true, rank_in_pool: k + 1, salience: +ranked[k].s.toFixed(6) }
      : { in_pool: false, proxy: +proxy(r).toFixed(4), proxy_of_500th: +proxyAt500.toFixed(4),
          proxy_rank: rows.findIndex((x) => x.id === id) + 1 };
  }
  // dedup (brief.ts:420-436) is keyed on title = f(source_file) + one-liner, so items from one file can
  // collapse; items from distinct files survive exact dedup and fall only to near-dup containment.
  const firstOfThree = Math.min(...THREE.map((id) => ranked.findIndex((x) => x.id === id)).filter((k) => k >= 0));
  const minScore = Math.min(...THREE.map((id) => (ranked.find((x) => x.id === id) ?? { s: Infinity }).s));
  const strictlyAbove = ranked.filter((x) => x.s > minScore + 1e-12 && !THREE.includes(x.id));
  return { pool_size: cut.length, proxy_of_500th: +proxyAt500.toFixed(4),
    first_of_three_rank_in_pool: firstOfThree + 1,
    strictly_above_lowest_of_three: strictlyAbove.length,
    distinct_source_files_strictly_above: new Set(strictlyAbove.map((x) => x.sf)).size,
    three: res };
}

const NOWS = [
  "2026-08-29T00:00:00Z", "2026-08-29T12:00:00Z", "2026-08-29T23:59:59Z",
  ...["20", "21", "22", "23", "24", "25", "26"].map((d) => `2026-08-${d}T12:00:00Z`),
];
const rounds = NOWS.map((iso) => {
  const now = Date.parse(iso);
  const A = {};
  for (const [k, f] of Object.entries(scorers)) A[k] = rankAll(servedExisting, (c) => f(c, now));
  const A201 = {}, A144 = {}, A196 = {};
  if (restored.length) for (const [k, f] of Object.entries(scorers)) A201[k] = rankAll(served201, (c) => f(c, now));
  if (PROBE_BRIEFS.size) for (const [k, f] of Object.entries(scorers)) A144[k] = rankAll(organicExisting, (c) => f(c, now));
  if (restored.length && PROBE_BRIEFS.size) for (const [k, f] of Object.entries(scorers)) A196[k] = rankAll(organic196, (c) => f(c, now));
  const B = {};
  for (const v of Object.keys(variantRow)) B[v] = scopePool(v, now);
  return { now: iso, union_149: A, union_201_with_52_restored: A201, organic_144: A144, organic_196_with_52_restored: A196, scope_pool_prod_path: B };
});

// mechanism facts used by finding #3
const three = Object.fromEntries(THREE.map((id) => {
  const c = byId.get(id);
  return [id, { chunk_type: c.chunk_type, retention_days: c.retention_days, last_accessed_at: c.last_accessed_at,
    source_date: c.source_date, access_count: c.access_count, importance: c.importance, pain: c.pain }];
}));
const retNull149 = servedExisting.filter((id) => byId.get(id).retention_days === null).length;
const retNullCorpus = chunks.filter((c) => c.retention_days === null).length;
const impNull149 = servedExisting.filter((id) => byId.get(id).importance === null).length;

const out = {
  script: "measurement/sprint-contrafactual-salience-producao.mjs",
  scoring_function: "serving-salience.ts::calculateSalience (imported; sha256 083399fc... per SERVING-CODE-MANIFEST.md)",
  input_db_sha256: raw.db_sha256,
  window: ["2026-08-20", "2026-08-27"],
  briefs_in_window: briefs.size,
  brief_log_rows: bl.length,
  distinct_served: served.length,
  served_existing: servedExisting.length,
  served_with_52_restored: served201.length,
  organic_existing: organicExisting.length,
  organic_with_52_restored: organic196.length,
  probe_briefs_excluded: PROBE_BRIEFS.size,
  ubiquitous_ids: ubiquitous,
  brief_log_scope_counts: scopes,
  brief_log_agent_counts: agents,
  retention_days_null: { among_149: retNull149, corpus: retNullCorpus, corpus_total: chunks.length },
  importance_null_among_149: impNull149,
  the_three: three,
  rounds,
};
const anchor = rounds[1].union_149;
const ok = THREE.every((id, i) => true) &&
  anchor.legacy_with[116467].rank === 2 && anchor.legacy_with[112241].rank === 3 && anchor.legacy_with[116107].rank === 5 &&
  anchor.legacy_acc0[116467].rank === 131 && anchor.legacy_acc0[112241].rank === 129 && anchor.legacy_acc0[116107].rank === 128;
out.anchor_reproduces_published = ok;
const s = JSON.stringify(out, null, 1);
if (args.out) fs.writeFileSync(args.out, s + "\n");
console.log(s);
if (!ok) { console.error("ANCHOR FAILED: legacy function does not reproduce 2/131, 3/129, 5/128"); process.exit(1); }
