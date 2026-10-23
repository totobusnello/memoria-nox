# The 0.833 was a predicate nobody could re-run, and it was 7 points low

**2026-10-23.** Re-derivation of the S1 citation check. No LLM call: this
re-runs a mechanical predicate over judgements already made, so the judge's
labels are fixed and only the verification moves.

## Why it was reopened

Two things, found a day apart.

First, the second reading of the sample (`2026-10-22-judge-agreement.md`) found
that in **8 of the 9** KG disagreements `sustenta_segundo_juiz` was already
`True` — what rejected those triples was the citation check, on formatting:
pipe tables, `<u>`, an escaped `R\$`, curly quotes.

Second, and worse: **the predicate that produced the published 0.833 was never
committed.** Only the per-row boolean `confere_solto` survives, in
`s1-rows-recheck.json`. A number cited in `DECISIONS.md` rested on code that no
longer exists anywhere — not reproducible, and not inspectable. This file is
the predicate, in the open: `audits/2026-10-23-kg-s1-recheck-conferidor.py`.

## What the old predicate was missing

Dropping a marker leaves the space it occupied. `**"Trading Market"**`
normalises to `" trading market "`, the quote to `"trading market"` — equal
content, unequal string. Two spacing rules close it:

```python
s = re.sub(r'\s+([,.;:!?)\]"])', r"\1", s)   # space left by a dropped marker
s = re.sub(r'(["(\[])\s+',       r"\1", s)
```

Plus `~` (strikethrough), which the old rule did not strip.

That is the whole difference, and it is worth **10 of 150 rows**.

## The numbers, recomputed over all 150

| criterion | | CI95 (Wilson) |
|---|---|---|
| strict (accent + whitespace only) | 0.700 | [0.622, 0.768] |
| **markdown-insensitive, calibrated** | **0.907** | **[0.849, 0.944]** |
| alphanumeric only (all punctuation dropped) | 0.913 | [0.857, 0.949] |
| judge's word, no check at all | 0.913 | — |
| *[published 2026-10-22, not reproducible]* | *0.833* | *[0.766, 0.884]* |

**Faithfulness is 0.907, not 0.833.** The published figure was not the judge
being generous; it was a check that counted markdown as fabrication.

## The check still has power — measured, not assumed

A relaxed check that stops rejecting is not calibrated, it has surrendered. A
negative control against a *random* chunk does not settle that: chunks from
different documents share little vocabulary, so even a hopeless predicate
scores zero. So the control perturbs the quote itself, against **its own**
chunk — a check that accepts a perturbed quote is matching vocabulary, not
citation.

```
quote PERTURBED, tested against its OWN chunk — must be rejected
criterion            1 word swapped    1 digit changed   words shuffled
strict                 0/105 accepted     0/14 accepted   0/102 accepted
markdown calibrated    0/136 accepted     0/25 accepted   0/130 accepted
alphanumeric only      0/137 accepted     0/25 accepted   0/131 accepted

weak control (quote vs a RANDOM chunk): 0/137 false positives, all three
```

The digit column matters most here: the corpus is contracts, and `R$ 50.000`
against `R$ 60.000` is the failure that costs something. All three criteria
reject it.

## Where 0.907 and 0.913 differ: one row

A single quote separates them. The chunk reads `“<u>Trading Market</u>” means
any of…`; the judge copied the term and the sentence but not the typographic
quotes around the defined term. Formatting or imprecision, arguable either way
— and immaterial, since the two readings are 0.907 and 0.913. The reported
number uses the criterion that **keeps linguistic punctuation** and drops only
markup, because a comma the judge added is a paraphrase and a pipe character is
not.

## The finding that transfers

The first pass of the PT-BR gold set asked for a *free-length* verbatim span
and **34.5%** of the spans were not in the source. S1 asked for **eight words**
and the rate is **1 of 137 ≈ 0.7%**.

> Asking for a bounded quote, rather than "the passage that supports this", is
> what keeps an LLM judge from inventing one. The verification predicate then
> has almost nothing to catch — which is a property of the prompt, not evidence
> that the predicate is weak. Measure its power separately, or the two are
> indistinguishable.

## What this does not change

The item 4 verdict stands and for untouched reasons: 39.3% of predicates are
hapax, and **82.2% of the graph's evidence sits in the vault** (14.592 of
17.753 relations, censused 2026-10-22). A graph 0.907 faithful to the wrong
corpus is still the wrong corpus.

---

> **Superseded in part, same day.** The four disputed rows were adjudicated as four *policy*
> questions, and applying all four to the 150 moves faithfulness to **0.900 [0.842, 0.938]** —
> one point BELOW the 0.907 here, because relaxing the check (P4) recovers one row while ruling
> out inversions (P1) and example placeholders (P3) costs two. The reasoning in this file stands;
> the figure does not. See `2026-10-23-kg-s1-quatro-principios.md`.
