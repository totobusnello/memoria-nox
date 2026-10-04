## 3. Execution: the realized window is not the projected one

The trial went `active` on **2026-09-01 at 10:25:39Z** and the dose was switched off on
**2026-09-21 at 09:43:05Z**, closing the window at the `2026-09-20` epoch.

| | epochs |
|---|---:|
| registered design | 234 |
| designated in the realized window | **20** |
| served data | **19** |
| whole by clock exposure | **16** |
| partial by clock exposure | **3** (`09-01`, `09-03`, `09-20`) |
| empty | **1** (`09-02`, never served) |

Realized allocation over the 20 designated: **9 control · 6 at `w=2` · 4 at `w=4` · 1 at
`w=7.5`**, i.e. 9 control and 11 treatment.

**Correction.** Two different denominators, both correct, and we first wrote one number for both.

| analysis | epochs | why |
|---|---:|---|
| **ITT (§4.1–4.4)** | **20** | every designated epoch. `09-02` served no brief but its sessions produced **88 episodes**; it was designated control, and dropping it would be post-randomization conditioning — the exact defect §3.1 records us committing once already |
| **coverage and M10 (§4.5–4.6)** | **19** | coverage is defined over served briefs, and `09-02` has none. The quantity does not exist there, which is not the same as being zero |

An earlier draft said "19 analyzable clusters" throughout. That is the coverage
denominator applied to the ITT, and it is the family of error this project catalogues as
*a correct number attributed to the wrong population*.

**`09-01` is reported with both phases declared**, as §6 item 6 of the analysis spec
requires: 42 briefs in `shadow` until 10:22Z and 630 in `active` from 10:37Z, with no
overlap. The sensitivity leg that removes it is reported alongside.

### 3.0 The stopping rule, and a feasibility question we cannot yet answer

The trial closed at the `2026-09-20` epoch by a decision taken on 2026-09-21, executed by
`desliga-dose-p2.sh` at 09:43:05Z. It was not a data-dependent stop: no outcome had been
computed, and the analysis specification that governs this report was written on
2026-09-10, eleven days earlier. It was a calendar decision, and saying so is the whole of
the stopping rule.

### 3.0.1 `N = 234` was infeasible by construction, and the trial ran exactly as long as it could

An adversarial reviewer asked whether the fixed designation ages out of eligibility. It
does, and the measurement is unambiguous.

All 19 designated chunks live in `memory/entities/lessons/*.md`, the **global** sub-pool,
whose window is `freshGlobalMaxAgeDays = 30`. Their `source_date` is NULL in all 19, so
the predicate falls through to `created_at`, which is a **single value for all nineteen**:

```
created_at = 2026-08-21 22:51:23   (identical across all 19)
+ 30 days  = 2026-09-20 22:51:23   ← they leave the window together, in one instant
```

| | |
|---|---:|
| epochs registered | **234** (2026-09-01 → 2027-04-22) |
| epochs in which the designation is eligible | **20** (2026-09-01 → 2026-09-20) |
| share of the registered design that could carry an intervention | **8.5%** |

**After that instant the intervention is not weak: it does not exist.** A chunk that
fails `fetchFreshCandidates` never reaches the list handed to the boost provider, and the
boost is addressed **by id**. No value of `w` and no number of `freshSlots` reaches a
chunk that is not in the candidate list. For 214 of the 234 registered epochs, the
treatment arm and the control arm would have been **the same intervention**.

**This reframes the stopping rule and the headline.** The trial did not stop early. It ran
for the entire interval in which it could have an effect, and closed 51 minutes before the
designation expired. The `09-20` epoch is partial for this reason and not by arbitrary
truncation: the analysis spec's cut *"falls inside the epoch, at 22:51:23Z"* is that
instant.

**Caveat.** The under-powering is a property of the registration, not a consequence of the
realized window. `sizing.py` computed `N = 234` from the pilot; nothing in that
computation knew that the designation it would act on had a 30-day life. Both numbers are
ours, both were locked, and they are incompatible: the same shape as the H1b collision of
§4.4, on a larger object. A trial cannot be sized for 234 epochs on an intervention that
exists for 20.

We record two further facts so the finding is not overstated. The designation **passed**
the full eligibility predicate (file pattern, `importance/pain ≥ 0.7`, age ≤ 30 d) in
19 of 19 on 2026-09-09, in both the served corpus and `current.db`; expiry was a future
event, not a live defect. And the replay harness compensates for the window
(`cfgEm` offsets `freshGlobalMaxAgeDays`), so what stops biting is the **trial**, not the
instrument.

**Key point.** This was measurable on 2026-09-09 and was measured then, eleven days before the
close, in a session that recorded it and left the design decision open. It did not reach
this manuscript until an adversarial reviewer asked the question from the outside. The
finding is ours; noticing that it belonged in the paper was not.

### 3.1 Two classification errors of ours, and what they cost

**Correction.** We classified `09-20` with the wrong ruler. We first published *16+3+1* as
*"17 whole + 2 partial + 1 empty"*, having measured **delivery volume** (672 of 672
serving records ⇒ "whole") where the pre-registered spec classifies by **clock exposure**
(13.86 h of 24 ⇒ partial, included with offset). The rulers are different and the
pre-registered one is not optional. The error propagated to six places including a pushed
commit, and was presented as *"matches the spec exactly"* when only the **total** matched
and the decomposition (which decides whether the epoch enters with an offset)
did not. Corrected in `DEVIATIONS-FOR-PAPER.md` §10.31(1).

**Correction.** We derived the arm from the data instead of from the designation. The first pass
took each epoch's arm as the mode of its observed `active` dose. That is
post-randomization conditioning: the mode is a function of *when* `active` took effect.
The arm is taken from `ASSIGNMENT-SERVING.json`. Compared, the two agree on **0
divergences across 19 epochs**. The premise still changes, and it is the premise that goes
in a paper. This also voided a cross-validation we had claimed: comparing our own census
against the spec's table is not a second opinion, because both derive from the same
designation.

**Caveat.** The spec's own table **omits `09-10`**, summing to 19 against 20 allocated; it was
written on 2026-09-10 at 21:40 with that epoch still open. Including it gives 16 whole.
We record this rather than silently reconciling, because a spec that miscounts and an
analyst who miscounts are different failures with different fixes.

---

