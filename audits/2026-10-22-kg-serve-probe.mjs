// What does the KG actually serve to an engineering question?
// Read-only probe. Uses PRODUCTION's compiled spo-injection module — not a
// reimplementation of the entity match or the ranking — and traces each served
// triple back to the chunk it was extracted from.
//
// Writes nothing: opens the DB readonly, calls no endpoint (the /api/search
// route records telemetry and access counts, which would feed the signals the
// probe measures).

import Database from "/root/.openclaw/workspace/tools/nox-mem/node_modules/better-sqlite3/lib/index.js";
import { readFileSync } from "node:fs";

const SPO = "/root/.openclaw/workspace/tools/nox-mem/dist/lib/spo-injection.js";
const DB = "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db";
const QUERIES = "/root/medicoes/2026-10-22-kg-serve/gold-queries-55.json";

// Mirror production's env exactly (read off /proc/<pid>/environ before running).
process.env.NOX_VAULT_FACTS_MODE = "active";
process.env.NOX_VAULT_FACTS_K = "8";
delete process.env.NOX_VAULT_FACTS_LOG; // keep the probe quiet, it logs nothing to the db anyway

const { extractCandidateEntities, lookupTopK, getK, pickBudget, applyBudget, formatVaultFacts } =
  await import(SPO);

const db = new Database(DB, { readonly: true, fileMustExist: true });

// Evidence of a served triple. Matched by (subject, relation, object) because
// lookupTopK returns names, not row ids; a SPO that resolves to several
// relations is counted as ambiguous and reported separately rather than
// silently attributed to the first row.
const evidenceStmt = db.prepare(`
  SELECT r.id, r.evidence_chunk_id, r.relation_reason, r.extraction_method, r.created_at,
         c.source_file, c.chunk_type
  FROM kg_relations r
  JOIN kg_entities src ON r.source_entity_id = src.id
  JOIN kg_entities tgt ON r.target_entity_id = tgt.id
  LEFT JOIN chunks c ON c.id = r.evidence_chunk_id
  WHERE src.name = ? AND r.relation_type = ? AND tgt.name = ?
`);

function corpusOf(sourceFile) {
  if (!sourceFile) return "NO_EVIDENCE_CHUNK";
  if (sourceFile.startsWith("memory/mac-docs/")) return "mac-docs (vault/legal)";
  if (sourceFile.startsWith("memory/entities/")) return "entities";
  if (sourceFile.startsWith("shared/")) return "shared (engineering)";
  return sourceFile.split("/").slice(0, 2).join("/");
}

const queries = JSON.parse(readFileSync(QUERIES, "utf8"));
const rows = [];
let served = 0, withEntities = 0, ambiguous = 0, orphanEvidence = 0;
const corpusCount = new Map();
const perQuery = [];

for (const { id, q, cat, diff } of queries) {
  const entities = extractCandidateEntities(q, db);
  const triples = entities.length ? lookupTopK(entities, db, getK()) : [];
  const trimmed = applyBudget(triples, pickBudget(q));
  const block = formatVaultFacts(trimmed);
  if (entities.length) withEntities++;
  served += trimmed.length;

  const byCorpus = new Map();
  for (const t of trimmed) {
    const ev = evidenceStmt.all(t.subject, t.relation, t.object);
    if (ev.length > 1) ambiguous++;
    const corpora = new Set(ev.map((e) => corpusOf(e.source_file)));
    const corpus = corpora.size === 1 ? [...corpora][0] : `AMBIGUOUS(${[...corpora].join("|")})`;
    if (ev.length && ev.every((e) => e.evidence_chunk_id && !e.source_file)) orphanEvidence++;
    corpusCount.set(corpus, (corpusCount.get(corpus) || 0) + 1);
    byCorpus.set(corpus, (byCorpus.get(corpus) || 0) + 1);
    rows.push({
      query_id: id, category: cat, difficulty: diff,
      subject: t.subject, relation: t.relation, object: t.object,
      reason: t.reason, confidence: t.confidence,
      corpus, evidence_rows: ev.length,
      source_files: [...new Set(ev.map((e) => e.source_file))].slice(0, 3),
    });
  }
  perQuery.push({
    query_id: id, query: q, entities: entities.length, entity_names: entities.slice(0, 8),
    triples: trimmed.length, corpora: Object.fromEntries(byCorpus),
    block_preview: block ? block.split("\n").slice(1, 4).join(" | ") : null,
  });
}

const total = served || 1;
console.log(JSON.stringify({
  probe: "what the KG serves to an engineering question",
  date: "2026-10-22",
  db: DB, mode: "active (as in production)", k: getK(),
  queries: queries.length,
  queries_matching_any_entity: withEntities,
  queries_served_at_least_one_triple: perQuery.filter((p) => p.triples > 0).length,
  triples_served_total: served,
  triples_per_served_query_mean: +(served / Math.max(1, perQuery.filter((p) => p.triples > 0).length)).toFixed(2),
  ambiguous_spo_matches: ambiguous,
  evidence_chunk_missing_from_chunks: orphanEvidence,
  corpus_of_served_triples: Object.fromEntries(
    [...corpusCount.entries()].sort((a, b) => b[1] - a[1])
      .map(([k, v]) => [k, `${v} (${(100 * v / total).toFixed(1)}%)`])
  ),
  per_query: perQuery,
  triples: rows,
}, null, 2));
db.close();
