# Related work — draft for Paper B (`MANUSCRIPT-B.md`, working-list item 7)

> **Status: DRAFT, 2026-10-03/04 (BRT).** Written for insertion as a new section of Paper B. Citations are
> pandoc-style (`@bibkey` inside square brackets) and resolve in `B-related-work.bib` (same directory). Every reference was opened or
> machine-resolved before use; what was checked, and how deeply each work was read, is in
> `B-related-work.verification-log.md`. **Reading depth matters for how far a sentence can go**, so each
> subsection ends with a one-line provenance note. Paper A's §8 (`MANUSCRIPT.md`) covers the exposure /
> surface literature (Singh–Joachims, Diaz et al., popularity bias, Bower et al.) and is not repeated here.
>
> **Length:** this is the long form (~4,000 words with the table and open items). If the venue wants ~1,200 words, keep
> the opening paragraph, the §8.2 table and the CMP paragraph, §8.5, and one paragraph each from §8.3 and §8.4.
>
> Numbers about *this* trial are quoted from `MANUSCRIPT-B.md` as it stood on 2026-10-03 and must be
> re-synchronised if that manuscript changes (the sham replay of §4.0.1b was still running).

---

## 8. Related work

Four bodies of work bear on this trial, and each is read here for two things: what it gives us, and what this
trial does **not** do that its authors do. The short version, argued below, is that (i) the agent-memory
literature has benchmarks, cost characterisations and — as of two days before this draft — one randomised
design, but no pre-registered randomised trial on live traffic that we could find; (ii) the methods this
trial needs (switchback designs, interference, few-cluster inference, power) come from online experimentation,
which has no memory-specific content; and (iii) pre-registration is argued for in ML and IR but rarely
practised, and a failure it rarely discusses — a registration that contradicts itself — is the one this trial hit.

### 8.1 How agent-memory evaluation is done, and what the surveys ask for

**Benchmarks compare systems on fixed tasks.** MemoryArena [@he2026memoryarena], Evo-Memory
[@wei2025evomemory], LifelongAgentBench [@zheng2025lifelongagentbench], MemoryAgentBench
[@hu2025memoryagentbench], LoCoMo [@maharana2024locomo], LongMemEval [@wu2025longmemeval] and InterruptBench
[@zou2026interruptbench] differ in what they stress — interdependent sessions, task-stream order, lifelong
skill reuse, the four memory competencies, long conversational recall, mid-task goal revision — but share one
structure: a curated task suite, run once per system, with systems compared to each other. Paper A (§8.1)
reports a full-text read of MemoryArena and Evo-Memory and the consequence for novelty: their contrast is
between *systems on fixed tasks*; ours is between *two policies of one system on traffic we did not choose*.
Evo-Memory is the sharpest case for randomisation, because it both fixes task order ("a unified task sequence
ordering within each dataset") as a fairness device and measures that order matters: in its Table 2, ExpRAG's
average success over AlfWorld and ScienceWorld is 0.57 under Easy→Hard and 0.69 under Hard→Easy. Those are two
*difficulty-sorted* orders, not sampled ones, and the same section highlights "the importance of task sequence
design for fair evaluation and effective learning". We re-found all three statements in the v2 text on
2026-10-04.

**What the canonical survey asks for.** The TMLR survey [@huang2026survey] closes its evaluation discussion
(§9.6) by asking for "closed-loop, longitudinal, and execution-grounded evaluation paradigms", with agent-centric
memory evaluated in "partially open or continuously evolving environments, where experience accumulation has
real consequences", "enabling comparison between memory-augmented agents and memory-free baselines under
identical conditions", with versioned and replayable state and provenance metadata. This trial is a neighbour
of that direction rather than an instance of it, and the difference should be stated: §9.6 contrasts memory
against *no* memory; we contrast two policies of an always-on memory (a dose-weighted promotion rule against the
production brief policy). What the trial does share with §9.6 is the paradigm — a live system, a closed loop,
logged provenance (`ids_tratado` / `ids_controle` per brief) and a frozen, replayable serving state.

What the survey does **not** ask for is equally specific, and we recomputed it on the version pinned in
Paper A (sha256 `497e9549…`, 4 Aug 2026): zero occurrences of `random*` and zero of `pre-regist*`/`preregist*`;
one `A/B`, which appears as a *cost to be spared* — high-fidelity user simulators are valued for "reducing
costs associated with live user studies and online A/B testing" — and one `interventional`, in the same simulator paragraph, where
simulators are said to enable evaluation of "interventional impacts under dynamic conditions rather than
static test collections". The survey therefore names the paradigm and, in passing, files the live experiment
under things to be substituted. We read that as an *absence of a convention*, not as a claim that no one has run
such experiments; the counts are about one document. The three other surveys we checked
[@zhang2024memorysurvey; @hu2025memoryage; @du2026memoryautonomous] return zero for `randomi[sz]ed`, `A/B` and
`pre-?regist` on a plain-text extraction (hyphenation not stitched, so these are lower bounds).

**Telemetry is the other measurement axis.** Omri et al. [@omri2026agentmemory] build a phase-aware harness
that attributes token volume, latency, utilisation and energy to memory *construction*, *retrieval* and
*generation*, characterise ten systems across two benchmark suites (LongMemEval- and EventQA-derived
workloads), and argue that benchmarks which score
"purely on downstream accuracy" leave system behaviour uncharacterised. This is orthogonal to ours, and each
side lacks what the other has: they measure what memory *costs*, per phase, and run no randomised contrast
(zero `random`, `A/B`, `counterfactual`, `causal` or `pre-regist*` in their text); we measure whether a
promotion lever changed what agents *did*, and report **no cost, latency or energy** (a search of
`MANUSCRIPT-B.md` for `latency` and `token cost` returns nothing). A trial that carried their per-phase
attribution would answer a question ours cannot — whether a lever that changes a brief a few percent of the
time pays for itself — and we flag it as the natural extension, not as something we have.

*Provenance.* Survey: full text, §9.6 read, strings counted on the pinned PDF. Omri et al.: §1–3, Rec. 9 and the
profiling-harness description read, strings counted; remainder skimmed. MemoryArena v2 and Evo-Memory v2:
string-searched this sprint; the full reads are those of 2026-08-15 in `RELATED-WORK.md`, **of the earlier
arXiv version for MemoryArena** (v2 is dated 17 Sep 2026; see open items). All others: abstract level.

### 8.2 Controlled and interventional studies of memory components

Beyond benchmarks there is a thin literature that *intervenes* on memory. We list what each intervenes on, in
what setting, and — the three questions that separate it from this trial — whether exposure is randomly
assigned, whether the design was registered in advance, and whether it ran on live traffic.

| Work | What is varied | Setting | Randomised exposure | Pre-registered | Live traffic |
|---|---|---|---|---|---|
| Xiong et al. [@xiong2025memorymanagement] | memory addition / deletion; stored-record quality | four agents, controlled experiments | not determined (abstract) | not determined | no |
| Feng et al. [@feng2026memorytransplants] | memory architecture × content, 2×2 factorial, 7 conditions | LiveCodeBench → MATH, 3 seeds, 360+ runs | not determined | "six pre-registered validation gates"; negative controls (random retrieval, placebo, write-only, frozen store) specified in advance | no |
| Sun et al. [@sun2026experienceserving] | none / random / global / retrieved experience injected into prompts | production moderation workload; results on a benchmark built from human-labelled production data | random-*content* control, not randomised assignment of units | not stated | serving system is in production; results are reported on an offline benchmark |
| Tablan et al. [@tablan2026learningonthejob] | no-memory vs. two feedback-learned stores vs. static-RAG control | τ-bench banking, simulated; paired contrasts | not determined | not stated | no |
| Srivastava [@srivastava2026cmi] | no-memory / with-memory / perturbed-memory conditions, per candidate memory | Causal-LoCoMo (87 filtered examples; synthetic harmful memories) | assignment not described in what was read | not stated | no |
| **Behnam & Wang** [@behnam2026cmp] | which memories fill *k* reserved context slots | LongMemEval, LoCoMo, multi-hop QA; replay of Mem0 over LongMemEval histories | **yes**, balanced assignment with known propensities | not stated (no `pre-regist*` in the text) | no |
| **This trial** | promotion dose *w* on 19 designated chunks | production fleet, 24 h epochs | **yes**, constrained randomisation from a public beacon | **yes** (OSF `yf7d2`) | **yes** |

"Not determined" means *we did not read far enough to say*, not that the answer is no. The row that matters is
Behnam & Wang, because it is the nearest work and it is new.

**Causal Memory Policy.** Behnam and Wang [@behnam2026cmp] (arXiv, 1 Oct 2026) argue that estimating a
memory's utility from logged interactions, or from a store-level intervention, fails whenever the memory is not
retrievable: Theorem 1 shows utility is "not identified by any design that holds M−m fixed while randomizing
only whether m is included", because retrieval mediates the effect of the memory state on the output. They
call this a *retrieval-level positivity violation* and restore identification by randomising which memories
occupy *k* reserved context slots, with propensities fixed by design and a self-normalised inverse-propensity
estimator. Empirically, identification fails for 54% of required memories on LongMemEval and 67% on LoCoMo, and
"persists in a deployed memory system" — Mem0, replayed through its own extraction and retrieval path over
benchmark histories; the paper's own limitation section notes the exposure costs −0.026 F1 on average (not
distinguishable from zero) and that their demonstration pool was built with knowledge of which memories are
required.

Three points of contact, stated plainly. **First, an instance of their failure is in our data.** Paper B §3.0.1
reports that the 19 designated chunks leave eligibility together at 2026-09-20 22:51:23, after which "no value
of the dose reaches them, because the boost is addressed by id and they are no longer in the candidate list" —
treatment and control become the same intervention for 214 of the 234 registered epochs. That is a
positivity failure of the policy lever, and CMP is the formal name and the first treatment of it we have found.
We did not have the framing at registration (OSF, 2026-08-18; CMP is dated six weeks later) and we make no
priority claim in either direction. Whether the 20 *realised* epochs also contain a partial failure — designated
chunks that never entered a brief at some doses — is a question for Paper A's exposure measurements and §4 of
this paper; this section does not assert it. **Second, the designs answer different estimands.** CMP
identifies the utility of an individual memory on a query, by randomising slots per interaction (time
step). This trial estimates an intention-to-treat effect of one lever on the share of repeated
failures among opportunities, with the fleet-wide epoch as the unit. We do **not** identify any individual
memory's utility, we do **not** randomise within a brief, and we have no propensity-weighted estimator.
**Third, the evidence differs in kind.** Theirs is benchmark and replay evidence with a measured per-query cost;
ours is live traffic, pre-registered, with an interval that — by our own account in §1 — does not
deserve trust, and an effect estimate that could not have been detected. Neither subsumes the other; the
combination CMP-style slot randomisation *on* a live fleet *under* a registration is, as far as we found,
empty, and it is what a successor trial would need.

**Randomised evaluations of deployed AI tools exist, but not of memory.** Peng et al. [@peng2023copilot]
and Becker et al. [@becker2025metr] randomise developers or tasks to AI-assisted and unassisted conditions
(the latter: 16 developers, 246 tasks, a 19% slowdown against a 24% forecast speed-up); Bean et al.
[@bean2026llmmedical] run a randomised, pre-registered study of LLMs as medical assistants for the public.
These randomise *people or tasks*, which presumes that one unit's assignment does not alter another's
experience. A memory store shared by a fleet violates that presumption, which is why §8.3 is the relevant
literature for the unit of randomisation here. A position paper on causal methods for LLM development
[@frauen2026causalmethods] argues the area is under-served by them; we cite it as agreement on the
diagnosis, not as evidence.

*Provenance.* CMP: sections 1–3, the deployed-system replay setup, F.1 and Limitations read; strings counted on
the PDF (sha256 `5b298624…`). Feng et al.: abstract, contributions, gates and negative-control passages read.
All other rows: abstract, plus (Sun, Tablan) the experimental-design passages returned by search. The
Randomised-exposure and Pre-registered cells marked "not stated" mean *not found in what was read*.

### 8.3 Online controlled experiments for ranking and recommendation

The machinery for this trial is not from agent memory. It is from online experimentation, and the gaps between
that practice and ours are the substance of §7.

**Randomise, then check the randomisation.** The practice literature on online controlled experiments
[@kohavi2020trustworthy; @kohavi2009controlled; @kohavi2012puzzling] is the standard reference for running
randomised experiments on live systems; we know it at title and metadata level only (no book or chapter was
opened), so we cite it for that role and not for any specific prescription. One concern from this literature is
verified at abstract level: Fabijan et al. [@fabijan2019srm] describe sample ratio mismatch — the observed
sample ratio differing from the expected one — as an indicator of a variety of data-quality problems in
experiments. This trial's analogues of such checks are the registered assignment script with its committed
hash, the positive control (11/11 treatment epochs with a changed brief) and the dual negative control (8/8
control epochs with no treated ids) of §4.0.1b; the sham replay, which plays the role of a placebo /
specificity control on the non-designated pool, was still running when this was written. We use **no variance-reduction** from pre-experiment covariates
[@deng2013cuped] — `MANUSCRIPT-B.md` contains no mention of covariate adjustment — and we do not know what it
would have bought at this N.

**Within-subject designs buy sensitivity this trial did not use.** Interleaving [@radlinski2008clickthrough;
@chapelle2012interleaved; @hofmann2016online] shows two systems' items in one list and credits whichever the
user prefers; the review of Hofmann et al. reports one to two orders of magnitude more sensitivity than
absolute metrics. The brief is also a list of items (ten, per Paper A §8.2). We did not interleave, we have no per-item credit
signal (an outcome is attributed to a session, not to an item), and whether interleaving transfers to memory
briefs is an open question we do not answer.

**Why the unit is the epoch.** When treated and control units share state, per-unit randomisation is biased:
the marketplace [@blake2014marketplace; @johari2022twosided] and network
[@saveski2017network; @aronow2017interference] experimentation literatures are built around this problem
(Aronow and Samii's abstract frames it as "interference between units"). One standard remedy is to randomise
the *whole system over time*. The switchback literature
[@bojinov2023switchback; @hu2022switchback; @basse2023minimax] formalises it and names its price —
carryover, which converts interference into dependence across periods — and supplies randomisation-based
inference [@bojinov2023switchback; @bojinov2019timeseries]. Our design is a fleet-level switchback: every
agent is in the same arm at any instant, epochs are 24 h, and a two-hour washout is excluded. What we did
**not** do, and the literature does: we fixed the washout ex ante rather than estimating the carryover order
from data (Bojinov et al. give theory for a misspecified order and a data-driven procedure to identify it);
we have 20 periods, and how their finite-population results behave at that count we did not check; and a
memory store accumulates, so carryover through *state* may outlast any fixed washout. Basse et al.
treat a nearby temporal pattern — effects that attenuate with repeated exposure, "habituation" — which is not the
same thing as state carrying over, and we flag the difference rather than claim coverage. We read these papers
at abstract level, and we claim only the relation, not that their theorems apply to our state process.

**Few clusters.** Our reported interval is a percentile cluster bootstrap with the epoch as the unit, on 9–11
clusters, and §1 concedes it under-covers. That is the known regime. Cameron, Gelbach and Miller
[@cameron2008bootstrap] introduce the wild cluster bootstrap because ordinary cluster bootstraps
over-reject with few clusters; Webb [@webb2014reworking] shows these procedures "perform poorly with fewer than
eleven clusters" and proposes a six-point weight distribution; Cameron and Miller [@cameron2015practitioner]
recommend that six-point version below ten clusters. We used none of them. The registered
re-randomisation test over 10,000 redesigns (§4.0.2) is the finite-sample alternative that avoids the
asymptotics — a Fisher randomisation test of the kind Imbens and Rubin [@imbens2015causal] treat in general
and Bojinov and Shephard [@bojinov2019timeseries] for time-series experiments — and it is the inference we
should weight when the two disagree, as they do on H1a.

**Under-power is the normal condition of field experiments with a rare, noisy outcome.** Lewis and Rao
[@lewis2015unfavorable] report that across twenty-five large field experiments "the median confidence interval
on return on investment is over 100 percentage points wide" and that informative experiments "can easily
require more than 10 million person-weeks". This is the nearest precedent for a field null that carries little
information, and it is a *weaker* case than ours: they were under-powered by the economics of the outcome,
we by a registration whose sample size ignored a 30-day eligibility window (§3.0.1). They also argue the right
conclusion is not to retreat to observational comparisons: Gordon et al. [@gordon2019comparison] find that
observational methods often fail to recover the effects measured in the same Facebook experiments, and
Garcin et al. [@garcin2014offline] and Rossetti et al. [@rossetti2016contrasting] address the relation between
offline and online evaluation of recommenders (we know both at title level only and cite them for the topic, not
for a finding). Our replay-based analyses are of the family of Li et al. [@li2011unbiased], whose abstract
introduces a replay methodology for offline evaluation. The ghost-ads method of logging, in the control arm, the
exposures the treatment *would* have produced [@johnson2017ghost] is the closest published analogue of our sham
replay: in both, the analysis has to be restricted to the units the treatment would have reached, and our first
attempt at the sham, which counted over the log without re-executing the serving code, was invalid (§4.0.1b).

*Provenance.* All works in this subsection were resolved by Crossref or arXiv metadata. Read at abstract
level: Radlinski et al., Bojinov et al., Bojinov–Shephard, Basse et al., Aronow–Samii, Fabijan et al., Li et al.,
Lewis–Rao, Webb (working-paper abstract), Gordon et al. (one-sentence summary). Title/metadata level only:
Kohavi et al. (three items), Deng et al., Chapelle et al., Blake–Coey, Johari et al., Saveski et al., Garcin et
al., Rossetti et al., Cameron et al. (both; the six-point recommendation is from a text excerpt of Cameron–Miller
returned by search). The Hofmann et al. sensitivity statement ("one to two orders of magnitude") is from an
excerpt of the monograph, not from the full text. Ghost Ads is described from the authors' 2016 draft. No book
in this subsection was opened.

### 8.4 Pre-registration, registered reports, and what a null is worth

**In ML and NLP, pre-registration has been proposed and piloted, not adopted.** The NeurIPS 2020 and 2021
workshops [@bertinetto2020prereg; @albanie2022prereg] ran a registered-report–style review: the 2021 preface
reports 22 proposals, 10 accepted, and 3 results papers, all 3 judged to have followed protocol. Van Miltenburg
et al. [@vanmiltenburg2021prereg] argue for it in NLP; Søgaard et al. [@sogaard2023twosided] list costs
(confirmatory bias, publication bias, flag-planting) and observe that the earlier workshops "seemingly did not
lead to publications or a change in practice yet". Hofman et al. [@hofman2023prereg] adapt registration to
predictive modelling. Two recent pieces bear directly on agents. Vaccaro [@vaccaro2026prereg] catalogues the
researcher degrees of freedom of experiments with AI agents (Table 1) — and lists **memory settings** among them
(enabling or disabling conversation memory, or clearing state between trials, "based on which configuration
yields favorable results"); her setting is *agents as experimental subjects* ("in silico" behavioural
experiments), not interventions on a deployed agent's infrastructure, so the fit is by analogy. Wilder and Zhou [@wilder2025evaluation] propose
that ML venues require authors to declare whether field experiments were preregistered. In IR the Dagstuhl
report on information-access experimentation [@bauer2023dagstuhl] recommends results-blind review and suggests
piloting protocol-reviewed tracks. The only memory-specific pre-registered design we found is the six-gate
protocol of Feng et al. (§8.2), on benchmarks. **What this trial does not do:** it is a *registration* (OSF,
Zenodo), not a registered report — the protocol was never peer-reviewed before data — and our own deviations
are recorded in Appendix A. The cross-field arguments [@nosek2018prereg; @chambers2022registeredreports;
@munafo2017manifesto] are the standing justification; none is specific to systems or to agents.

**Registration changes what gets reported.** Kaplan and Irvin [@kaplan2015nullnhlbi] find that 17 of 30 large
NHLBI trials before 2000 reported significant benefit against 2 of 25 afterwards, coinciding with mandatory
prospective registration of outcomes — a natural experiment in why registered trials publish nulls. It is the
background against which we choose to publish an under-powered one.

**Power language needs care here.** The critique that low power makes significant results unreliable
[@ioannidis2005false; @button2013power] ("low power also reduces the likelihood that a statistically
significant result reflects a true effect"), the Type S / Type M framing [@gelman2014beyond] ("in noisy,
small-sample settings, statistically significant results can often be misleading"), and the argument that
post-experiment power calculations are "fundamentally flawed" because observed power is a one-to-one function of
the p-value [@hoenig2001abuse] all apply — and the same authors also say power calculations "can be valuable in
planning an experiment". Paper B's saturated minimum detectable effect is **prospective and
outcome-independent** — arithmetic over the realised N, the registered ICC and the baseline rate — which is the
planning form that critique permits; but its inputs are the problem, since the ICC was estimated for a
different quantity (§1). In IR, Urbano et al. [@urbano2019significance] show that
the type of significance test materially changes Type I/II rates on test collections; we know of no
corresponding analysis for experiments on live retrieval, and ours is not one.

**Searched and not found.** To avoid reading absence as a negative result: web and arXiv searches (Perplexity,
Firecrawl; 2026-10-03/04) for `pre-registered`/`registered report` combined with *information retrieval*,
*ECIR*, *SIGIR* and *agent memory*, and for *randomised trial / A/B test / production* combined with *agent
memory* and *memory policy*, returned the works cited above and no IR registered-report track, no
pre-registered live memory experiment and no memory A/B test with a reported effect estimate. This is a
bounded search by one agent, not a systematic review, and the field moves weekly — the most relevant result
(Behnam & Wang) is two days old.

*Provenance.* NeurIPS 2021 preface, Søgaard et al., Vaccaro and the Dagstuhl report: PDFs fetched, passages
verified by text search. Kaplan–Irvin abstract read on the PLOS page. All others: Crossref metadata and, where
noted in the log, abstract.

### 8.5 Position, in six lines

1. **Not new:** the observation that memory evaluation scores representation or system comparison rather than
   behavioural effect (MemoryArena, Evo-Memory, the survey); randomising a retrieval-side lever with known
   propensities (Behnam & Wang); the switchback design, its carryover and its inference (Bojinov et al. and
   successors); the argument for pre-registering ML experiments.
2. **What this trial is:** a pre-registered, public-beacon-seeded, fleet-level switchback on live agent traffic,
   with logged per-brief provenance, positive and negative instrument controls, and a null reported with
   its power failure and two of its own contradictions.
3. **What it is not:** it does not identify per-memory utility; does not randomise within a session or brief;
   does not interleave; does not estimate carryover; does not measure cost; compares two policies, not memory
   against no memory; is one system on one fleet; and its interval is not trustworthy at ~10 clusters.
4. **What it adds, narrowly:** an empirical instance (§3.0.1) of the retrieval-level positivity failure that
   CMP formalises, observed on live traffic rather than benchmarks; and a worked example of a registration
   whose sample size and estimand each looked complete alone and contradicted each other.
5. **Where the field is heading, by our reading:** per-query randomised exposure on live systems under
   registration, with per-phase cost attribution (Omri et al.). The three have not been combined, to our
   knowledge, and none is cheap.
6. **What would falsify the positioning:** a pre-registered randomised memory trial on live traffic published
   before ours. We found none; see "Searched and not found".

---

## Open items before this goes into `MANUSCRIPT-B.md`

- **Re-read MemoryArena v2** (17 Sep 2026) in full — Paper A's and `RELATED-WORK.md`'s statements rest on the
  08-15 read of an earlier version. This sprint only string-searched v2 (no `A/B`, `counterfactual`,
  `pre-regist*`; four `random` hits, none about assignment of memory policy).
- **CMP is two days old** and not peer-reviewed. Re-check for a revised version and for follow-ups immediately
  before submission; if it changes its claims, §8.2 changes with it.
- **Sections cross-referenced above** (§1, §3.0.1, §4.0.1b, §4.0.2, §4.4, Appendix A) are those of the 2026-10-03
  `MANUSCRIPT-B.md`; renumbering will break them.
- **Books not opened** (Kohavi et al.; Imbens–Rubin): used only for what their titles and Crossref records
  support. Replace the generic attributions with chapter-level citations if a reviewer asks.
- **Cambridge page HTTP 429** blocked the Kohavi table of contents; retry.
- The author should decide whether Paper A's §8.3 ("zero occurrences of pre-registration" in the survey) should
  also carry the CMP, Feng et al. and Vaccaro findings; they weaken "no one has done this" from a statement about
  the field to a statement about live traffic, which is what the register of this section already says.
