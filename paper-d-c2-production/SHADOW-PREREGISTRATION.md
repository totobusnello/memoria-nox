# C2 against C0 on production's own blocks: pre-registration

Written 2026-11-07, after the shadow was turned on (`SHADOW-PROTOCOL.md`) and before any record
beyond the deviation in §9 was read. Nothing here is fixed until the tag
`paper-d-shadow-prereg-v1.0` is on the public main branch. Proposed by the session on 2026-11-07;
the author asked for it to be checked («checa a leitura do shadow que vc mencionou»), and decided
its two open points on 2026-11-07 08:05 BRT («3. excecao aqui 4. ok»): the writer keeps Paper D's
family under an exception to the protocol's privacy rule for this study only (§3), and the
stopping rule stands (§2). On 2026-11-08 at 18:17 BRT the author approved the tag («segue com os
scripts do shadow»), after the scripts of §6 passed their offline tests; paid calls still wait for
the steps of §6 in order.

## 1. Question

Paper D asked whether criterion C2 extracts a more useful memory than the deployed C0 from
production sessions, and its fidelity control failed: the offline replay kept the scheduled-job
prompts production drops, so the replayed C0 was not production's C0 (`NOTE.md` §4). The shadow
records, for every block production sends to its model, the block as sent, the units production's
C0 call returned for it, and the units a C2 call returned for the same block.

**On the blocks production actually distils, does C2 extract a more useful memory than C0?**

C0 here is production's own output, not a re-implementation, so the failure that stopped Paper D
cannot recur. What the records cannot say is in §8.

## 2. Material and stopping rule

- **Records.** The shadow files `c2-shadow-<UTC date>.jsonl` on the production host, private,
  never copied into this repository.
- **Excluded by date.** The file `c2-shadow-2026-11-07.jsonl` (3 sessions, 4 blocks), read beyond
  the permitted counts before this document existed (§9), and every later block of those three
  session keys.
- **Stopping rule.** Using only the counts `SHADOW-PROTOCOL.md` §5 permits
  (sessions, blocks, calls, failures, skips, cost), the freeze takes every record dated from
  2026-11-08 up to the first UTC date on which the eligible records reach 300 blocks from at least
  100 sessions, and not before 2026-12-01. If 2027-01-10 comes first, the freeze takes what exists
  on that date and reports the shortfall. The count is checked weekly and the check is logged.
- **Eligible block.** A record whose C2 call succeeded (`c2.ok`, no error), whose C2 prompt sha256
  is the registered one, whose block text hashes to its `block_sha256`, and whose block has at
  least 500 characters. The C0 side is taken as recorded, including blocks where C0 returned no
  unit: dropping those would select on the comparator's output. Failures and exclusions are counted
  and published.
- **Freeze.** On the freeze date the eligible records are copied from the host to a private
  directory under `~/Backups/` (mode 700); a commitment with counts, the date range, the seed and
  the sha256 of each file is committed before any question is written.

## 3. Questions

- **Unit.** The block: questions are written from one block's text and answered from units, so a
  question always has its evidence inside the material both arms were extracted from.
- **Writer.** `glm-5.3` (Z.ai), temperature 0, as in Paper D: a family that is neither distiller
  and reader (Gemini) nor judge (OpenAI). `SHADOW-PROTOCOL.md` §3 says the block text is sent to
  no service other than the C2 call; the author made an exception for this study only
  (2026-11-07, «excecao aqui»), recorded in §3 of the protocol: the text of the frozen eligible
  blocks may also be sent to the writer's provider, once per block, to write the questions. Nothing
  else changes in §3: the text stays private, out of this repository, and is deleted on the
  protocol's date.
- **Prompts.** Paper D's two prompts (`d-generate.py`), applied to a block instead of a 20,000-
  character window: **primary**, up to 2 facts per block in C0's declared categories; **secondary**,
  up to 2 facts per block in the two classes C2 adds (an exact identifier, a concrete fact said in
  passing). The two sets are never pooled.
- **Validation.** Paper D's rules, unchanged: malformed, answer over 25 words, category outside the
  set, no citation, citation not a byte-exact substring of the block; each drop counted by reason.
- **Draw.** If the eligible blocks yield more than 400 primary questions, 400 are drawn uniformly
  (seed: first eight hex digits of the tag commit); otherwise all are used. The secondary set is
  drawn the same way, seed + 1.

## 4. Arms, reader and judges

| arm | material served for a question | role |
|---|---|---|
| **A** | the question's evidence region (citations plus 1,500 characters each side, inside the block) | ceiling |
| **C0** | every C0 unit production returned for the session's eligible blocks | comparator |
| **C2** | every C2 unit the shadow returned for the same blocks | treatment |
| C2-cut | C2 units for the session, with the question's block re-distilled under C2 after removing every evidence region of its questions | positive control |

- **Serving:** Paper D's order and format (importance descending, ties by block then position,
  `[<date>] [<category>] <text>`); `(vazio)` when there is none. No retrieval, no dedup on either
  side, because the shadow records C0 before production's dedup and C2 is never deduplicated.
- **Reader:** `lme-run.answer`, reader R0, production's `ANSWER_SYSTEM`, `gemini-2.5-flash-lite`,
  temperature 0, `NAO SEI` allowed.
- **Judge 1:** `gpt-6-luna`, CONTEM / CONTRADIZ, correct iff P(contem) > 0.5 (Paper D's).
- **Judge 2:** `lme-run.judge2` on `gemini-2.5-flash-lite`, every row.
- **Spend cap:** US$ 5 in the runner's ledger; the writer's calls are counted.

## 5. Controls, hypotheses and analysis

### 5.1 Controls, read first

| control | measured on | passes when |
|---|---|---|
| ceiling | arm A, primary set, judge 1 | accuracy ≥ 0.70 |
| positive | arm C2-cut, primary set, judge 1 | accuracy ≤ 0.10 |
| record integrity | every eligible block | block hash matches; C2 prompt hash is the registered one; no C2 unit with importance below 0.5 |

If a control fails, H-S1 and H-S2 are reported as not interpreted, with every number.

### 5.2 Hypotheses

**H-S1 (primary).** On the primary set, under judge 1, the mean over questions of
Y(C2) − Y(C0), Y = 1 if the answer contains the reference fact. Interval: 95% percentile
bootstrap with sessions as clusters, 10,000 resamples, seed of §3. Reading: lower bound > 0,
**C2 better**; upper bound < 0, **C0 better**; otherwise **not shown**, with whether the interval
excludes +0.10. The same interval under judge 2 is the bracket: C2 is said to be better across
judge families only if both lower bounds are above 0.

**H-S2 (secondary).** The same on the secondary set, reported apart.

### 5.3 Human sample

Paper D's §5.4, unchanged: 60 (primary question, arm) rows with arm C0 or C2, blind, graded before
any contrast is read; Cohen's kappa with judge 1 reported; below 0.40 the paper says its
judge-dependent conclusions are not validated by a human.

### 5.4 Descriptive, no threshold

Units per block under C0 and C2; blocks where either side returned none; accuracy per arm and
judge; the effect by agent and by C0 category; contradiction per arm; tokens and cost per arm.

## 6. Order

1. Tag `paper-d-shadow-prereg-v1.0` with this document and the scripts it names.
2. Weekly count checks (§2), logged; nothing else read.
3. Freeze and its commitment.
4. Questions written and validated; questions commitment.
5. Arms, reader and judges; results commitment.
6. Human sheet, graded and committed.
7. Reading, then the note. The block text on the host and in the private copy is deleted when the
   note is deposited, or on 2027-06-30, whichever comes first (`SHADOW-PROTOCOL.md` §3).

Each script refuses to run unless the previous commitment is on the public main branch and
byte-equal to its private file, as in Papers B and D. Scripts are written and tested offline
(synthetic records, stubbed calls) before the tag: `s-common.py`, `s-count.py`, `s-freeze.py`,
`s-generate.py`, `s-run.py`, `s-human.py` and `s-read.py`, tested by `s-test.py`.

## 7. Cost

Expected: a few hundred blocks; distillation for C2-cut only (C0 and C2 already exist); reader and
judges over two sets and four arms. Paper D's whole reading cost US$ 0.75 with eight arms; this
design is under the US$ 5 cap by a wide margin.

## 8. What a result can and cannot say

It compares C0 and C2 on production's own input, block by block, with C0 being what production's
call returned. It cannot say what C2 would do once ingested: C2 units never enter the database, the
dedup, the brief or retrieval. The record does not hold which model served production's C0 call;
if production fell back from Gemini to its second provider on some blocks, those C0 units come from
another model, and the distiller's log is used to count such runs and report them. Blocks are
production's 2,000-character split, so facts that span two blocks are asked of one only.

## 9. Deviation before this document

On 2026-11-07 at about 01:55 UTC the session that wrote this document, checking that the first
shadow run worked, read beyond the counts `SHADOW-PROTOCOL.md` §5 permits: the text of the C0
units of the four blocks in `c2-shadow-2026-11-07.jsonl`, and the number of units per arm in those
blocks. No C2 unit text was printed. Those blocks and their sessions are excluded (§2). Nothing
else in the shadow directory has been read beyond the permitted counts.
