# The gap is extraction, not the window — arm C, 2026-10-27

**The question.** The net value of memory measured this morning is **−21.2 pp** against BM25 over the
raw transcript at equal context cost, and `session-distill.ts:141-144` was shown to hide 76% of the
prose in the large sessions behind a see-once rule. Two causes were still indistinguishable, and
publishing before separating them would have sold an implementation defect as a property of the
field:

- **extraction** — the prompt and its 10-item ceiling lose the fact even when shown the text. Then
  the finding is the field's.
- **the window** — the builder was never shown the text. Then the finding is ours, the fix is a few
  lines, and the paper is a before/after.

**Arm C answers it.** The same 20 sessions were re-distilled from their **complete** prose with the
builder's own `DISTILL_SYSTEM`, blocking algorithm, model (`gemini-2.5-flash-lite`), temperature and
`importance >= 0.5` filter, and the result was handed to the same 99 questions and the same judge.

563 blocks distilled, 0 failures. **872 real units → 2,141 from the whole prose = 2.46×**; on
`9c75f331`, 19 → 480.

## Result — seeing the whole session recovers 8.7% of the gap

| arm | correct | silent | contradicts |
|---|---|---|---|
| A — oracle window on raw *(control)* | 88.9% | 0.0% | 17.2% |
| **B — memory as actually built** | **42.4%** | 49.5% | 7.1% |
| C_iso — whole-session memory, B's budget | 44.4% | 46.5% | 13.1% |
| **C_all — whole-session memory, all 2.41× of it** | **46.5%** | 39.4% | 17.2% |
| bm25_iso — naive RAG, B's budget | **63.6%** | 24.2% | 15.2% |
| dense_iso — naive RAG, B's budget | 64.6% | 18.2% | 20.2% |

🔑 **Fixing see-once recovers +4.0 pp of a 46.5 pp gap — 8.7%.** The residual tax against the oracle
is **47.7%**, and the net value against BM25 stays at **−17.2 pp**. The window is real, costs
something, and is not the explanation.

⚠️ So the morning's reading was wrong in its emphasis, and in the direction that flattered us: the
see-once rule looked like the mechanism because the net value tracks session size, and it does — but
the size-dependence is mostly something else. **The defect is the extraction criterion.**

## Where the whole session does and does not help

| category | n | A | B | **C_all** | bm25_iso |
|---|---|---|---|---|---|
| `lesson` | 28 | 92.9% | 60.7% | **75.0%** | 67.9% |
| `decision` | 29 | 82.8% | 48.3% | **48.3%** | 55.2% |
| **`context`** | 42 | 90.5% | 26.2% | **26.2%** | 66.7% |

🔑 **Showing the builder the whole conversation improves the lesson and does nothing at all for the
project detail.** `context` is 26.2% either way — not one point. `decision` likewise. Only `lesson`
moves, by +14.3 pp.

That settles which cause owns `context`: the builder is not missing the file name because it never
read the turn. It reads the turn and does not keep the name. `DISTILL_SYSTEM` asks for *"contexto de
projetos relevantes (nomes, status, detalhes)"* and the model returns the insight, not the path —
and `lesson` is the category whose shape the prompt's own examples teach.

| final prose | n | A | B | C_all | bm25_iso |
|---|---|---|---|---|---|
| < 50k | 52 | 90.4% | 53.8% | 51.9% | 63.5% |
| 50–200k | 7 | 71.4% | 42.9% | 28.6% | 71.4% |
| **200k–1M** | 40 | 90.0% | **27.5%** | **42.5%** | 62.5% |

In the band where see-once bites, C_all gains **+15.0 pp** — the window does cost real memory there.
It still ends 20 pp under naive RAG over the same text. Below 50k, where the builder already saw
everything, C_all is 1.9 pp *under* B, which is the no-dedup noise discussed below.

## Controls

| control | result |
|---|---|
| **fidelity** — re-distilling the VISIBLE prefix must reproduce the real arm B | median ratio **1.17**, min 0.58, max 1.75 over 20 sessions. Mine runs ~17% high, in the declared direction |
| **budget** of C_iso against arm B's characters | aggregate **0.971**, 0 pairs over budget |
| C_all's context against B's | **2.41×** — stated, not hidden: C_all is the system as it *would be*, and arm B likewise received all of its own units |
| judge | not re-run on A and B; shown deterministic on this corpus (540 pairs, 0 label changes) |
| distillation failures | **0 of 563** blocks |

**Not reproduced, and each favours C** — so the conclusion survives them: the embedding dedup
(`isDuplicate`) needs the live database, so C keeps near-duplicates; the learned noise prototypes are
skipped because `isNoise` writes to `noise_prototypes` (justified: the 240 prototypes hold **4 hits**
in total); the 1 call/sec rate limit is dropped.

The 1.17 fidelity ratio and the missing dedup are the likely reason C_all sits 1.9 pp below B in the
`<50k` band, where the two should be identical by construction — ~17% more near-duplicate units in a
small context dilutes rather than adds. It bounds how finely C can be read: **a difference of a
couple of points is inside this instrument's noise, and the +4.0 pp headline is near that edge.**
The +15.0 pp in the 200k–1M band is not.

## What this changes

- **The net-value finding is the field's, not an implementation defect of ours.** It survives giving
  the builder the complete conversation: −17.2 pp against BM25 instead of −21.2 pp.
- **Fix see-once for the product, not for the number.** It recovers 15 pp on the large sessions,
  which is worth having, and 8.7% of the gap, which is not a paper.
- **The lever on `context` is the prompt, not the window.** The next thing worth measuring is a
  `DISTILL_SYSTEM` that is required to carry identifiers verbatim — the only arm so far that has not
  been tried, and the one every number here points at.
- **Do not claim damage, third day.** C_all contradicts at exactly **17.2%**, the arm-A false-positive
  floor. More memory produced no more detectable damage.

**Cost.** Distillation US$ 0.2152 (1,395,339 in / 189,059 out tokens), answers US$ 0.1082, judging
US$ 0.0158, all from the providers' own token counts; smokes ~US$ 0.01. **US$ 0.35.**

**Artifacts.** `audits/2026-10-27-arm-c-whole-session-{build,answer}.py`. Units, answers and judge
keys stay on the host (`/root/medicoes/2026-10-26-memory-tax/`): the corpus is private and this
repository is public.
