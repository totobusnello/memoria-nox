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

// ⚠️ ESTE PREDICADO E UM PISO, nao o valor de abstencao. Calibrado em
// 2026-10-26 contra um juiz delimitado sobre os mesmos 48 itens (entrada
// igualada e provada: reaplicado ao `answer_head` ele reproduz o rotulo em
// 48/48): kappa 0,7938, e a celula "so o detector" VAZIA — ele nunca marca
// abstencao a mais, perde cinco. 0,6957/0,2000 vira 0,7826/0,3200; o GAP, que
// e o que a linha de base afirma, sobrevive (0,4957 -> 0,4626). Duas das cinco
// perdas sao uma flexao de numero: "informação" NAO e substring de
// "informações". Nao ampliar a lista — repete o defeito mais adiante; o conserto
// duravel e a abstencao emitir CANON deterministicamente em vez de pedir ao LLM
// que a escreva. O predicado fica como esta porque e o que produziu o numero
// publicado. Ver audits/2026-10-26-abstention-judge.md.
const CANON = "i have no memory matches for this question";

// `abstainedSubstr` is the predicate that produced the PUBLISHED 0.6957/0.2000.
// It is kept byte-identical so that number stays reproducible; do not extend the
// list — adding inflections repeats the defect one step further out.
const abstainedSubstr = (t) => {
  const s = (t || "").toLowerCase();
  return s.includes(CANON) || s.includes("não tenho") || s.includes("nao tenho")
      || s.includes("não há informação") || s.includes("nao ha informacao");
};

// STRUCTURAL predicate, added 2026-10-27 and measured before being adopted. The
// serving prompt requires EVERY factual claim to carry a [chunk_N] marker, so an
// answer with no citation has nothing anchored in the context. Against the
// bounded judge over the same 48 items:
//
//   five substrings   TP=21 FP=0 FN=5  kappa 0.7938
//   citations === 0   TP=23 FP=0 FN=3  kappa 0.8754   <- strictly better
//   either            TP=23 FP=0 FN=3  kappa 0.8754
//
// Neither over-marks (FP=0 for both), which matters more than recall here: a
// detector that turns a useful answer into a refusal is worse than one that
// misses a refusal. See audits/2026-10-27-abstention-structural-predicate.py.
//
// ⚠️ It does NOT close the gap, and the three it still misses say why: on
// `tier_decay`, `reflect_quota` and Q57 the model cites a chunk AND declares the
// context does not explain the thing — citing the neighbour while refusing. No
// surface predicate over the answer text can separate that, because the answer
// is genuinely both. The durable fix is a structured signal from serving, not a
// better reader of its prose; the design is in
// audits/2026-10-27-abstention-the-durable-fix.md.
const abstainedStructural = (r) => (r?.citations?.length ?? 0) === 0;

const abstained = (txt, r) => abstainedSubstr(txt) || abstainedStructural(r);

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
    abstained: abstained(txt, r),
    abstained_substr: abstainedSubstr(txt),
    abstained_structural: abstainedStructural(r),
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
