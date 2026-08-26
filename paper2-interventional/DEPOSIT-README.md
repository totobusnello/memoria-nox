# Interventional Memory — pre-registration and evidence package

> *In the repository this file is `DEPOSIT-README.md`; in the deposit it is
> `README.md`. The repository's own `README.md` is a navigation index for
> contributors and points at working documents that are deliberately not
> deposited.*

**The study has not started.** No randomised epoch exists, no arm has been
assigned, and no outcome has been observed. Everything measured in this package
is **pre-treatment**. That is the point of depositing it now: the design, the
numbers that size it, and the rules that will analyse it are fixed and
timestamped **before** any data that could adapt them exists.

⚠️ **CORRECTED for v1.12.** This paragraph used to add *"over a historical
corpus"*. That was true of v1.11 and is no longer true of the whole package:
v1.12 adds a **pilot series of 2,221 live serving decisions** taken between
2026-08-21 and 2026-08-25 in `shadow` mode, plus the λ panel round over episodes
from 2026-08-15 to 08-20. Those are measurements over production traffic, not
over a frozen historical corpus. They remain **pre-treatment** — in 2,221 of
2,221 decisions the brief served was the control arm, and no arm has been
assigned — but the corpus is no longer the only thing measured. The distinction
matters because "historical corpus" invites the reading that nothing in this
package touched live serving, and something did.

## Start here, for v1.12

`AMENDMENT-v1.12.md` is the document this version exists for. It is
**descriptive**: it declares facts about the serving mechanism and the pilot
series, retracts **27** earlier claims with the measurement that replaces each,
and names the defects that must be fixed before the confirmatory study starts.
It deliberately specifies **no** estimand and fixes **no** `N` — with zero
outcome observed under treatment, neither is estimable from this series, and any
estimand written after seeing the series would be post-observational.

Read it before `PREREG-DRAFT.md`. Where the two disagree, the amendment is
later and says so; the registration is preserved as registered.

⚠️ **One defect is declared open rather than repaired.** The designation rule —
which chunk of a signature group receives the boost — is not validly frozen: it
consumes a constant whose referent the amendment retracts, the registered
tie-break names a column that does not exist, and exact ties occur in 4 of the 7
multi-member signature groups, where the designated chunk came from incidental
SQLite row order. The aggregates in the amendment are **reproducible** and **not
attributable** to a deterministic rule. `DECISION-designacao-2026-08-25.md`
carries the replacement options and a recommendation.

## What this is

Retrieval metrics (nDCG, recall) measure **representation**, not **decision** —
and an agent's memory exists to keep it from repeating costly actions. This is a
**pre-registered randomised crossover on live production traffic** that measures
that directly: fleet-wide 24 h epochs, arms assigned from a public randomness
beacon, a 2 h washout, and an outcome adjudicated by a panel of LLMs from three
distinct training families under a frozen, hash-locked prompt.

**The observation that retrieval is the wrong instrument is not ours.**
MemoryArena (February 2026) published it first. Our contribution is the
**method** — randomised, pre-registered, on traffic nobody selected — not the
diagnosis. `RELATED-WORK.md` states the boundary precisely, and no claim in this
package should be read against it.

## The locked design

| | |
|---|---|
| Epochs | **234** (2 arms for the primary; 4 groups — 117 control · 39 per dose), 24 h each, boundary 09:00 UTC |
| Detectable effect | **30%** relative, via Sec. 3's escape clause — the 20% target is *not* amended and is *not* reached |
| Sized on | the **upper** 95% confidence limit of the ICC, not the point estimate |
| ICC | **0.0985**, 95% CI **[0.0570 ; 0.1814]** (Searle, one-way), 30 clusters, m̄ = 55.96 over the 27 that carry ≥ 2 sessions |
| `r̂` / `p̂0` | **29.838403** opportunities per unit exposure / **0.111813** failure rate under control — the latter a **floor**, since unadjudicable outcomes sit in the denominator and can only move into the numerator |
| Design effect | **13.482928** at the ICC's upper limit, i.e. `1 + ((0.3833 + 1) × 50.4667 − 1) × 0.18141` |
| Cluster-size dispersion `cv²` | **0.3833**, measured over the same 30-epoch pilot window as every other sizing input |
| Calendar | 234 epochs from 2026-09-01, cap **323 days** (38% slack) |
| Severity cut τ | **S1**, outcome by strict majority; an exact tie resolves to `not_failure` |
| Treatment dose | `W_OUTCOME = w × Δ_cut`, `Δ_cut = 0.043`, `w ∈ {2.0, 4.0, 7.5}`, boosting **one designated chunk** per opportunity |
| Carry-over bound δ | **36.67** |

> **Two different `m̄` appear above and the difference is not a typo.** The ICC's
> `m̄ = 55.96` averages over the **27** epochs that carry at least two sessions —
> an epoch with one session contributes no within-variance and is excluded by the
> registered rule, reported rather than dropped. The design effect's
> `m̄ = 50.4667` averages over all **30**. Recomputing `DE` from 55.96 gives 6.41
> and will look like an error; it is the wrong denominator, not the wrong
> arithmetic.

> ### ⚠️ Amended 2026-08-17 — the design effect was computed for equal cluster sizes
>
> Earlier versions of this table published `N` = **174** beside a design effect of
> **5.87**. Two things were wrong with that pair.
>
> First, they came from **different regimes**: 5.87 is the design effect at the
> ICC's *point* estimate, which sizes at 102 epochs; 174 comes from the *upper*
> limit, whose design effect is 9.9738. One table, two regimes, nothing marking
> the difference.
>
> Second — and this is what moved `N` — both values used
> `DE = 1 + (m̄ − 1) · ρ`, which assumes **equal cluster sizes**. Epoch sizes here
> run from 1 to 115 sessions (`cv²` = 0.3833), so the correct form is
> `DE = 1 + ((cv² + 1) · m̄ − 1) · ρ`. The equal-size formula *understates* the
> design effect, hence understates the variance, hence **under-sizes the study** —
> the one direction the registration's own sizing lock exists to forbid. `N` = 174
> therefore never satisfied the standard it was written to satisfy. Corrected:
> **`N` = 234**, design effect **13.482928**, allocation **117 / 39 / 39 / 39**
> (exact, where 174 required rounding to 87 / 29).
>
> This is an **error correction plus a feasibility update**, not a re-size. The
> MDE stays at 30%; `r̂`, `p̂0`, the ICC and its interval, `m̄`, `λ₀`, `δ`, the dose
> band and every reachability number are untouched — `cv²` enters the variance,
> not the rate. The amendment is published **before any epoch is randomised,
> before any arm is assigned, and before the beacon round that seeds the
> assignment has been drawn**, so no outcome or arm label existed anywhere that
> could have informed it. `sizing.py` without `--cv2` still returns 174 and
> `assign_arms.py --epochs 174` still reproduces the published sequence, so the
> superseded record stays executable rather than overwritten.
>
> Found by an adversarial voice asking whether the design effect assumed equal
> cluster sizes — a question about a **formula's applicability**, which
> recomputing the arithmetic could never have surfaced, because the arithmetic was
> correct for the formula used.

Two consequences are registered **before** any arm data exists, so that widening
them later is visibly an amendment rather than a refinement.

> ### ⚠️ Read the next two blocks against `AMENDMENT-v1.12.md` §1.1
>
> They are the v1.11 text, preserved. Two things in them the amendment retracts.
>
> **The phrase "by construction."** The amendment declines to use it in any
> substantive claim, because it was the phrase that carried the defects of 16 and
> 17 August, and because v1.11 showed a guarantee of that shape can be voided by
> an operational failure. The *claim* it decorates here — that the boost acts on
> the coverage slots and never on the primary ones — **survives**, and the
> amendment re-derives it from the code: the boost is added to salience inside
> `ordenarCobertura`, which orders only the coverage candidates. It survives as a
> property of the code path, not as a construction.
>
> **The arithmetic about "clearing the main cut."** The amendment finds no
> threshold comparison in the serving code at all, and finds that the registered
> `0.8524` is one agent's measurement generalised into a system constant, lying
> outside the span later measured across agents (0.610–0.792,
> `CUTS-MEASURED-2026-08-18.json`). The margins quoted below — `0.0214`,
> `0.2151`, "6.75 days" — are arithmetic over that constant, and are correct
> arithmetic over a quantity whose referent the amendment retracts. They are kept
> because the superseded record should stay legible, not because they still
> license a conclusion.

**First: the boost acts on the two coverage slots and never on the eight primary
ones — by construction.** Until 2026-08-17 this package derived that from
arithmetic instead: at the band `w ∈ {0.5, 1.0, 2.0}` no dose could clear the
main cut, the best case falling `0.0214` short. That margin is exact for
`w = 2.0` at severity S4, the top of the **old** band, and it stopped being true
when the band became `{2.0, 4.0, 7.5}` on 2026-08-16 — at `w = 7.5` the best case
**exceeds** the main cut by `0.2151`, and an S2 chunk crosses it up to 6.75 days
of age. The restriction is now a property of where the boost is applied, which is
also how every reachability number in this package was measured, rather than a
consequence that a change of band could silently repeal. `PREREG-DRAFT.md` §2
carries the full correction and the three neighbouring claims that went stale
with it.

**Second: the population the treatment can reach depends on the arm, and reaching
the modal failure is the top arm's property alone.** S1 is 69.73% of failures and
needs `w = 5.97` at age zero, rising to 6.03 at 24 h and 7.49 at 30 days; the
band's top is 7.5. So S1 is unreachable at `w = 2.0` and `w = 4.0`, and reachable
at `w = 7.5` within a 30-day window — a margin of 0.0056 in `w`, far too thin to
be treated as a design property. S2 (29.62%) enters from `w = 2.0`, and S3 and S4
from below the band entirely.

The age condition is not a caveat added in prose; it is measured. The written
chunk's salience decays as `2^(−age/180)` through the 0.15-weighted recency term,
and Sec. 3 requires the chunk to be at least 24 h old before it can act. At 24 h
an S2 episode needs `w = 1.85`, inside the band; at **6.66 days** it crosses
`w = 2.0` and is out of reach at that dose — though not at `w = 4.0`, whose
salience arithmetic carries S2 to 97 days. That last figure is a property of the
cut, not of what the system will serve: the coverage pool admits a candidate only
within 30 days, so the 97 is unreachable in practice and is quoted here only
because the decay table in Sec. 2 states it. The dose table in Sec. 2 is a **freshest-case ceiling**,
published with the decay alongside it rather than as a single number.

A third constraint, measured on 2026-08-17 and not visible in the reach
arithmetic at all: the coverage pool is filtered by **age** as well as salience —
7 days in the agent-scoped pool, 30 in the global one. It costs `w = 2.0` exactly
nothing (that dose only ever reaches S2, which the 6.66-day cliff already caps
below the window), 18.45 points at `w = 4.0` and 11.94 at `w = 7.5`. **H1's
testability rests on the `w = 2.0` ceiling of 60.18% against a 30% MDE, so the
primary contrast is untouched**; the cost falls on the dose–response arms.

## How to check that this was fixed in advance

The package does not ask to be believed. Three mechanisms make it checkable:

**Seeds declared before the randomness existed.** Each sampling seed names a
`drand` (League of Entropy, quicknet) round, and the file naming it was committed
and pushed to a public repository *before that round was emitted* — ten minutes
before, in the case of extension 2. Repository history is the precedence stamp.
`CALIBRATION-SEED.md`, `EXTENSION-SEED-2026-08-11.md`,
`EXTENSION-2-SEED-2026-08-14.md` each carry the chain hash, the round, the
derivation rule and a shell command a third party can run.

**Artifacts pinned by hash.** `extract_episodes.py` (SHA-256
`e860357bd9f1fc0690ec8a817b7f6d23ac0c237882152d3a8714f7c0af7748b2`) and the
adjudication prompt body (`5b22f02c1a557417fe874b98cdf8a3ad6441cada74d69ace8e54f82b3438b03e`,
in the file `adjudication_prompt.md`, which itself hashes to `3767fdb5…`) are
locked. The prompt hash governed all 1,685 adjudication calls executed to date.
The corpus the taxonomy was derived over is frozen by hash in
`CORPUS-FREEZE.md`.

**Scripts with no dependencies.** `sizing.py`, `pilot_replay.py` and
`assign_arms.py` are pure standard library on purpose — a third party must be able to run them without
installing anything. `scipy` appears only in a test that confronts the
hand-rolled F distribution against it, never in the canonical path.

## What is here

**The amendment (new in v1.12)**
`AMENDMENT-v1.12.md` — read first; see *Start here* above.
`DECISION-designacao-2026-08-25.md` — the open designation defect, its
requirements and the replacement options.

**The pilot series, and the guard that pins it**
`p2-serving-WINDOW-2026-08-25.ndjson` — the 2,221 serving decisions, clipped to
the closed window `[2026-08-21T22:57:00Z ; 2026-08-25T10:22:00Z]`. Integer chunk
ids, timestamps and mode flags only; no corpus content.
`pilot_window_stats.mjs` — emits every series figure the amendment cites, and
accepts `--assert-json` to fail if the window stops reproducing
`PILOT-WINDOW-2026-08-25.json`. The live log grows 28 records an hour, so a count
cited as a snapshot would go false inside an immutable deposit on its own; the
window is declared closed and the guard is deposited so a third party can run it
rather than trust the prose.

**λ, and where the treated population's size comes from**
`LAMBDA-SEED-2026-08-21.md` — the sampling design, locked before the sample:
population 1,305, stratum A a census of 48, stratum B 242 drawn from 1,257 by
`SHA256(seed ‖ episode_id)`. `LAMBDA-RESULTS-2026-08-21.md` — the
Horvitz-Thompson estimate and the limitation that matters: 22 of 22 consolidated
S2 verdicts carry `xai = S2`, so the size of the treated population depends on
one panel family's severity calibration.

**The serving code itself (new in v1.12)**
`serving-brief.ts` · `serving-brief-diversity.ts` · `serving-brief-outcome.ts` ·
`serving-salience.ts` · `serving-search.ts`, with path, commit, date, size and
sha256 in `SERVING-CODE-MANIFEST.md`. Until v1.12 the code carrying the mechanism
lived only on a private host, so every citation of the form `brief.ts:608-618`
was unauditable by whoever read the registration — a defect the amendment's §7
declares and this closes. ⚠️ These are the **modules, not the system**: they
import from parts of the package that are not deposited, so they are auditable
and **not executable standalone**. That is narrower than reproducibility and is
the honest claim.

**The cuts, measured rather than assumed**
`CUTS-MEASURED-2026-08-18.json` · `cuts_measure.mjs` ·
`AUDIT-SECTION2-SERVING-2026-08-18.md` · `SHARES-PROVENANCE-2026-08-19.md` ·
`reachable_share_fila.py` — the last is a one-line variant of
`reachable_share.py` under the amended reading of `CUT_FRESH`, and its dose band
is now parsed by `claims_check.py` rather than merely allowlisted.

**The registration**
`PREREG-DRAFT.md` — the registered document, registered as v1.11 and preserved
as registered, save for one added block that declares itself to be outside the
registered copy (the OSF GUID, which could not exist before it was minted).
Everything the design decides is here or cited from here.
`PREREG-v1.11-2026-08-17.pdf` / `.html` are the v1.11 document rendered — they
are **not** re-rendered for v1.12 and do not contain the amendment; the Markdown
is authoritative and `AMENDMENT-v1.12.md` is later than all three.

`render_ascii.py` · `render.css` · `RENDER.md` — how the PDF and HTML are
produced, deposited so that the rendered copies are checkable rather than
merely present. `render_ascii.py` transliterates symbols but never values, and
**aborts if the multiset of numeric tokens differs between input and output**;
`RENDER.md` records the four ways that guard was wrong before it was right, each
of which looked like success. It exists because a mechanical rewrite already
damaged this document once: the decimal-separator pass of v1.4 turned
`a ∈ {0,1}` into `a ∈ {0.1}`, and it stood in four deposits before anyone read
it. Unlike the analysis scripts these are not dependency-free — they need
`pandoc` and a headless Chrome — which is why the Markdown, not the PDF, is
authoritative.

**How the design was sized, and what is uncertain in it**
`SIZING-2026-08-14-v2.md` · `STABILITY-TEST.md` ·
`WASHOUT-SENSITIVITY-2026-08-14.md` · `LINK-FEASIBILITY-2026-08-15.md` ·
`DOSE-REACH-2026-08-15.json`

**Provenance and precedence**
`CORPUS-FREEZE.md` · `corpus-manifest-20260729T094609Z.txt` ·
`CALIBRATION-SEED.md` · `EXTENSION-SEED-2026-08-11.md` ·
`EXTENSION-2-SEED-2026-08-14.md`

**Where this sits in the literature**
`RELATED-WORK.md` — read before reading any novelty claim.

**The instruments**
`assign_arms.py` — **the randomisation itself.** It produces the epoch→arm
sequence from the beacon-derived seed, and the same code path produces the
permutation draws for the sharp-null test, so the test cannot drift from the
design it is testing. `verify` recomputes a published sequence and re-checks
the registered balance tolerance. Until 2026-08-16 the registration referred to
this script as if it existed; it did not.

`claims_check.py` — **the guard against the defect that produced this version.**
Three passes: it recomputes every *derived* band-dependent quantity from the
frozen constants; it sweeps the package, recursively and in both languages it is
written in, for the superseded phrasings, allowing them only in a file that is
both named in its allowlist and carries a correction marker; and it cross-checks
the *measured* figures by parsing the band declaration out of the other scripts
and reading the reach shares back out of the JSON artifact. `--show` prints the
table.

It exists because prose asserting a computed result is a cache with no
invalidation: nothing links the sentence to the parameter it depends on, and a
reviewer checks whether the sentence is coherent, not whether its inputs still
hold. Its own docstring states what it does **not** cover, including two
overclaims an external review found in an earlier version of that very
paragraph. Its phrase list is a list — it catches the shapes that have already
failed here, not shapes nobody has written yet — and its "ok" should be read as
*none of the known failure shapes are present*, never as *the package is
consistent*.

`extract_episodes.py` (locked) · `sizing.py` · `pilot_replay.py` ·
`reachable_share.py` · `run_panel.py` · `icc_bootstrap.py` · `task_regret.py` ·
`delta_carryover.py` · `washout_sensitivity.py` ·
`maturity_sensitivity.py` · `stability_sample.py` ·
`dose_reach.mjs` · `link_feasibility.mjs`

**The adjudication**
`adjudication_prompt.md` (Portuguese, hash-locked — the prompt actually sent) ·
`adjudication_prompt.en.md` (informative English translation, **not**
interchangeable: a translated prompt is a different prompt and a different hash)
· `positive-control.jsonl` (synthetic, never enters the action corpus)

**Reading aids**
`OUTPUT-KEYS.md` — the scripts emit JSON with Portuguese keys, for the reason
given there; this translates them. `EXTERNAL-REFERENCES.md` — every reference in
this package that points outside it, and where it actually lives.

## What is deliberately not here

The **adjudicated verdicts and the episode corpus** are not deposited. They are
the contents of actions executed by live agents in production, and depositing
them would publish that. What is deposited instead is everything needed to check
the reasoning: the code that produced and consumed them, the seeds that
determine every sample, and the hashes.

This is a real limitation and it is stated rather than implied: a third party can
verify every seed, every hash, and every computation, and can reproduce the
sampling given an equivalent archive — but cannot re-derive the verdicts.

## Language

The package is in English. Two exceptions, both deliberate:
`adjudication_prompt.md` is Portuguese because it is hash-locked and translating
it would break the lock; and the scripts' JSON output keys are Portuguese because
they are the names under which every published number was recorded — renaming
them would make the scripts' output disagree with the documents. `OUTPUT-KEYS.md`
translates them.

## Honest reading of the state

Four things a reviewer should know without having to dig for them:

1. **The panel cannot prove it judged with `glm-5.2`** on verdicts collected
   before 2026-08-14. The provider began serving `glm-5.3` for `glm-5.2`
   requests and the harness recorded only the request. It records the served
   model from now on; it cannot do so retroactively.
2. **Two corpus epochs are partial** (2026-08-11 and 2026-08-14) through
   right-censoring at extraction, declared before adjudication rather than after.
3. **30 clusters is Sec. 9's floor, not slack.** The ICC interval is wide, and
   the width is worth more calendar than the point estimate is.
4. **The positive control was completed unblinded**, on 2026-08-15, after the
   other four verdicts were known. It is reported because a result obtained
   unblinded and declared is worth more than a gap explained away.

## Citation

Cite the DOI of this deposit. The pre-registration is versioned; `PREREG-DRAFT.md`
carries its own version and a dated record of every lock and every correction,
including the ones that were wrong the first time.
