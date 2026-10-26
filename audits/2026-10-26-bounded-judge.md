# A bounded judge over 100% of the top-10 — 2026-10-26

**Question.** The published retrieval claim is an interval, nDCG@10 in **[0.2428, 0.5114]**, and
every relevance label inside it was written by one `gemini-2.5-flash-lite` prompt asking for prose
plus a boolean. Two defects of that shape are measured, not suspected: the prose and the field can
disagree and only the field is read, and 34.5% of the spans it called VERBATIM were not in the
chunk. Inter-judge agreement on the pooled cell was **kappa +0.400 over 20 of the 518 pairs**. So
the upper bound rested on labels one reader in two would redo, estimated from 4% of them.

**What was done.** The same 548 (query, chunk) pairs of the same 55 rankings were re-judged by a
judge that cannot write prose at all — OpenAI's Decisions API (`gpt-6-luna`), which returns a
probability for a predicate and a distribution over ordered levels. There is no free-text field, so
the defect class where the sentence contradicts the field **cannot occur by construction**.

542 of 548 pairs judged (98.9%); the other 6 are chunks deleted from the corpus in the four days
since, and they score 0 rather than being dropped. **12 seconds, US$ 0.0312.** For comparison, the
strict arm had 9.1% of the top-10 judged.

Three disciplines carried over from earlier failures in this repository:

- **Equalised input.** Same ids, same `chunk_text[:6000]` cut, same question wording, word for word,
  as `2026-10-22-gold-pooling.py`. Showing a second rater less context than the first fabricates
  disagreement asymmetrically — measured on 2026-10-22, where 5 of 8 "no" verdicts came from
  missing text, not from disagreement.
- **The gold was judged too.** The 30 pre-registered gold pairs that appear in a top-10 went
  through the *same* judge. Exempting them would have given the bounded arm a privileged class the
  prose arm did not have.
- **The recomputation proves itself before it reports.** `2026-10-26-rescore-bounded.py` reproduces
  **0.2428 / zero_hit 29** and **0.5114 / zero_hit 5** from the published labels and **exits 1** if
  either misses by more than 0.0005. A rescoring that cannot reproduce the published number is a
  broken instrument, and its new figure would be a fact about the bug.

## The corpus had to be shown unchanged first

The evaluation copy (`eval.db`) was deleted; only its `-wal`/`-shm` survive. Re-judging from the
live database risks the ids having moved — a re-ingest mints new ones, which is what cost 0/525 on
the 7b gate. Two controls, both free:

| control | result |
|---|---|
| `source_file` of each id matches what the pooling recorded | **518/518**, zero divergence |
| the old judge's 8-word anchor is still a substring of the chunk | **106/106 = 100%** |

The second is the stronger one: it shows the *text* is the same, not just the filename.

## Result — the upper bound survives the judge swap

| labels | nDCG@10 | MRR | zero-hit | relevant in top-10 |
|---|---|---|---|---|
| strict, pre-registered gold only *(published)* | 0.2428 | 0.2437 | 29 | 30 |
| pooled, prose judge *(published)* | **0.5114** | 0.5412 | 5 | 138 |
| bounded judge, p > 0.3 | 0.4521 | 0.4311 | 14 | 112 |
| **bounded judge, p > 0.5** | **0.4315** | 0.4092 | 17 | 102 |
| bounded judge, p > 0.7 | 0.3995 | 0.3728 | 19 | 88 |

A predicate returns a probability, so the binary cut is a choice and not a measurement; all three
cuts are reported so the reader sees what the number owes to it. **The headline is that nothing
collapses:** a different model family, a different output shape and 10.9× the judged coverage move
the upper bound from 0.5114 to 0.4315, −15.6%. The interval becomes **[0.2428, 0.40–0.51]**. The
pooled figure was not an artefact of the judge.

⚠️ **The three bounded rows are corrected; the first version of this file read 0.5085 / 0.4764 /
0.4406.** Those came from an IDEAL built out of the relevants found inside the ranking, while both
published arms carry the whole pre-registered gold in theirs. An ideal that counts only what the
ranking returned cannot see a relevant document the system failed to retrieve: one relevant item
returned at rank 1 scores 1.0 even where the corpus holds five. So the denominator was looser for
the new arm, in the direction that flatters it, and the −6.8% first reported understated the gap.
Rebuilt over (top-10 ∪ gold) — 609 of 615 pairs labelled, which is what made it possible — the
drop is −15.6%. Applying the same rule to the OLD labels leaves the pooled arm at 0.5114
**exactly**: its construction was already the fair one, and only the new arm needed fixing. MRR is
unchanged because it never depended on the ideal. `2026-10-26-rescore-canonical.py`, which refuses
to print any new number until it has reproduced 0.2428, 0.5114 **and** the superseded 0.4764 —
and on its first execution it did refuse, because the labels for the 30 gold pairs live in a
second file and loading only the first left them scoring zero at 0.3579.

⚠️ The graded arm (gain 0–3, nDCG 0.8384) is **not comparable** to any row above — different gain,
different ideal ranking — and it is close to uninformative as built: the ideal is the same ranking
re-sorted, and almost every chunk scores above zero, so it measures ordering, not relevance. It is
recorded, not published.

## Agreement, now on 100% of the pairs

| | new: yes | new: no | kappa |
|---|---|---|---|
| old `relevante` (= judge AND citation check) | 51 | 55 | **0.4412** |
| old `trecho_responde` (judge alone) | 76 | 79 | **0.5458** |
| old said no (either criterion) | 6 / 31 | 349 / 373 | — |

Three things fall out:

**1. The 20-item sample was right.** kappa +0.400 on 20 pairs → **0.4412** on 510. The earlier
estimate held, which is worth knowing for the next time a sample is all that is affordable.

**2. The citation check costs 0.105 of kappa.** Judge-against-judge agrees at 0.5458; adding the
mechanical check to one side drops it to 0.4412. The check is not adding precision, it is adding
formatting noise — the same conclusion the KG audit reached (8 of 9 disagreements were the check,
not the model), now reproduced on retrieval with n=510.

**3. Stratum B beats stratum A.** The pairs the check *rejected* score **higher** than the ones it
accepted:

| stratum | n | confirmed (p>0.5) | median level |
|---|---|---|---|
| A — published `relevante` | 106 | 51 = 48.1% | 1.88 |
| B — judge said yes, **quote failed to verify** | 49 | 25 = 51.0% | **2.17** |
| C — judge said no | 355 | 6 = **1.7%** | 0.49 |

So `relevante = trecho_responde AND citacao_confere` partitions on *whether an 8-word span happens
to be copyable*, not on relevance. Markdown table pipes, `<u>` wrappers and escaped `R\$` are what
it separates.

**C is the control that makes the rest readable.** 98.3% agreement on the negatives. A judge that
marked everything relevant would score high on A and B and fail here; this one does not.

**And the pre-registered gold is not above question either:** 19 of 30 confirmed (median 0.94,
against 0.31 for pooled A). The two-leg oracle — closed-book `NAO SEI` + triage + a 160-char quote —
produced better labels than one-leg pooling, as it should, but 11 of its 30 do not survive a second
family.

## What this changes

- **The interval stands, with a wider upper end.** Quote **[0.2428, 0.40–0.51]**, not 0.5114.
- **Retire the 8-word citation check as a relevance gate.** It was an improvement on the strict
  check and it is the wrong instrument for this job: it rejects on formatting. Keep a citation check
  where the claim *is* about a quote (the oracle, KG fidelity); drop it from the relevance AND.
- **Do not recalibrate old numbers against the new judge.** Nothing above licenses rewriting
  0.5114; it licenses reporting a second label set beside it.
- **Abstention (0.696 / 0.200) is still unsampled** on this axis and remains the open hole.
- The human pass on `claude.ai/artifact/VaJ5vB3WsudP7yxK6EUjQy` is still the only leg that is not a
  model reading another model.

## Defect found and fixed mid-run

One sqlite3 connection shared across 8 worker threads died with `InterfaceError: bad parameter or
other API misuse` at pair ~300 of 516 — **after passing the 30-pair smoke**, which is how that class
survives. `2026-10-22-gold-pooling.py` has the same shape and got away with it. The fix is not a
per-thread connection: the phases are unrelated, so every chunk text is now read serially up front
and only the network calls fan out.

And the first level rubric was wrong: three levels whose adjacent criteria were not distinct
("contains the answer" restated the predicate). The smoke showed it — predicate 1.0 against level
confidence 0.16 — before any money was spent. Rewritten so each level names an observable property
of the text.

**Artifacts.** `audits/2026-10-26-bounded-judge.py`, `audits/2026-10-26-rescore-bounded.py`.
Labels and rescoring stay on the host (`/root/medicoes/2026-10-26-judge/`): the corpus is private
and this repository is public.
