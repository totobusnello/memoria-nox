# The v3 interval: [0.2567 · 0.4394], narrower than v2's at both ends — 2026-10-27

v3 judged in full and rescored. **Cost US$ 0.0362** for 620 pairs, 0 errors, 21 seconds.

| | v2 | **v3** |
|---|---|---|
| queries scored | 55 | **57** |
| judged fraction of the top-10 | **9.1%** on the first run | **100.0%** (568/568) |
| nDCG@10 strict | 0.2428 | **0.2567** |
| nDCG@10 pooled | 0.5114 | **0.4394** |
| **honest interval** | [0.2428 · 0.5114] | **[0.2567 · 0.4394]** |
| interval width | 0.269 | **0.183** |
| zero-hit, strict | 52.7% | 56.1% |
| zero-hit, pooled | — | **26.3%** |

**The floor rose and the ceiling fell**, which is the shape a better ruler should produce. The
ceiling fell because the top-10 is now **fully judged**: v2's 0.5114 rested on partial labels, where
an unjudged result could enter the relevant set by pooling convention rather than by a judgement.
Judge everything and fewer results get the benefit of the doubt.

⇒ **The publishable claim is now the interval [0.26 · 0.44], not [0.24 · 0.51].**

## Robustness and what each arm can see

The threshold is an input, not a constant, so all three arms are reported at all three values and the
published figure says which it used — **p > 0.5**, the registered one:

| threshold | strict | pooled | bounded |
|---|---|---|---|
| p > 0.3 | 0.2567 | 0.4482 | 0.6943 |
| **p > 0.5** | **0.2567** | **0.4394** | 0.6984 |
| p > 0.7 | 0.2567 | 0.4243 | 0.6933 |

Pooled moves 0.024 across the whole range, so the number is not an artefact of where the line was
drawn.

⚠️ **`bounded` 0.6984 is not a third estimate of the same thing.** Its ideal counts only relevants
*inside the ranking*, so it cannot see a relevant document the system failed to retrieve: a query
with one relevant item returned at rank 1 scores 1.0 even if the corpus holds five. It measures
**ordering**, and it is printed for continuity with 2026-10-26, never as a headline.

## The control, and why it is the one that matters

The recomputation must reproduce the number it extends. Strict came back **0.2567 against 0.2567**
from `run-gold-eval.mjs` — PASS, and the script exits 1 otherwise, because a rescore that cannot
reproduce its own base is reading different data.

And the judged fraction is printed **before** any metric. The first v2 run published 0.2428 with
**9.1%** of the top-10 ever judged, and on its 29 zero-scoring queries 96.9% was unjudged; a metric
over mostly-unjudged results is not a measurement of the system. At 100% that objection is closed.

## One defect in this script, worth recording

The label file is `{"meta", "rows"}` with the probability in `prob_contem_resposta`. My first version
read `lab["pairs"] if "pairs" in lab else lab` — and the fallback iterated the dict's **keys**, so a
wrong field name surfaced as `'str' object has no attribute 'get'` two frames away from the cause. It
is now an `assert` on the shape plus an `assert` that some probability parsed: **a fallback that
silently accepts the wrong object converts a naming error into a type error, and a type error into a
guess.**

**Artifacts.** `audits/2026-10-27-v3-rescore.py`. Labels and per-query rows stay on the host under
`/var/tmp/score-v3-161128/`.
