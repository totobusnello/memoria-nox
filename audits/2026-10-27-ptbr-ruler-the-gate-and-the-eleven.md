# The PT-BR ruler: the gate was red for a permanent reason, and 9 queries were excluded in the direction that flatters us — 2026-10-27

Two findings, one free. And a number I had been repeating that does not exist.

## 🔴 First, a correction to my own reporting

Every "next steps" list since 2026-10-22 said the ruler had **"43 of 97 gold confirmed"**. **That
number appears in no audit, no artifact and no measurement.** The actual state, read from the files:

| | |
|---|---|
| queries in `golden-queries-v2.jsonl` | 66 — **55 accepted**, 4 `quote_unverified`, 6 `no_source_in_pool`, 1 `negative_unvalidated` |
| gold entries | 95, of which **91 resolve exactly** today |
| negatives | 23 |

43/97 reads as a broken ruler; 55/66 accepted with 91/95 resolving is a healthy one. I used the
invented figure to argue for priority in four separate lists. The ruler was never the state I
described.

## The anchor decision was validated by a real re-ingest

The resolver was run first, because the ruler's own rule is that no evaluation is readable until it
exits clean:

| state | n |
|---|---|
| resolved | 91 |
| moved | 0 |
| **ambiguous** | **4** |
| unresolved | **0** |

Zero unresolved. And the entity-file ids have moved since October (the gold records `chunk_id`
116814 for one anchor; today's chunks there are 227xxx), so a re-ingest **did** happen — and the
v1-style id key would have died on it while the anchor key survived. That is the 2026-10-22 decision
being paid off by an event, not by an argument.

## 🔴 But the gate exited 1, and would have for ever

All four ambiguities are one shape:

| ids | sections |
|---|---|
| 227319 / 227320 | `frontmatter` / `compiled` |
| 227267 / 227268 | `frontmatter` / `compiled` |
| 227611 / 227612 | `frontmatter` / `compiled` |

`ingestEntityFile()` emits exactly one `frontmatter` chunk and one `compiled` chunk per entity file
and their texts overlap **by construction** (CLAUDE.md §6 states the invariant), so an anchor inside
an entity file matches both. **This is not decay and it will never go away.** The resolver treated it
identically to a dead anchor, so the gate was permanently red — and a gate that is always red for a
known structural reason is a gate people learn to step over, at which point it stops protecting
against the thing it exists for.

**Fix: split ambiguity by a behavioural predicate — the `section` column, not the path.**

| state | fatal? | rule |
|---|---|---|
| `unresolved` | **yes** | decay |
| `ambiguous` | **yes** | anything not explained below |
| `ambiguous_structural` | no | exactly two hits in one file, sections exactly `{frontmatter, compiled}`. **All** hits kept as gold |
| `moved` | no | the anchor resolving to a new id is the anchor doing its job |

Keeping both hits rather than choosing one is deliberate: a system that returns either half found the
information, and marking it wrong for which half it returned is the same error as the 8-word citation
check, retired on 2026-10-26 for partitioning on formatting instead of relevance.

**And the loosened gate is proved to still bite.** `--selftest` injects two mutations and requires a
non-zero exit for each:

| mutation | result |
|---|---|
| a dead anchor | `unresolved=1` → **PASS** |
| a non-structural ambiguity (897 hits on one file) | `ambiguous` → **PASS** |

A relaxed guard with no mutation test is indistinguishable from a removed one. Today: **exit 0**, with
4 structural cases named in the output rather than hidden.

## 🔴 Second finding: the 11 unscored queries are excluded in the direction that flatters us

All 11 have `gold = []` — they were never given gold, not quietly dropped. But *why* they have none
splits them, and the split is testable without a model. Asking whether the corpus covers each
query's distinctive token:

| query | token | chunks | |
|---|---|---|---|
| Q72 cross-search between agents | `cross-search` | 11 | covered |
| Q83 how the KG is populated | `kg-build` | 17 | covered |
| Q85 Lex and Cipher in incidents | `Cipher` | 2,762 | covered |
| Q89 rotating the Slack key | `rotacion` | 30 | covered |
| Q49 graphify against nox-mem KG | `graphify` | 24 | covered |
| Q52 running reindex safely | `reindex` | 128 | covered |
| Q79 OpenClaw's current version | `OpenClaw` | 2,278 | covered |
| Q108 when the corpus tripled | `triplic` | 32 | covered |
| Q68 (a negative) | — | — | — |
| **Q93 `kg-reclassify`** | `kg-reclassify` | **0** | **not covered** |
| **Q94 `RELATION_TYPE_TO_REASON`** | `RELATION_TYPE_TO_REASON` | **0** | **not covered** |

**Nine of the eleven ask about topics the corpus holds, and the deep pool (BM25 top-40 ∪ KNN top-40)
brought back nothing the oracle would accept.** Dropping them removes the queries where retrieval
failed hardest — which is the selection-that-drops-where-the-effect-acts defect, running in the
direction that *raises* the score.

What it costs, arithmetically:

| | published (n=55) | the 9 as zero-hit (n=64) |
|---|---|---|
| nDCG@10 strict | 0.2428 | **0.2087** (−14.1%) |
| nDCG@10 pooled | 0.5114 | **0.4395** (−14.1%) |
| zero-hit rate | 29/55 = 52.7% | 38/64 = **59.4%** |

⚠️ **This is a bound, not a correction.** Topic coverage is not answer coverage: 2,762 chunks
containing "Cipher" does not mean one answers *how Lex and Cipher complement each other in
incidents*. So the honest reading of the published interval is that its upper and lower ends are both
**up to 14% optimistic**, and an oracle pass over the 9 — building gold where an answer exists,
promoting to a negative where it does not — is what resolves it. Estimated cost US$ 0.05.

## Delivered: the two uncovered queries become negatives

Q93 and Q94 pass `golden-negatives-v1`'s own criterion, verified three ways with a positive control:

| token | raw | FTS5 phrase | KG entity | stem present |
|---|---|---|---|---|
| `kg-reclassify` | 0 | 0 | 0 | `reclassify` in **10** chunks |
| `RELATION_TYPE_TO_REASON` | 0 | 0 | 0 | `RELATION_TYPE` in **7** chunks |
| *control* `kg-build` | 17 | 19 | — | criterion correctly refuses it |
| *control* `reindex` | 128 | 126 | — | criterion correctly refuses it |

The stems make them the **provoking** kind of negative: a plausible neighbour is present and pulls,
which is the `recusa_com_vizinho` case the abstention judge separates. 17.4% of the existing
negatives fabricate with a citation; these two are built to catch exactly that.

`eval/golden-negatives-v2.jsonl`, 25 entries. **v1 is not touched** — it is the artifact the item-8
abstention baseline (0.7826 / 0.3200) was measured on, and the repaired set sits beside it, the same
rule v1-to-v2 followed for the queries.

## What is still open

1. **The oracle pass over the 9**, which decides whether the −14.1% is real. ~US$ 0.05.
2. **Judge-against-human agreement** on a sample — every label in this ruler still carries that
   unmeasured error. It is the artifact pass only Toto can do.
3. The 4 `quote_unverified` queries, which the same oracle pass would settle.

**Artifacts.** `eval/resolve-gold-anchors.py` (rewritten, with `--selftest`),
`eval/golden-negatives-v2.jsonl`, `audits/2026-10-27-negative-candidates-verify.py`. Everything here
is read-only against the live database; no search path was called, so no telemetry row was written
and no `access_count` was bumped.
