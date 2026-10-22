// Item 8 baseline: does /api/answer abstain when the corpus has no answer?
//
// Runs the production `answer()` against an ISOLATED copy. Isolation is not
// optional here: retrieveContext calls searchHybrid with trackAccess=TRUE, so
// running this against the served database would bump access_count on every
// chunk it touches — access_count feeds salience, which is part of what the
// abstention gate would later rank on.
//
// Negatives alone cannot answer the question. A system that abstains on
// everything scores 100% on negatives and is useless, so the same run carries
// POSITIVES from the golden set: the number that matters is the gap.
import { readFileSync, writeFileSync } from "node:fs";

const DIST = process.env.NOX_DIST || "/root/.openclaw/workspace/tools/nox-mem/dist";
const NEG  = process.argv[2];
const GOLD = process.argv[3];
const OUT  = process.argv[4];
const NPOS = Number(process.env.N_POS || 25);

const { answer } = await import(`${DIST}/lib/answer/index.js`);

const CANON = "i have no memory matches for this question";
const abstained = (t) => {
  const s = (t || "").toLowerCase();
  return s.includes(CANON) || s.includes("não tenho") || s.includes("nao tenho")
      || s.includes("não há informação") || s.includes("nao ha informacao");
};

const negs = JSON.parse(readFileSync(NEG, "utf8")).filter((c) => c.clean)
  .map((c) => ({ kind: "negative", id: c.token, query: c.query }));
const golds = readFileSync(GOLD, "utf8").trim().split("\n").map((l) => JSON.parse(l))
  .filter((g) => g.status === "accepted").slice(0, NPOS)
  .map((g) => ({ kind: "positive", id: `Q${g.query_id}`, query: g.query }));

const all = [...negs, ...golds];
console.log(`${negs.length} negativas (verificadas) + ${golds.length} positivas = ${all.length}`);

const rows = [];
for (const t of all) {
  const t0 = Date.now();
  let r = null, err = null;
  try { r = await answer({ question: t.query }); }
  catch (e) { err = String(e && e.message || e); }
  const txt = r?.answer ?? "";
  const row = {
    kind: t.kind, id: t.id, query: t.query,
    abstained: abstained(txt),
    retrieval_count: r?.metadata?.retrieval_count ?? 0,
    failed_reason: r?.metadata?.failed_reason ?? null,
    citations: (r?.citations ?? []).length,
    answer_head: txt.slice(0, 180), error: err, latency_ms: Date.now() - t0,
  };
  rows.push(row);
  console.log(`${t.kind === "negative" ? "NEG" : "POS"} ${String(t.id).padEnd(24)} abst=${row.abstained ? "SIM" : "nao"} ret=${row.retrieval_count} cit=${row.citations}${err ? " ERRO " + err : ""}`);
}

const pick = (k) => rows.filter((r) => r.kind === k && !r.error);
const rate = (k) => { const a = pick(k); return a.length ? +(a.filter((r) => r.abstained).length / a.length).toFixed(4) : null; };
const summary = {
  negatives: { n: pick("negative").length, abstention_rate: rate("negative"),
               mean_retrieval: +(pick("negative").reduce((s, r) => s + r.retrieval_count, 0) / Math.max(1, pick("negative").length)).toFixed(2) },
  positives: { n: pick("positive").length, abstention_rate: rate("positive"),
               mean_retrieval: +(pick("positive").reduce((s, r) => s + r.retrieval_count, 0) / Math.max(1, pick("positive").length)).toFixed(2) },
  errors: rows.filter((r) => r.error).length,
};
summary.gap = (summary.negatives.abstention_rate != null && summary.positives.abstention_rate != null)
  ? +(summary.negatives.abstention_rate - summary.positives.abstention_rate).toFixed(4) : null;
writeFileSync(OUT, JSON.stringify({ summary, rows }, null, 1));
console.log("\n=== RESUMO ===\n" + JSON.stringify(summary, null, 1));
