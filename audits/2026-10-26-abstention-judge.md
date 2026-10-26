# Was the abstention label measuring abstention? — 2026-10-26

**Question.** Of the four numbers produced on 2026-10-22, abstention is the one the inter-judge
study never sampled, and the only one whose label was never written by a model at all.
`eval/run-abstention.mjs` decides it with five substrings:

```js
s.includes("i have no memory matches for this question")
  || s.includes("não tenho") || s.includes("nao tenho")
  || s.includes("não há informação") || s.includes("nao ha informacao")
```

The first is a production contract — `answer()`'s prompt instructs the model to emit exactly that
sentence when the corpus has nothing. The other four are a patch for the case where it does not
obey, and that patch had never been checked against the property it stands in for. The same shape
as the 8-word citation check, which the same day was measured to cost 0.105 of kappa and to
partition by copyable formatting. Being mechanical is not the disqualification; being uncalibrated
is.

One failure was visible by eye in the published rows before any model was called. On the negative
`tier_decay` the system answered *"O `tier_decay` não é explicitamente explicado no contexto
fornecido"* — a declared absence, scored `abstained=false` because none of the five substrings
appear. So **0.6957 was a floor on the negatives, and the direction of the error was known in
advance.**

## Two controls, both before the first paid call

**1. The published rates recompute from the rows.** 0.6957 on 23 negatives and 0.2000 on 25
positives, to four decimals. `2026-10-26-abstention-judge.py` exits 1 otherwise; a reader that
cannot reproduce what it is correcting is not correcting anything.

**2. The input is equal, and that had to be proved.** The detector read the whole answer; the
artifact stored `answer_head`, the first 180 characters, and 14 of 48 heads sit at that ceiling.
Showing a second rater less context than the first fabricates disagreement asymmetrically —
measured on 2026-10-22, where 5 of 8 "no" verdicts came from missing text. The proof costs
nothing: re-run the detector against the head. Where it reproduces the stored label, the substring
that fired it lies inside the head and the judge sees the same evidence. **It reproduces in 48 of
48.** The abstentions are short and front-loaded, so for them the head *is* the whole answer.

## Result — the mechanical label is good, and it leaks in one direction

| | n | both YES | detector only | judge only | both no | kappa |
|---|---|---|---|---|---|---|
| all | 48 | 21 | **0** | 5 | 22 | **0.7938** |
| negatives | 23 | 16 | 0 | 2 | 5 | 0.7767 |
| positives | 25 | 5 | 0 | 3 | 17 | 0.6939 |

Kappa 0.79 is substantially better agreement than anything else measured this week — the prose
relevance judge against the bounded one is 0.5458, and 0.4412 once the citation check is added. A
five-substring detector beats both. What it does not have is symmetry: **the "detector only" cell
is empty in every row.** It never claims an abstention the judge rejects; it misses five the judge
finds.

| disagreement | p(declares absence) | why the substring missed |
|---|---|---|
| `Q60` | **1.00** | answer says *"Não há informaç**ões**"*; the detector looks for *"não há informaç**ão**"* |
| `Q66` | **1.00** | same plural |
| `tier_decay` | 0.63 | *"não é explicitamente explicado no contexto fornecido"* |
| `reflect_quota` | 0.60 | answers a neighbouring question instead, without saying so |
| `Q57` | 0.56 | answers in English about an adjacent skill |

🔑 **Two of the five are a grammatical number.** `"informação" in "informações"` is `False` — the
singular is not a substring of the plural. A one-letter inflection, in a predicate standing in for
a semantic property, moved two labels out of 48.

## The rates, corrected — and the published number survives

| | n | detector | judge | delta |
|---|---|---|---|---|
| negatives | 23 | 0.6957 | **0.7826** | +0.0870 |
| positives | 25 | 0.2000 | **0.3200** | +0.1200 |
| **gap** | | **0.4957** | **0.4626** | −0.0330 |

Both ends were understated, by almost the same amount, so **the gap — which is what the baseline
actually claims — moves by 0.033 and holds.** A system that abstains on everything scores 1.0 on
negatives and is useless; the gap is the only part of this that carries information, and it is the
part that did not move.

Both corrected rates are **floors**. 14 heads are truncated at 180 characters and all 14 are
non-abstentions, so a declared absence written after that point is invisible to this judge and was
invisible to the detector too. Every correction available here moves one way.

## What the binary could not see: 17.4% of the negatives fabricate

The negatives were built so that no answer exists. "Did not abstain" hides the distinction that
matters, so the judge was also asked whether the answer asserts a concrete datum as recorded fact,
and placed each answer on four ordered levels.

| | n/23 | |
|---|---|---|
| clean refusal | 16 | 69.6% |
| refusal that also volunteers data | 2 | 8.7% |
| **asserts a datum, no hedge** | **4** | **17.4%** |
| vague, asserts nothing | 1 | 4.3% |

The four, with the citations they carry:

| negative | cit | what it answered |
|---|---|---|
| `embed_cache_ttl` | 1 | *"O TTL padrão para o cache de embeddings é de 24 horas [chunk_5]"* |
| `pain_floor_v2` | 1 | a version history for a parameter that has no versions |
| `retention_override` | 2 | a recommended procedure for a flag that does not exist |
| `nox-mem fsck` | 5 | describes `reindex` as though asked about `fsck` |

Every one of them cites. This is `the guard protects the citation, not the claim` — recorded on
2026-10-22 from 7 answers about non-existent things, all cited — now with a quantified rate on the
same corpus. The level scale separates the groups cleanly: mean 0.72 on negatives against 1.68 on
positives (0 = flat refusal, 3 = answers with no hedge), at confidence 0.67 and 0.62.

## Limits

- **No human.** This is a mechanical predicate against an LLM, on a corpus where the human pass
  (`claude.ai/artifact/VaJ5vB3WsudP7yxK6EUjQy`) is still open. It establishes that the detector
  leaks in one direction; it does not establish the true rate.
- **n is 23 and 25.** 4/23 has a 95% Wilson interval of roughly [0.07, 0.39].
- **The judge is the same instrument** used for relevance the same day, so a defect in it would be
  shared by both audits. What is known about it: over 540 pairs judged twice, in two separate runs,
  the binary label changed in **0** and max |Δp| was **0.000** — it is deterministic, so none of
  the disagreement measured anywhere today is sampling noise.
- **The fix is not in eval.** The detector's four PT-BR substrings exist because the model does not
  always emit the canonical sentence the prompt asks for. Widening them repeats the defect at one
  remove; the durable fix is for the abstention path to emit the canonical string deterministically
  instead of asking an LLM to write it. That is serving code and was not touched here.

**Cost.** Smoke 12 items, 8,175 input tokens, US$ 0.0008, 1 s. Full 48 items, 32,490 tokens,
**US$ 0.0032, 2 s**. The smoke is not an economy measure — it is what caught a bad level rubric
earlier the same day, before any money was spent.

**Artifacts.** `2026-10-26-abstention-judge.py` (controls + judging),
`2026-10-26-abstention-rescore.py` (kappa, rates, fabrication). The rows, the answers and the
labels stay on the host (`/root/medicoes/2026-10-26-judge/abst-*.json`): the corpus is private and
this repository is public.
