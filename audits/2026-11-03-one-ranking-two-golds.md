# One ranking, two golds — Kimi's two open gaps on the PT-BR ruler (2026-11-03)

Source of the gaps: `audits/2026-10-27-kimi-challenge-medicoes.md` — (6) per-query effect of corpus
duplication, and the v2 → v3 decomposition (item B: freeze the rankings, swap the gold). Scripts:
`audits/2026-11-03-one-ranking-two-golds.{sh,py}`. Cost: 57 × 2 query embeddings; nothing written to
production (VACUUM INTO copy, `NOX_DB_PATH` at the copy, `trackAccess=false`). Artifacts on the host
under `/root/medicoes/2026-11-03-kimi-gaps/` — `texts.json` holds private corpus text and **stays
there**; the 1.6 GB copy was deleted after the run.

## The decomposition Kimi asked for is no longer possible, and why

The v3 per-query rows were said to *"stay on the host under `/var/tmp/score-v3-161128/out.json`"*
(`audits/2026-10-27-v3-scored-and-my-prediction-refuted.md:78`). **That directory does not exist any
more**; only `/var/tmp/score-v3.sh` survived. The v2 rows exist (`/root/medicoes/2026-10-22-gold/
eval-result.json`) but in chunk ids the re-ingest retired (116xxx; today 227xxx+), and no backup
reaches back to 22/10. So "freeze the v3 rankings" cannot be done. What can be done, and isolates
the same thing, is **one ranking of today's corpus scored under both golds**, each resolved by
anchor on the same copy. A difference is the gold, because the list is literally the same.

## Controls

| control | result |
|---|---|
| recomputed v3 strict nDCG@10 against the harness's own per-row value | **57 / 57** match |
| K=20 top-10 equal to K=10 top-10 (needed for refill after removing copies) | **0 / 57** — hybrid ranking depends on K, so refill is unusable; moot, see (a) |
| duplicate detector on planted pairs | 2 / 2 caught |
| copies EXIST among served chunks (so a zero is not blindness) | **29 of 481** served chunks have ≥1 exact-text twin in the corpus, one of them **126** |

## (a) Duplication per query

**Zero duplicate slots in all 57 top-10s.** The copies exist — 29 of the 481 served chunks have an
exact twin, up to 126 — and the search's dedup layer never serves two of them together. So the
corpus-wide arithmetic (1.9% duplicated ⇒ ~0.19 wasted slots per query) and Kimi's worry that a
cluster of 127 could fill a top-10 are both answered the same way: **in the served list, duplication
costs no slots.**

It costs something else, through a channel neither the corpus rate nor the slot count sees: **the
search can serve a twin of the gold under another id.** Strict scoring credits ids, so that is a
miss. Measured: **1 query** — Q51, strict nDCG 0.0 → **1.0** when a gold-text twin is credited. That
one query moves the aggregate **0.2551 → 0.2727 (+0.0176, +6.9%)**. Kimi's point, that a corpus mean
says nothing about the query-weighted mean, holds exactly — the effect is real and it is one query.

⚠️ Not a ruler change. Whether an identical text from another file is the same evidence is a
judgement the ruler has to make in advance, for every query; it is recorded here as a candidate for a
v4 rule, not applied.

## (b) One ranking, two golds

| | value |
|---|---|
| queries both golds score | 54 (only v2: 1, only v3: 3) |
| strict nDCG@10, **v2 gold** on today's ranking | **0.2587** |
| strict nDCG@10, **v3 gold** on the same ranking | **0.2693** |
| difference — the gold alone | **+0.0106** (+4.1%) |
| queries whose score moves with the gold alone | 16 (9 up, 7 down) |
| queries whose resolved gold is identical in v2 and v3 | 26 |
| today's v3 strict nDCG, all 57 | 0.2551 (27/10 published **0.2567** on that day's corpus) |

The published v2 → v3 move was 0.2428 → 0.2567 (+0.0139) and confounded gold, query set and corpus.
With the ranking held fixed, **the gold change is worth +0.0106 and it is not one-directional** (9
queries up, 7 down): the repair of the 21 wrong-file golds raised some queries and lowered others.
The rest of the published move is corpus and query-set drift between 22/10 and 27/10, which cannot
be measured now for the reason in the first section.

## What this closes and what it leaves

- Kimi (6) closed: duplication wastes **no** served slot; its measurable effect is the twin-id miss,
  **one query, +6.9% of the aggregate**.
- Kimi B closed in the only form still possible: the gold is worth **+0.0106** on a fixed ranking.
- Left open, stated: the corpus/ranking drift share of the 22/10 → 27/10 move — its inputs are gone.
- Lesson recorded: an audit that says per-query rows "stay on the host" in `/var/tmp` is a promise no
  retention policy keeps. Rows that a published number rests on go to `/root/medicoes/`.
