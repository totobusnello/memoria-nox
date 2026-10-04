# Spare capacity, narrow surface: what a production agent-memory system actually surfaces

> **Correction: the title changed on 2026-08-29, and the reason belongs to the paper itself.** It used to be
> *"Spare capacity, **starved coverage**"*, and adversarial review pointed out two flaws in the
> metaphor. First, the coverage channel is **not** starved: it exhausts the eligible pool at 100% every day
> (§4.3.1). It is the corpus that is starved, not the coverage, so the image inverted the mechanism
> described in the body. Second, *starved* is normative, and §4.5 explicitly refuses that judgment:
> "a reader who concludes 'the system is losing valuable information' has gone beyond what was
> measured". A subtitle cannot sell the conclusion that the body declines.

> **Status (2026-10-04).** v1.0 of this manuscript (Portuguese) was published on Zenodo on
> 2026-08-30 (`10.5281/zenodo.22181415`). This is v1.1: the text revised after the 2026-09-21
> corrections and the 2026-10-04 audit of aged claims (Appendix H), translated to English, and
> not yet deposited as a new version of that record. **Rule of this file:** where there is a
> number, it comes from an artifact locked by `--assert-json` and its reproduction command is
> cited.
>
> Sources: `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` ·
> `REMEDIATION-2026-08-27.md` · `DEVIATIONS-FOR-PAPER.md` ·
> `PROTOCOL-CALIBRATION-2026-08-27.md`.

---

## Abstract

Memory systems for agents are evaluated by retrieval quality over sets of queries. Among the 218 papers of the field's canonical survey, none measures what the
agent **actually receives** in production. Retrieval is also conditional on a query having been
issued, so an item that no query reaches has an undefined nDCG, not a low one. For 12 weeks we
instrumented the two surfaces through which a memory system in operation delivers content to a
fleet of 6 agents: a proactive 10-item brief and on-demand search.

The brief delivered **583,763 slots**, **8.7 times** the size of the corpus, enough to
serve each of the 67,187 chunks eight times. It delivered **1,635 distinct live chunks:
2.43%** (1,787 counting the 152 that were served and later deleted; see §4.1). The
**aggregate** capacity, therefore, did not force this result: there was room to show
the whole corpus eight times over. It does not follow that the ordering is wrong, only that
the number was not produced by a lack of space. The **per-session** capacity (10 items)
is not tested here. (The 99.98% coverage under uniform service appears as an arithmetic limit of what
the capacity would allow, not as a recommended policy.) Adding search, **83.78% of the corpus was never
exposed by either surface**. The change of universe between the two sentences is
deliberate and must be read as such: the capacity slack above is **the brief's**, whereas the 83.78% counts the
**union**. And the exposure that exists is, for the most part, **initiated by the agent and not delivered by the system**: 9,755 of the 10,899 exposed chunks came from search.
The surface the system decides, the brief, exposed 1,787. Every claim in this paper about
*mechanism* concerns the brief; the 83.78% describes the state, not the culprit.

**The two channels of the surface freeze, for opposite reasons and neither tied to
capacity.** The 8 slots of the main pool are ordered by a score whose terms, with
one exception, **do not decay**: the access component is monotone in a counter that only
goes up. The 3 chunks present in **100%** of the 4,632 briefs of the week were last accessed
90, 30 and 42 days ago (measured at the close of the window, 2026-08-28) and occupy
positions **2, 3 and 5**. Search traffic from months ago determined those positions, and the
top-10 takes **47.16%** of the slots. The other 2 slots are a *coverage* channel, whose declared
purpose is to serve the never-served, and it **freezes** for a different reason:
its eligible population is **108 chunks in a corpus of 67,187** (0.16%, carved out by
two path patterns), and it exhausts that population **entirely, every day**, with 12.4 slots per
candidate **on a closed day** (5.6 on a partial day, and the two are not comparable; see
§4.3.1). There is never any never-served item left to serve. The channel that would respond to a score adjustment is the one nobody adjusts; the one designed
to compensate for the other is the one that does not respond to score.

The mechanism of the coverage channel is **deducible from the code**. It orders by a
**lexicographic** comparator `(last_served ASC, salience DESC)`: the score is the
**subordinate** coordinate and decides only within ties of the dominant one. That predicts a **ceiling**,
not a proportional response, for any additive bonus on the score **of that channel**.
We tested with an increasing dose by **counterfactual replay** over **350 of 350** real
brief states, faithful to the serving pipeline. **Caveat: the states are from production; the intervention
was not served.** The mode is *shadow*: the treated composition is computed and recorded, and
what the agent received during the measured window was always the control (§7). Result: a monotone response in each state, saturation at `w ∈ (4.0, 4.4]`, and a ceiling of
**4.86%** of briefs. The ceiling is also not a constant of the mechanism, along two axes we measured:
under the same rule with another draw of designated items it reaches **7.43%** (the draw
in force sits at the minimum of the distribution, tied with another), and truncating the timestamp resolution from second to
minute or hour takes it to **36%** and **80%**, without changing a single line of code. **The reach of the
mechanism is fixed by decisions that nobody took as policy.** **Correction: a third axis
exists**, and an audit on 2026-08-30 found it in an artifact we had recorded and never read:
excluding the rows of our own health probes moves the replay's anchor. The ceiling above was
computed **without** excluding them. Measured the same day with a paired design, excluding them
lowers it from 17/350 (4.86%) to 13/350 (3.71%), and only **one** sensitive state is common to
the two arms (§5.7.2).

**Caveat: what we do not claim.** No effect on agent behavior: no downstream outcome is
instrumented (§5.4). Nor do we claim that the concentration is *wrong*. A policy
that serves 10 items per session **should** concentrate, and serving uniformly would be useless;
the finding is that the non-exposure is a **result of policy and not a capacity limit**,
hence revisable by a design decision. And we claim nothing about the field: this is **one** system. The generalization
of the mechanism is deductive and holds for any ranker with lexicographic order and a bonus on the subordinate coordinate. How many systems have this shape is an open question, and the
executable diagnostic we publish exists so that others can answer it one at a time.

**Caveat: two notes on reading.** First, of the 10,899 exposed chunks, **9,755 came from search, which is
initiated by the agent**; only the brief is a delivery decided by the system, and the mechanism claims
hold for it. Second, collection size, which correlates with exposure
(§4.2), may be a **proxy for how the type is produced**: curation is not ruled out
as a common cause.
