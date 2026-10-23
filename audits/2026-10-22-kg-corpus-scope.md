# Scoping the KG to what search already returned

**2026-10-22.** Follow-up to `2026-10-22-kg-what-search-serves.md`, which found
that the KG answers an engineering question out of the personal/legal vault.
This one asks whether holding the graph to the corpora the search itself
returned closes that door, and at what cost. It does, and the cost is 8 triples
in 201 — but only under one of the three partitions tried, and the obvious one
is not it.

## What was measured

Production's own compiled modules, on the production database, read-only:
`searchHybrid` for the result set and `extractCandidateEntities` / `lookupTopK`
/ `applyBudget` for the triples. Nothing is reimplemented — a second
implementation of the entity match would measure the second implementation.

The same 55 engineering questions as the first probe. For each one: run the
search, take the `source_file` of the top 10 chunks, map each to a corpus, and
ask of every served triple whether its evidence chunk falls in one of them.

`searchHybrid` writes one `search_telemetry` row per call. It ran with
`trackAccess=false`, so the access counters that feed salience were never
touched, and the rows land as `probe:kg-corpus-scope` — the 55 stay separable
from agent traffic in any later reading of that series.

Probe: `audits/2026-10-22-kg-corpus-scope-probe.mjs`.
Aggregates: `audits/out/kg-corpus-scope-2026-10-22.json` (per-query rows stay on
the VPS: they carry vault entity names and this repository is public).

## The partition is the decision

"Scope by corpus" is not one rule. How finely the corpus is cut changes the
answer by a factor of ten, so three partitions were run side by side over the
same search results:

| partition | triples kept | % | queries with ≥1 triple | queries emptied | vault triples served |
|---|---|---|---|---|---|
| first path component | 187 | 93.0 | 41 of 42 | 1 | **11 — cuts nothing** |
| two components | 119 | 59.2 | 28 of 42 | 14 | 3 |
| **vault × workspace** | **193** | **96.0** | **41 of 42** | **1** | **3** |

Baseline: 201 triples served to 42 of the 55 questions, 11 of them out of
`memory/mac-docs/`.

The first partition fails for a structural reason: `memory/mac-docs/` and
`memory/plan-autonomous-agents.md` collapse into the same bucket, so the vault
is never separated from the engineering notes and nothing is cut.

The second — the one the first probe used — works, and costs 82 of 201 triples
and 14 of 42 questions. Not because it separates domains better, but because
every loose file under `memory/` becomes its own corpus: a question whose
triples came from `memory/plan-autonomous-agents.md` is emptied whenever search
returned anything else. That is an accident of file layout being read as a
provenance boundary.

The third cuts exactly as much leakage as the second at a twentieth of the
cost. It is a list of corpus **roots**, not of words: finite, mirroring a
directory split the corpus already has, and extensible by one line.

> The finest partition is not the safest. It removed the same 8 vault triples
> and 74 others for nothing, and the gap would have read as the price of the
> fix rather than as a property of the ruler.

## Why three vault triples survive, and why that is right

In the three questions where a vault triple still comes through, search had
**already returned vault material** in its own top 10. The scope asks for
coherence with the answer being given, not for a ban on a subject. A rule that
dropped those three would be a content policy wearing a provenance argument.

## What the probe found that the design had to answer

- **No served triple lacked an evidence chunk** (0 of 201). The permissive and
  strict policies for missing provenance are therefore indistinguishable on this
  population, and the choice could be made on principle rather than on a number:
  provenance that cannot be checked is not provenance, and the JOIN excludes it.
- **Search returned nothing for 0 of 55 questions**, so "empty scope" is not a
  routine state. It is still handled — an empty scope serves nothing — because
  the alternative reading ("no restriction") is the one that caused this bug.

## What this does not fix

The door itself. `extractCandidateEntities` still matches a bare common word
against `kg_entities.name`, and `confidence = 0.8` in 17.678 of 17.753
relations, so the `ORDER BY confidence DESC` is still a universal tie broken by
`created_at DESC`. The scope bounds the damage of both; it removes neither. A
ranking that discriminates, and a match that requires a distinctive name, remain
open — and neither requires re-extraction.

## Status

Implemented in nox-workspace#71. Production has been at
`NOX_VAULT_FACTS_MODE=shadow` since 2026-10-22, so nothing is served today; this
is the precondition for returning to `active`, not an incident fix.
