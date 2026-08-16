# Intra-panelist stability (test–retest) — spec

> **Status:** declared 2026-08-13T13:47Z, **before the seed existed** and before any draw.
> **Nature:** **exploratory**, not confirmatory. It does not alter the PREREG, does not touch H1–H3, and enters no corrected family.
> **Origin:** an operational accident (§1). The finding came before the design — which is why blinding has to be reconstructed, and §4 says how.

---

## 1. How this came about

On 2026-08-13, two processes adjudicated the same backlog in parallel: the
automatic loop (`extensao-moonshot-loop.sh`, cycle 29, written 12:34Z) and a
manual cycle fired in this session (`cycle-m2`, written ~12:36Z). Both read the
same `extensao-moonshot-ainda-restante.jsonl` before either wrote. No lock
existed.

Result: **40 episodes adjudicated twice by the same panelist** (`moonshot`), with
the same `prompt_sha256` (`5b22f02c…`), in independent runs.

Comparing the 40 pairs: **39 agree, 1 diverges** (`b1ec491db1b16642`: `failure`
in the cycle-29 run, `abstain` in the m2 run).

In other words: an accidental race produced, for free, the only measure of
**intra-rater stability** this project has. It is a dimension the panel's κ
**assumes** and never tested — κ measures agreement *between* panelists on the
premise that each is stable with itself.

## 2. Why the 40 accidental pairs are not enough

Three limitations, all fatal for publishable use:

1. **n = 40** — the binomial confidence interval for 39/40 is roughly
   **[87.7% ; 99.9%]**. Far too wide to support a claim.
2. **Non-random sample** — they are the first 40 episodes in the queue at that
   instant, a contiguous block. It does not represent the corpus.
3. **Blinding lost** — the result was inspected before any design existed. Any
   rule chosen now over *those* 40 is suspect by construction.

They serve as an **indication** that motivates the test. Not as an estimate.

## 3. Design

**Question.** Given the same episode, the same panelist and the same prompt, how
often does the verdict repeat?

**Draw population.** All episodes from the extension backlog with an `ok` verdict
from panelist `moonshot` at draw time, **excluding the 40 from the collision** —
those have already had their result seen, and including them would import the
blinding break into the sample.

**Size.** n = 100. With true agreement around 97%, the Wilson CI is about
±3.3 pp — narrow enough to report, and 100 calls is negligible cost.

**Draw.** Simple random sample without replacement, seeded by the drand beacon
(§4).

**Execution.** Re-adjudicate the 100 drawn with `run_panel.py --only moonshot`,
same `--workers 2`, and **the same `prompt_sha256`** — if the prompt hash
diverges, the test is measuring something else and must be aborted.

**Output.** `extensao-moonshot-stability-<round>.jsonl`, **outside** the
`extensao-moonshot-cycle-*.jsonl` glob — it must not enter backlog accounting nor
become a vote on the panel.

## 4. Seed — declared before it existed

| | |
|---|---|
| Chain | drand mainnet, `8990e7a9aaed2ffe…`, period 30 s |
| Round observed at declaration | **6,373,253** (2026-08-13T13:43:55Z) |
| **Declared target round** | **6,373,493** |
| Occurs at | ≈ 2026-08-13T15:37Z (≈ 1 h 54 after the declaration) |

At the moment of this declaration the target round **had not yet been
generated**, so its `randomness` was unknown to everyone, including the author.
The draw uses `random.Random(int(randomness, 16))` over the population ordered by
`episode_id` — deterministic and reproducible by any third party who downloads
the same round.

This reconstructs the blinding that §1 lost: the sample cannot have been chosen
to produce any particular result.

## 5. Metric and what may be claimed

- **Primary:** proportion of identical pairs, with a 95% Wilson CI.
- **Secondary, descriptive:** transition matrix between verdict categories — it
  matters whether the instability concentrates at the boundary with `abstain` (as
  in the single divergent case observed) or reaches the substantive categories.

**What may not be claimed** from this test: anything about H1–H3; anything about
the other panelists (the test covers only `moonshot`); anything causal.

**Intended use:** a paragraph of methodological limitation/validation. If
stability is high, the panel's κ gains a justified floor. If it is low, that is a
real threat to the design and must be reported as such — **this test can produce
an inconvenient result, and the commitment is to publish it either way**.

## 6. Handling the 40 duplicates in consolidation

Independently of the test, the corpus has 40 episodes with two verdicts from the
same panelist. **This must be resolved before any replay**, or they become a
double `moonshot` vote.

**Rule, chosen because it is independent of content:** keep the
**chronologically earlier** adjudication (cycle-29's, written 12:34Z, over
cycle-m2's, 12:36Z), discarding the later one. The rule does not look at the
verdict, only at write order.

⚠️ **Mandatory declaration:** this rule was written **after** I had seen that 39
of the 40 agree and which pair diverges. The choice is defensible for not
depending on content, but the blinding does not exist and that is recorded here
rather than omitted.

### 6.1 Verified — and measured (2026-08-13T19:2xZ)

The pipeline **does not dedupe**. `pilot_replay.carregar_verdicts()` aggregates
by `episode_id` alone:

```python
por_ep[r["episode_id"]].append(NIVEIS.index(nivel))
...
out[ep] = "failure" if n_falha * 2 > len(v) else "not_failure"
```

Without `panelist` in the key, `moonshot`'s second adjudication enters as an
extra vote. Measurement over the real corpus (`extensao-pass1.jsonl` + all
`extensao-moonshot-cycle-*.jsonl`, τ=S1):

| | |
|---|---|
| Episodes with a repeated panelist (after filtering `abstain`) | **39** |
| Of those, with an **even** panel (4 votes instead of 3) | **39** |
| Consolidated verdicts **changed** | **0** |

**Zero changes** — because the 39 pairs agreed, and the double vote merely
reinforced the same side. The 2–2 tie, which strict majority would silently
resolve to `not_failure`, never occurred.

⚠️ **This is a benign result by accident, not by design.** The odd-panel premise
— "no ties by construction" — was violated in 39 episodes, and only escaped
causing damage because intra-panelist stability was high in those cases. It is
exactly the class of failure recorded in
`[[feedback_by_construction_can_be_voided_by_ops_failure]]`: the structural
guarantee dies through an operational failure, and the harness silently decides
what the spec did not say.

**Correction needed even at zero impact:** dedupe by `(episode_id, panelist)`
keeping the chronologically earlier record. It restores oddness and prevents the
next collision — which may not be benign — from passing unnoticed. **Patch to
`pilot_replay.py` pending approval**: touching the analysis pipeline of a
pre-registered study is not a change to make without an explicit decision, even
when the measured effect is nil.

## 7. RESULT — executed 2026-08-14T09:16–09:27Z

100/100 adjudicated, `prompt_sha256` = `5b22f02c…` (identical to the original
runs), 0 quota pendencies.

```
agree: 99   diverge: 1
stability: 0.9900   Wilson 95% CI: [0.9455 ; 0.9982]

not_failure -> not_failure: 55
failure     -> failure:     44
failure     -> not_failure:  1
```

### 7.1 The magnitude does not threaten κ

At 99% stability (CI floor 94.6%), individual instability is **not the limiting
factor** on the panel's κ of 0.8747 — the ceiling it imposes sits well above
that. So disagreement between panelists is **genuine** (criterion or difficulty),
not model resampling noise. This strengthens the interpretation of κ.

### 7.2 ⚠️ But the average hides where the divergence falls

The single divergent case, `aa6591cf2a05c044`:

| | verdict | level |
|---|---|---|
| moonshot 1st | `failure` | S1 |
| moonshot 2nd | `not_failure` | S0 |
| xai | `failure` | S2 |
| zhipu | `not_failure` | S0 |

**xai and zhipu already disagreed with each other.** moonshot was the tie-breaking
vote — and it is the one that oscillates, **inverting the consolidated outcome**
(2/3 above τ becomes 1/3).

Context: **21 of the 100** sampled episodes had an xai×zhipu disagreement, and
the only divergence fell in that group.

- global instability: **1%**
- conditional on a tie-break: **1/21 ≈ 4.8%**
- conditional on no tie-break: **0/79 = 0%**

Under independence, the chance that the single divergence lands in the 21% group
is 21% — **n=1 proves nothing** (p≈0.21). But the structure is the worst
possible: in the ~21% of the corpus where the other two diverge, moonshot decides
alone, and the global 99% average **dilutes** that edge with the 79% easy cases.
The same class of error recorded in
[[feedback_by_construction_can_be_voided_by_ops_failure]] and
[[feedback_always_check_then_recheck_conclusions]]: a reassuring aggregate
concealing concentration at the edge that decides.

### 7.3 Next test — stratified on the tie-breaks

The test above used a **uniform** sample, and therefore spends almost all its
power where it does not matter. What is missing: a sample **stratified on the
tie-break episodes** (xai×zhipu disagreeing). In the full corpus these should be
~300 (21% of 1,442); replicating 100 *of those* separates 4.8% from 0% with real
power. Cost: 100 calls, same mechanics, **a new drand seed declared before it
exists**.

**Conditional rule, to be pre-declared before running:** if the concentration is
confirmed, an episode whose tie-breaking vote oscillates between runs becomes
**`unknown`** — consistent with the treatment the design already gives to "fewer
than 3 substantive verdicts". Instability becomes absence of evidence, not a coin
flip.

**Do not:** adjust the prompt, temperature or panelist parameters. That would
invalidate the 1,442 verdicts already collected and would mean choosing the
instrument after seeing the result.

## 8. TIE-BREAK CENSUS — executed 2026-08-14T09:33–09:49Z

§7.3 anticipated a stratified sample of ~100 over ~300. **Wrong:** the estimate
of 300 came from *level* disagreement (240 in the corpus, ~17%); the disagreement
that **crosses τ=S1** — the only kind that creates a tie-break over
`failure`/`not_failure` — is **21 episodes in 1,442 (1.46%)**. A population small
enough for a **census**, which eliminates sampling and seed: there is no way to
allege sample selection.

**Design:** the 21 episodes, **5 replicates each** (105 calls, 100% ok, same
`prompt_sha256`), added to the original adjudication = 6 observations per
episode.

```
UNANIMOUS across 6:   11
OSCILLATING:          10   (47.6%)

08dbe564  FNFFNN  3F/3N     14eeb72e  NFNFNN  2F/4N
1a46289e  NFFNFN  3F/3N     dc56238c  NFNFFF  4F/2N
5d9ba5d9  FNNNFF  3F/3N     e15081c2  NFNFFF  4F/2N
480d41a6  FNFFFF  5F/1N     ec03b721  FFNFFN  4F/2N
4f77fa6f  NNNFNN  1F/5N     f962162d  FFFFFN  5F/1N
```

**Confirms the §7.2 hypothesis, and by census rather than inference.** In these
21, `moonshot` is the casting vote by definition (xai and zhipu on opposite sides
of τ), so **in 10 episodes the consolidated outcome changes with the run**. Three
are 3–3: the verdict is literally a coin toss.

| | |
|---|---|
| global instability (§7, uniform sample) | **1%** |
| discordant observations within tie-breaks | **20 of 126 = 15.9%** |
| tie-break episodes that oscillate | **10 of 21 = 47.6%** |

The 99% average was not wrong — it averaged the wrong place. The 98.5% of easy
episodes drowned out the edge where the panel decides.

### 8.1 Weighted impact — the concern was NOT confirmed

The design weights by Horvitz–Thompson: stratum A (`is_error=true`) is a census,
weight 1.0; stratum B, a sample of 800 from 4,163, weight ≈ 5.2. There was reason
to fear amplification: this project has already seen 1.4% of ties × weight 5.2
turn into 20% of influence.

| | |
|---|---|
| oscillating by stratum | A: **3** · B: **7** |
| unweighted fraction | 0.69% |
| **weighted fraction** | **0.79%** |

Amplification of **1.14×**, not 15×: the denominator is also dominated by B, so
the weight largely cancels. **The study's results are not threatened.** A
hypothesis raised, measured, and not sustained — recorded because keeping a
record of what was tested and not confirmed is part of the method.

### 8.2 Proposed rule

**A tie-break episode whose verdict oscillates between runs → `unknown`.**
Consistent with the treatment the design already gives to "fewer than 3
substantive verdicts": instability becomes absence of evidence, not a coin flip.
Cost: **0.8% of the weighted mass**.

**Operational cost, now known:** replicating the tie-breaks 5×. They are ~1.5% of
the corpus — 21 today, plus ~11 once the remaining 737 are adjudicated.

⚠️ **Limits of this evidence, declared:**
- The hypothesis came from a **post-hoc** observation (p=0.02 over n=2). The
  **census** is the evidence; that p-value is motivation, not confirmation.
- "Oscillating" is defined over 6 observations. A 5–1 may be genuinely stable
  with one outlier, and the rule treats it the same as a 3–3. A graded criterion
  (e.g. only 4–2 and 3–3) is defensible and **was not pre-specified** — which is
  why I did not adopt it unilaterally.
- The census covers the **current** corpus. The 737 unadjudicated episodes will
  generate new tie-breaks.

## 9. Provenance

- Collision detected 2026-08-13 ~13:39Z; automatic loop stopped at 13:39:59Z.
- Duplicate counting and verdict comparison: sweep of
  `extensao-moonshot-cycle-*.jsonl` in `~/.paper2-verdicts/`.
- Context: `[[feedback_safety_probe_output_is_paid_work]]`,
  `docs/INCIDENTS.md#2026-08-13`.
