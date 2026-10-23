# Four policy calls, applied to all 150: faithfulness is 0.900

**2026-10-23.** No LLM call. This re-runs mechanical predicates and a reading
over judgements already made, so the first judge's labels are fixed and only
the adjudication moves.

## What was decided

Four rows of the blind sample were still open after the second reading. None
of the four was a disagreement about what the source text says — both readers
read it the same way. Each was a question about what *counts* as "supports",
and the owner settled all four:

| | principle | decided |
|---|---|---|
| **P1** | a triple that **inverts** the relation does not support it, even with a verbatim quote and the two entities side by side | does not support |
| **P2** | a predicate that is **impoverished but not inverted** | supports |
| **P3** | a **placeholder inside a worked example** is not an entity | does not support |
| **P4** | **formatting does not reject**: the citation check drops all punctuation | supports |

A disagreement about a criterion, unlike a disagreement about a fact, is not
contaminated by seeing the other reader's position first. That is why these
four could be handed over as four questions rather than four verdicts.

## Applying them moved the number DOWN

| step | | CI95 (Wilson) |
|---|---|---|
| P4 alone — alphanumeric citation check | 0.913 | [0.857, 0.949] |
| − P1 (inversion) | 0.907 | [0.849, 0.944] |
| **− P3 (placeholder) = verified** | **0.900** (135/150) | **[0.842, 0.938]** |
| + P2 (poor predicate) = substantive ceiling | 0.927 (139/150) | [0.873, 0.959] |
| *2026-10-23, markdown criterion* | *0.907* | *[0.849, 0.944]* |
| *2026-10-22, published* | *0.833* | *[0.766, 0.884]* |

**Reported figure: 0.900.** P4 relaxes the check and recovers one row; P1 and
P3 tighten the claim and cost two. The net of agreeing with all four second-
reader positions is **one point lower** than yesterday's 0.907, not higher.

**Verified** means the triple is supported *and* the judge's quote checks out.
**Substantive** adds the four rows P2 restores — and those four have no quote
at all: the judge that rejected them returned an empty string, so there is
nothing to verify. They are reported as a declared ceiling, never as the
estimate, for a second reason given below.

## How each principle reaches the 150

P4 is mechanical and applies to every row at once.

P1 and P3 are semantic. They are enumerated by marker — an exception marker
(`exceto`, `except`, `unless`, `other than`) in the quote for P1, an example
marker (`Ex:`, `e.g.`, `por exemplo`) for P3 — and the enumeration is then
read. Each filter returned **exactly one** candidate among the 137 rows P4
accepts, and both were the known cases.

P2 cannot be enumerated that way at all. A judge that rejects a row returns an
**empty quote**, and an empty quote leaves nothing for a substring check to
find: the mechanical sweep returns 0 candidates among the 13 excluded rows,
including the one P2 was decided on. So the 13 were read, one by one. Four came
back; the mechanisms that keep the other nine out are listed in the script.

⚠️ **Re-reading only the rejected rows is asymmetric — it can only move the
number up.** That is the same defect, mirrored, that the agreement study found
on 2026-10-22, where showing the second rater less context fabricated
disagreement only in the "unsupported" direction. Here the selection fabricates
agreement only in the "supported" direction. 0.900 excludes this pass entirely;
0.927 is what it buys, and it is a ceiling.

## The filter was checked against a reader, and the sample was spent

Two measurements that the recomputation alone does not give.

**Does the marker filter find what a reader finds?** Of the 137 rows P4
accepts, 19 are in the blind sample. The blind reader rejected 2 of them; the
filter flags exactly those 2, with no false positive. Recall 2/2 on n=19 —
real, and far too small to extend to the 118 rows nobody has read. The
coverage of P1 and P3 over the unsampled remainder is **unknown**, and that is
the largest open term in the 0.900.

**Mutation.** Switching off one principle reopens its disagreement and only
its own: without P1 one row, without P2 one, without P3 one, without P4 one.
No principle is redundant and none subsumes another.

**The blind sample is spent.** The new criterion now agrees with all 20 KG
verdicts. That is not validation — the four principles were decided *from*
those verdicts, so 20/20 measures the criterion against itself. The population
correction that produced 0.913 on 2026-10-22 rested on criterion and reader
being independent, and they no longer are.

> 🔑 Adjudicating the disagreements of an agreement study consumes the study.
> The corrected estimate and the corrected criterion cannot both come out of
> one sample. Correcting again needs rows judged by someone who took no part in
> fixing the criterion.

## What this does not change

ROADMAP item 4 stands on untouched ground: 39.3% of predicates are hapax and
**82.2% of the graph's evidence sits in the vault** (14,592 of 17,753
relations, censused 2026-10-22). A graph 0.900 faithful to the wrong corpus is
still the wrong corpus.

One judge error is worth recording on its own. In `kg-41383` the judge reached
the right verdict ("does not support") on a stated reason that is **false** —
it claimed the object entity is absent from the passage, and the passage names
it. A correct verdict carried by a wrong reason survives any check that reads
only the boolean.

## Artifacts

`audits/2026-10-23-kg-s1-quatro-principios.py`. Per-triple rows, the blind
sample and the verdicts stay on the host (`/root/medicoes/2026-10-22-kg-s1/`):
82.2% of the KG evidence is vault material and this repository is public.
