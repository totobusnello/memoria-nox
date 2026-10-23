// Would scoping the KG match to the search results' own corpora close the leak?
//
// The 2026-10-22 probe showed the KG answers an engineering question with legal
// triples because `extractCandidateEntities` matches a bare common word against
// `kg_entities.name`. This probe measures the proposed fix WITHOUT changing
// production: for each query it runs production's own `searchHybrid`, collects
// the corpora of the chunks that search actually returned, and asks how many of
// the served triples have their evidence in one of those corpora.
//
// Two policies are measured, not assumed:
//   permissive  — a triple with no evidence chunk passes
//   strict      — a triple with no evidence chunk is dropped
//
// Writes: `searchHybrid` records one `search_telemetry` row per query. It is
// called with trackAccess=false, so it never touches the access counters that
// feed salience, and the row lands as `probe:kg-corpus-scope` — the series stays
// readable afterwards. Nothing else is written.

import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { readFileSync } from "node:fs";

const ROOT = "/root/.openclaw/workspace/tools/nox-mem";
const DB = `${ROOT}/nox-mem.db`;
const QUERIES = "/root/medicoes/2026-10-22-kg-serve/gold-queries-55.json";
const TOPN = parseInt(process.env.PROBE_TOPN || "10", 10);

process.env.NOX_DB_PATH = DB;
process.env.NOX_VAULT_FACTS_MODE = "active"; // the probe measures what active WOULD serve
process.env.NOX_VAULT_FACTS_K = "8";
delete process.env.NOX_VAULT_FACTS_LOG;

const { extractCandidateEntities, lookupTopK, getK, pickBudget, applyBudget } =
  await import(`${ROOT}/dist/lib/spo-injection.js`);
const { searchHybrid } = await import(`${ROOT}/dist/search.js`);

const db = new Database(DB, { readonly: true, fileMustExist: true });

const evidenceStmt = db.prepare(`
  SELECT r.id, r.evidence_chunk_id, c.source_file
  FROM kg_relations r
  JOIN kg_entities src ON r.source_entity_id = src.id
  JOIN kg_entities tgt ON r.target_entity_id = tgt.id
  LEFT JOIN chunks c ON c.id = r.evidence_chunk_id
  WHERE src.name = ? AND r.relation_type = ? AND tgt.name = ?
`);

// Three candidate partitions, measured side by side. Which one the fix should
// use is a design decision with a measurable cost, not a matter of taste:
// too fine and every loose file under memory/ becomes its own corpus; too
// coarse and the vault sits in the same bucket as the engineering notes.
const PARTITIONS = {
  // G1 — first path component.
  g1: (f) => f.split("/")[0],
  // G2 — two components. What the 2026-10-22 probe used.
  g2: (f) => {
    if (f.startsWith("memory/mac-docs/")) return "mac-docs (vault/legal)";
    if (f.startsWith("memory/entities/")) return "entities";
    if (f.startsWith("shared/")) return "shared (engineering)";
    return f.split("/").slice(0, 2).join("/");
  },
  // G3 — by domain: the personal/legal vault, and everything else.
  g3: (f) => (f.startsWith("memory/mac-docs/") ? "vault" : "workspace"),
};
function corpusOf(sourceFile, part) {
  if (!sourceFile) return null;
  return PARTITIONS[part](sourceFile);
}
const IS_MAC = (f) => !!f && f.startsWith("memory/mac-docs/");

const queries = JSON.parse(readFileSync(QUERIES, "utf8"));
const PARTS = ["g1", "g2", "g3"];
const tally = Object.fromEntries(PARTS.map((p) => [p, {
  kept: 0, qKept: 0, macKept: 0, droppedWholeQuery: 0,
}]));
let servedBefore = 0, qServedBefore = 0, macBefore = 0, noEvidence = 0, searchEmpty = 0;
const perQuery = [];

for (const { id, q, cat } of queries) {
  // One search per query — the three partitions reuse the same result set, so
  // the comparison is between partitions and not between two search runs.
  const results = await searchHybrid(q, TOPN, false, { surface: "probe", agent: "kg-corpus-scope" });
  const resultFiles = results.map((r) => r.source_file).filter(Boolean);
  if (resultFiles.length === 0) searchEmpty++;

  const entities = extractCandidateEntities(q, db);
  const triples = entities.length ? lookupTopK(entities, db, getK()) : [];
  const trimmed = applyBudget(triples, pickBudget(q));
  servedBefore += trimmed.length;
  if (trimmed.length > 0) qServedBefore++;

  // Evidence files per triple, fetched once.
  const evFiles = trimmed.map((t) =>
    evidenceStmt.all(t.subject, t.relation, t.object).map((e) => e.source_file).filter(Boolean)
  );
  evFiles.forEach((fs) => { if (fs.length === 0) noEvidence++; });
  const macFlag = evFiles.map((fs) => fs.some(IS_MAC));
  macBefore += macFlag.filter(Boolean).length;

  const row = { query_id: id, category: cat, triples_before: trimmed.length,
                mac_docs_before: macFlag.filter(Boolean).length, by_partition: {} };

  for (const part of PARTS) {
    const searchCorpora = new Set(resultFiles.map((f) => corpusOf(f, part)));
    let kept = 0, macKept = 0;
    evFiles.forEach((fs, i) => {
      const known = [...new Set(fs.map((f) => corpusOf(f, part)))];
      if (known.length === 0) return; // no evidence: dropped (measured separately)
      if (known.some((c) => searchCorpora.has(c))) { kept++; if (macFlag[i]) macKept++; }
    });
    tally[part].kept += kept;
    tally[part].macKept += macKept;
    if (kept > 0) tally[part].qKept++;
    if (trimmed.length > 0 && kept === 0) tally[part].droppedWholeQuery++;
    row.by_partition[part] = { kept, mac_kept: macKept, search_corpora: [...searchCorpora].length };
  }
  perQuery.push(row);
}

console.log(JSON.stringify({
  probe: "corpus scoping — what the fix would keep and drop, by partition",
  date: new Date().toISOString().slice(0, 10),
  db: DB,
  top_n_of_search: TOPN,
  queries: queries.length,
  queries_where_search_returned_nothing: searchEmpty,
  triples_with_no_evidence_chunk: noEvidence,
  baseline: {
    triples_served_today: servedBefore,
    queries_with_at_least_one_triple: qServedBefore,
    mac_docs_triples: macBefore,
  },
  by_partition: Object.fromEntries(PARTS.map((p) => [p, {
    triples_kept: tally[p].kept,
    triples_dropped: servedBefore - tally[p].kept,
    pct_kept: +(100 * tally[p].kept / servedBefore).toFixed(1),
    queries_with_at_least_one_triple: tally[p].qKept,
    queries_that_lost_everything: tally[p].droppedWholeQuery,
    mac_docs_triples_kept: tally[p].macKept,
  }])),
  per_query: perQuery,
}, null, 2));
