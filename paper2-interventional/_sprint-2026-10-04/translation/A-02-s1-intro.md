## 1. Introduction

An agent memory system is judged today by retrieval quality: given a set of queries,
how well it ranks what is relevant. This is the question the benchmarks answer and the
one engineering optimizes — better embeddings, reranking, query expansion. It
presupposes, without saying so, that what the agent receives is the top of that
ranking.

The question nobody asks comes before it: **what does the agent actually receive?** It
cannot be answered with a set of queries, because it requires the system in operation —
and it can be answered, because every delivery passes through a small number of
surfaces that can be instrumented. Here there are two: a proactive 10-item brief at the
start of each session, and on-demand search.

**The expected answer would be "it doesn't fit". It does.** In 84.7 days the brief
delivered **583,763 slots** against 67,187 chunks — capacity to serve every chunk
**8.7 times**. It served **1,635 distinct live chunks, 2.43% of the corpus** (1,787 in
the historical count, which includes 152 deleted afterwards — the reason both numbers
exist is in §4.1); under uniform serving the expected coverage would be 99.98%.
Adding search, **83.78% of the corpus was never exposed**. The non-exposure is not
imposed by the number of slots. ⚠️ **The part that the ranking explains is the brief's**
— §4.1.1 delimits what can be attributed to each surface. The claim about mechanism is
about the brief, and the aggregate number measures what did not arrive, not what the
ranker refused.

⚠️ This is not an accusation against the policy. A 10-item surface **must**
concentrate — serving memory at random would be worse than not serving it. What the
number changes is the nature of the problem: as long as the surface is believed to be
too small, non-exposure is a fact of life; once it is measured to be 8.7× larger than
the corpus, non-exposure becomes a **policy choice**, and a choice can be examined.

We examined it, and the concentration has an address. The 8 slots of the main pool
converge: 3 chunks appear in **100%** of briefs, and the top-10 takes **47.16%** of a
week's slots. The remaining 2 slots are a **coverage** channel, which exists precisely
to serve the never-served — and it is the one that fails, for two reasons that have
nothing to do with relevance:

1. **calendar.** The channel cuts by age, and ingestion arrives in **batches**. Between
   batches the pool is empty and the channel serves the same set for days: we measured
   **five consecutive days** with zero new items, with the minimum age of what was
   served rising by exactly **+1.00 per day** — the signature of a frozen set. The
   window is **not unique**: there are two sub-pools, the per-agent one with 7 days and
   the global one with 30 (§4.3.1), and the five-day observation belongs to the first.
   Applying one's window to the other's batch is an error we made and that a registered
   prediction refuted (H-2);
2. **algebra.** The channel orders by a **lexicographic** comparator
   `(last_served ASC, salience DESC)`, in which the score is the **subordinate**
   coordinate and decides only within ties of the dominant one. This predicts —
   deductively, from seven lines of code — a **ceiling** for any additive bonus on the
   score of that channel.

The prediction is testable and we tested it, with increasing dose in **counterfactual
replay** over 350 of 350 real brief states, faithful to the serving pipeline — ⚠️
production states, intervention **not served** (*shadow* mode, §7): monotonic in each
state, saturating at `w ∈ (4,0; 4,4]`, with a ceiling of **4.86%** of briefs. It
survived the test that could have killed it — and an earlier instrument that
**confirmed it for the wrong reason** (§5.6).

⚠️ **Scope, stated before the results and not after.** It is **one** system. We did
not measure the effect on the agent's behavior — there is no downstream outcome
instrumented (§5.4). We do not claim that the field optimizes the wrong coordinate: we
claim that there is a coordinate the benchmarks do not measure, we give the instrument
to measure it, and we leave the question open. And, of the two surfaces, only the brief
is decided by the system; the other is initiated by the agent and accounts for most of
the exposure (§4.1.1).

- **The gap.** The field's canonical survey (TMLR 2602.06052v4, 218 papers) maps agent
  memory architectures and benchmarks. Benchmarks measure nDCG/recall over sets of
  queries. None measures the **delivery surface**: how many distinct items an agent in
  production actually sees, and which ones.

  And the vocabulary of experimental methodology **is not there**. Recomputed over the
  v4 PDF (`measurement/survey-string-count.py`, sha256 `497e9549…b46a6`, 429,387
  characters, 63 end-of-line hyphenations stitched together before counting):

  | term | body | bibliography |
  |---|---|---|
  | `pre-registration` / `preregistration` (and the 6 other spellings) | **0** | **0** |
  | `randomized` / `randomised` | **0** | **0** |
  | `ablation` / `ablations` | **0** | **0** |
  | `interventional` | 1 | 0 |
  | `counterfactual` | 1 | 0 |

  It is not the absence of one word: it is the absence of the **whole family**. A
  survey of 218 papers that says `memory` 1,169 times and `randomized` never is not
  omitting a term — it is describing a field whose instrument is the offline benchmark,
  not the experiment. The two occurrences that exist are singular, and one of them,
  that of `counterfactual`, appears as a suggested future direction.

  ⚠️ **Zero is the result that a broken extraction produces for free**, so the count
  runs with a positive control (`memory`, `agent`, `benchmark`, `evaluation` above
  floors) and aborts if it fails. The control did fire once, on `ablation=0`: it was
  the **floor** that was wrong — a survey catalogs, it does not ablate — and the direct
  check (`memory`=1,208, `benchmark`=126 in the same text) showed the extraction was
  intact. The term left the control and became data.
- **Why the question matters.** ~~If the surface has fixed, small capacity, then
  improving ranking does not improve exposure, and the field optimizes the wrong
  coordinate.~~ **That was the hypothesis this work started with, and the measurement
  contradicts it:** the surface is not small — it is 8.7× the corpus. What matters is
  what remains after that: a surface with slack delivers 2.43%, and the channel that
  would exist to compensate for it is governed by two path patterns that see 0.16% of
  the corpus, and by a lexicographic order in which the score does not decide. Whether
  other systems have this shape is an open question — not a claim of this paper — and
  the published diagnostic exists so that it can be answered.
- **Contributions.** (i) the measurement of the exposure surface of an agent memory
  system **in production**, with the result that capacity exceeds the corpus by 8.7×
  and yet 83.78% is never exposed — ⚠️ a number that sums the **two** surfaces, whereas
  the capacity cited is only the brief's, and §4.1.1 delimits what each one authorizes
  concluding; (ii) the localization of the bottleneck in the **coverage channel**, with
  the two mechanisms that freeze it — an eligible population of **108 chunks (0.16% of
  the corpus)**, cut by path patterns, and a lexicographic order that demotes the score
  to a subordinate coordinate; (iii) a **deductive** ceiling prediction for additive
  bonuses in that channel, tested with dose-response and faithful replay; (iv) the
  **executable diagnostic** (`measurement/`), so that the measurement is reproducible
  on another system.

  ⚠️ **The catalog of instrument defects (Appendix E) does not count as a
  contribution**, and the reason is an honest one: they are **17 defects that we
  committed**, eight of them altering a number that this paper reports. Reporting them
  is an obligation, not a merit — and above all, eight findings **do not bound** the
  non-findings. They are in the appendix because whoever reproduces the measurement
  will fall into the same ones, not because they credential us.

