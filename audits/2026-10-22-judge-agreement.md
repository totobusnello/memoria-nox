# Does the judge agree with a second reader? — 2026-10-22

**Question.** Every number produced today — KG fidelity 0.833, nDCG in [0.24, 0.51], abstention
0.696/0.200 — was labelled by `gemini-2.5-flash-lite`, and that judge's agreement with anyone else
had never been measured. All three carried an error of unknown size and unknown *direction*.

⚠️ **This is inter-judge agreement, not human validation.** The second reader here is Claude Opus 5
(this session), a different model family, not a person. It is a real signal — a more capable model,
reading blind, with no access to the first judge's labels — and it is not the thing the blind
sample was built for. The page at `claude.ai/artifact/VaJ5vB3WsudP7yxK6EUjQy` is still open for the
human pass, and these numbers should be re-read when it lands.

**Design.** 40 items, 10 per `(family × judge label)` cell, stratified by the judge's own label
because the rare class is what fixes precision. Labels hidden, items shuffled. The second reader
wrote a verdict and a one-line reason for each before seeing any of the first judge's labels, and
never opened the key file.

## Two corrections made before the comparison, both of which mattered

**1. The evidence was truncated shorter than the judge saw it.** The sample displayed 2,600
characters; `2026-10-22-kg-s1-precision.py` and `2026-10-22-gold-pooling.py` both send the judge
6,000. 18 of 40 items were cut, and **5 of the second reader's 8 "no" verdicts inside them were
produced by missing text, not by disagreement** — the tail of `kg-28596` carries the definition
listing *the New York Stock Exchange*; the tail of `kg-37703` carries the quoted string verbatim;
the tail of `pool-47` explains what `withOpAudit` does. All five were corrected against the full
6,000 characters, still blind.

🔑 **Showing a second rater less context than the first fabricates disagreement, and it fabricates
it asymmetrically** — only in the direction of "unsupported". An agreement study has to equalise
the input before it equalises the question.

**2. The sample was stratified on the wrong field.** The key was built from `sustenta`, which is
the **strict** criterion (105/150 = 0.700), not the one that produced the published number:
`sustenta_segundo_juiz AND confere_solto` (125/150 = **0.833**). Rebuilt against the published
criterion; the cells are then 14/6 for KG instead of 10/10, which widens the negative cell's
interval. The same 40 verdicts were reused — nothing was re-judged after the key was known.

## Result

| | judge said YES | judge said NO | kappa |
|---|---|---|---|
| KG faithfulness | **13/14 = 0.929** [0.69, 0.99] | **1/6 = 0.167** [0.03, 0.56] | +0.118 |
| pooled relevance | **6/10 = 0.600** [0.31, 0.83] | **8/10 = 0.800** [0.49, 0.94] | +0.400 |

Population correction, `p · P(yes|yes) + (1−p) · P(yes|no)`:

```
KG fidelity       published 0.833  ->  corrected 0.913
pool relevance    published 0.208  ->  corrected 0.283
```

### The citation check, not the model, is what rejects

In **8 of the 9** KG triples the two readers disagreed on, `sustenta_segundo_juiz` was already
**True** — the model agreed. What rejected them was the mechanical citation check, and its
rejections are formatting, not falsehood:

| triple | why the substring failed |
|---|---|
| `Cap 5 — mentions — Vettel Turquia 2010` | the source is a pipe table; the quote drops the `\|` |
| `Optional Redemption Notice Date — defined in — Section 6(a)` | source has `“<u>…</u>”`, quote has plain text |
| `DECLARAÇÃO DE FATURAMENTO — reports — junho/2023` | source escapes it as `R\$`, quote has `R$` |
| `Trading Market — … — New York Stock Exchange` | same `<u>` wrapping |

Each of those is verbatim in the document to a reader's eye. **0.913 — the figure the S1 audit set
aside as "what taking the judge at its word would have reported" — is the one the second reader
reproduces**, and the corrected estimate lands on it exactly. The loose, markdown-insensitive check
was an improvement over strict (0.700) and is still biased downward: **0.833 is a floor, not the
estimate.**

The one triple going the other way is `contrato X — mentions — Y`, which both the model and the
citation check accepted and the second reader rejected: the source reads *`Ex: "o que diz o
contrato X sobre Y?"`* — X and Y are placeholders in an example, read as entities.

### What this does and does not change

- **ROADMAP item 4 is unaffected.** "Do not buy broad LLM extraction yet" rested on two structural
  facts — 39.3% of predicates are hapax, 74.7% of evidence is `mac-docs` — not on the fidelity
  figure. A graph that is 0.91 faithful instead of 0.83 is still a graph of the wrong corpus with
  an unusable predicate vocabulary.
- **The nDCG interval gets worse, not better.** At kappa 0.400 the pooling labels are moderate
  agreement at best, the judge over-marks relevance (6/10 confirmed) and the corrected relevance
  rate is 0.283 against 0.208. [0.24, 0.51] was already an interval rather than a number; this says
  the interval itself rests on labels one reader in two would redo.
- **Abstention (0.696/0.200) was not sampled** and remains unmeasured on this axis.

**Limits.** 6 and 10 per cell. A cell at 13/14 has a 95% Wilson interval of [0.69, 0.99]; the KG
negative cell, at 1/6, spans [0.03, 0.56]. This separates "the judge is roughly right" from "the
judge errs in one direction" — it does not support publishing a corrected figure to three digits.
And the second reader is a model, not a person.

**Artifacts.** Sample builder `audits/2026-10-22-build-judge-sample.py`, scoring
`audits/2026-10-22-judge-agreement.py`. The sample, the key and the verdicts stay on the host
(`/root/medicoes/2026-10-22-kg-s1/`): 74.7% of the KG evidence is `mac-docs` and this repository is
public.

---

> **Superseded in part, 2026-10-23.** The 0.833 reported here came from a predicate that was
> never committed — only the per-row boolean survived. Rebuilt in the open, with the spacing a
> dropped markdown marker leaves, faithfulness is **0.907 [0.849, 0.944]**, and the check's power
> was measured by perturbing the quote against its own chunk (0/136 accepted with a word swapped,
> 0/25 with a digit changed). The reasoning in this file stands; the figure does not. See
> `2026-10-23-kg-s1-conferidor-reproduzivel.md`.
