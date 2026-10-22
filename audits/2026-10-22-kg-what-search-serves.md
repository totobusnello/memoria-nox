# What the knowledge graph actually serves to a question — 2026-10-22

**Question.** The S1 precision audit of the same day found that 74.7% of the graph's evidence comes
from `memory/mac-docs/` — 6-K filings, an SPA, a settlement agreement — a graph of legal documents
rather than of engineering memory. That is a fact about the *store*. The question left open was
whether it is also a fact about what gets *served*: does an agent asking an engineering question
receive contract triples?

**How the KG reaches a prompt.** One path only. `src/lib/spo-injection.ts` → `getVaultFacts()`,
called from `/api/search` (`src/api-server.ts:481`), which appends a `<vault-facts>` block to the
response when `NOX_VAULT_FACTS_MODE=active`. `/api/brief` and `api/answer.ts` serve no KG at all.
Production is `active` with `K=8` (read off `/proc/<pid>/environ` of `nox-mem-api`, and matching
`/root/.openclaw/.env`).

The selection is: lowercase the query, split on whitespace and punctuation, and match each token
≥ 2 chars **exactly** against `kg_entities.name` (case-insensitive, no NER, no fuzzy). Every
relation touching a matched entity is a candidate, ordered by `relation_reason != 'unknown'`, then
`confidence DESC`, then `created_at DESC`.

**Design.** The 55 accepted queries of the PT-BR golden set — real engineering questions — run
through production's **compiled** `dist/lib/spo-injection.js`, so the entity match and the ranking
are the ones that run, not a reimplementation. Each served triple is then traced to its
`evidence_chunk_id` → `chunks.source_file`, matched by `(subject, relation, object)`; an SPO
resolving to several relations is counted as ambiguous rather than attributed to the first row
(there were none). Read-only: the DB is opened `readonly`, and no endpoint is called, because
`/api/search` writes the access counts and telemetry that feed the signals being measured.

## Result: the premise was wrong, and what replaced it is worse

42 of 55 queries are served at least one triple; 201 triples in all, 4.79 per served query.

```
corpus of the 201 served triples
  shared/ (engineering)              115  (57.2%)
  memory/plan-autonomous-agents.md    51  (25.4%)
  mac-docs (vault/legal)              11  ( 5.5%)
  everything else                     24  (11.9%)
ambiguous SPO matches: 0      evidence chunk missing from chunks: 0
```

**5.5%, not 74.7%.** The store's bias does not carry through, because the entrance is a literal
name match and an engineering question names engineering entities. The hypothesis is refuted.

Two things showed up in its place.

### 1. The ranking cannot be relevant, because `confidence` is a constant

`ORDER BY confidence DESC` is a universal tie: **17,678 of 17,753 relations have `confidence =
0.8`** (99.58%; the other two values are 0.6 and 0.7), and `confidence_base` has exactly **one**
distinct value across the whole graph. The tiebreak that actually orders is the next clause,
`created_at DESC`.

So what an agent receives is not the 8 most reliable triples about the subject. It is **the 8 most
recent relations touching a name that appears in the sentence**, with no signal of relevance to the
question. 56.7% of them carry `relation_reason = mentions`, the weakest edge in the vocabulary.
Visible directly in the output:

| question | triple served |
|---|---|
| "qual o trigger de cascade delete em chunks" | `Config v2026.3.31 com chave cascade` — the word matched in an unrelated context |
| "como funciona monkey-patch do Issue 62028" | `OpenClaw has skill coding-agent` |
| "diferença entre tier core warm peripheral" | `working promoted to core` — this one answers |

### 2. 🔴 Common-word entities are an open door from engineering into the vault

The 11 vault triples are not spread thin. They concentrate on queries that happen to contain a
common Portuguese or English word that **is** an entity name. The pure case:

> `qual foi a decisão sobre fallback chain após v.26`

matches the entity `decisão` and is served **6 of 6 triples from the legal corpus**, including
personal names, a Brazilian court ruling and a jurisdiction. Nothing in the question is legal.
`estratégia`, `tipo`, `Backup`, `Busca` and `IA` do the same on other queries.

This is not a long tail. Counting entities whose entire name is a single word of ≤ 12 characters —
the ones reachable from an arbitrary sentence:

```
entities in the graph                                        15,620
  whose name is one short word                                3,169  (20.3%)
  of those, having at least one relation                      1,825
  of those, ≥50% of their evidence in mac-docs                1,273
relations reachable through that set                         11,781  (66.4% of the graph)
```

The highest-degree ones are contract vocabulary, each with its evidence **entirely** in the vault:
`Company` (731 relations), `Sociedade` (639), `Contrato` (529), `Compradora` (389), `Note` (316),
`Holder` (272), `Investor` (219), `Acordo` (186), `Partes` (158). Several are given names of real
people, not quoted here. `Note` is the worst of them: it is ordinary English prose, and it opens
316 relations of private legal material.

So the store's 74.7% does reach the serving surface — not proportionally, but through a narrow,
enumerable set of doors, and it carries exactly the material that should not travel: counterparty
names, settlement terms, people.

## What this changes

- **For ROADMAP item 4**, the predicate vocabulary is not the bottleneck. The ranking has no
  relevance signal at all (constant confidence), and the entity match has no disambiguation.
  Closing an 8,359-value vocabulary would not fix either.
- **The cheapest honest fix is at the entrance, not in the graph**: refuse to match a query token
  against an entity whose name is a single common word, or scope the match to the corpus the asker
  is working in. Both are changes to `extractCandidateEntities`, not re-extraction.
- **`NOX_VAULT_FACTS_MODE=shadow` turns the whole surface off** while the fix is decided, at the
  cost of the 57.2% of triples that are engineering and the small share that answer the question.
  This is a production change and a ranking change (rule 5), so it is the user's call.

**Artifacts.** Probe `audits/2026-10-22-kg-serve-probe.mjs`, aggregates in
`audits/out/kg-what-search-serves-2026-10-22.json`. The full per-triple output stays on the host
(`/root/medicoes/2026-10-22-kg-serve/saida.json`), not in this public repo, because it contains
vault entity names.
