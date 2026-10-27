// Scoring of the PT-BR golden set against the real hybrid search (v2, then v3).
//
// Runs the PRODUCTION code path (searchHybrid from dist/), not a reimplementation:
// an ad-hoc reimplementation of BM25 -> KNN -> RRF would be a second implementation
// of the thing under test, and would agree with itself rather than with production.
//
// Isolation, two layers because one is not enough:
//   1. NOX_DB_PATH points at a VACUUM INTO copy, so every write (search_telemetry,
//      reflect_cache) lands in the copy and never in the served database;
//   2. trackAccess=false, so access_count is not bumped even inside the copy —
//      access_count feeds salience, which is part of what is being scored.
//
// Gold ids are resolved on the SAME copy the search runs against; resolving them
// anywhere else would compare ids minted in two different databases.
import { readFileSync, writeFileSync } from "node:fs";

const DIST  = process.env.NOX_DIST  || "/root/.openclaw/workspace/tools/nox-mem/dist";
const GOLD  = process.argv[2];
const RESOLVED = process.argv[3];     // query_id -> [chunk ids] no banco de avaliacao
const OUT   = process.argv[4];
const K     = Number(process.env.GOLD_K_EVAL || 10);

const { searchHybrid } = await import(`${DIST}/search.js`);

const gold = readFileSync(GOLD, "utf8").trim().split("\n").map((l) => JSON.parse(l));
const resolved = JSON.parse(readFileSync(RESOLVED, "utf8"));

const dcg = (rels) => rels.reduce((s, r, i) => s + r / Math.log2(i + 2), 0);

const rows = [];
for (const g of gold) {
  if (g.status !== "accepted" && g.status !== "accepted_marginal") continue;
  // v3 adds one accepted_marginal (Q52), whose gold answers only partly.
  // It is scored but tagged, and the summary reports with and without it:
  // folding a declaredly weak gold into the aggregate silently would make
  // the number depend on a judgement the number does not disclose.
  const marginal = g.status === "accepted_marginal";
  const want = new Set(resolved[String(g.query_id)] || []);
  if (!want.size) { rows.push({ query_id: g.query_id, skipped: "gold nao resolveu no banco de avaliacao" }); continue; }
  const t0 = Date.now();
  let hits = [];
  let err = null;
  try {
    hits = await searchHybrid(g.query, K, false, { surface: "eval", agent: "golden-set-v2" });
  } catch (e) { err = String(e && e.message || e); }
  const ids = hits.map((h) => h.id).filter((x) => x != null);
  const rels = ids.map((id) => (want.has(id) ? 1 : 0));
  const ideal = Array(Math.min(want.size, K)).fill(1);
  rows.push({
    query_id: g.query_id, query: g.query, category: g.category, difficulty: g.difficulty,
    marginal,
    gold_ids: [...want], ranked: ids, hit_ranks: rels.map((r, i) => (r ? i + 1 : 0)).filter(Boolean),
    ndcg: ideal.length ? +(dcg(rels) / dcg(ideal)).toFixed(4) : null,
    recall: want.size ? +(rels.reduce((a, b) => a + b, 0) / Math.min(want.size, K)).toFixed(4) : null,
    mrr: (() => { const i = rels.indexOf(1); return i < 0 ? 0 : +(1 / (i + 1)).toFixed(4); })(),
    latency_ms: Date.now() - t0, error: err,
  });
  const r = rows[rows.length - 1];
  console.log(`Q${String(r.query_id).padEnd(4)} nDCG=${String(r.ndcg).padEnd(6)} recall=${String(r.recall).padEnd(6)} mrr=${String(r.mrr).padEnd(6)} ${r.latency_ms}ms${err ? " ERRO " + err : ""}`);
}

const ok = rows.filter((r) => r.ndcg != null && !r.error);
const mean = (f) => +(ok.reduce((s, r) => s + f(r), 0) / ok.length).toFixed(4);
const strict = ok.filter((r) => !r.marginal);
const summary = {
  n_scored: ok.length, n_strict: strict.length, n_marginal: ok.length - strict.length,
  ndcg_at_10_without_marginal: strict.length
    ? +(strict.reduce((s, r) => s + r.ndcg, 0) / strict.length).toFixed(4) : null, n_skipped: rows.length - ok.length,
  ndcg_at_10: mean((r) => r.ndcg), recall_at_10: mean((r) => r.recall), mrr: mean((r) => r.mrr),
  zero_hit_queries: ok.filter((r) => r.mrr === 0).map((r) => r.query_id),
  median_latency_ms: (() => { const a = ok.map((r) => r.latency_ms).sort((x, y) => x - y); return a[Math.floor(a.length / 2)]; })(),
  by_category: {},
};
for (const r of ok) {
  const c = (summary.by_category[r.category] ||= { n: 0, ndcg: 0 });
  c.n++; c.ndcg += r.ndcg;
}
for (const c of Object.values(summary.by_category)) c.ndcg = +(c.ndcg / c.n).toFixed(4);

writeFileSync(OUT, JSON.stringify({ summary, rows }, null, 1));
console.log("\n=== RESUMO ===");
console.log(JSON.stringify(summary, null, 1));
