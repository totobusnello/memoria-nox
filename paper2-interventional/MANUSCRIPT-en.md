# Spare capacity, narrow surface: what a production agent-memory system actually surfaces

> 🌐 **English edition, started 2026-09-01.** The Portuguese `MANUSCRIPT.md` is the
> source of record and the one the 22 guards in `claims_check.py` verify. This file is
> translated section by section; anything not yet here is not yet translated, and the
> Portuguese remains authoritative until it is.
>
> **Translation rule:** every figure keeps the value it has in the source. Decimal
> separators switch to the English convention (`2.66%`, not `2,66%`) and thousands
> separators to commas (`583,763`, not `583.763`) — the *numbers* are identical, only
> the notation changes. Section references (`§4.1.1`) and artefact names are left
> untouched, because they are identifiers, not prose.
>
> ⚠️ The 22 guards currently read the Portuguese file. Do not cite this file as a source
> for a number; cite `MANUSCRIPT.md`.
>
> What *does* guard this file is `measurement/paridade-de-traducao.py`, which normalises
> both notations to a plain value and compares the **multisets** — comparing sets would
> hide a lost repetition. Current state, `out/PARIDADE-TRADUCAO-2026-09-01.json`: **93
> figures on each side, exact parity**. The risk it exists to catch is not mistranslated
> prose but half-converted notation: `583,763` written as `583.763` reads as five hundred
> and eighty-three, and no human review catches that.

> 🔴 **The title changed on 2026-08-29, and the reason comes from the paper itself.** It
> was *"Spare capacity, **starved coverage**"*, and adversarial review found two faults
> in the metaphor. First: the coverage channel does **not** starve — it exhausts its
> eligible pool 100% every day (§4.3.1); what starves is the corpus, not the coverage,
> so the image inverted the mechanism the body describes. Second: *starved* is
> normative, and §4.5 explicitly declines that judgement — "a reader who concludes 'the
> system is losing valuable information' has gone beyond what was measured". A subtitle
> cannot sell the conclusion the body refuses.

---

## Abstract

Agent-memory systems are evaluated by retrieval quality over query sets. Across the 218
papers in the field's canonical survey, none measures what the agent **actually
receives** in production — and retrieval is conditional on a query having been issued,
so an item no query reaches has an undefined nDCG, not a low one. For 12 weeks we
instrumented the two surfaces through which a memory system in operation delivers
content to a fleet of 6 agents: a proactive 10-item brief and on-demand search.

The brief delivered **583,763 slots** — **8.7 times** the size of the corpus, enough to
serve each of the 67,187 chunks eight times over. It delivered **1,787 distinct chunks:
2.66%**. **Aggregate** capacity therefore did not force that outcome: there was room to
show the entire corpus eight times. It does not follow that the ordering is wrong — only
that a shortage of room is not what produced the number. **Per-session** capacity (10
items) is not tested here. (The 99.98% coverage under uniform service appears as an
arithmetic bound on what capacity would allow, not as a recommended policy.) Adding
search, **83.78% of the corpus was never exposed by either surface**. The change of
universe between those two sentences is deliberate and must be read: the spare capacity
above is **the brief's**, whereas the 83.78% counts the **union**. And the exposure that
does exist is mostly **agent-initiated rather than system-delivered** — 9,755 of the
10,899 exposed chunks came from search. The surface the system decides, the brief,
exposed 1,787. Every claim in this paper about *mechanism* concerns the brief; the
83.78% describes the state, not the culprit.

**The surface's two channels freeze, for opposite reasons and neither tied to
capacity.** The 8 slots of the main pool are ordered by a score whose terms, with one
exception, **do not decay** — the access component is monotone in a counter that only
rises. The 3 chunks present in **100%** of the week's 4,632 briefs were last accessed 90,
30 and 42 days ago: **the brief's first three positions** are determined by search
traffic from months back, and the top-10 takes **47.16%** of the slots. The other 2 slots
are a *coverage* channel whose declared purpose is to serve the never-served — and it
**freezes** for a different reason: its eligible population is **108 chunks out of a
corpus of 67,187** — 0.16%, carved out by two path patterns — and it exhausts that
population **entirely, every day**, at 12.4 slots per candidate. There is never any
never-served left to serve. The channel that would respond to a score adjustment is the
one nobody adjusts; the one designed to compensate for it is the one that does not
respond to score.

The coverage channel's mechanism is **deducible from the code**. It orders by a
**lexicographic** comparator `(last_served ASC, salience DESC)`: the score is the
**subordinate** coordinate and only decides within ties on the dominant one — which
predicts a **ceiling**, not a proportional response, for any additive bonus to the score
**in that channel**. We tested this with increasing dose via **counterfactual replay**
over **350 of 350** real brief states, faithful to the serving pipeline — ⚠️ **the states
are from production; the intervention was not served.** The mode is *shadow*: the treated
composition is computed and logged, and what the agent received was always the control
(§7). Result: a monotone response in every state, saturation at `w ∈ (4.0, 4.4]`, a
ceiling of **4.86%** of briefs. And the ceiling is not a constant of the mechanism, along
two axes we measured: under the same rule with a different draw of designated chunks it
reaches **7.43%** (the draw in force sits at the minimum of the distribution, tied with
one other), and truncating the timestamp resolution from seconds to minutes or hours
takes it to **36%** and **80%** — without changing a line of code. **The mechanism's reach
is fixed by decisions nobody made as policy.** 🔴 **A third axis exists and was not
measured**, and the audit of 30/08 found it in an artefact we had written and never read:
excluding the rows of our own health probes moves the replay anchor, and the ceiling was
computed **without** excluding them (§5.7.2).

⚠️ **What we do not claim.** No effect on agent behaviour: there is no instrumented
downstream outcome (§5.4). Nor that the concentration is *wrong* — a policy that serves
10 items per session **must** concentrate, and serving uniformly would be useless; the
finding is that non-exposure is **a result of policy and not a limit of capacity**, and
is therefore revisable by design decision. And we claim nothing about the field: this is
**one** system, and the mechanism's generalisation is deductive, holding for any ranker
with a lexicographic order and a bonus on the subordinate coordinate. How many systems
have that shape is an open question, and the executable diagnostic we publish exists so
that others can answer it one at a time.

⚠️ Two caveats for the reader: of the 10,899 exposed chunks, **9,755 came from search,
which is agent-initiated** — only the brief is delivery decided by the system, and it is
the brief the mechanism claims are about. And collection size, which correlates with
exposure (§4.2), may be a **proxy for how the type is produced**: curation is not ruled
out as a common cause.

## 1. Introduction

An agent-memory system is judged, today, by retrieval quality: given a set of queries,
how well does it rank what is relevant. That is the question benchmarks answer and the
one engineering optimises — better embeddings, reranking, query expansion. It presumes,
without saying so, that what the agent receives is the top of that ranking.

The question nobody asks comes before it: **what does the agent actually receive?** It
cannot be answered with a query set, because it requires the system in operation — and it
*can* be answered, because every delivery passes through a small number of surfaces that
can be instrumented. Here there are two: a proactive 10-item brief at the start of each
session, and on-demand search.

**The expected answer would be "it doesn't fit". It isn't.** Over 84.7 days the brief
delivered **583,763 slots** to 67,187 chunks — capacity to serve each chunk **8.7 times**.
It served **1,787 distinct, 2.66% of the corpus**; under uniform service the expected
coverage would be 99.98%. Adding search, **83.78% of the corpus was never exposed**.
Non-exposure is not imposed by the number of slots. ⚠️ **The part the ordering explains
is the brief's** — §4.1.1 delimits what can be attributed to each surface. The mechanism
claim is about the brief, and the aggregate number measures what did not arrive, not what
the ranker refused.

⚠️ This is not an accusation against the policy. A 10-item surface **must** concentrate —
serving memory at random would be worse than not serving it. What the number changes is
the nature of the problem: as long as one believes the surface is too small,
non-exposure is a fact of life; once measured to be 8.7× the corpus, non-exposure becomes
a **policy choice**, and choices get examined.

We examined it, and the concentration has an address. The 8 slots of the main pool
converge: 3 chunks appear in **100%** of briefs, and the top-10 takes **47.16%** of a
week's slots. The remaining 2 slots are a **coverage** channel, which exists precisely to
serve the never-served — and it is the one that fails, for two reasons that have nothing
to do with relevance:

1. **calendar.** The channel carves by age, and ingestion arrives in **batches**. Between
   batches the pool sits empty and the channel serves the same set for days: we measured
   **five consecutive days** with zero new items, with the minimum age of what was served
   rising by exactly **+1.00 per day** — the signature of a frozen set. The window is
   **not unique**: there are two sub-pools, the per-agent one at 7 days and the global one
   at 30 (§4.3.1), and the five-day observation belongs to the first. Applying one's
   window to the other's batch is a mistake we made and that a registered prediction
   refuted (H-2);
2. **algebra.** The channel orders by a **lexicographic** comparator
   `(last_served ASC, salience DESC)`, in which the score is the **subordinate**
   coordinate and only decides within ties on the dominant one. This predicts —
   deductively, from seven lines of code — a **ceiling** for any additive bonus to that
   channel's score.

The prediction is testable and we tested it, with increasing dose in **counterfactual
replay** over 350 of 350 real brief states, faithful to the serving pipeline — ⚠️
production states, intervention **not served** (*shadow* mode, §7): monotone in every
state, saturating at `w ∈ (4.0, 4.4]`, a ceiling of **4.86%** of briefs. It survived the
test that could have killed it — and an earlier instrument that **confirmed it for the
wrong reason** (§5.6).

⚠️ **Scope, stated before the results and not after.** This is **one** system. We did not
measure effects on agent behaviour — there is no instrumented downstream outcome (§5.4).
We do not claim the field optimises the wrong coordinate: we claim there exists a
coordinate benchmarks do not measure, we give the instrument to measure it, and we leave
the question open. And of the two surfaces, only the brief is decided by the system; the
other is agent-initiated and accounts for most of the exposure (§4.1.1).

- **The gap.** The field's canonical survey (TMLR 2602.06052v4, 218 papers) maps
  agent-memory architectures and benchmarks. Benchmarks measure nDCG/recall over query
  sets. None measures the **delivery surface**: how many distinct items an agent in
  production actually sees, and which ones.

  And the vocabulary of experimental methodology **is not there**. Recomputed over the v4
  PDF (`measurement/survey-string-count.py`, sha256 `497e9549…b46a6`, 429,387 characters,
  63 end-of-line hyphenations stitched before counting):

  | term | body | bibliography |
  |---|---|---|
  | `pre-registration` / `preregistration` (and the 6 other spellings) | **0** | **0** |
  | `randomized` / `randomised` | **0** | **0** |
  | `ablation` / `ablations` | **0** | **0** |
  | `interventional` | 1 | 0 |
  | `counterfactual` | 1 | 0 |

  This is not the absence of one word: it is the absence of the **entire family**. A
  survey of 218 papers that says `memory` 1,169 times and `randomized` not once is not
  omitting a term — it is describing a field whose instrument is the offline benchmark,
  not the experiment. The two occurrences that do exist are singletons, and one of them,
  `counterfactual`, appears as a suggested future direction.

  ⚠️ **Zero is the result a broken extraction produces for free**, so the count runs with
  a positive control (`memory`, `agent`, `benchmark`, `evaluation` above floors) and
  aborts if it fails. The control did fire once, on `ablation=0`: it was the **floor**
  that was wrong — a survey catalogues, it does not ablate — and a direct check
  (`memory`=1,208, `benchmark`=126 in the same text) showed the extraction intact. The
  term left the control and became data.
- **Why the question matters.** ~~If the surface has fixed, small capacity, then
  improving ranking does not improve exposure, and the field optimises the wrong
  coordinate.~~ **That was the hypothesis this work began with, and the measurement
  contradicts it:** the surface is not small — it is 8.7× the corpus. What matters is what
  remains after that: a surface with room to spare delivers 2.66%, and the channel that
  would exist to compensate is governed by two path patterns that see 0.16% of the corpus,
  and by a lexicographic order in which the score does not decide. Whether other systems
  have this shape is an open question — not a claim of this paper — and the published
  diagnostic exists so that it can be answered.
- **Contributions.** (i) the measurement of the exposure surface of an agent-memory
  system **in production**, with the result that capacity exceeds the corpus by 8.7× and
  even so 83.78% is never exposed — ⚠️ a number that sums **both** surfaces, whereas the
  capacity cited is the brief's alone, and §4.1.1 delimits what each one licenses one to
  conclude; (ii) the localisation of the bottleneck in the **coverage channel**, with the
  two mechanisms that freeze it — an eligible population of **108 chunks (0.16% of the
  corpus)**, carved out by path patterns, and a lexicographic order that demotes the score
  to a subordinate coordinate; (iii) a **deductive** prediction of a ceiling for additive
  bonuses in that channel, tested with dose-response and faithful replay; (iv) the
  **executable diagnostic** (`measurement/`), so that the measurement is reproducible on
  another system.

  ⚠️ **The catalogue of instrument defects (Appendix E) does not count as a
  contribution**, and the reason is an honest one: they are **17 defects we ourselves
  committed**, eight of them altering a number this paper reports. Reporting them is an
  obligation, not a merit — and above all, eight findings do **not** bound the ones not
  found. They are in the appendix because whoever reproduces the measurement will hit the
  same ones, not because they credential us.
