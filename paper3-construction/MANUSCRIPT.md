---
title: "Construction before search: a pre-registered test of what an LLM memory builder keeps"
author: "Luiz Antonio Busnello"
---

Status: working draft, not deposited, not peer reviewed. Every number in this text comes
from a file in this directory. §10 lists the sources.

## Abstract

Several recent studies find that memory extracted by a language model loses to retrieval over
the raw conversation. They conclude that agents need better search, not better construction.
All of them keep the extraction step at its defaults. One of them, *Fidelity before Structure*
(arXiv 2601.00821), predicts that better extraction prompts can narrow the gap but cannot reach
what a verbatim store retains.

We pre-registered a test of two repairs to the construction step: how much of the conversation
the builder is shown (the window), and the instructions it extracts under (the criterion). The
first instrument failed its own registered floor. With the full window, the pipeline answered
21% of LongMemEval questions against a required 50%, so its primary contrast was not
interpreted. Two more amendments followed, each fixed before its calibration calls. The first
of them tried four readers, and none passed. An exploratory run then located the loss in
distillation. Units distilled from the evidence sessions scored 0.475, and the raw turns of the
same sessions scored 0.830. A revised criterion, C2, asks the builder to keep facts said in
passing, the event's own time and what the assistant said. It passed calibration on the
development instances.

The confirmatory run used 242 instances with no prior exposure, defined by provenance and not
by question id alone. All four registered controls passed. Repairing both factors against
repairing neither raised accuracy by +66.5 pp [+60.6, +72.5] under judge 1 and +66.9 pp under a
second judge family. Descriptively, the window contrast is mostly evidence availability: at the
truncated window, 120 of the 242 instances kept no annotated evidence session. The criterion contrast at
the full window is +24.8 to +27.3 pp across judges. A length-matched arm rules out its own form
of padding as the explanation. The result confirms a revised intervention, not the original
hypotheses. It does not test the verbatim-store prediction on unseen data, because the
raw-evidence arm did not run on the confirmatory sample.

## 1. Introduction

An agent that remembers usually does it in two steps. A builder reads past conversations and
writes memory units, often facts or lessons with an importance score. A reader later answers
from the units that are served to it. When such systems are compared against retrieval over the
raw transcript, the raw transcript tends to win. Four studies we read report this in different
settings (2601.00821, 2609.34227, 2610.29823, 2609.34160). Their shared conclusion is
that selection over the raw record should replace extraction.

These studies vary the reader, the context budget, the construction order or the retrieval
method. None of them varies how much of the conversation the builder sees or the instructions
it extracts under. 2610.29823 says so directly: Mem0
and Zep "run with their default extraction and retrieval, and other settings may do better".
The closest of the four, 2601.00821, isolates the mechanism as lossy distillation. It also
states, as a prediction rather than a result, that "better extraction prompts — explicit
date/time targeting, temporal attribute modeling — could shrink this class, but cannot reach
the unconditional retention of a verbatim store."

That prediction can be tested, and our own system gave us a reason to test it. In a production
multi-agent memory system (§3), the builder skips sessions it has already logged, so in the
largest sessions it saw a median of 24% of the prose. Its criterion also turned specific facts
into general lessons. In an exploratory, unregistered measurement, repairing either factor alone
moved little, and repairing both moved a lot. A study can only see this if it changes the
construction step.

This paper reports a pre-registered test of that claim on a public benchmark, LongMemEval
`s_cleaned`. It reports the path to the result as well: the first instrument failed its own
floor, the first amendment selected no reader, and the criterion that passed was written after
looking at failures on development data. The registration records were deposited before the
runs they govern (§5), so a reader can check what was fixed when.

**What this paper claims.** On 242 LongMemEval instances the test had never touched, a full
construction window plus the revised criterion C2 raised answer accuracy from 0.153 to 0.818,
against the deployed criterion at a truncated window, with a fixed reader. All four registered
controls passed. The effect is not explained by the length-matched padding arm.

**What it does not claim.**

- It does not show that C2 beats the first repaired criterion, C1, on new data, because C1 did
  not run in the confirmatory stage.
- It does not confirm the interaction hypothesis H1 or the identifier-survival hypothesis H3 as
  first registered.
- It does not test 2601.00821's prediction on clean data, because no raw-evidence arm ran on
  the 242.
- It makes no comparison with the LongMemEval leaderboard, because our judges are not the
  benchmark's judge.

## 2. Related work

| study | what it varies | finding relevant here | what it holds fixed |
|---|---|---|---|
| 2601.00821 *Fidelity before Structure* | memory representation, with six confound controls | verbatim chunks beat lossy artifact extraction; of diagnosable failures, 69.0% are facts never written down and 31.0% retrieval misses | the extraction prompt, except a few-shot contamination control |
| 2609.34227 *When Does Selection Replace Extraction?* | context budget; pre-registered, blind human grading | reranking adds 17.4 points at a tight budget and 1.5 at a generous one | the extractor |
| 2610.29823 *MemoryTax* | reader tier, cost | a stronger reader does not recover what a weaker writer left out; build cost can exceed the rollout it saves | default Mem0 and Zep extraction |
| 2609.34160 *RoutePrism* | construction order | restoring one displaced record recovers more than 60 pp | window and criterion |

The studies above already establish that extracted memory loses to raw retrieval and that the
writer limits the reader. What we add is narrower: a registered test of a change to the
builder's configuration, with controls that can fail. 2609.34227 is the methodological
model, with a registered plan, a primary test and blind human grading. We have the first two
and not yet the third (§8).

`gbrain-evals` (not peer reviewed) uses the same `longmemeval_s_cleaned.json` file, identified
by sha256. It repaired a writer's triage and quoting and measured page recall, not downstream
answer accuracy. Two of its observations shaped our controls: LongMemEval's official judge
accepts a "not available" answer to an answerable question 19 times in 100, and preference
questions defeat readers told to abstain (§8).

## 3. Motivation: an exploratory production measurement

This section is not evidence for the confirmatory claim. It explains why the factors are the
window and the criterion.

The system is a hybrid memory (BM25, dense embeddings, rank fusion) for a group of agents. A
builder, `session-distill`, cuts each session transcript into blocks of 2,000 characters and
asks `gemini-2.5-flash-lite` for at most ten units per block, each with a category and an
importance. Units below 0.5 are dropped. The builder skips any session it has already logged.
Long sessions keep growing after their first distillation, so in the 200k to 1M character band
the builder saw a median of 24.0% of the session's prose. That median rests on six sessions
ranging from 0.020 to 0.894.

On 99 questions over that corpus (2026-10-27, one judge family, not pre-registered):

| arm | accuracy |
|---|---|
| oracle (raw window around the evidence) | 88.9% |
| deployed builder | 42.4% |
| window repaired alone | 46.5% |
| criterion repaired alone (identifiers kept verbatim) | 46.5% |
| both repaired | 63.6% |

Each repair alone added 4.1 pp. Both together added 21.2 pp, of which 13.0 pp is the additive
interaction. At an equal context budget the deployed memory was 21.2 pp below BM25 over the raw
text. The repaired memory, at its own budget of 2.41× the deployed context, was level with it.

The limits are serious. Only 12 sessions had any variance in the window, 8 of them were used to
form the hypothesis, the corpus is private, and one judge family graded it. A second judge
family on the same items moved the criterion effect at the full window from +8.1 pp to
+21.2 pp. The disagreement between judges was larger than the effect one of them reported.
That is why the registered analysis reports criterion effects as a bracket across judge
families (§4.7).

## 4. Design

### 4.1 Corpus

LongMemEval `s_cleaned` (revision `98d7416c`, MIT licence) has 500 instances. Each instance is a
haystack of 38 to 62 chat sessions (455k to 514k characters) and one question, with the
evidence sessions annotated. The 30 abstention instances are excluded, and 8 more were spent on
a declared smoke run, which leaves 462.
LoCoMo was rejected because its 1,986 questions sit on 10 conversations, and the conversation
is the unit of inference.

Instances share distractor sessions: 20.5% of session ids appear in more than one haystack.
Only 5 pairs share an evidence session. Standard errors are therefore cluster-robust over
answer-session groups.

### 4.2 Factors and cells

Each instance passes through every cell, so all contrasts are paired.

| | criterion C0 (deployed) | criterion C2 (revised) |
|---|---|---|
| **window 0.240** | cell 00 | cell 01 |
| **full window** | cell 10 | cell 11 |

- **Window.** At level 0 the builder sees the most recent sessions whose cumulative prose
  reaches 0.240 of the haystack's characters. The session that crosses the threshold is
  included whole. The realised dose in cell 00 had median 0.251 [0.240, 0.274]. At level 1 it
  sees all sessions. The cut approximates production's window by its median seen-fraction. It
  does not reproduce production's mechanism, which is a prune crossed with a lookback and a
  per-run ceiling.
- **Criterion.** C0 is the deployed `DISTILL_SYSTEM`, verbatim. C1, the repair registered in
  v1.0, adds one paragraph requiring identifiers verbatim. C2 adds a second paragraph to C1
  (§5.4). The prompts are in Portuguese, the deployed system's language.

Two dose cells (W = 0.020 and W = 0.894, the band's observed extremes) run on a seeded
subsample of 60. A length-matched cell serves cell 00's material, padded to cell 11's length
with raw text from sessions that hold no answer.

Each block is distilled once per criterion, and every window that contains it reuses the same
units. The truncated memory is therefore an exact subset of the full one, and a difference
between windows comes from which sessions the builder saw. Sampling noise in the extractor
cancels out of that contrast.

### 4.3 Serving and reading

All units of a cell are served, sorted by importance, each as `[session date] [category] text`.
The question carries LongMemEval's own question date. The reader in the confirmatory run is R3:
`gemini-3.8-flash` with prompt B and thinking set to low. Prompt B tells the reader the material
is dated memories, asks it to count, compare and do date arithmetic where the question needs
it, and reserves the abstention answer `NAO SEI` for material in which nothing is relevant.

### 4.4 Judges

Judge 1 is `gpt-6-luna` through a structured decision API with no free-text field. An answer is
correct when the judge's probability for "contains the reference fact" exceeds 0.5. Judge 2 is
`gemini-2.5-flash-lite` with a fixed prompt, and it grades every row. Before any run, a
preflight checks that judge 1 accepts none of 16 abstentions offered against real references.
The reader and judge 2 are both Gemini models, so the judge bracket is read on contrasts, not on
levels (§8).

### 4.5 Primary hypothesis and analysis

> H1′: E[ Y(full window, C2, R3) − Y(0.240 window, C0, R3) ] > 0 on the 242.

This is the total effect of repairing both factors against repairing neither. The estimate is
a paired difference in accuracy with a cluster-robust standard error. The test is two-sided at
α = 0.05, in one stage, with no interim look. The interaction is a registered secondary, tested
against a serial null, not against zero. A model where the window decides whether the evidence
arrives and the criterion decides whether it is used produces a positive additive interaction
with no joint mechanism. The serial null predicts Y11 = Y01 · Y10 / Y00.

### 4.6 Controls

| control | construction | passes when |
|---|---|---|
| answerable floor | cell 11 on every instance | acc ≥ 0.50 |
| positive | full window minus every annotated answer session, 40 instances | acc ≤ 0.10 |
| negative | the 0.240 cut applied to non-answer sessions only, all answer sessions kept, 40 instances | \|acc − acc(11)\| ≤ 0.10 and item-wise discordance ≤ 0.20 |
| counterfactual | 31 instances whose numeric answer was rewritten inside the evidence sessions (+3 for years, +7 otherwise) | in cell 11, answers with the original number ≤ 10% and fewer than answers with the altered number |

A pipeline that always abstains passes the positive and negative controls, and the floor
catches it. A pipeline that reads the benchmark's annotations instead of the constructed memory
can pass the first three. The counterfactual is the control that checks the answer came from
the memory. If the floor fails, the run is reported as an instrument failure and the primary
contrast is not interpreted.

### 4.7 Pre-specified reporting rules

- Criterion contrasts are reported as the bracket across the two judge families.
- An interval that contains zero is inconclusive. It is never read as a null or as equivalence.
- Served length is recorded per row. The primary is also estimated with length as a covariate.
- A missing annotated session does not prove that no usable information remained.

## 5. How the registration changed, and why

Each amendment was fixed by a git tag of this repository before the calls it governs. Where a
DOI is given, a Zenodo deposit followed. The v1.3 calibration was fixed by tag on 2026-11-03,
and the v1.3 deposit, which includes the calibration result, was published before the
confirmatory run.

| version | fixed | DOI | what it changed | outcome |
|---|---|---|---|---|
| v1.0 | 2026-10-27 | 10.5281/zenodo.23716613 | the 2×2 factorial on LongMemEval with C1 | not run as written |
| v1.1 | 2026-11-03 | 10.5281/zenodo.23914868 | excluded the 30 abstention instances; pinned the seed, serving, controls and judges; declared a smoke run | stage 1: instrument failure |
| v1.2 | 2026-11-03 | tag `paper3-prereg-v1.2-calibration` | the reader, calibrated over four candidates | no reader selected |
| v1.3 | 2026-11-04 | 10.5281/zenodo.23934489 | criterion C2, reader R3, confirmatory sample of 242 | controls pass, H1′ confirmed |
| result | 2026-11-04 | 10.5281/zenodo.23949145 | the confirmatory result as its own record | |

### 5.1 v1.0 to v1.1: a census error

v1.0 stated that the corpus held no abstention instances. The census script had looked for the
`_abs` suffix in the question type, while the marker is in the question id. There are 30. The
v1.1 amendment excluded them before any arm ran. It also pinned what v1.0 had left to the
runner. A declared smoke run on 8 excluded instances checked the plumbing and was not evidence.

### 5.2 Stage 1: the floor failed

Stage 1 ran on 200 instances with C1 and the deployed reader (R0, `gemini-2.5-flash-lite`) and
cost US$ 18.80. The answerable floor was acc(11) = 0.210 against the required 0.50. The other
three controls passed. Under the registered rule the run is an instrument failure. The printed
primary of +14.5 pp is not a finding, and stage 2 was not run.

Two defects of the registration were exposed. The 0.50 floor had been justified by numbers from
the production corpus of §3, not from LongMemEval. The smoke had passed the floor at exactly
4/8, a sample that cannot test a threshold.

### 5.3 v1.2: no reader passed

v1.2 calibrated four readers on the spent stage-1 instances, as a 2×2 of model and prompt. The
pass bar was 0.55, set above the floor to absorb selection over four candidates.

| reader | model | prompt | acc(11), judge 1 |
|---|---|---|---|
| R0 | gemini-2.5-flash-lite | A | 0.210 |
| R1 | gemini-2.5-flash-lite | B | 0.245 |
| R2 | gemini-3.8-flash | A | 0.360 |
| R3 | gemini-3.8-flash | B | 0.505 |

None passed, and v1.2 stopped as registered (US$ 19.03). The prompt helped the larger model
(+14.5 pp) far more than the smaller one (+3.5 pp).

### 5.4 Exploratory: the loss is in distillation

An unregistered run on the same spent 200 asked how much of the gap was the reader and how much
was the material (US$ 1.71). R3 read three materials:

| material | mean characters | acc, judge 1 |
|---|---|---|
| cell 11: all sessions as C1 units | ~161,700 | 0.505 |
| evidence sessions only, as C1 units | 9,178 | 0.475 |
| evidence sessions only, as raw turns | 26,458 | 0.830 |

Removing roughly fifty distractor sessions made no detectable difference (12 against 6
discordant pairs, exact McNemar p = 0.24, which is not an equivalence result). Replacing the
units with the raw turns they came from did (6 against 77, p < 10⁻¹⁶). The largest losses were
in temporal reasoning (0.37 against 0.94) and single-session-assistant questions (0.46 against
1.00). With the weaker reader R0 the same comparison gave 0.205 and 0.340. A weak reader hides
the construction loss, and that is why stage 1 seemed to point at the reader.

A cache-only diagnosis compared the 77 instances R3 answered from raw turns and missed from
units with the 89 it answered from both. The answer-bearing block was rarely distilled to
nothing (5 of 77). The losses were in what the units kept. A fact said in passing became a
lesson: "the commute takes 45 minutes each way" became "the user retains more from audiobooks".
The date of the conversation replaced the time of the event. Items the assistant had listed
were not kept.

C2 adds one paragraph to C1 that asks for exactly those three things. It wants concrete facts
about the user's life kept even when said in passing, as facts and not lessons, at importance
of at least 0.5. It wants the event's own time expression copied with the event. And it wants
specific information the assistant gave and the user may ask back, such as lists, names and
numbers.

### 5.5 v1.3: calibration, then a sample defined by provenance

v1.3 fixed the reader at R3 and replaced C1 with C2. Calibration on the spent 200 (pass bar
0.55) gave acc(11) = 0.770 and acc(pos) = 0.000. C2 was right on 56 instances that C1 under R3
missed and wrong on 3 that C1 got. C2 was written from these instances' failures, so 0.770 was
declared likely optimistic.

Before deposit, two adversarial reviews from other model families read the amendment and
both advised against depositing it as written. One found that "untouched" had been defined by
question id only. Seventeen of the 262 instances left after stage 1 had run as counterfactual
variants, and 3 more shared an answer session with a spent instance. The confirmatory sample
became the remaining 242, the counterfactual control was reclassified as a regression control
on known examples, and the hypothesis was renamed H1′ to say that it tests a revised
intervention. A third review found two defects in the spending cap, which were fixed in the
runner. v1.3 was deposited before the confirmatory run began.

## 6. Results

The confirmatory run produced 1,654 rows, all with a normal finish. Of 155,506 distinct blocks,
87 failed to distil and were served empty (0.056%). It ran as three processes on one output
directory, resumed from its own cache after a rate limit and after the provider's prepaid
credit ran out. It cost US$ 70.73 against a cap of US$ 110. No row was read for its outcome
until every row existed. `lme-analyze.py runs/confirm-2026-11-04 --check` reproduces the
analysis byte for byte.

### 6.1 Controls

| control | result | required |
|---|---|---|
| answerable floor | acc(11) = 0.818 (n = 242) | ≥ 0.50 |
| positive | 0.000 (n = 40) | ≤ 0.10 |
| negative | 0.775 against 0.775, discordance 0.100 | ≤ 0.10, ≤ 0.20 |
| counterfactual | original number 1, altered number 28, of 31 | original ≤ 3.1, altered > original |

All four pass, so the primary is interpreted.

### 6.2 Primary

| | estimate | 95% interval |
|---|---|---|
| judge 1 | **+66.5 pp** | [+60.6, +72.5] |
| judge 2 | +66.9 pp | [+61.0, +72.9] |

acc(00) = 0.153 and acc(11) = 0.818, with G = 241 answer-session clusters. The interval
excludes zero, so H1′ is confirmed. The two judge families agree on 922 of 968 primary-cell
judgments.

### 6.3 Contrasts behind the total

These are reported by the registered analysis, and none is a confirmatory test.

| contrast | judge 1 | judge 2 |
|---|---|---|
| window, 11 − 01 (C2 held) | +59.5 [+53.1, +65.9] | +61.6 [+55.2, +67.9] |
| criterion, 11 − 10 (full window held) | +24.8 [+18.8, +30.8] | +27.3 [+21.1, +33.4] |
| criterion, 01 − 00 (0.240 window held) | +7.0 [+3.6, +10.4] | +5.4 [+2.1, +8.6] |

Cell accuracies under judge 1 are 0.153 (00), 0.223 (01), 0.570 (10) and 0.818 (11). The
contrasts are conditional and interact, so they are not shares of the total. In one order the
total splits as +59.5 (window) plus +7.0 (criterion), and in the other as about +41.7 plus
+24.8. The criterion contrast at the full window is reported as the bracket
[+24.8 · +27.3] pp. It compares C2 with the deployed C0, not with C1.

**Interaction.** The additive interaction is +17.8 pp. Against the serial null it is −1.4 pp
[−20.2, +11.8]. The interval contains zero, so the secondary is inconclusive. It is not a null,
and it licenses no equivalence claim.

**Served length.** Cell 00 served a mean of 36,199 characters and cell 11 served 231,416. The
length-matched arm serves cell 00's material padded to cell 11's length. It scored +0.8 pp
[−0.8, +2.4] above cell 00 and −65.7 pp below cell 11. The primary adjusted for served length
is +66.5 pp. The registered test asks whether this arm reproduces cell 11, and it does not. That
rules out this form of padding as the explanation. It does not rule out every explanation by
length.

**Dose.** On the subsample of 60, Y(full, C2) − Y(dose, C0) was +83.3 pp at W = 0.020 and
+35.0 pp at W = 0.894. The sign is the same across the observed band. The analysis output
labels these levels `W=0.20` and `W=8.94`. That is a formatting defect in the frozen analysis
script, and the cells it reads are `d020` and `d894`.

### 6.4 Where the window contrast comes from (descriptive)

The design predicted that the window contrast would be dominated by evidence availability (v1.1
§12.8). The table below splits the 242 by how many annotated evidence sessions the 0.240 cut
kept in cell 00. The split depends only on the instance and the cut, both fixed before any
answer is read. It is not a registered analysis.

| evidence kept by the cut | n | 00 | 01 | 10 | 11 |
|---|---|---|---|---|---|
| none | 120 | 0.000 | 0.000 | 0.550 | 0.808 |
| some | 79 | 0.177 | 0.278 | 0.595 | 0.861 |
| all | 43 | 0.535 | 0.744 | 0.581 | 0.767 |

When the cut kept no evidence session, the truncated cells answered nothing under either
criterion. That is the positive control's result, reproduced on a different subset. When the
cut kept all the evidence, the window added +4.6 pp under C0 and +2.3 pp under C2, and the
criterion added +20.9 pp at the truncated window and +18.6 pp at the full one. On this corpus
the window contrast is mostly a question of whether the evidence reached the builder. The
criterion contrast appears at both windows once it has. The "all kept" group has 43 instances,
and these figures carry no interval.

### 6.5 By question type, and against calibration

| question type | n | 00 | 01 | 10 | 11 |
|---|---|---|---|---|---|
| knowledge-update | 30 | 0.333 | 0.467 | 0.733 | 0.900 |
| multi-session | 68 | 0.059 | 0.147 | 0.603 | 0.838 |
| single-session-assistant | 28 | 0.250 | 0.321 | 0.536 | 0.786 |
| single-session-preference | 16 | 0.062 | 0.062 | 0.312 | 0.438 |
| single-session-user | 32 | 0.281 | 0.312 | 0.781 | 0.906 |
| temporal-reasoning | 68 | 0.088 | 0.147 | 0.441 | 0.824 |

Abstention falls from 0.760 in cell 00 to 0.074 in cell 11. On the 242 unseen instances cell 11
scored 0.818, against 0.770 in calibration on the 200 spent ones. The drop that §5.5 expected
did not appear. The two numbers come from different samples, so the comparison is descriptive.

## 7. Discussion

**The four studies' shared conclusion.** On this corpus, with this reader, changing
how the builder is configured moved accuracy from 15% to 82%. A study that holds the extraction
step at its defaults measures one configuration of the builder, and the gap it reports between
extraction and raw retrieval holds for that configuration. We ran no retrieval arm in the
confirmatory stage, so nothing here says extraction beats retrieval. What the run shows is that
the comparison depends on a variable these studies did not vary.

**The prediction of 2601.00821.** It concerns retention, and on retention it is
right: units are not a verbatim store. Whether C2 closes the accuracy gap to raw evidence is
not answered by this run. On the spent 200, raw evidence scored 0.830 under R3 and C2 units
scored 0.770 in cell 11 and 0.745 on the evidence sessions alone. On the 242, cell 11 scored
0.818, but the raw-evidence arm did not run. The two numbers cannot be compared as a test,
because one sample informed the writing of C2 and the other has no raw arm. A registered
follow-up would run the raw-evidence arm and C2 on the same unseen instances, with a
non-inferiority margin fixed in advance.

**The window.** The production finding that motivated the window factor is a property of a
deployed system. The benchmark imposes it by construction. Here the window acted mostly by
deciding whether the evidence sessions reached the builder (§6.4). That is the serial
mechanism the analysis plan named, and the interaction against the serial null was
inconclusive. We do not claim a joint mechanism.

**The instrument.** Three things went wrong before the result. The floor was justified with
numbers from another corpus. A smoke of 8 instances was treated as if it could check a
threshold. And a clean sample was defined by question id
when exposure also travels through rewritten variants and shared evidence sessions. The first
two were found by the run itself and the third by external review before deposit. A
pre-registration let these be stated as failures rather than absorbed into the analysis. It did
not prevent them.

## 8. Limitations

- **Judges.** Both judges are language models, and R3 and judge 2 are both Gemini. The bracket
  is read on contrasts. The blind human pass the plan provides for has not been done, so the
  conclusions are conditional on the judges.
- **Adaptive development.** R3 and C2 were chosen on development data after earlier versions
  failed. The confirmatory sample was untouched, but the intervention it tests was shaped by
  what failed before.
- **Preference questions.** Their references are rubrics, not answers. They scored 0.077 under
  R3 even on raw evidence, and they cap every cell. They are 16 of the 242 and stayed in the
  sample.
- **Window shape.** The cut takes whole sessions, most recent first. Sensitivity to the shape of
  the cut was not measured.
- **One corpus, one reader, one extraction model.** LongMemEval sessions are synthetic
  dialogue. The extractor is `gemini-2.5-flash-lite` throughout.
- **Language.** The builder, reader and abstention prompts are in Portuguese, the deployed
  system's language, while LongMemEval is in English. Units mix both languages. The
  distillation-loss diagnosis found no difference in the share of Portuguese units between lost
  and kept instances (0.10 against 0.14).
- **No leaderboard comparison.** Neither judge is LongMemEval's official judge.
- **No production confirmation.** C2 has not run on the production corpus that motivated it.

## 9. Release

- Pre-registration, cumulative through v1.3: 10.5281/zenodo.23934489 (concept
  10.5281/zenodo.23716612).
- Confirmatory result with data: 10.5281/zenodo.23949145. It holds the rows, receipt, analysis,
  manifests and runner. `lme-analyze.py --check` reproduces the analysis without any API key.
- Code: the public repository `totobusnello/memoria-nox`, directory `paper3-construction/`, at
  tags `paper3-prereg-v1.0` through `paper3-prereg-v1.3`.

## 10. Sources of the numbers in this text

| section | file |
|---|---|
| §3 | `README.md`, "Numbers it rests on"; `PREREGISTRATION-DRAFT.md` §11.2, §11.5 item 7, §11.6 |
| §4 | `PREREGISTRATION-DRAFT.md` §11.1–§11.5, §12.3–§12.7, §13.3, §14.3, §14.9 |
| §5.2 | `STAGE1-RESULT.md`, `runs/stage1-2026-11-03/` |
| §5.3 | `PREREGISTRATION-DRAFT.md` §13.10, `runs/calibration-2026-11-03/` |
| §5.4 | `READER-CEILING.md`, `runs/ceiling-2026-11-03/`; `PREREGISTRATION-DRAFT.md` §14.1 |
| §5.5 | `PREREGISTRATION-DRAFT.md` §14.8–§14.10, `runs/c2-calibration-2026-11-03/` |
| §6.1–§6.3, §6.5 | `CONFIRM-RESULT.md`, `runs/confirm-2026-11-04/analysis.txt` |
| §6.3 cell accuracies, §6.4 | `manuscript-tables.py` (descriptive, keyless) |

## References

- *Fidelity before Structure: Verbatim Chunks Beat Lossy Artifact Extraction.* arXiv 2601.00821.
- *When Does Selection Replace Extraction? A Pre-Registered Test.* arXiv 2609.34227.
- *MemoryTax: The Bitter Lesson of Agent Memory.* arXiv 2610.29823.
- *RoutePrism: Tracing Construction Order Effects in Agent Memory.* arXiv 2609.34160.
- *LongMemEval*, `s_cleaned` release, revision `98d7416c24c778c2fee6e6f3006e7a073259d48f`.
- `gbrain-evals`, workstreams W8, W10b and Cat 35 (not peer reviewed).
