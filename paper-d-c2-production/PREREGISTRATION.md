# Paper D: criterion C2 on the production corpus. Pre-registration (DRAFT, not fixed)

Status: draft of 2026-11-05, written from `PROTOCOL-DRAFT.md` (all nine decisions taken, §11 there)
and the smoke (`SMOKE-2026-11-05.md`). It becomes binding when the tag `paper-d-prereg-v1.0` is
pushed; nothing listed under "Order" (§6) may run before that push. The scripts it names are
written and tested before the tag; until then this document and they may still change, and every
change after an adversarial review is listed in §10.

## 1. Question

Paper 3 found, on LongMemEval, that replacing the deployed extraction criterion C0 with the
revised criterion C2, at the full window, raised answer accuracy by +24.8 to +27.3 pp across two
judge families (`paper3-construction/CONFIRM-RESULT.md`, row "criterion, 11 − 10"). That benchmark
is personal chat. The memory this system builds is from agent work sessions: engineering
decisions, paths, commands, lessons, in Portuguese and English.

**Does C2 extract a more useful memory than C0 from the same production sessions?**

The question is asked offline, on sessions frozen before any call, with no deploy. The product's
"second wave" depends on the answer (`docs/DECISIONS.md`, D-2026-11-04).

## 2. Material

- **Archive.** Transcripts are read from the action archive on the serving host, the only place
  where sessions older than 7 days survive (`PROTOCOL-DRAFT.md` §4.1). The listing of the archive
  taken on the freeze day is hashed into the freeze commitment.
- **Freeze date.** The UTC date of the tag. Eligible sessions have their last event between
  2026-08-15 (start of the archive) and the freeze date minus 7 days, so that the archive holds
  the final transcript (`PROTOCOL-DRAFT.md` §4.2).
- **Frame.** Eligible sessions with cleaned prose of at least 3,000 characters (the rule of
  `audits/2026-10-26-replay-build.py`) that the production distiller reached, i.e. with a row in
  `session_distill_log` (the behavioural test of `audits/2026-10-26-construction-tax-probe.md`,
  Defect 2). Excluded by id, with the counts published: the 20 sessions spent on 2026-10-26/27 and
  the 5 sessions of the smoke. Sessions the distiller reached but from which it stored no unit stay
  in the frame: dropping them would select on the comparator's output.
- **Census on 2026-11-05** (`d-frame-census.py`, output `FRAME-CENSUS-2026-11-05.json`, window
  2026-08-15 to 2026-10-29, live database read-only): 634 eligible, of which 414 logged (126 with
  stored units, 288 with none) and 220 never logged, all of those in the directories of four agent
  workspaces and `-tmp`. Of the 414 logged sessions, 410 have under 50,000 characters of prose.
  The frame on the freeze day is recomputed; these figures are what the design was set on.
- **Database copy.** The daily snapshot of the freeze day (`daily-main`, 03:00 UTC), decompressed
  on the host outside `/tmp` and deleted after use, with the sha256 of the `.gz` recorded. From it,
  for each drawn session: the units production stored (`chunks` under `sessions/`), the
  `processed_at` (the maximum across agents, as in `audits/2026-10-27-see-once-probe.py`) and the
  `chunks_extracted` of its log rows.
- **Deployed criterion.** The sha256 of the deployed `src/session-distill.ts`, and a check that its
  `DISTILL_SYSTEM` equals the C0 text in `paper3-construction/lme-run.py`. If they differ, C0 is
  the deployed text, and the difference is reported.
- **Privacy.** Session ids, transcripts, questions, citations, units and answers stay on the host
  or in a private directory under `~/Backups/`. The repository receives code, counts, hashes and
  aggregate results only.

## 3. Draw and questions

- **Draw.** `d-freeze.py`, seed `20261106`: the frame sorted by session id and shuffled once; the
  first 80 sessions are the sample, and the rest of the order is kept for the extension below. No
  strata: with 410 of 414 sessions under 50,000 characters, the size bands of the draft
  (`PROTOCOL-DRAFT.md` §4.3) would leave 4 sessions in the upper two; the bands are reported as a
  description.
- **Windows.** The cleaned prose of each session, cut as in `audits/2026-10-26-replay-build.py`: a
  window of 20,000 characters from the start and one from the middle (starting at half the length
  minus 10,000), each kept only if it has at least 3,000 characters, and the middle one only if it
  does not overlap the first, so no fact is asked twice from the same text.
- **Writer.** `glm-5.3` (Z.ai), a family that is neither the distiller and reader (Gemini) nor
  judge 1 (OpenAI), temperature 0. Two prompts, fixed in `d-generate.py` as in `d-smoke.py`:
  **primary**, up to 4 facts per window in C0's declared categories (decision, preference, lesson,
  context; the categories of `audits/2026-10-26-replay-generate.py`); **secondary**, up to 3 facts
  per window in the two classes C2 adds (an exact identifier asked so that the answer is the
  identifier letter by letter; a concrete fact said in passing). The two sets are never pooled.
- **Validation, fixed now.** A fact is kept only if it has a question, a short answer and at least
  one citation, and every citation is a byte-exact substring of its window. Questions must name
  their entities (the prompt says so; it is not checked mechanically). Drops are counted by reason
  and published.
- **Evidence region.** The span from the first to the last character of the fact's citations, plus
  1,500 characters on each side, inside the window (`audits/2026-10-27-net-value-and-see-once.md`).
- **Extension, by yield only.** The smoke kept 3.4 primary questions per session, and the smallest
  sample it sized was 232 primary questions (`SMOKE-2026-11-05.md`: discordance 0.20, 10 pp, design
  effect 1.5). If the 80 sessions yield fewer than 232 primary questions, the next sessions of the
  drawn order are added in blocks of 10 until the count is reached or 120 sessions are in. The
  decision uses only the number of questions written from raw prose, before any distillation or
  answer exists.

## 4. Arms, reader and judges

All arms read the same questions from the same frozen sessions, so every contrast is paired.
Components are those of `paper3-construction/lme-run.py`, imported, not copied.

| arm | material | role |
|---|---|---|
| **A** | the question's evidence region | ceiling; floor of the contradiction predicate |
| **C0** | every unit distilled under C0 from the session's complete prose | comparator |
| **C2** | every unit distilled under C2 (`DISTILL_SYSTEM_V3`) from the same prose | treatment |
| C2-cut | every unit distilled under C2 from the prose with every evidence region of the session's questions removed | positive control |
| C0-cf, C2-cf | units distilled under C0 and C2 from the counterfactual rewrite (§5.3) | counterfactual control |
| P | the units production stored for the session (from the freeze-day snapshot) | fidelity control |
| V | every unit distilled under C0 from the visible prefix: the turns with timestamp at or before `processed_at` | fidelity control |

P and V are controls of the re-implementation, not arms of any contrast; decision D3 (no as-built
arm) stands.

- **Distillation:** `lme-run.distill`, `gemini-2.5-flash-lite`, temperature 0.1, blocks of 2,000
  characters per session that never split a line, `is_noise_static`, `importance >= 0.5`, at most
  10 items per block (the prompt's own ceiling). Each block is distilled once per criterion and
  reused. Failed blocks are counted; V also applies production's rule that a session with fewer
  than 3 messages never reaches the model (`audits/2026-10-27-see-once-probe.py`).
- **Serving:** all units of the session, importance descending, ties by block then position, each
  line `[<last event date>] [<category>] <text>` (Paper 3's §12.3 order). No retrieval.
- **Reader:** `lme-run.answer`, reader R0, the production `ANSWER_SYSTEM`, `gemini-2.5-flash-lite`,
  temperature 0, `NAO SEI` allowed (decision D6). Question line `PERGUNTA: <question>`.
- **Judge 1** (registered): `gpt-6-luna`, CONTEM / CONTRADIZ, correct iff P(contem) > 0.5.
- **Judge 2:** `lme-run.judge2`, the family-2 prompt on `gemini-2.5-flash-lite`, on every row.
- **Spend cap:** US$ 10 in the runner's ledger; the writer is not priced by the ledger and its
  calls are counted.

## 5. Hypotheses, controls and analysis

### 5.1 Controls, read first

The contrasts are read only if all four controls pass. If any fails, H-D1 and H-D2 are reported
as not interpreted (an instrument failure), with every number, as in Paper 3's stage 1.

| control | measured on | passes when |
|---|---|---|
| ceiling | arm A, primary set, judge 1 | accuracy ≥ 0.70 (judge 2's figure is reported, not gated) |
| positive | arm C2-cut, primary set, judge 1 | accuracy ≤ 0.10 |
| counterfactual | §5.3 | answers with the original number ≤ 10%, and fewer than with the altered number |
| fidelity | arms P and V, primary set, judge 1 | the two accuracies differ by at most 0.05 |

### 5.2 Hypotheses

**H-D1 (primary).** On the primary set, under judge 1, the mean over questions of
Y(C2) − Y(C0), where Y = 1 if the answer contains the reference fact. Interval: 95% percentile
bootstrap with sessions as clusters, 10,000 resamples, seed `20261106`. Reading: lower bound > 0,
**C2 better**; upper bound < 0, **C0 better**; otherwise **not shown**, and in that case the paper
says whether the interval excludes +0.10, the smallest effect the sample was sized for. The same
interval under judge 2 is the bracket: C2 is said to be better across judge families only if both
lower bounds are above 0; a disagreement is reported as judge-dependent.

**H-D2 (secondary).** The same contrast, interval and reading on the secondary set (C2's two
classes). Reported apart and labelled secondary.

No prediction of size is registered. Paper 3's effect was measured on another corpus; the smoke
saw 2 discordant pairs in 17 primary questions, which decides nothing.

### 5.3 Counterfactual construction

Eligible: primary questions whose reference answer contains a run of digits that also occurs in
one of its citations. A seeded subsample (seed `20261106`) of up to 30. For each, the session's
prose is rewritten: every occurrence of that run as a whole token (not adjacent to another digit)
has its last digit d replaced by (d + 5) mod 10. The rewritten session is distilled under C0 and
C2 and the question answered from each. The check is mechanical, with no judge: whether the answer
contains the original run or the altered run as a whole token. Pooled over the two arms. With fewer
than 10 eligible questions the control is reported as not testable, and the reading goes on with
that stated.

### 5.4 Blind human sample (mandatory, decision D8)

`d-human.py make` draws 60 rows uniformly from the (primary question, arm) pairs with arm C0 or
C2, seed `20261106`, and writes a sheet with the question, the reference answer and the candidate
answer, without the arm or either judge's output. The sheet's header states the predicate the
grader applies: `contem` = s if the answer contains the fact in the reference answer, n otherwise
(a `NAO SEI` is n). The author grades it before any contrast is read. `d-human.py commit` writes
`HUMAN-COMMITMENT.json` (the sheet's sha256, the counts, and the sha256 of the results it was drawn
from). `d-human.py agree` reports agreement and Cohen's kappa with judge 1. No threshold is
registered; if kappa is below 0.4, the paper states that its judge-dependent conclusions are not
validated by a human.

### 5.5 Descriptive, no threshold

Accuracy per arm and judge; the effect by C0 category and by prose band; on the sessions from which
production stored no unit; units per session under C0 and C2; distillation failures; contradiction
(CONTRADIZ) per arm, with no arm said to cause damage unless its rate exceeds arm A's; discordant
pairs and the exact McNemar test, which ignores the clustering; the volume of V against
`chunks_extracted`; the drops of generation by reason.

## 6. Order

1. This document and the scripts it names are fixed by the tag `paper-d-prereg-v1.0`, pushed to
   the public repository. The smoke ran before the tag on 5 sessions now excluded; it used seed
   1105001, never `20261106`.
2. **Freeze.** On the serving host, read-only, on the tag's date: `d-freeze.py` lists the archive,
   computes the frame, draws, copies the drawn sessions and reads the snapshot (§2). The private
   copy goes to `~/Backups/` with a manifest of sha256 per file. `FREEZE-COMMITMENT.json` (frame
   counts, exclusions, seed, the sha256 of the listing, of the ordered draw, of the manifest and of
   the production units, the snapshot's sha256, and the deployed-criterion check) is committed and
   pushed before step 3.
3. **Questions.** `d-generate.py` writes the questions, applies the extension rule and commits
   `QUESTIONS-COMMITMENT.json` (the sha256 of the questions file, of the prompts and of the writer
   cache, counts by set and category, drops by reason, sessions used), pushed before step 4.
4. **Run.** `d-run.sh` executes the code extracted from the tag (`git archive`), not the working
   tree, reads both commitments from their commits on `origin/main` and checks every hash against
   the private files before the first paid call. It distils, answers and judges every arm, and
   prints no accuracy: only counts, cost and the sha256 of `results.json`.
5. **Human sample.** Made from `results.json`, graded blind, `HUMAN-COMMITMENT.json` pushed.
6. **Reading.** `d-read.sh` refuses to run until the human commitment is on `origin/main`,
   descends from the questions commitment, and names the sha256 of the `results.json` it is given.
   It reads the controls, then H-D1 and H-D2, then the descriptives.
7. Each commitment file is written once: every script that reads one refuses if a commit other than
   the one given has touched it.

## 7. What this cannot show

That the result holds on another corpus, another language or another system; that questions a
model writes from a transcript behave like questions a user would ask; that the judge is right
beyond what the human sample measures; or what C2 would do inside production, where the distiller
sees a growing session once (`PROTOCOL-DRAFT.md` §10): the arms here read the complete prose, so
the contrast is the criterion alone. Production sessions are short (410 of 414 under 50,000
characters), so the result describes short sessions.

The order of §6 is enforced by the scripts on the registered path and evidenced by the public
history. The scripts cannot stop the person who runs them from computing a reading privately; what
they guarantee is that the reported reading came from the published, ordered commitments.

## 8. Deviations

Any change after the tag (a frame that differs from the census in kind, a deployed criterion that
differs from C0, a call that cannot be retried, a control that cannot be built) is reported with
the result, with what was done and why. None turns a result that did not hold into one that did.

## 9. What changed from the protocol draft

1. **Frame.** The draft's frame (sessions the distiller reached) is applied. The smoke's pool of
   639 did not apply it; 414 of its 634 non-smoke sessions pass it.
2. **No size strata.** The draft stratified by prose band; 410 of 414 sessions are in the lowest
   band, so the draw is uniform and the bands are descriptive.
3. **Sample size.** 80 sessions (D4), with the extension by yield of §3.
4. **Windows.** The middle window is kept only when it does not overlap the first; the smoke's rule
   allowed an overlap in sessions between 20,000 and 40,000 characters.
5. **Distillation temperature** is 0.1, the value in `lme-run.py`; the draft said 0.
6. **Fidelity** is read on accuracy, with production's stored units and the visible-prefix
   re-distillation as two control arms, as in `audits/2026-10-27-neither-cause-explains-it-alone.md`
   ("fidelity, now on accuracy"). D7's "within 5 points" is read as accuracy points.
7. **Serving order** of units fixed as in Paper 3; the smoke served them in block order.

## 10. Review before fixing

None yet.
