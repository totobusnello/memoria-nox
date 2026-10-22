# Item 8 baseline: the anti-hallucination guard protects the citation, not the claim

ROADMAP v6 item 8 (abstention), 2026-10-22. Item 8's gate was "negatives come from item 9", and
item 9 established that an LLM judge cannot supply them. So the negatives here are not judged at
all — they are **constructed and verified mechanically**.

## 1. Negatives that are true by construction

Thirty candidates were written from the corpus's own naming patterns (`nox-mem <subcommand>`,
`nox-*` services, `NOX_*` variables, `kg_*` tables), so the question looks like it belongs — an
implausible negative makes abstention trivial and measures nothing.

A candidate survives only if its distinctive token occurs **zero** times, checked three ways
because each misses what the others catch:

1. raw substring over every `chunk_text`, accent- and case-folded — catches the token inside a
   larger word, which an index would not;
2. FTS5 `MATCH` — catches what the retriever can actually reach, which is what abstention is about;
3. `kg_entities` by name — the graph serves triples beside the chunks.

**23 of 30 survived.** The seven dropped are instructive about the probe rather than the corpus:
`quorum` (177 raw hits, from unrelated documents), `rehydrate` (10), `rebalance` (23 — the vault is
full of portfolio text), `bisect` (2), and three — `nox-ledger`, `nox-sentinel`, `salience v4` —
with **zero raw hits but non-zero FTS**, because the FTS probe ANDs the word components and matches
chunks containing `nox` and `ledger` separately. That is a limitation of the probe, not evidence the
token exists; they were dropped anyway, since a negative that needs an argument is not airtight.

## 2. Negatives alone cannot answer the question

A system that abstains on everything scores 100% on negatives and is useless. So the same run
carries 25 **positives** from the accepted golden set. The number that matters is the gap.

Both ran through the production `answer()` on a `VACUUM INTO` copy with `NOX_DB_PATH`. The copy is
not optional: `retrieveContext` calls `searchHybrid` with **`trackAccess=true`**, so running this
against the served database would bump `access_count` on every chunk it touched — and
`access_count` feeds salience, which is part of what an abstention gate would later rank on.

## 3. Result

| | n | abstention | mean retrieval |
|---|---|---|---|
| **negatives** (no answer exists) | 23 | **0.696** | 8.0 |
| **positives** (answer exists) | 25 | **0.200** | 8.0 |
| gap | | **0.496** | |

**Seven of 23 unanswerable questions got an answer. Five of 25 answerable ones were refused.**

## 4. 🔴 All seven fabrications carry a citation

Every one of the seven non-abstentions attached a real `[chunk_N]` marker to a claim about a subject
that does not exist in the corpus:

| question (subject absent from corpus) | answer |
|---|---|
| `qual o embed_cache_ttl padrão` | "O TTL padrão para o cache de embeddings é de 24 horas **[chunk_5]**" |
| `como o kg_entity_merge decide fundir duas entidades` | "O `kg_entity_merge` atualiza o knowledge graph **[chunk_5]**" |
| `como o nox-mem fsck repara o índice` | answers about `nox-mem reindex`, 5 citations |
| `qual o reflect_quota por agente` | answers about Claude quota consumption, **[chunk_2]** |
| `como aplicar um retention_override por arquivo` | "a recomendação principal é usar `never_decay` … **[chunk_2]**" |

The guard in `prompt.ts` forbids inventing a *marker*, and a retry pass catches markers that are not
in the context. It works: no invented marker appeared. **But the marker was never the thing at
risk.** The model picks a real neighbouring chunk, cites it correctly, and states something about a
subject that chunk never mentions. The citation is valid and the claim is fabricated.

One case states both positions at once: for `tier_decay` the answer opens *"não é explicitamente
explicado no contexto fornecido"* and then answers anyway. Saying it does not know is not the same
as abstaining.

## 5. 🔴 The hard gate is dead code in practice

`answer()` short-circuits when `chunks.length === 0`. Across all 48 runs, `retrieval_count` was
**8 every single time** and the gate fired **zero** times. Hybrid search always returns `topK`:
there is no query for which it returns nothing, so the only abstention actually in service is the
sentence in the system prompt.

This is CLAUDE.md rule 9 in a new place: *a guard whose predicate requires the data that is missing
does not cover the missing data.* Here the predicate is "no results", and the retriever is
structurally incapable of producing no results.

## 6. What item 8 has to build

Not "a sufficiency check" in the abstract — specifically a gate that can fail **while the retrieval
set is full and the citations are valid**, because that is the only failure mode observed. Two
concrete requirements fall out of §4 and §5:

1. **Score the evidence, not the retrieval.** `retrieval_count` carries no information (it is always
   topK) and marker validity carries no information (the retry already enforces it). The gate needs
   a quantity that distinguishes "chunk_5 is about this" from "chunk_5 is nearby" — a floor on the
   similarity of the cited chunk to the *question's subject*, not to the question as a whole.
2. **Measure both directions, always.** The current prompt-only behaviour already costs 20% false
   abstention on answerable questions. Any gate that raises negative abstention from 0.696 while
   pushing positive abstention past 0.20 is not an improvement, and only running both sets shows it.

`eval/golden-negatives-v1.jsonl` carries the 23 with their verification counts and this baseline, so
the next change is measured against a number, not an impression.

**Not done.** The 23 are all "absent subject" negatives; the harder class — real subject, attribute
never recorded — is not built, and it is the class where a similarity floor is most likely to fail.
The positive sample is the first 25 accepted queries, not a random draw. And the abstention detector
is a string match over known refusal phrasings; a refusal worded in some other way would be counted
as an answer.

**Artifacts.** `audits/2026-10-22-build-negatives.py`, `eval/run-abstention.mjs`,
`eval/golden-negatives-v1.jsonl`, data `audits/out/abstention-baseline-2026-10-22.json`.
Evaluation copy deleted after the run; production untouched.
