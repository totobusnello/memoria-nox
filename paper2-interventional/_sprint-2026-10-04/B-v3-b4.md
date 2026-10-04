## 5. What is not evaluable, and why: declared, not omitted

| registered rule | why unevaluable | what stands in its place |
|---|---|---|
| **H1b** | collision between the 2026-07-29 and 2026-08-16 locks (§4.4) | nothing; the mechanism question is not answered |
| **TOST arm×coverage** at `\|r\| ≤ 0.15` | requires K ≥ 30; K = 19 | correlation + CI, unconditional (§4.6) |
| **dose-response / H3** | `n = 1` at the top dose (§4.7) | per-dose effect with `n` on the same line, no gradient |
| **leave-one-agent-out** | 6 agents over 19 epochs | exploratory, no inference |
| **first-half / second-half contrast** | window truncated inside the first half | not reported |

These are listed **before** the discussion, and were listed in §8 of the analysis spec
before the window closed, so that their absence cannot be read as omission. A rule that
becomes unevaluable and is simply dropped is indistinguishable from a rule that was never
there.

---

## 6. Instrument defects that changed a reported number

Consistent with Paper A's §6, defects that changed a number we had published are part of
the contribution rather than an appendix.

1. **Ruler substitution (`09-20`)** — delivery volume where the spec locks clock exposure;
   16+3+1 published as 17+2+1, propagated to six places including a pushed commit (§3.1).
2. **Post-randomization conditioning on the arm** — mode of observed dose instead of
   designation; 0 divergences, but the premise was wrong (§3.1).
3. **"Zero inversions" is a tautology** — adding a vote to an odd panel under strict
   majority can only hold or tie, so zero inversions is structurally guaranteed and a coin
   would achieve it. The metric with content is agreement with the three-family majority:
   **1 111 / 1 145 = 97.0%**.
4. **A rate generalized from one batch** — *"100% of abstentions are `xai`"* was true in
   the first 100 episodes and false over 1 195 (`xai` 26 + 6 quota + 1 missing · `zhipu`
   13 · `google` 11), and was never re-measured before being asserted.
5. **Claiming the data confirm a locked parameter** — τ is locked since July over five
   families; "confirming" it with outcome-period data is post-hoc. We also called marginal
   rates "agreement", and cited the S1/S2 boundary that τ absorbs while omitting S0/S1,
   which it does not and where the 12 pp gap lives.
6. **A rationalized sign** — we explained a +7/−8 swing by claiming a retry had recovered
   what a fourth panelist rescued; the sets are **disjoint**, and the sign comes from the
   28 losses, not the gains. Recomputed under the published rule: gains 20, losses 28,
   balance **−8**.
7. **A panel composed after counting ties in the trial's own verdicts** — post-hoc by §9
   of the spec, recorded as such. What stands: the fourth family enters **only** as a
   substitute where fewer than three substantive verdicts exist (the role PREREG §695
   assigns it), never as a fourth vote, so it generates no ties; the four-vote set is
   published as declared sensitivity.

Defects 1–7 were found by two mechanisms that catch **disjoint** classes: adversarial
review by independent model families, and mechanical census. Six of the seven above came
from the former on a body of work the latter had already passed.

---

## 7. Threats to validity

**Power.** Addressed throughout and not mitigated: the study is under-powered by
construction and no analysis choice repairs that.

**One-system, one-fleet.** Everything is measured on a single production system. Nothing
here establishes that the effect, or its absence, generalizes.

**Directional bias toward the null.** The 2-2 tie rule resolves to `not_failure` by
design. The study's conservative choice runs in the same direction as its result, and a
reader is entitled to weigh that.

**Denominator.** §4.2. The exposure measure counts idleness, and one epoch dominates.

**Our own bookkeeping.** §1.1. The claim that two estimand decisions preceded the
estimates rests on our commit timestamps in an append-only log.

---

## 8. Related work

Four bodies of work bear on this trial, each read for what it gives us and for what this
trial does **not** do that its authors do. In short: the agent-memory literature has
benchmarks, cost characterisations and (dated 1 October 2026) one randomised design, but
no pre-registered randomised trial on live traffic that we could find; the methods this
trial needs come from online experimentation, which has no memory-specific content; and
pre-registration is argued for in ML and IR but rarely practised. Paper A's §8 covers the
exposure and surface literature and is not repeated here.

### 8.1 Agent-memory evaluation, and what the surveys ask for

**Benchmarks compare systems on fixed tasks.** MemoryArena [@he2026memoryarena],
Evo-Memory [@wei2025evomemory], LifelongAgentBench [@zheng2025lifelongagentbench],
MemoryAgentBench [@hu2025memoryagentbench], LoCoMo [@maharana2024locomo], LongMemEval
[@wu2025longmemeval] and InterruptBench [@zou2026interruptbench] stress different
competencies but share one structure: a curated task suite, run once per system, systems
compared to each other. Their contrast is between *systems on fixed tasks*; ours is between
*two policies of one system on traffic we did not choose*. Evo-Memory both fixes task order
as a fairness device and measures that order matters: ExpRAG's average success is 0.57
under Easy→Hard and 0.69 under Hard→Easy (its Table 2), over two *sorted* orders, not
sampled ones.

**What the canonical survey asks for.** The TMLR survey [@huang2026survey] closes its
evaluation discussion (§9.6) by asking for "closed-loop, longitudinal, and
execution-grounded evaluation paradigms", in environments "where experience accumulation has
real consequences", "enabling comparison between memory-augmented agents and memory-free
baselines under identical conditions", with replayable state and provenance. This trial is
a **neighbour of that direction, not an instance of it**: §9.6 contrasts memory against
*no* memory; we contrast two policies of an always-on memory. We share the paradigm: a
live system, a closed loop, per-brief provenance (`ids_tratado` / `ids_controle`) and a
replayable serving state. §4.0.1c shows what "replayable" costs: the replay reproduces
production only on the corpus that actually served and with an exact serve-state cut. On
the version pinned in Paper A (sha256 `497e9549…`, 4 Aug 2026) we count zero occurrences of
`random*` and of `pre-regist*`; the single `A/B` appears as a cost that user simulators
spare ("reducing costs associated with live user studies and online A/B testing"). We read
that as the **absence of a convention**, not a claim that no one has run such experiments.
Three other surveys [@zhang2024memorysurvey; @hu2025memoryage; @du2026memoryautonomous]
return zero for `randomi[sz]ed`, `A/B` and `pre-?regist` (lower bounds: hyphenation not
stitched).

**Telemetry is the other axis.** Omri et al. [@omri2026agentmemory] attribute tokens,
latency, utilisation and energy to memory construction, retrieval and generation across ten
systems, with no randomised contrast. We measure whether a lever changed what agents
*did*, and report **no cost, latency or energy**; a trial carrying their per-phase
attribution would answer whether a lever that changes a brief a few percent of the time
pays for itself.

### 8.2 Interventional studies of memory

A thin literature *intervenes* on memory. Three questions separate it from this trial:
randomised exposure, advance registration, live traffic.

| Work | What is varied | Setting | Randomised exposure | Pre-registered | Live traffic |
|---|---|---|---|---|---|
| Xiong et al. [@xiong2025memorymanagement] | memory addition / deletion; record quality | four agents, controlled experiments | not determined | not determined | no |
| Feng et al. [@feng2026memorytransplants] | memory architecture × content, 2×2 factorial | LiveCodeBench → MATH, 3 seeds, 360+ runs | not determined | "six pre-registered validation gates" | no |
| Sun et al. [@sun2026experienceserving] | none / random / global / retrieved experience in prompts | production moderation workload; results on an offline benchmark | random-*content* control, not randomised units | not stated | in production; results offline |
| Tablan et al. [@tablan2026learningonthejob] | no-memory vs. feedback-learned stores vs. static RAG | τ-bench banking, simulated | not determined | not stated | no |
| Srivastava [@srivastava2026cmi] | no / with / perturbed memory, per candidate | Causal-LoCoMo (87 examples) | not described in what was read | not stated | no |
| **Behnam & Wang** [@behnam2026cmp] | which memories fill *k* reserved context slots | LongMemEval, LoCoMo, multi-hop QA; Mem0 replay | **yes**, known propensities | not stated | no |
| **This trial** | promotion dose *w* on 19 designated chunks | production fleet, 24 h epochs | **yes**, public-beacon seed | **yes** (OSF `yf7d2`) | **yes** |

"Not determined" means *we did not read far enough to say*; "not stated" means *not found
in what was read*.

**Causal Memory Policy.** Behnam and Wang [@behnam2026cmp] (arXiv, 1 Oct 2026, not
peer-reviewed) show that a memory's utility is "not identified by any design that holds
M−m fixed while randomizing only whether m is included" when retrieval mediates the effect
(a *retrieval-level positivity violation*), and restore identification by randomising
which memories occupy *k* reserved context slots, with design-fixed propensities and a
self-normalised inverse-propensity estimator. Identification fails for 54% of required
memories on LongMemEval and 67% on LoCoMo, and the failure persists in Mem0 replayed over
benchmark histories.

Three points of contact. **First, an instance of their failure is in our data.** The 19
designated chunks leave eligibility together at 2026-09-20 22:51:23, after which no dose
reaches them, because the boost is addressed by id and they are no longer candidates;
treatment and control become the same intervention for 214 of 234 registered epochs
(§3.0.1). CMP is the formal name and the first treatment of that failure we have found. We
did not have the framing at registration (2026-08-18) and claim no priority. Whether the 20
*realised* epochs also contain a partial failure is a question for Paper A's exposure
measurements and §4 of this paper; this section does not assert it. **Second, the
estimands differ.** CMP identifies an individual memory's utility per interaction; we
estimate an intention-to-treat effect of one lever with the fleet-wide epoch as unit, do
not randomise within a brief, and have no propensity-weighted estimator. **Third, the
evidence differs in kind.** Theirs is benchmark and replay evidence with a measured
per-query cost; ours is live, pre-registered, with an interval that by our own account
(§4.1.1) does not deserve trust. CMP-style slot randomisation *on* a live fleet *under* a
registration is, as far as we found, empty; it is what a successor trial would need.

Randomised evaluations of deployed AI tools exist [@peng2023copilot; @becker2025metr;
@bean2026llmmedical], but randomise *people or tasks*, which presumes no interference
between units. A memory store shared by a fleet violates that presumption.

### 8.3 Online controlled experiments

**Randomise, then check the randomisation.** The online-experimentation literature
[@kohavi2020trustworthy; @kohavi2009controlled] is the standard reference for randomised
experiments on live systems (cited for that role, not for a specific prescription);
Fabijan et al. [@fabijan2019srm] describe sample ratio mismatch as an indicator of
data-quality problems. Our analogues are the registered assignment
script with its committed hash and the positive (11/11) and dual negative (8/8) controls of
§4.0.1b. The sham replay, the placebo-like specificity control, was **not executed**: the
configuration launched was invalid, and a valid one awaits data that exist only on the
production host (§4.0.1c). We used no covariate variance reduction [@deng2013cuped] and did
not interleave [@radlinski2008clickthrough; @chapelle2012interleaved; @hofmann2016online],
for which Hofmann et al. report one to two orders of magnitude more sensitivity than
absolute metrics; we have no per-item credit signal to interleave on.

**Why the unit is the epoch.** When units share state, per-unit randomisation is biased;
this is the problem around which marketplace [@blake2014marketplace; @johari2022twosided] and
network [@saveski2017network; @aronow2017interference] experimentation are built. The
switchback remedy randomises the whole system over time
[@bojinov2023switchback; @hu2022switchback; @basse2023minimax] and comes with
randomisation-based inference [@bojinov2019timeseries]. Ours is a fleet-level switchback
with 24 h epochs and a two-hour washout. Unlike that literature, we fixed the washout ex
ante instead of estimating the carryover order; we have 20 periods; and a memory store
accumulates, so carryover through *state* may outlast any fixed washout. We claim the
relation, not that these theorems apply to our state process.

**Few clusters.** Our percentile cluster bootstrap runs on 9–11 clusters per arm, the
regime in which ordinary cluster bootstraps over-reject [@cameron2008bootstrap], perform
"poorly with fewer than eleven clusters" [@webb2014reworking], and for which a six-point
wild bootstrap is recommended [@cameron2015practitioner]. We used none of these. The
registered re-randomisation test (§4.0.2) is the finite-sample alternative (a Fisher
randomisation test [@imbens2015causal; @bojinov2019timeseries]) and the inference to
weight where the two disagree, as on H1a.

**Under-power and counterfactual logging.** Across twenty-five large field experiments,
"the median confidence interval on return on investment is over 100 percentage points
wide" [@lewis2015unfavorable]. Ours is a *weaker* case: they were under-powered by the
economics of the outcome, we by a registration whose sample size ignored a 30-day
eligibility window (§3.0.1). Observational comparison is not the remedy: observational methods often fail to recover the
effects measured in the same advertising experiments [@gordon2019comparison]. Our replay analyses belong to the family of Li et al.
[@li2011unbiased], and the closest analogue of our sham is ghost-ads logging of the
exposures the treatment *would* have produced [@johnson2017ghost]: in both, the
counterfactual is only as good as the state it is computed from, which is exactly where
our sham configuration failed (§4.0.1c).

### 8.4 Pre-registration, and what a null is worth

Pre-registration in ML and NLP has been piloted, not adopted: the NeurIPS 2020 and 2021
workshops [@bertinetto2020prereg; @albanie2022prereg] ran registered-report-style review
(the 2021 preface reports 22 proposals, 10 accepted and 3 results papers); it has been argued for in NLP [@vanmiltenburg2021prereg],
weighed against its costs [@sogaard2023twosided] and adapted to predictive modelling
[@hofman2023prereg]. Vaccaro [@vaccaro2026prereg] lists **memory settings** among the
researcher degrees of freedom of experiments with AI agents (agents as subjects, so the
fit is by analogy), and Wilder and Zhou [@wilder2025evaluation] propose that ML venues
require a declaration of preregistration for field experiments. In IR, a Dagstuhl report
[@bauer2023dagstuhl] recommends results-blind review. The only memory-specific
pre-registered design we found is Feng et al.'s, on benchmarks. This trial is a
*registration*, **not a registered report** (its protocol was never peer-reviewed before
data), and its deviations are in Appendix A. The cross-field arguments
[@nosek2018prereg; @chambers2022registeredreports; @munafo2017manifesto] are the standing
justification. Registration changes what gets reported: 17 of 30 large NHLBI trials before
2000 reported significant benefit, against 2 of 25 after mandatory prospective registration
of outcomes [@kaplan2015nullnhlbi].

**Power language needs care.** The critiques of low power [@ioannidis2005false;
@button2013power; @gelman2014beyond] and of post-experiment power calculations
[@hoenig2001abuse] apply here; Hoenig and Heisey also call power calculations "valuable in
planning an experiment". Our saturated minimum detectable effect is **prospective and
outcome-independent**, which is the planning form, but its inputs are the problem: the ICC was
estimated for a different quantity (§4.1.1). The choice of significance test is known to
change error rates on IR test collections [@urbano2019significance]; we know of no
corresponding analysis for live retrieval experiments.

### 8.5 Position

**Not new:** that memory evaluation scores systems rather than behavioural effect;
randomising a retrieval-side lever with known propensities; the switchback design and its
inference; pre-registering ML experiments. **What this trial is:** a pre-registered,
beacon-seeded, fleet-level switchback on live agent traffic, with per-brief provenance,
instrument controls, and a null reported with its power failure and its own
contradictions. **What it is not:** it does not identify per-memory utility, randomise
within a brief, estimate carryover or measure cost; it compares two policies, not memory
against none; it is one system on one fleet; and its specificity control has not been run
(§4.0.1c). **What it adds, narrowly:** a live-traffic instance of the positivity failure
CMP formalises (§3.0.1), and a registration whose sample size and estimand each looked
complete alone and contradicted each other. **What would falsify this positioning:** a
pre-registered randomised memory trial on live traffic published before ours. A bounded
search (web and arXiv, 2026-10-03/04, one agent, not a systematic review) found none, nor
an IR registered-report track.

*Reading depth.* Full or partial text was read for the TMLR survey (§9.6, with string
counts on the pinned PDF), Omri et al., Evo-Memory, Behnam & Wang, Feng et al., the
NeurIPS 2021 preface, Søgaard et al., Vaccaro and the Dagstuhl report. MemoryArena v2 was
only string-searched. No book was opened, and several items are known at abstract or
metadata level and are cited for their topic, not for a finding. Per-reference record:
`_sprint-2026-10-04/B-related-work.verification-log.md`; long form of this section:
`_sprint-2026-10-04/B-related-work.md`.

---

## 9. Discussion

In short, this trial **could not have detected its own effect**, and
we knew this ten days before the window closed and wrote it down rather than
discovering it afterwards. What remains is not an effect estimate but three observations
about instruments, each of which cost us a published error to find:

**A pre-registration can contradict itself, and the contradiction can survive to the
outcome.** It happened twice here, at two scales. Two locks three weeks apart defined one
estimand incompatibly (§4.4), and neither review caught it. And the sample size was
computed for 234 epochs while the intervention it would act on had a 30-day life:
**8.5% of the registered design** (§3.0.1). The second is the more instructive, because
each number is correct in isolation: `sizing.py` did its arithmetic faithfully, and the
30-day window is a documented default. Neither document was wrong; they were never read
against each other. The failure mode is not a missing lock but two locks that each
look complete alone, with no step in the process whose job is to cross them.

**An interval that excludes zero can be the artifact, and the null the sound result.** The
only significance this trial produced is on the hypothesis previously ruled out as
requiring a 955% effect. Reading the significant line and ignoring the null one would have
inverted the paper.

**A pre-committed alternative explanation can be refuted by the data it was written to
protect.** The concentration projection that made a null ambiguous did not hold; coverage
was flat. That weakens a defence we had reserved for ourselves, which is the only
circumstance in which a pre-commitment demonstrably did its job.

We publish an under-powered null in full because the two alternatives (not publishing, or
publishing a claim the design cannot support) are the behaviours that make under-powered
trials worth less than nothing to the people who read them.

---

## References

Citations in §8 are pandoc-style (`[@key]`) and resolve in `_sprint-2026-10-04/B-related-work.bib`,
which carries the full author lists, URLs and the per-entry notes on what is not established
(venue, publication status). The list below is generated from that file for the keys cited
here; where the two differ, the `.bib` file is authoritative. Reading depth per reference is
in `_sprint-2026-10-04/B-related-work.verification-log.md`. Artifacts of this study are cited
by file name in the text and listed in Appendix B.

- Albanie, S. et al. (eds.) (2022). Proceedings of the NeurIPS 2021 Workshop on Pre-registration in Machine Learning. https://proceedings.mlr.press/v181/. `[@albanie2022prereg]`
- Aronow, P. M. and Samii, C. (2017). Estimating average causal effects under general interference, with application to a social network experiment. *The Annals of Applied Statistics* 11(4). doi:10.1214/16-AOAS1005. `[@aronow2017interference]`
- Basse, G., Ding, Y. and Toulis, P. (2023). Minimax designs for causal effects in temporal experiments with treatment habituation. *Biometrika* 110: 155–168. doi:10.1093/biomet/asac024. `[@basse2023minimax]`
- Bauer, C. et al. (2023). Report from Dagstuhl Seminar 23031: Frontiers of Information Access Experimentation for Research and Education. *Dagstuhl Reports* 13(1): 68–154. doi:10.4230/DagRep.13.1.68. `[@bauer2023dagstuhl]`
- Bean, A. M. et al. (2026). Reliability of LLMs as medical assistants for the general public: a randomized preregistered study. *Nature Medicine* 32(2): 609–615. doi:10.1038/s41591-025-04074-y. `[@bean2026llmmedical]`
- Becker, J. et al. (2025). Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity. arXiv preprint. arXiv:2507.09089. `[@becker2025metr]`
- Behnam, A. and Wang, B. (2026). Causal Memory Policy: Making Memory Utility Identifiable by Intervening on Retrieval. arXiv preprint. arXiv:2610.02070. `[@behnam2026cmp]`
- Bertinetto, L. et al. (2020). The pre-registration experiment: an alternative publication model for machine learning research. *NeurIPS 2020 Workshop*. https://neurips.cc/virtual/2020/workshop/16158. `[@bertinetto2020prereg]`
- Blake, T. and Coey, D. (2014). Why marketplace experimentation is harder than it seems: the role of test-control interference. *Proceedings of the Fifteenth ACM Conference on Economics and Computation*: 567–582. doi:10.1145/2600057.2602837. `[@blake2014marketplace]`
- Bojinov, I. and Shephard, N. (2019). Time Series Experiments and Causal Estimands: Exact Randomization Tests and Trading. *Journal of the American Statistical Association* 114(528): 1665–1682. doi:10.1080/01621459.2018.1527225. `[@bojinov2019timeseries]`
- Bojinov, I., Simchi-Levi, D. and Zhao, J. (2023). Design and Analysis of Switchback Experiments. *Management Science* 69(7): 3759–3777. doi:10.1287/mnsc.2022.4583. `[@bojinov2023switchback]`
- Button, K. S. et al. (2013). Power failure: why small sample size undermines the reliability of neuroscience. *Nature Reviews Neuroscience* 14(5): 365–376. doi:10.1038/nrn3475. `[@button2013power]`
- Cameron, A. C., Gelbach, J. B. and Miller, D. L. (2008). Bootstrap-Based Improvements for Inference with Clustered Errors. *The Review of Economics and Statistics* 90(3): 414–427. doi:10.1162/rest.90.3.414. `[@cameron2008bootstrap]`
- Cameron, A. C. and Miller, D. L. (2015). A Practitioner's Guide to Cluster-Robust Inference. *Journal of Human Resources* 50(2): 317–372. doi:10.3368/jhr.50.2.317. `[@cameron2015practitioner]`
- Chambers, C. D. and Tzavella, L. (2022). The past, present and future of Registered Reports. *Nature Human Behaviour* 6(1): 29–42. doi:10.1038/s41562-021-01193-7. `[@chambers2022registeredreports]`
- Chapelle, O. et al. (2012). Large-scale validation and analysis of interleaved search evaluation. *ACM Transactions on Information Systems* 30(1): 1–41. doi:10.1145/2094072.2094078. `[@chapelle2012interleaved]`
- Deng, A. et al. (2013). Improving the sensitivity of online controlled experiments by utilizing pre-experiment data. *Proceedings of the Sixth ACM International Conference on Web Search and Data Mining*: 123–132. doi:10.1145/2433396.2433413. `[@deng2013cuped]`
- Du, P. (2026). Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers. arXiv preprint. arXiv:2603.07670. `[@du2026memoryautonomous]`
- Fabijan, A. et al. (2019). Diagnosing Sample Ratio Mismatch in Online Controlled Experiments. *Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining*: 2156–2164. doi:10.1145/3292500.3330722. `[@fabijan2019srm]`
- Feng, Z., Yao, M. and Lewis, D. S. (2026). Memory Transplants for LLM Agents: Disentangling Architecture and Content Transfer under a Code-to-Math Shift. *ICLR 2026 Workshop on Memory for LLM-Based Agentic Systems (MemAgents)*. https://openreview.net/forum?id=AIJsjIqfsp. `[@feng2026memorytransplants]`
- Gelman, A. and Carlin, J. (2014). Beyond Power Calculations: Assessing Type S (Sign) and Type M (Magnitude) Errors. *Perspectives on Psychological Science* 9(6): 641–651. doi:10.1177/1745691614551642. `[@gelman2014beyond]`
- Gordon, B. R. et al. (2019). A Comparison of Approaches to Advertising Measurement: Evidence from Big Field Experiments at Facebook. *Marketing Science* 38(2): 193–225. doi:10.1287/mksc.2018.1135. `[@gordon2019comparison]`
- He, Z. et al. (2026). MemoryArena: Benchmarking Agent Memory in Interdependent Multi-Session Agentic Tasks. arXiv preprint. arXiv:2602.16313. `[@he2026memoryarena]`
- Hoenig, J. M. and Heisey, D. M. (2001). The Abuse of Power: The Pervasive Fallacy of Power Calculations for Data Analysis. *The American Statistician* 55(1): 19–24. doi:10.1198/000313001300339897. `[@hoenig2001abuse]`
- Hofman, J. M. et al. (2023). Pre-registration for Predictive Modeling. arXiv preprint. arXiv:2311.18807. `[@hofman2023prereg]`
- Hofmann, K., Li, L. and Radlinski, F. (2016). Online Evaluation for Information Retrieval. *Foundations and Trends in Information Retrieval* 10(1): 1–117. doi:10.1561/1500000051. `[@hofmann2016online]`
- Hu, Y. and Wager, S. (2022). Switchback Experiments under Geometric Mixing. arXiv preprint. arXiv:2209.00197. `[@hu2022switchback]`
- Hu, Y. et al. (2025). Memory in the Age of AI Agents. arXiv preprint. arXiv:2512.13564. `[@hu2025memoryage]`
- Hu, Y., Wang, Y. and McAuley, J. (2025). Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions. arXiv preprint. arXiv:2507.05257. `[@hu2025memoryagentbench]`
- Huang, W. et al. (2026). A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents. *Transactions on Machine Learning Research*. arXiv:2602.06052. `[@huang2026survey]`
- Imbens, G. W. and Rubin, D. B. (2015). Causal Inference for Statistics, Social, and Biomedical Sciences: An Introduction. *Cambridge University Press*. doi:10.1017/CBO9781139025751. `[@imbens2015causal]`
- Ioannidis, J. P. A. (2005). Why Most Published Research Findings Are False. *PLoS Medicine* 2(8): e124. doi:10.1371/journal.pmed.0020124. `[@ioannidis2005false]`
- Johari, R. et al. (2022). Experimental Design in Two-Sided Platforms: An Analysis of Bias. *Management Science* 68(10): 7069–7089. doi:10.1287/mnsc.2021.4247. `[@johari2022twosided]`
- Johnson, G. A., Lewis, R. A. and Nubbemeyer, E. I. (2017). Ghost Ads: Improving the Economics of Measuring Online Ad Effectiveness. *Journal of Marketing Research* 54(6): 867–884. doi:10.1509/jmr.15.0297. `[@johnson2017ghost]`
- Kaplan, R. M. and Irvin, V. L. (2015). Likelihood of Null Effects of Large NHLBI Clinical Trials Has Increased over Time. *PLOS ONE* 10(8): e0132382. doi:10.1371/journal.pone.0132382. `[@kaplan2015nullnhlbi]`
- Kohavi, R. et al. (2009). Controlled experiments on the web: survey and practical guide. *Data Mining and Knowledge Discovery* 18(1): 140–181. doi:10.1007/s10618-008-0114-1. `[@kohavi2009controlled]`
- Kohavi, R., Tang, D. and Xu, Y. (2020). Trustworthy Online Controlled Experiments: A Practical Guide to A/B Testing. *Cambridge University Press*. doi:10.1017/9781108653985. `[@kohavi2020trustworthy]`
- Lewis, R. A. and Rao, J. M. (2015). The Unfavorable Economics of Measuring the Returns to Advertising. *The Quarterly Journal of Economics* 130(4): 1941–1973. doi:10.1093/qje/qjv023. `[@lewis2015unfavorable]`
- Li, L. et al. (2011). Unbiased offline evaluation of contextual-bandit-based news article recommendation algorithms. *Proceedings of the Fourth ACM International Conference on Web Search and Data Mining*: 297–306. doi:10.1145/1935826.1935878. `[@li2011unbiased]`
- Maharana, A. et al. (2024). Evaluating Very Long-Term Conversational Memory of LLM Agents. *Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*: 13851–13870. doi:10.18653/v1/2024.acl-long.747. `[@maharana2024locomo]`
- Munafò, M. R. et al. (2017). A manifesto for reproducible science. *Nature Human Behaviour* 1(1): 0021. doi:10.1038/s41562-016-0021. `[@munafo2017manifesto]`
- Nosek, B. A. et al. (2018). The preregistration revolution. *Proceedings of the National Academy of Sciences* 115(11): 2600–2606. doi:10.1073/pnas.1708274114. `[@nosek2018prereg]`
- Omri, Y. et al. (2026). Agent Memory: Characterization and System Implications of Stateful Long-Horizon Workloads. arXiv preprint. arXiv:2606.06448. `[@omri2026agentmemory]`
- Peng, S. et al. (2023). The Impact of AI on Developer Productivity: Evidence from GitHub Copilot. arXiv preprint. arXiv:2302.06590. `[@peng2023copilot]`
- Radlinski, F., Kurup, M. and Joachims, T. (2008). How does clickthrough data reflect retrieval quality? *Proceedings of the 17th ACM Conference on Information and Knowledge Management*: 43–52. doi:10.1145/1458082.1458092. `[@radlinski2008clickthrough]`
- Saveski, M. et al. (2017). Detecting Network Effects: Randomizing Over Randomized Experiments. *Proceedings of the 23rd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*: 1027–1035. doi:10.1145/3097983.3098192. `[@saveski2017network]`
- Søgaard, A., Hershcovich, D. and de Lhoneux, M. (2023). A Two-Sided Discussion of Preregistration of NLP Research. *Proceedings of the 17th Conference of the European Chapter of the Association for Computational Linguistics*. doi:10.18653/v1/2023.eacl-main.6. `[@sogaard2023twosided]`
- Srivastava, S. S. (2026). Causal Intervention-Based Memory Selection for Long-Horizon LLM Agents. arXiv preprint. arXiv:2605.17641. `[@srivastava2026cmi]`
- Sun, L., Zhang, H. and Zhang, X. (2026). External Experience Serving in Production LLM Systems: A Deployment-Oriented Study of Quality-Cost Trade-offs. arXiv preprint. arXiv:2606.11806. `[@sun2026experienceserving]`
- Tablan, V., Taylor, S. and Bernhem, K. (2026). Learning on the Job: Continual Learning from Deployment Feedback for Frozen-Weights Agents. arXiv preprint. arXiv:2607.22157. `[@tablan2026learningonthejob]`
- Urbano, J., Lima, H. and Hanjalic, A. (2019). Statistical Significance Testing in Information Retrieval: An Empirical Analysis of Type I, Type II and Type III Errors. *Proceedings of the 42nd International ACM SIGIR Conference on Research and Development in Information Retrieval*: 505–514. doi:10.1145/3331184.3331259. `[@urbano2019significance]`
- Vaccaro, M. (2026). Preregistration for Experiments with AI Agents. arXiv preprint. arXiv:2606.11217. `[@vaccaro2026prereg]`
- van Miltenburg, E., van der Lee, C. and Krahmer, E. (2021). Preregistering NLP research. *Proceedings of the 2021 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies*. doi:10.18653/v1/2021.naacl-main.51. `[@vanmiltenburg2021prereg]`
- Webb, M. D. (2014). Reworking Wild Bootstrap Based Inference for Clustered Errors. *Queen's University, Department of Economics*, Queen's Economics Department Working Paper 1315. http://qed.econ.queensu.ca/working_papers/papers/qed_wp_1315.pdf. `[@webb2014reworking]`
- Wei, T. et al. (2025). Evo-Memory: Benchmarking LLM Agent Test-time Learning with Self-Evolving Memory. arXiv preprint. arXiv:2511.20857. `[@wei2025evomemory]`
- Wilder, B. and Zhou, A. (2025). Fostering the Ecosystem of AI for Social Impact Requires Expanding and Strengthening Evaluation Standards. arXiv preprint. arXiv:2510.18238. `[@wilder2025evaluation]`
- Wu, D. et al. (2025). LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. arXiv preprint. arXiv:2410.10813. `[@wu2025longmemeval]`
- Xiong, Z. et al. (2025). How Memory Management Impacts LLM Agents: An Empirical Study of Experience-Following Behavior. arXiv preprint. arXiv:2505.16067. `[@xiong2025memorymanagement]`
- Zhang, Z. et al. (2024). A Survey on the Memory Mechanism of Large Language Model based Agents. arXiv preprint. arXiv:2404.13501. `[@zhang2024memorysurvey]`
- Zheng, J. et al. (2025). LifelongAgentBench: Evaluating LLM Agents as Lifelong Learners. arXiv preprint. arXiv:2505.11942. `[@zheng2025lifelongagentbench]`
- Zou, H. P. et al. (2026). When Users Change Their Mind: Evaluating Interruptible Agents in Long-Horizon Web Navigation. arXiv preprint. arXiv:2604.00892. `[@zou2026interruptbench]`

---

## Appendix A: relation to the pre-registration

Deviations are logged in `DEVIATIONS-FOR-PAPER.md`, which is append-only, and the
substantive ones for this paper are §10.29 through §10.34. The list is not summarized here
because a summary of a deviation log is a second copy that will diverge from the first.

Three that a reader cannot reconstruct from the estimates alone:

- the analysis stratum migrated from `S2` to `≥ S1` by panel agreement (κ 0.87–0.93 at
  `≥ S1` against 0.31–0.53 for the S1/S2 split), so the S1/S2 division became an
  instrument finding rather than an analysis boundary;
- the dose band `{2 · 4 · 7.5}` was registered among *"what does not move, and could not"*
  and **moves**: 11/15/17 states of 350, monotone, saturating in `(4.0; 4.4]`. The
  registration promises **less** than what was measured;
- the designation was recorded as an open defect in v1.12 and was **closed** on 2026-08-26.

The two items where the registration promises *less* are the ones that matter, because
nobody corrects unprompted an error that favours them.

## Appendix B: artifacts

| artifact | holds |
|---|---|
| `ITT-2026-09-21.json` | the estimates, both legs, bootstrap parameters |
| `ITEM7-DOSE-TOPO-2026-09-21.json` | the full 2 000-seed distribution of §4.7 |
| `ASSIGNMENT.json` · `ASSIGNMENT-SERVING.json` | designation and served arms |
| `DESIGNATION-2026-08-26.json` | the 19 designated chunks |
| `estimador_itt.py` · `assign_arms.py` · `pilot_replay.py` | the instruments |
| `p2-serving.ndjson` · `episodios-ensaio-20260921.jsonl` | serving log and episodes |
| `ensaio-20260921-PRIMARIO-3fam.jsonl` | 3 592 verdicts, three families |
| `ensaio-20260921-SENSIB-deepseek.jsonl` | 1 195 verdicts, fourth family (sensitivity) |
| `COBERTURA-M10-2026-09-21.json` · `cobertura_e_m10.py` | coverage by arm, per-signature share, M10 and its four legs |
| `RERANDOMIZACAO-2026-09-21.json` · `rerandomizacao.py` | the registered sharp-null test, 10 000 redesigns (§4.0.1a, §4.0.2) |
| `CONTROLES-JANELA-COMPLETA-2026-09-21.json` · `controles_instrumento.py` | instrument controls over all 20 epochs (§4.0.1b) |
| `out/CONTROLES-2026-09-10.json` | the same controls at the trial's midpoint — 6/6 and 3/3, superseded by the row above |
| `out/H1C-POWER-REALIZADO-2026-09-10.json` | the MDE saturation of §4.1, computed before the window closed |
| `out/H1C-POWER-FRACIONARIA-2026-09-10.json` · `out/H1C-POWER-SEM-0903-2026-09-10.json` | the two other inclusion cuts of the power margin (§4.1.1) |
| `out/expiracao-designados-2026-09-09.json` | the designation's expiry measurement of §3.0.1 — `created_at` and the 30-day window |
| `MANIFESTO-LASTRO-P2.json` | sha256 of every artifact above, for loss detection — **caveat: except the rows marked † below** (2026-10-04) |
| † `ITT-SENSIB-PRECOMPROMETIDA.json` (sha256 `0191ee54…`) | the **pre-committed** sensitivity leg (§9.1 of the spec: all partials removed) — source of the pre-committed rows of §4.1, §4.2, §4.3 and of Figure B1(b). Not in the manifest, and not listed here before v2 |
| † `out/NOGO-replay-sonda{2,3}-2026-09-23.json` · `out/NOGO-replay-ts-com-alteracao-2026-09-23.txt` | the two replay probes of §4.0.1c and the 132 states they replayed |
| † `_sprint-2026-10-04/B-replay-fidelity/` (8 runs, 2 stratum files, `RESUMO.txt`) · `measurement/sprint-replay-estratos.mjs` · `measurement/sprint-replay-fidelidade-resumo.py` | the corpus × cut replay test and the stratum structure of §4.0.1c; the summary script recomputes every number from the runs |
| † `measurement/sprint-figB-h1a-inversao.py` · `measurement/sprint-figB-sementes-dose-topo.py` · `_sprint-2026-10-04/figures/` | Figures B1 and B2 (SVG + PNG + `.run.json`), regenerated from the artifacts above; each script aborts if its plotted values diverge from the locked JSON |
| † `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` · `measurement/sprint-figB-item7-crosscheck.py` | an independent 20 000-seed redraw with a declared seed recipe, corroborating §4.7 within Monte-Carlo error; not a reproduction of the 2 000-seed run, whose seed recipe was not recorded |

### B.1 Where each number in the text comes from

Added 2026-09-21 after an adversarial reviewer observed that the header promised universal
traceability and several numbers had no artifact named beside them. **That review was
right, and understated: two of them had no artifact at all**: the coverage figures and
the whole of M10 were computed by an ad-hoc script and never saved. `cobertura_e_m10.py`
now produces them, and reproduces the ad-hoc values exactly.

| number | §  | artifact |
|---|---|---|
| H1, H1a, H1c and every interval | 4.1–4.3 | `ITT-2026-09-21.json` — except the pre-committed legs: |
| pre-committed sensitivity of H1c, H1a and H1; session-hours 12.16 / 4.08 | 4.1–4.3 | `ITT-SENSIB-PRECOMPROMETIDA.json`, field `sensibilidade` (added 2026-10-04) |
| session-hours per arm, opportunities, repeats | 4.2 | idem |
| 7.13 h at `09-14`; session `d37a5964…`, 3 episodes, span 6.33 h; 74/65/56 episodes | 4.2 | `episodios-ensaio-20260921.jsonl` |
| coverage 27.98% / 26.92%; 4 324 occurrences; 19/19 signatures at ≈5.3% | 4.5 | `COBERTURA-M10-2026-09-21.json` |
| the fabricated 139 650 that `boost_by_id` would yield | 4.5 | idem, field `nota_boost` |
| `r` and all four legs; −0.0521 against dose | 4.6 | idem, field `M10` |
| truncation/chance split, 2 000 seeds | 4.7 | `ITEM7-DOSE-TOPO-2026-09-21.json` |
| Monte-Carlo s.e. 0.035 of the conditional mean; signed shares −1.0% / +101.0% | 4.7 | computed from the histogram in `ITEM7-DOSE-TOPO-2026-09-21.json`; recorded in `_sprint-2026-10-04/figures/figB2-sementes-dose-topo.run.json` |
| `control` conditional mean 9.991 | 4.7 | **no artifact** — `DEVIATIONS-FOR-PAPER.md` only; corroborated (10.0124 ± 0.0146) by `_sprint-2026-10-04/figures/figB2-item7-crosscheck-20000.json` |
| spans 9.71 / 8.86 / 8.03 min of the three busiest `09-14` sessions | 4.2 | `episodios-ensaio-20260921.jsonl`; recorded in `_sprint-2026-10-04/figures/figB1-h1a-inversao.run.json` |
| every number of §4.0.1c (0/132; 22/22; 17/22; strata; pool 108 / 115) | 4.0.1c | `_sprint-2026-10-04/B-replay-fidelity/RESUMO.txt` and the runs beside it; 11.9 and 1.5 × 10⁻¹⁰ are hypergeometric arithmetic on those counts (`B-replay-fidelity.md` §4) |
| agreement 1 111/1 145; abstentions 26+6+1 / 13 / 11; gains 20, losses 28 | 6 | `ensaio-20260921-*.jsonl`, recomputed in `DEVIATIONS-FOR-PAPER.md` §10.31 |
| 20 designated, 19 served, 16+3+1 | 3 | `ASSIGNMENT-SERVING.json` + `p2-serving.ndjson` |

**Caveat.** Several of these are **outside the repository** and several are large.
`scripts/manifesto-lastro-p2.py` hashes all 14 (154 MiB) and
`scripts/backup-lastro-p2.sh` copies them with the hash recomputed **at the destination**.
**Done: both legs now verified at the destination** (2026-09-22 01:48Z): local **12/12**,
off-machine **12/12** on a host that is not the one that served the trial: it has no
`/root/.openclaw`, its epoch pointer is frozen at 2026-08-23, and it already holds Paper
1's ballast. Identified by **capability, never by address**. A manifest proves the bytes
are the bytes; it does not prove a copy exists, which is why the copy is verified
separately and carries a dated receipt.

---

## Working list: struck in the commit that closes it

1. ~~**Ballast**: manifest + two verified copies~~ → **Done, 2026-09-22**: 17 artifacts,
   154 MiB, **both legs 12/12 recomputed at the destination**. Three defects of ours found
   and fixed along the way: a directory hash reimplemented in shell that diverged by one
   trailing newline, an `rsync` that ran *before* the check and so restored the corrupted
   byte it was meant to detect, and an `ssh` inside a `while read` that ate the loop's
   stdin and verified **1 of 12** while reporting "0 divergem".
   **Caveat (2026-10-04):** the manifest does not cover `ITT-SENSIB-PRECOMPROMETIDA.json`, the
   only source of the pre-committed rows of §4.1–4.3, so a published number rests on an
   artifact the ballast does not protect. Open as item 10.
2. ~~**Run the registered re-randomization**~~ → **Done, 2026-09-21** (§4.0.1a, §4.0.2):
   10 000 redesigns, 9 941 distinct patterns, control of 300/300 reproducing the spec. It
   **disagrees with the bootstrap on H1a**, and `H1` is now reported as an unexplained
   rejection.
3. ~~**Report the pre-committed instrument controls**~~ → **Done, two of three, 2026-09-21**
   (§4.0.1b): positive **11/11**, negative dual **8/8**, both re-measured over the full
   window. ~~**Critical.** **Still open: the sham replay**, which needs the serving code re-executed;
   our attempt to do it by counting over the log was invalid and is recorded as such.~~
   **Correction (2026-10-04): the sham was not executed** (§4.0.1c). The run launched on 2026-09-22
   produced no output, and its configuration was invalid: wrong corpus, inclusive cut,
   shams drawn from the 115-pool instead of the 108-pool. On the served corpus with the
   exact cut, the replay reproduces production 22/22 and responds to dose. Still open as
   item 9.
4. ~~**Measure the 30-day freshness question**~~ → **Done, 2026-09-21** (§3.0.1):
   `N = 234` **was** infeasible: the designation expires 2026-09-20 22:51:23, giving 20
   eligible epochs of 234. §9 *(numbered §8 before v2)* rewritten around it.
5. ~~**Adversarial review** of this manuscript~~ → **Done, 2026-09-21**: five families
   launched, **four delivered with `exit: 0` receipts** (DeepSeek, Grok, GLM on this paper;
   Kimi on Paper A). Their findings produced §1.1, §3.0, §3.0.1, §4.0.1, §4.0.2, §4.1.1,
   §4.4.1, Appendix B.1 and the corrections in §3.1, §4.1–4.5. The fifth (Codex) returned a
   parecer whose citations do not resolve against the file and is recorded as invalid in
   `REVISAO-ADVERSARIAL-2026-09-21.md`; a review that cites sections the document does not
   have is not evidence about the document.
6. ~~**Figures**: the H1a sensitivity (the single-epoch inversion) and the §4.7 seed
   distribution. Both derive from locked artifacts.~~ → **Done, 2026-10-04**: Figure B1
   (§4.2) and Figure B2 (§4.7), each generated by a script that aborts if its values
   diverge from the locked artifacts. Making them surfaced four corrections to the text
   (§4.2 pre-committed leg; "8 to 10 minutes"; the signed truncation share; the unresolved
   sign of +0.023); see the changelog. **Caveat.** The headline embedded in the B1 SVG still reads
   *"H1a turns on one epoch"*; regenerate it with the caption title of §4.2 (item 11).
7. ~~**Related work** — Paper A's §8 covers the surface literature, not trials of memory
   interventions.~~ → **Done, 2026-10-04**: §8, condensed (~2 000 words) from
   `_sprint-2026-10-04/B-related-work.md` (~4 100 words), with references resolving in
   `B-related-work.bib`. Before submission: re-check Behnam & Wang (arXiv 2610.02070,
   1 Oct 2026, not peer-reviewed) for a revised version, and re-read MemoryArena v2 in
   full.
8. **Deposit** as a new version of the registration, declaring the deviations **and** the
   result in one record. Blocked by 1 (off-machine), 2 and 3 *(the open part of 3 is now item 9)*.
9. **Valid sham**: needs the trial `brief_log` 2026-09-08..09-20 from the production host
   (authorization pending). Everything else for it is in hand: served corpus, `rowid`
   cut, shams redrawn from the 108-pool (89 non-designated). `gera-shams.py` /
   `roda-sham.sh` must first be fixed, since both hard-code the preserved corpus and
   `--corte inclusivo` (§4.0.1c).
10. **Ballast gap**: add `ITT-SENSIB-PRECOMPROMETIDA.json` and the artifacts marked † in
    Appendix B to `MANIFESTO-LASTRO-P2.json` and to both verified copies.
11. **Traceability of §4.7 and Figure B1**: save the `control` distribution (the 9.991)
    and the seed recipe of the 2 000-seed run in an artifact, or cite the 20 000-seed
    crosscheck instead; regenerate the B1 SVG headline.

**Caveat.** Items 2 and 3 are **registered analyses that were not run**, not enhancements. A
manuscript that omits its own pre-registered inference test and its own instrument
controls is not ready, and the fact that three adversarial reviewers had to tell us is
itself the §6 pattern repeating on this document.

---

## Changelog: v2 (2026-10-04)

Prepared from `MANUSCRIPT-B.md` as of 2026-10-03, in `_sprint-2026-10-04/B-v2.md`; the
original is untouched. Every content change below traces to a sprint report with its
artifacts; old text that was wrong is kept struck through beside its correction, as this
manuscript already does.

**Sham / replay fidelity** (source: `_sprint-2026-10-04/B-replay-fidelity.md` and
`B-replay-fidelity/`):

1. §4.0.1b table, specificity row: "running since 2026-09-22 01:40Z" struck → "not
   executed; the configuration launched was invalid; a valid one is runnable and not yet
   run".
2. §4.0.1b: the "It is now running" paragraph struck, with a correction note; the
   bullets on the 30-day pool and on the "two routes, one number" control annotated: both
   routes read the same, wrong corpus, so their agreement could not catch it (served pool
   108, not 115).
3. §4.0.1b limitation: the sentence calling `corpus-preservado-20260908.db` "the
   deliberately preserved corpus of the trial" struck and corrected: it is not the corpus
   that served (60 `memory/lessons.md` chunks re-ingested 2026-09-07 that production never
   had; served corpus = fd-recovered `e20260903`).
4. New §4.0.1c. The "no power by construction / `p = 1.0`" reading of 2026-09-23 is
   presented as superseded: the tie hypothesis is **refuted**. The zero came from (1) the
   wrong corpus and (2) the inclusive cut. With the served corpus and the `rowid` cut, the
   replay reproduces production 22/22 and responds to dose: 17/22 states at `w = 2`, 22/22
   at `w = 100 000`. Also declared: `gera-shams.py` drew from the 115-pool rather than the
   108-pool (a prediction of spurious "failed specificity", not a measurement). A valid sham
   is runnable and **not run**: it needs the trial `brief_log` after 2026-09-08, which
   exists only on the production host. Measured: 22 states, all in epoch `09-01`. Not
   measured: 110 of 132.
5. Working list item 3 updated; new item 9 (valid sham, authorization pending).

**Figures** (source: `phase2-inputs/B-figures.json`, `_sprint-2026-10-04/figures/`):

6. Figure B1 inserted in §4.2 and Figure B2 in §4.7, with captions, as relative links
   `figures/*.svg` from this file's location.
7. §4.2: the **pre-committed** sensitivity leg (`ITT-SENSIB-PRECOMPROMETIDA.json`: H1a
   −133.34, CI [−203.62; +7.41], contains zero; session-hours 12.16 / 4.08) is added and
   reported before the post-hoc leg, per §4.1's own rule. The section title "inverts its
   conclusion on one epoch" is replaced by "excludes zero only on the locked leg", and the
   abstract sentence is corrected to match. The B1 caption title is written to agree; the
   headline embedded in the SVG does not yet (item 11).
8. §4.3: H1's pre-committed leg added (−15.59, CI [−22.43; −4.05], excludes zero). Same
   artifact, same omission; no conclusion changes.
9. §4.2: "9 to 10 minutes" → "8 to 10 minutes" (measured 9.71 / 8.86 / 8.03 min).
10. §4.7: truncation share "1.0%" → "−1.0%" (the unsigned shares summed to 102%); "+0.023 …
    in the direction opposite to the intuition" → the sign is not resolved (0.7 MC s.e.;
    20 000-seed redraw gives −0.007 ± 0.011); notes that the `control` 9.991 has no
    artifact, that the 2 000-seed recipe was not recorded, and that `P(n = 1) = 10.15%`
    carries ≈0.7 pp of MC noise.
11. Appendix B: rows for `ITT-SENSIB-PRECOMPROMETIDA.json`, the replay probes, the
    replay-fidelity runs, the figure scripts and the 20 000-seed crosscheck, marked † as
    not covered by `MANIFESTO-LASTRO-P2.json`. B.1: rows for the pre-committed legs, the
    §4.7 MC numbers, the 9.991 (declared as having no artifact), the session spans and
    §4.0.1c. Working list: items 10 and 11 added; item 1 annotated.

**Related work** (source: `_sprint-2026-10-04/B-related-work.md`, `.bib`, verification
log):

12. New §8 "Related work" (~2 000 words), condensed from the ~4 100-word draft. It keeps
    the positioning against Behnam & Wang (arXiv 2610.02070) and the TMLR survey §9.6.
    Section references inside the draft were re-pointed to the manuscript's actual
    sections: "§1" for the under-covering interval and the ICC became §4.1.1. Sentences
    saying the sham was "still running" were replaced by the §4.0.1c status. The draft's
    relative dates ("two days old") became absolute ones.
13. New "References" section, generated from `B-related-work.bib` for the 61 keys cited;
    citations are pandoc-style `[@key]`. Four `.bib` entries are not cited in the condensed
    text (`frauen2026causalmethods`, `kohavi2012puzzling`, `garcin2014offline`,
    `rossetti2016contrasting`).
14. Renumbering: Discussion §8 → §9. Cross-references fixed: §1.1 ("One phrase in §9
    overstates") and working-list item 4. References to "§8 of the analysis spec" and to
    "Paper A's §8" are to other documents and are unchanged.

**Form only:**

15. The duplicated heading "### 3.1 Two classification errors of ours, and what they cost"
    was removed; one copy remains. Status header updated.
