# Paper D: criterion C2 on the production corpus (protocol draft)

Status: DRAFT, 2026-11-05. Not fixed, not tagged, nothing has run. Written while Paper A waits for
H-A2. Every number below names its source file; a number without a source is a defect of this
draft. The decisions this draft cannot make are listed at the end, for Toto.

## 1. Question

Paper 3 found, on LongMemEval, that replacing the deployed extraction criterion C0 with the revised
criterion C2, at the full window, raised answer accuracy by +24.8 to +27.3 pp across two judge
families, on 242 instances (`paper3-construction/CONFIRM-RESULT.md`, "Contrasts behind the total
effect", row "criterion, 11 − 10"). That is a benchmark of personal chat. The memory this system
actually builds is from agent work sessions in Portuguese and English: engineering decisions,
paths, commands, lessons.

**Does C2 extract a more useful memory than C0 from the same production sessions?**

`docs/DECISIONS.md` D-2026-11-04 makes the product's "second wave" ("a memória que constrói certo")
conditional on this paper: "só se o paper D (C2 em replay offline e depois no produto) confirmar".
`PLANO.md` (Decisões, 2026-11-04) fixes the order: "D começa por replay offline pareado C0 × C2",
with no deploy.

## 2. What already exists on this corpus (exploratory, and spent)

An exploratory replay on production sessions ran on 2026-10-26/27. It is the template for this
protocol and also the reason a new sample is needed.

| fact | value | source |
|---|---|---|
| sessions | 20, stratified by produced memory, seed 20261026 | `audits/2026-10-26-faithfulness-replay.md`; `audits/2026-10-26-replay-build.py` (`SEED`, `PER_STRATUM = 8`) |
| questions | 117 generated, 104 kept (13 had no verifiable citation); 99 used in the net-value arms | `audits/2026-10-26-faithfulness-replay.md`; `audits/2026-10-27-net-value-and-see-once.md` |
| memory as built (C0, see-once window) vs BM25 on raw text at equal budget | 42.4% vs 63.6%, net value −21.2 pp | `audits/2026-10-27-net-value-and-see-once.md` |
| window alone / prompt alone / both | each +4.0 pp; both +21.2 pp; interaction 13.2 pp (13.0 pp in `audits/2026-10-27-codex-and-deepseek-on-the-prereg.md`; motivation only, not reconciled here) | `audits/2026-10-27-neither-cause-explains-it-alone.md` |
| the prompt arm there | the "verbatim identifiers" paragraph, i.e. C1, not C2 | `audits/2026-10-27-arm-d-verbatim-identifiers-build.py`; `paper3-construction/lme-run.py` (`IDENT_PARAGRAPH`, `PROMPTS`) |

Those 20 sessions and 99 questions shaped C1 and, through Paper 3, C2. They are excluded from this
paper's sample (§4.3). The 2026-10-27 figures are cited as motivation only.

## 3. Estimand

Unit: a question generated from the raw transcript of one frozen production session. Questions are
clustered in sessions.

Arms, all on the SAME frozen sessions, so every contrast is paired:

| arm | material the reader gets | role |
|---|---|---|
| **A** | the raw evidence window of the question (±1,500 chars around its citations) | ceiling, and the false-positive floor of the damage predicate (`audits/2026-10-27-net-value-and-see-once.md`) |
| **C0** | all units distilled from the session's COMPLETE prose under C0 (deployed `DISTILL_SYSTEM`) | comparator |
| **C2** | all units distilled from the same complete prose under C2 (`DISTILL_SYSTEM_V3` in `paper3-construction/lme-run.py`) | treatment |
| C0-asbuilt *(optional, §10 D3)* | the units production actually stored for that session (see-once window) | links the result to the deployed product |

Primary estimand (proposed): E[ Y(C2) − Y(C0) ] over questions, at the full window, with Y = 1 if
the judge says the answer contains the reference fact. This is Paper 3's criterion contrast
(11 − 10) on production material. The full window is used in both arms so that the contrast is the
criterion alone; whether production's see-once window is also fixed is a product decision, and
Paper 3 already showed window and criterion interact (`paper3-construction/MANUSCRIPT.md` §6.3).

Each session is distilled once per criterion with temperature 0, and every question of that session
reads the same units, as in Paper 3 (`paper3-construction/MANUSCRIPT.md` §4.2).

## 4. Sessions: where they live, how they are frozen and sampled

### 4.1 Where transcripts live

Per the 2026-10-22 measurement (`audits/2026-10-14-brief-usage.md`, §2026-10-22; summarised in the
project memory note on the three roots):

| root | role |
|---|---|
| `/root/.claude-nuvini-team/projects` | live, main |
| `/root/.claude/projects` | live, secondary; `prune-claude-sessions.sh` (04:23) deletes `.jsonl` older than 7 days, and those under 50 KB older than 12 h |
| `/var/lib/nox-mem/action-archive` | the archive: 1,543 jsonl, 443 MB, from 2026-08-15 (as of 2026-10-22) |

`nox-archive-transcripts.sh` copies every `~/.claude*/projects` root into the archive at
03:40/09:40/15:40/21:40. The archive is the only place the past survives. The distiller reads only
the live roots, never the archive (`audits/2026-10-26-construction-tax-probe.md`).

### 4.2 Freezing

Freezing is a copy, not a pointer. On the day of the freeze, on the serving host, read-only:

1. List the archive and record the listing.
2. For each sampled session, copy its archive `.jsonl` to a private directory outside the
   repository, and write a manifest of sha256 per file. The manifest's sha256 (not its contents)
   goes into the public commitment.
3. Record, per session, the units production stored (`chunks WHERE source_file LIKE 'sessions/%'`,
   as `audits/2026-10-26-replay-build.py` does), from a copy of the database, never the live one.
4. Record the sha256 of the deployed `src/session-distill.ts` and assert that its `DISTILL_SYSTEM`
   equals the C0 text in `paper3-construction/lme-run.py`. The source is on the host, not in this
   repository; if they differ, C0 is redefined as the deployed text and the difference is reported.

**The 7-day constraint.** A session is eligible only if its last turn is at least 7 days before the
freeze. That way the live copy has been pruned or is no longer growing, so the archive holds the
FINAL transcript (the see-once audit relies on exactly this: `audits/2026-10-27-net-value-and-see-once.md`,
"The archive keeps the final transcript"). Sessions under 50 KB can be deleted from the secondary
root 12 h after their last write, and the archive copies every 6 h, so a small session can in
principle be lost before it is archived. That loss is not measurable from the archive alone and is
stated as a coverage limit, not corrected.

Proposed dates (to confirm, §10 D5): freeze on the day the protocol is fixed; eligible sessions are
those with last turn between 2026-08-15 (archive start) and freeze − 7 days.

### 4.3 Sampling

- **Frame:** sessions present both in the archive and in the database as built units, the same join
  as `audits/2026-10-26-replay-build.py` (`both = built ∩ raw`), restricted to the agent directories
  the distiller can reach (`audits/2026-10-26-construction-tax-probe.md`, Defect 2: the behavioural
  test "ever produced a log row or a chunk"; 54 transcripts in `-root`, `-tmp`, `-root-medicoes-7b`,
  `-root--openclaw-workspace-skills` are out of reach by design).
- **Exclusions:** the 20 sessions of `replay-set.json` (2026-10-26). Their ids stay on the host; the
  exclusion is applied by id and the count of exclusions is published.
- **Strata:** by final prose size, because the effect concentrates in large sessions (memory 53.8%
  under 50k chars against 27.5% at 200k–1M, `audits/2026-10-27-net-value-and-see-once.md`). Bands
  < 50k, 50–200k, 200k–1M, as in that audit.
- **Seed:** new, fixed in the protocol before the draw. Not 20261026.
- **Size:** not set here (§10 D4). It needs the discordant-pair rate between C0 and C2 on production
  questions, which no run has measured; the per-question C1-vs-C0 pairs of 2026-10-27 are on the host
  and could bound it, but they are C1, not C2.

## 5. Questions and the outcome, without a gold set

Production has no gold answers. As in the 2026-10-26 replay, the reference is the raw transcript
itself:

1. Windows of 20,000 chars are cut from the raw prose, so a question can need evidence that crosses
   the distiller's 2,000-char blocks (`audits/2026-10-26-replay-build.py`, `WINDOW`; block size from
   the same file's docstring).
2. A generator writes facts with verbatim citations; every citation is checked as a byte-exact
   substring of the window, and facts that fail are dropped (`audits/2026-10-26-replay-generate.py`,
   discipline 2). Questions must name their entities (discipline 3).
3. The outcome Y is the judge's predicate "the answer contains the reference fact" (CONTEM,
   `P > 0.5`), and a second predicate for contradiction (CONTRADIZ), with arm A as its floor
   (`audits/2026-10-27-net-value-and-see-once.md`, 17.2% on arm A).

**The question criterion is the decision that can bias this paper (§10 D1).** In 2026-10-26 the
generator asked for facts in C0's own declared categories (decision, preference, lesson, context;
`audits/2026-10-26-replay-generate.py`, `SYSTEM`), to measure C0 against its own promise. C2 adds
two promises: identifiers verbatim, and concrete facts said in passing (`IDENT_PARAGRAPH`,
`EVENT_PARAGRAPH` in `paper3-construction/lme-run.py`). Asking only C0's categories under-counts
what C2 adds; asking C2's categories favours C2 by construction. The proposal is to generate under
C0's criterion (the deployed promise), report by category, and add C2's two classes as a labelled
secondary set, never pooled into the primary.

**Writer family.** The 2026-10-26 generator was `gemini-2.5-flash-lite`, the same family as the
distiller and the answerer (`audits/2026-10-26-faithfulness-replay.md`). Paper A used a third family
(`glm-5.3`) as writer for exactly this reason (`paper-a-eval-ptbr/PREREGISTRATION.md` §3). Proposed:
a writer from a family that is neither the distiller nor the judge.

## 6. Reader and judges

Reused from Paper 3 where it applies (`paper3-construction/lme-run.py` header):

- distiller: `gemini-2.5-flash-lite`, temperature 0, `BLOCK_SIZE` 2000 per session, never splitting
  a line, `importance >= 0.5`, at most 10 items per block, `is_noise_static`;
- answerer: `ANSWER_SYSTEM` verbatim, `gemini-2.5-flash-lite`, temperature 0, `NAO SEI` permitted;
  Paper 3's v1.3 reader R3 is the alternative (§10 D6);
- judge 1: `gpt-6-luna`, Decisions API, CONTEM / CONTRADIZ, correct iff P(contem) > 0.5;
- judge 2: `gemini-2.5-flash-lite` family-2 prompt (`audits/2026-10-27-second-family-judge.py`), on
  every row, so the criterion effect is reported as a bracket across judge families, as in Paper 3.

**A blind human sample is mandatory.** Paper A's human sample agreed with `gpt-6-luna` at kappa 0.038
on 60 pairs (`paper-a-eval-ptbr/HUMAN-COMMITMENT.json`), and the grader said "yes" far more often
than the judge. A judge-only result on production material would repeat that exposure. Proposed:
60 (question, answer) pairs drawn uniformly from the C0 and C2 arms, graded blind to arm and to the
judge, before the contrast is read.

## 7. Controls

Adapted from Paper 3 §4.6 (`paper3-construction/MANUSCRIPT.md`):

| control | construction | passes when |
|---|---|---|
| ceiling | arm A on every question | high enough that the questions are answerable from the transcript (threshold to fix, §10 D7; arm A was 88.9% in `audits/2026-10-27-net-value-and-see-once.md`) |
| positive | C2 units distilled from the session with every evidence window removed | accuracy near zero |
| damage floor | CONTRADIZ on arm A | reported; no arm is said to cause damage unless it exceeds this floor |
| counterfactual | a number inside the evidence rewritten before distillation, on a seeded subsample | answers carry the altered number, not the original |
| fidelity of the re-implementation | C0 re-distilled from the visible prefix reproduces the units production stored, on aggregate | as in `audits/2026-10-27-neither-cause-explains-it-alone.md` ("Controls", fidelity row) |

The last control matters here: the 2026-10-27 re-implementation matched production's aggregate but
not every cell, and the missing embedding dedup was the likely cause
(`audits/2026-10-27-neither-cause-explains-it-alone.md`).

## 8. Privacy

The corpus is private and the repository is public. Only code, counts, hashes and aggregate
results are committed. Session ids, transcript text, questions, citations, units and answers stay on
the host or in `~/Backups/`, identified by sha256 in a public commitment, as in Paper A. The
privacy gate of `tools/hooks/pre-commit` runs on every commit.

## 9. Cost, with the arithmetic

From measured runs on this corpus, all with `gemini-2.5-flash-lite` at the list price in
`paper3-construction/lme-run.py` (`G_IN, G_OUT = 0.10 / 1e6, 0.40 / 1e6`):

| component | measured | per unit | source |
|---|---|---|---|
| distillation of complete prose, 20 sessions, one criterion | 1,395,339 in / 189,059 out tokens = US$ 0.2152 | ≈ US$ 0.0108 per session per criterion | `audits/2026-10-27-the-gap-is-extraction-not-the-window.md` |
| answers, 99 questions × 2 arms | US$ 0.1082 | ≈ US$ 0.00055 per answer | same |
| judging (judge 1), arm C | US$ 0.0158 | not split per item | same |
| question generation, 117 questions | US$ 0.051 | ≈ US$ 0.00044 per question | `audits/2026-10-26-faithfulness-replay.md` |

Check of the distillation figure: 1,395,339 × 0.10/1e6 + 189,059 × 0.40/1e6 = 0.13953 + 0.07562 =
US$ 0.21516, which rounds to the reported 0.2152.

Illustration only, not a sample size: S sessions and Q questions, three answered arms (A, C0, C2),
two criteria distilled, plus the positive control (one more C2 distillation):

  cost ≈ 3 × S × 0.0108 + Q × (0.00044 + 3 × 0.00055) + judging

For S = 100 and Q = 500 this is ≈ 3.24 + 1.05 + judging. Judging cost per row is not derivable from
the arm-C figure without its row count, and the per-session distillation cost assumes the new sample
has the same size mix as the 2026-10-26 one, which stratification by size changes. Both are to be
re-estimated in a smoke, as Paper 3 did, with a hard spend cap in the runner (`--cap-usd` in
`paper3-construction/lme-run.py`).

## 10. What would make live shadow necessary

The offline replay answers "is C2's memory better on the same sessions". It cannot answer:

- **drift:** whether C2 keeps its advantage on sessions written after the freeze;
- **cost in production:** a stricter criterion changes how many units are stored; C1 produced
  +8.5% units on production (`audits/2026-10-27-neither-cause-explains-it-alone.md`, Controls), and
  C2's count on production is unmeasured. Units change embedding cost, index size and the brief;
- **interaction with see-once:** production distils a growing session once (`session-distill.ts:141-144`,
  quoted in `audits/2026-10-27-net-value-and-see-once.md`); the replay uses complete prose.

A live shadow (C2 writing to a separate table, not served) is justified only if the replay shows an
effect and the product decision needs one of these three. It touches production and needs its own
plan and Toto's explicit go-ahead.

## 11. Open decisions for Toto

Decided on 2026-11-05 (19:2x BRT): **D2** no C1 arm and **D3** no as-built arm, so the paper compares
C0 and C2 only; **D8** the blind human sample of 60 pairs, graded by the author, is mandatory;
**D9** the protocol is frozen as a tagged pre-registration before the session draw, as Paper A was.
Decided the same evening, in one block: **D1** questions generated under C0's declared categories
(the deployed promise), reported by category, with C2's two extra classes (verbatim identifiers,
concrete facts said in passing) as a labelled secondary set never pooled into the primary, and a
writer from a third family (`glm-5.3`); **D5** freeze on the day the protocol is tagged, eligible
sessions from 2026-08-15 (start of the action archive) to the freeze date minus 7 days, excluding
the 20 sessions spent on 2026-10-26/27 and the smoke's sessions; **D6** the production reader
(`ANSWER_SYSTEM`, `gemini-2.5-flash-lite`); **D7** the contrast is read only if arm A (raw
transcript) reaches accuracy ≥ 0.70; positive control (evidence removed) ≤ 0.10; counterfactual:
answers with the original number ≤ 10% and fewer than with the altered number (Paper 3 §4.6);
re-implementation fidelity: re-distilled C0 aggregate within 5 points of the units production
stored. A paid smoke (about 5 sessions, under US$ 1) sizes the sample (D4); its sessions are
excluded from the draw. All decisions are now taken except D4.

- **D1. Question criterion.** C0's declared categories (proposed, with C2's two extra classes as a
  labelled secondary), C2's, or the union.
- **D2. Third arm C1.** Paper 3 never ran C2 against C1 on new data (`paper3-construction/CONFIRM-RESULT.md`,
  "it does not show that C2 beats C1"). Add C1 as an arm (one more distillation per session), or keep
  the paper to C0 vs C2.
- **D3. Arm C0-asbuilt.** Include production's stored units (see-once window) as a fourth arm, so the
  paper also measures the gap to what the product serves today.
- **D4. Size and power.** Number of sessions and questions per session, after a smoke measures the
  C0-vs-C2 discordance on production questions.
- **D5. Freeze date and eligibility window.** Proposed: freeze on the day the protocol is fixed;
  eligible sessions from 2026-08-15 to freeze − 7 days.
- **D6. Reader.** The 2026-10-27 production reader (`ANSWER_SYSTEM`, flash-lite) or Paper 3's R3.
- **D7. Thresholds** for the ceiling and positive controls, fixed before any call.
- **D8. Human sample** of 60 pairs, graded blind by the author (proposed mandatory, given Paper A's
  kappa 0.038).
- **D9. Pre-registration.** Freeze this as a tagged pre-registration before the draw, as Paper A
  did, or run it as a documented exploratory replay.
