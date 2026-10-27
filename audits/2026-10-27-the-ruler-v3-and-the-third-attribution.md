# Ruler v3: the FILE was wrong, not the span and not the chunk — 2026-10-27

The morning's audit said the bad anchors "landed on a mention of the term". I corrected that to "it
resolved to the wrong chunk of the right file". **Both were too local.** Measurement settled it:

| pass | what it tested | result |
|---|---|---|
| file-level | every chunk of the gold's own `source_file`, judged | **6 of 38** entries repaired |
| corpus-wide | BM25 top-40 over the whole corpus, judged | **21 of the remaining 22** repaired |
| attribution check | is the repaired file one the file-level pass tested? | **0 of 21** — so the FILE was wrong in 21 of 21 |

That check exists because the corpus-wide report printed `was: gold[0].source_file` — the query's
**first** gold entry, not the rejected one it was repairing — and four rows therefore showed an
identical `was:`, which would have been a contradiction. It was my print comparing the wrong field.
Verified against the rejected entry's own `source_file`: **zero contradictions.**

Where the real answers live: `shared` 9 · `memory` 6 · `events` 5 · `docs` 1.

## v3, and what it changes

| | v2 | **v3** |
|---|---|---|
| scorable queries | 55 | **57** |
| gold entries | 95 | 85 |
| unchanged from v2 | — | 58 |
| repaired or added | — | **27** |
| `invalid_gold` | 0 | **1** (Q99) |
| queries with no valid gold | 15 (**27.3%**) | **1 (1.8%)** |

**v2 is untouched** — it is the artifact the published interval was measured on, the same rule that
kept v1 intact. Q99 is the only query for which nothing anywhere in the corpus answers: its recorded
gold is a per-call Groq limit against a question about storage capacity, and 0 of 40 candidates
answer it.

⚠️ **The nDCG is NOT recomputed here.** v3 changes which queries are scorable and repairs 27 gold
entries, so the published 0.2428 / 0.5114 describe v2 and nothing in this audit replaces them. The
new number needs a scoring run against the production path with an isolated database — that is a
separate measurement and no figure for it is asserted.

## Controls, recomputed in each batch rather than inherited

A calibration is a fact about its batch; this repository has measured the same data giving 0.700 /
0.833 / 0.913 under three readings of one verification predicate.

| batch | negative (random chunk) | positive |
|---|---|---|
| gold audit | 1.8% of 55 | 100% of 2 built today |
| file-level repair | **0.0% of 28** | **100% of 12** accepted re-judged |
| corpus-wide repair | 0.0% | 100% of the 6 just repaired |

## 🔴 An anchor cannot separate byte-identical chunks, and the gate was right to say so

The first v3 build produced an anchor for Q71 matching chunks 316535 and 316569 of
`memory/2026-04-05.md`. Lengthening the anchor did not help, and the reason is that the two chunks
share **sha1 `721d225e2539c37e`** — identical, 361 chars each. The file holds **93 chunks with 46
distinct texts: 47 exact duplicates.**

So `ambiguous_duplicate` was added to the resolver as a **third** structural state, for the same
reason as the entity `frontmatter`+`compiled` pair: the system cannot be punished for which of two
indistinguishable chunks it returned, and a gate that demands the impossible stops protecting — the
lesson this resolver was already rewritten for once today.

The selftest now has **three legs**, and the third one is the one that matters, because it proves the
new exemption does not swallow real ambiguity:

| leg | required |
|---|---|
| dead anchor | `unresolved` ≥ 1 |
| wide ambiguity | `ambiguous` (fatal) — fired on 897 hits |
| **exact duplicate** | `ambiguous_duplicate` — fired on 4 hits |

v3 against the extended resolver: 85 entries, **83 resolved**, 1 structural, 1 duplicate, **0 fatal,
exit 0**, selftest PASS.

⚠️ And the exit code had to be read properly to see any of this. The first run was reported through
`python … | tail`, which showed `EXIT=0` from `tail` while the resolver was exiting **1** on the
ambiguity. Same masking as `node --test | grep` earlier today, and the fix is the same: capture the
code, do not pipe past it.

## Duplication: 1.9% of the corpus, concentrated

Since duplicates score identically and arrive adjacent, they could cap nDCG@10 by construction, so it
was measured: **62,446 chunks, 61,241 distinct texts, 1,205 duplicate rows = 1.9%**, in 760 clusters
(largest **127 copies**, median 2, 109 clusters inside a single file).

⇒ **Immaterial on average** (~0.2 of 10 slots) but **concentrated**: `memory/2026-04-05.md` 51%
duplicated, `2026-03-09-relay-fallback.md` 59%, `2026-04-06-2239.md` 54%. A query whose gold lives in
one of those is penalised; the corpus as a whole is not. Stated as a bound, not an estimate — the
real waste needs the actual top-10s.

## Public-repo exposure, measured rather than assumed

The 27 new anchors were scanned against 12 credential and PII pattern classes: **no hits**. Length
median 200, max 200, 22 over v2's 160 cap.

v2 — **already public** — carries 95 anchors of which **21 come from `events/` or `sessions/`**,
median 99 chars and **max 400**. The 27 new ones add 8 of that kind at max 200. ⇒ v3 widens neither
the class of exposure nor the maximum span, which is why it ships where v2 already is.

**Artifacts.** `eval/golden-queries-v3.jsonl`, the extended `eval/resolve-gold-anchors.py`, and
`audits/2026-10-27-v3-*.py` plus `-dup-census.py`. Labels stay on the host.
