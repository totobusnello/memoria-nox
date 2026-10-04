## Appendix A — Relation to the pre-registration

There is a public pre-registration (OSF `yf7d2`, Zenodo `10.5281/zenodo.22110203`) and **this paper
is not the study it registers.** The registration covers an **interventional** study — designating
chunks, serving a dose, estimating an effect — which went `active` on **2026-09-01 at 10:25:39Z**
and whose dose was switched off on **2026-09-21 at 09:43:05Z**, closing the window at the
`2026-09-20` epoch. Of 234 registered epochs, 20 were realized and 19 carry serving data (16 whole
and 3 partial under the analysis spec's clock ruler; `09-02` is empty); 11 were in treatment arms
and 8 in control (`DEVIATIONS-FOR-PAPER.md` §10.29, §10.31). When the first version of this
manuscript was closed, the study had not yet begun, and the text
below was written under that condition; it no longer holds. **The interventional results
are not here.** They are Paper B (`MANUSCRIPT-B.md`, a draft opened on 2026-09-21 and not yet
deposited), whose underlying records are `DEVIATIONS-FOR-PAPER.md` §10.29–§10.34, in the version
deposited with this text; the v1.0 deposit (Appendix D) predates them, and its
`DEVIATIONS-FOR-PAPER.md` stops at §9.

⚠️ Nothing this paper measures depends on the trial having run — the surface, the
carousel, the mechanism and the ceiling are measurement on the real serving and replay of the real code,
all of it **pre-treatment**. The only thing that changes with the close of the trial is that the sentence "had
not begun" can no longer be read in the present tense.

What this paper reports are the measurements made **while** that study was being built:
the surface, the carousel, the mechanism and its ceiling. They were not pre-registered,
and saying so is the only honest way to present them — they are **exploratory and descriptive**,
not confirmatory.

⚠️ **Three things we measured here contradict the registration, and they are stated here because the
registration is public and someone will cross-check the two:**

| the registration states | what was measured | direction |
|---|---|---|
| `Δ_cut = 0.043` is *"the measured salience spread at the brief cut"* | **there is no cut**: the code applies no threshold. The comparator is lexicographic and `salience` only breaks ties between identical `last_served` values (§5.1) | ⬆ the registration promises more |
| the `{2 · 4 · 7.5}` band is among *"what does not move, and could not"* | **it moves**: 11 / 15 / 17 states out of 350, monotonic, with saturation in `(4.0, 4.4]` (§5.4) | ⬇ the registration promises **less** |
| *(v1.12 §5)* the designation is an **open** defect | **closed** on 2026-08-26 at 20:28Z, with a verifiable precedence of 1,056 s over the drand round (Appendix B) | ⬇ the registration promises **less** |

**The two ⬇ rows are the ones that matter**, because nobody corrects on their own an error that
favors them: the registration states that a parameter has **no** effect when it does, and that a
defect is **open** when it has been closed.

⚠️ And the band row changed status because of an **instrument defect of ours**, not because of new data: the
positive control that produced the *"does not move"* was running on a **reimplemented**
pool. That is a matter for §5.6, not a footnote.

The full list of deviations — including those that affect only the interventional study, such as the
migration of the analysis stratum from `S2` to `≥ S1` by panel agreement — lives in
`DEVIATIONS-FOR-PAPER.md` and belongs to the interventional paper.

## Appendix B — Designation chain

Draw with a declared seed: drand quicknet round **31657512** (issued at 20:25:00Z),
declaration pushed at **20:07:24Z** — **1,056 s** of precedence, with the round returning
HTTP 425 at the time of writing. An independent reviewer re-derived the designated set
using **only** the public beacon and the deposited CSV.

## Appendix C — The panel, and why it is not here

The population of 55 chunks in 19 groups comes from `p2_verdict`, the product of a 3-family severity
adjudication panel. The panel, its agreement per boundary and the rate parameter it estimates belong to the
**interventional study** and are reported in Paper B (`MANUSCRIPT-B.md`, Appendix A, relation to the pre-registration),
which carries the split agreement: κ 0.87–0.93 at `≥ S1` against 0.31–0.53 at the `≥ S2`
boundary. The aggregate `κ` of 0.874 that hid this split is not in Paper B nor in
`DEVIATIONS-FOR-PAPER.md`; it is recorded here.

For what **this** paper reports, the panel enters in one way only: it fixed a population.
The 19 designated items are **a fixed and publicly re-derivable set** (Appendix B), and that is
all §5 needs. See the caveat in §5.1 on which of the two numbers in §5 depends
on the severity label and which does not.

## Appendix D — Artifacts

Scripts are in `measurement/`. Artifacts are in `out/`, in `measurement/`
(`CHANNEL-ATTRIBUTION-2026-08-29.json`), at the root of `paper2-interventional/` (`CEILING-*`,
`TIEBREAK-*`, `POOL-ELEGIVEL-2026-08-28.json`, `BATCH-CYCLE-*`, `PREDICTION-*`), and, for the
ones produced on 2026-10-04, in `_sprint-2026-10-04/` (`POOL-ELEGIVEL-2026-08-26-to-29.json`;
`A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json`):

| what | script | artifact |
|---|---|---|
| exposure surface | `superficie-de-exposicao.py` | `out/superficie.json` |
| replay + dose + threshold + gaps | `replay-oportunidade.mjs` · `replay-resumo.py` | `out/c-350-v3.json` · `out/dose-350-v3.json` · `out/limiar-17.json` · `out/gaps.json` |
| ceiling granularity (§5.7) | `replay-oportunidade.mjs --granularidade` · `granularidade-do-teto.py` | `out/gran-{seg,min,hora,dia}.json` · `out/gran3-{seg,min,hora}.json` · `CEILING-GRANULARITY-2026-08-28.json` |
| exposure to arbitrary tie-breaking (§5.7) | `empates-por-granularidade.py` | `TIEBREAK-EXPOSURE-2026-08-29.json` |
| ceiling sensitivity to the designation (§5.7.1) | `sensibilidade-da-designacao.py` | `out/sens-*.json` · `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json` |
| eligible pool of the coverage channel (§4.3.1) | `pool-elegivel.py` · `sprint-pool-elegivel-multidia.py` | `POOL-ELEGIVEL-2026-08-28.json` · `POOL-ELEGIVEL-2026-08-26-to-29.json` |
| differential attribution by channel (§4.3.1) | `replay-oportunidade.mjs --modo canal` | `CHANNEL-ATTRIBUTION-2026-08-29.json` |
| batch cycle, and the refuted prediction (§4.3.1, §6) | `ciclo-do-lote.py` · `regime-cobertura.py` | `BATCH-CYCLE-2026-08-28.json` · `BATCH-CYCLE-2026-08-29.json` · `PREDICTION-2026-08-29.md` |
| exposure to the resolution defect | `irmaos-no-segundo.py` | — |
| monitoring triggers (retired 2026-09-21; kept as record) | `gatilho-saturacao.sh` · `gatilho-composicao.mjs` | `measurement/implantacao/` |
| probe-exclusion axis of the ceiling (§5.7.2) | `replay-oportunidade.mjs --excluir-briefs` | `out/CEILING-PROBE-EXCLUSION-{none,probes}-2026-08-30.json` · `out/ancora-sondas.json` · `out/ancora-sem-exclusao.json` |
| identity-level comparability control (§5.7.2) | `sprint-comparabilidade-identidade-572.py` | `COMPARABILITY-IDENTITY-5.7.2.json` |
| floor composition, cohort exposure (§4.1) | `composicao-do-piso.py` · `exposicao-por-coorte.py` | `out/FLOOR-COMPOSITION-2026-08-29.json` · `out/EXPOSURE-BY-COHORT-2026-08-29.json` |
| size axis (§4.2, §6.1) | `lacuna-no-eixo-de-tamanho.py` · `robustez-tamanho-exposicao.py` · `fig1-capacidade.py` | `out/SIZE-AXIS-GAP-2026-08-29.json` · `out/SIZE-ROBUSTNESS-2026-08-30.json` · `out/SIZE-EXPOSURE-15-2026-08-29.json` |
| top-of-pool counterfactual (§4.3.2) | `contrafactual-do-topo.py` | `out/TOP-COUNTERFACTUAL-2026-08-29.json` |
| verifier coverage and warning density (§6.1, App. H) | `claims_check.py` · `censo-de-alegacoes-sem-guarda.py` · `censo-de-universos-no-paragrafo.py` · `densidade-de-avisos.py` | `out/CLAIM-COVERAGE-2026-08-29.json` · `out/WARNING-DENSITY-2026-08-30.json` |
| survey count (§1) | `survey-string-count.py` | — |
| figures 0–3 | `fig0-arquitetura.py` · `fig1-capacidade.py` · `fig2-concentracao.py` · `fig3-dose-resposta.py` | `out/fig{0..3}-*.svg` |
| strict-cut field replay (§3.3) | `replay-resumo.py --campo-estrito` | `out/c-350.json` |
| deviations from the registration, and the records behind the interventional results (Paper B, not yet deposited) | — | `DEVIATIONS-FOR-PAPER.md` |
| source notes the text cites | — | `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` · `REMEDIATION-2026-08-27.md` · `PROTOCOL-CALIBRATION-2026-08-27.md` · `CORPUS-FREEZE.md` · `RELATED-WORK.md` · `REVISAO-ADVERSARIAL-2026-09-21.md` |

**Deposit.** Zenodo, concept DOI **`10.5281/zenodo.22181414`** (it resolves to the latest
version). Version 1.0 (`10.5281/zenodo.22181415`, published 2026-08-30T21:39:24Z, in Portuguese)
holds an earlier text of this manuscript (a 126,564-byte `MANUSCRIPT.md`, plus 12 supporting
files) and an earlier `DEVIATIONS-FOR-PAPER.md` that stops at §9. It does **not** contain the
§10.29–§10.34 cited in Appendix A, the 2026-09-21 corrections, this English translation, nor the
consolidated artifacts of §4.3.1, §5.7 and §5.7.1 listed above (10 of the paths this table
listed before 2026-10-04 are absent from it; `_sprint-2026-10-04/A-recon-5.7.2-appD.md`). The
version that matches this text is the next one (v1.1) under the same concept DOI.
**[TODO at deposit: insert its version DOI here, or a pre-reserved DOI if one is created before
deposit.]** The pre-registration of the interventional study is a separate record
(`10.5281/zenodo.22110203`, v1.12, still the latest version of that record as of 2026-10-03).

---

## Appendix H — Correction history

This appendix exists because of an adversarial-review finding about the **form** of the
document, not about a number: the narrative of each correction was in the body,
interrupting the argument to report the diff. Measured before touching anything
(`measurement/densidade-de-avisos.py`, `out/WARNING-DENSITY-2026-08-30.json`): **87 markers
distributed over 77 of the 288 paragraphs — 26.7% marked**, with retraction being the largest
category of repetition. ⚠️ The two units are distinct and the earlier wording
juxtaposed them (*"87 markers in 288 paragraphs — 26.7%"*), which gives 30.2% if read as a
ratio. The number comparable to the one below is that of **marked paragraphs**.

🔴 **The cleanup was partial, and the number after the change has to be here, otherwise this
appendix claims an effect it does not demonstrate.** In the body — before the appendices, which is what
a reviewer reads first — **91 of 297 paragraphs were marked (30.6%)** on 2026-08-30, on the
1,914-line version (`out/WARNING-DENSITY-2026-08-30.json`). The 2026-09-21 corrections added
marked paragraphs: recomputed on 2026-10-03 with the same script over the 2,058-line text
(`_sprint-2026-10-04/A-aging/WARNING-DENSITY-recomputed-2026-10-03.json`), the body has
**100 of 307 marked (32.6%)**, and the whole document 119 of 363 (32.8%), above the 26.7%
measured before the cleanup. (Both counts are of the Portuguese text; the English translation
needs its own measurement.) The
aggregate count is no use for judging: moving material to an appendix does not change the total, and the
appendix brings warnings of its own.

⚠️ **And the aggregate hides what decides the reading: the warnings are concentrated.** Measured on
2026-08-30, §4.2 had **12 markers in 21 paragraphs** and §4.1.1 had 5 in 8, while all of
§5 stayed between 8% and 17%. A reader who learns to skip ⚠️ learns it in §4.2 — and that is
where the retractions that change what the result means are. The intervention of 2026-08-30 was therefore
**surgical and not global**, on two fronts: (i) the retractions of §4.1, §4.2 and §5.7.2 came
to H-3, leaving a cross-reference; (ii) three paragraphs that **are the
result** — the unusable standard error, the confounder that prevents the strong conclusion, the
two properties of the corpus composition — lost the marker without losing a word.
The marker there announced as optional exactly what is not.

⚠️ **What remains undecided** is the third kind: the warnings of *provenance* and of
*scope*, which `measurement/densidade-de-avisos.py` promises in its own header to classify and
**does not classify** — the script counts repetition, which is what it measures without
judgment. As long as the classification is manual, the remaining reduction is editorial.

The material is part of the declared contribution — the method — and so was not discarded.
But it belongs here, and in the body only the corrected state remains, with a cross-reference where the
reader needs to know *why* the text is the way it is.

⚠️ What did **not** come here: validity conditions and scope limits. Those
qualify the claim at the point where it is made, and moving them would repeat the error that
Figure 1 itself taught — a caveat displaced from the point of reading protects no one.

### H-1 — The `slots / distinct` ratio, withdrawn as a test

⚠️ **An earlier version of this section carried here a table of "opposing predictions"** —
`slots/distinct` ratio ≈ 1 under a capacity bottleneck versus ≫ 1 under a policy bottleneck,
with 325 observed — presented as the test that separated the two hypotheses. **It was
withdrawn, and the reason for withdrawing it is instructive.** First, the "≈ 1" prediction is not
derived from the capacity hypothesis: it is the hypothesis rewritten in the unit of the ratio, so
that observing ≫ 1 *is* observing slack — a measurement with two labeled regions, not a test with an error
rate. Second, the hypothesis it overturned was already dead by the arithmetic above,
while the hypothesis a defender would sustain — demand per session above 10 — is
the one we declare out of scope. Third, and decisive: **any concentrating policy
produces ≫ 1**, including a correct one. In a corpus with thousands of session fragments and
3,231 chunks of type `daily`, a ratio near 1 would mean serving obsolete digests
— it would be the *worse* policy. The ratio measured concentration, and the inference to *defect* came
for free.

⚠️ **An earlier version of this section sustained the same conclusion through the
`slots / distinct` ratio = 325**, presented as a test that separated capacity from policy.
§4.1.1 withdraws that argument and the withdrawal holds here too: **any
concentrating policy produces a ratio ≫ 1, including a correct one**, so that the ratio measured
concentration and the inference to *defect* came for free.

### H-2 — Where else the correction did not reach

Each of these was found by adversarial review **after** the corresponding correction
had already been applied at another point in the text — which is the pattern of this class:
correcting where the defect was found does not correct it where it also is.

| correction applied | where it did not reach | who found it |
|---|---|---|
| the floor belongs to the channel, but passing the floor ≠ being eligible | the channel applies **three** conditions; the floor alone gives 13,388 and the three give **108** | DeepSeek |
| the floor belongs to the coverage channel, not to the system | the phrase "that the system marked as relevant", twenty lines below, in the same section | GLM |
| the 13-type Pearson is fragile to the filter | the partials (`−0.709`, `r=−0.843`) that are compared against it | GLM |
| brief ≠ search | Contributions (i), abstract, §4.2, §8.2 | Grok |
| `583,973` → `583,763` | none — the value was in five places and all were corrected, but no guard existed | Codex |
| the equal distribution is impossible "because only 201 fit" | **46,295 fit** — the measured value was treated as a ceiling, which makes the curve inevitable by construction | internal |
| the coverage channel window is 7 days | there are **two** sub-pools, 7 and 30 days; the window of one was applied to the batch of the other | registered prediction |
| "fossil" → "determined" (tone neutralization) | the swap **hardened** the claim: "determined" is causally stronger than the metaphor, and demanded a counterfactual that did not exist | DeepSeek |
| the `w = 2` column labeled **`(served)`** | the defense — "means the dose in force in the *shadow*" — lived in the paragraph **above** the table, and nobody reads a table together with the previous paragraph | DeepSeek |
| "Nobody measures what the agent actually receives" | a universal over the entire literature sustained by **one** vocabulary census of a survey of 218 papers | DeepSeek |
| "the **top** of the brief is determined by traffic" | the counterfactual measures **three** chunks; "the top" generalizes to the ten positions | DeepSeek |
| the 83.78% attributed to a system decision | **9,755 of the 10,899** exposed came from agent-initiated search; the caveat existed, but behind a ⚠️ in the middle of the paragraph | DeepSeek |

### H-3 — Six retractions that lived in the middle of the result

These six were **inside** §4.1, §4.2 and §5.7.2, each interrupting the sentence that
carried the finding to report what an earlier version of that same sentence said. The
outside reader never saw the earlier version; for them the paragraph alternated between a
result and the erratum of a document that does not exist. The corrected state stayed in the body,
with a cross-reference; the narrative of the correction is this.

**H-3.1 · §5.7.2 — "not measurable" conceded more ignorance than the facts required.**
The section stated for two days that the third axis of the ceiling was not measurable. There are **two**
distinct things: the *level* of the ceiling under probe exclusion is not recoverable (the corpus
`e20260826T060003Z.db` was an epoch snapshot and was rotated), but the *sensitivity*
is — the log of the 350 states is `.ndjson` and survived. Declaring ignorance is cheaper than
measuring, and that is why it is the path of inertia.

**H-3.2 · §4.1 — the table closed over two universes.** The earlier version listed the **historical**
union next to the **live** complement; whoever subtracted `67,187 − 11,051` got
56,136 instead of 56,288. Each number was right; the table was not. The row for the 152 chunks
served-and-then-deleted is what makes the bridge, and it is now explicit.

**H-3.3 · §4.1 — "verbatim from `brief.ts:642`" for values that are in another file.** The
*form* of the predicate is there; the *values* `0.7 / 0.7` are in `brief-diversity.ts:59-60`
and are **defaults overridable** by environment variable. Presenting runtime configuration as a
code constant is what makes a correct number age into a wrong one without
warning — the same class that §6 catalogs.

**H-3.4 · §4.1 — the mean length was that of another population.** The sentence names the
**8,928** `distilled` chunks that pass the floor, and the earlier version cited **205** characters, which is the mean of
**all 14,456 `distilled` in the corpus** — not that of the 8,928. Right number,
wrong population, from an *ad hoc* query that left no artifact. The correct value is **232**, and it only
appeared on recomputing: it survived three reviews because none of them could
recompute it.

**H-3.5 · §4.2 — "the test separated curation from size".** It does not, and nothing in the section
does: there is no variable in the corpus that measures curation. What the tests separate is
*filter artifact* from *signal*. The two explanations remain confounded by
construction, and the text and the title now say so.

**H-3.6 · §4.2 — orphan partials of the number the section itself had withdrawn.** The
partials (`−0.709`, `r = −0.843`) appeared without saying over which set they were
computed, **immediately after** the text demoted `−0.728` for fragility to the
filter. They are the 13 filtered types, and against the Pearson of the 15 (`−0.334`) "almost unchanged"
would be double. Found by GLM (see H-2).

## Appendix E — Full catalog of instrument defects

The eight of §6 plus the nine below. The separation is by **consequence**, not by
importance: these did not change any number reported in this paper — which does not make them
less transferable, and three of them are the lessons I would expect to be the most useful
to third parties.

| defect | measured consequence |
|---|---|
| database clock inside the eligibility filter, even though the function receives the instant as an argument | the brief is not a pure function of (corpus, state, `nowMs`); a naive replay measures another population |
| the sorter **discards** the key that ordered the pool | grouping by it gives **one** group, silently |
| monitoring trigger calibrated on **adjacent** gap | watches a quantity that does not bound the mechanism: stays **green while saturating** |
| **attributing the death of an instrument to a commit, without checking the timestamp** | I published that `7fdaab4f` erased it; the commit is from **2026-05-20 01:03 UTC** and the writes stopped **ten hours earlier**. It removed code that was already mute. A diff that *explains* the effect is not proof that it *caused* it |
| **census of "columns without a writer" by grep, by non-null, or by distinct>1** | the three give different answers and all are wrong: grep misses `UPDATE` and dynamic SQL (−3 columns), `DEFAULT` produces 11 false live ones, and pre-death history inflates the distinct counts (`reranker_latency_ms`: **394**, all earlier). The valid census is **distinct in a later window**, cross-checked with the literal `INSERT` list: **16** columns, at **six** distinct instants over 10 days — and in one of them a `CUT` exists, so it is a **withdrawal**, not a regression |
| field without a writer used as an **origin signature** | `requesting_agent` null was treated by me as proof that the telemetry measured the cron; it is null for everyone since 2026-05-18. The valid test is the **cron minute** (94.8%) |
| live series cited as a snapshot | an `n` changed within minutes and the assertion caught it |
| value **typed** inside the verification instrument itself | `w_min` maximum was pinned at `7.5` in the script and aged into false when the fine grid gave `4.4`; it is now a required argument coming from the dose artifact |
| **"the problem is the dissenting panelist"** — which here was false | `xai` is almost a superset of the others (1 of 16 and 1 of 13 outside): a threshold shift, correctable by normalization. The irreducible disagreement is between the **two families of similar severity** (16 and 13 severe, intersection **5**), which disagree about **which** episodes. Blaming the outlier would have "fixed" the wrong family |

## What is missing, in order of what blocks what

Done on 2026-08-28, unless indicated:

✅ **§1, §2, §8, §9** written · **§5** on 2026-08-27 · **Abstract** written.
✅ **Figures 1, 2 and 3** — each derived from a locked artifact, with its own guard.
✅ **survey count** recomputed over the PDF pinned by sha256, with positive control.
✅ **regime break of 2026-08-21–22** — explained (§4.3.1), with a dated prediction for 2026-08-29.
✅ **S2** — decided by measurement: substantive items at `≥ S1` (κ 0.87–0.93), the S1/S2 split
becomes an instrument finding (κ 0.31–0.53). Deviation declared in Appendix A.
✅ **defect catalog** — 8 in the body (those that changed a reported number), 9 in
Appendix E. No separate methods paper.

Missing:

~~1. **architecture figure** of §2~~ → ✅ **done on 2026-08-28**: Figure 0,
   `out/fig0-arquitetura.svg`. It is the only figure that does not derive from an artifact, because it
   describes structure and not data;
~~2. **verify the prediction of 2026-08-29**~~ → ✅ **done on 2026-08-29, and the prediction was
   REFUTED**: the gate came out `exit 1`, §4.3.1 was rewritten around what the
   investigation found (two sub-pools; eligible pool of 108 out of 67,187 = 0.161%, exhausted
   100% every day), and the new explanation was validated by a differential test
   `freshSlots=2` vs `freshSlots=0`. Resolved **by replacement, not by confirmation**;

⚠️ **The two items above went three weeks without being struck through, and on 2026-09-21 this list sent an entire
session in the wrong direction** — reading a worklist from 2026-08-28 and concluding
about today's state. A to-do list that is not struck through is a ruler
that ages. What is actually missing:

~~3. **adversarial review pass**~~ → ✅ **done on 2026-09-21**: Kimi (Moonshot),
   receipt `exit: 0`, 682 s, 76 KB over the 1,937 lines. Findings **applied in full** —
   see the correction history and `REVISAO-ADVERSARIAL-2026-09-21.md`. Codex ran in the
   same batch and returned an **invalid opinion**: four citations that do not resolve against this
   file, including *"there is no section §4.3.1"*; recorded with the evidence, because «the
   voice found nothing» and «the voice did not read» are not the same thing.

   ⚠️ **One voice is not the five.** The adversarial review of this manuscript was done by
   **one** family; Paper B took three. If the deposit requires more, this reopens.

   ~~original pass:~~ voices of distinct families over the
   entire manuscript; the recorded lesson is that adversarial review and mechanical census catch
   **disjoint** classes of defect, and only the second had been done so far;
4. ~~**deposit** with the manuscript + artifacts~~ → v1.0 was deposited on 2026-08-30, in
   Portuguese (`10.5281/zenodo.22181415`, concept DOI `10.5281/zenodo.22181414`; Appendix D).
   **Pending: a new version of that Zenodo record**, carrying this manuscript and the artifacts
   at the cited versions. The grouped amendment of the pre-registration makes sense then: a
   single registration, declaring the deviations **and** the new result.

5. 🟡 **PARTIAL — sweep of claims that have aged** (opened on 2026-09-21, three
   instances closed on 2026-09-21 **by adversarial review, not by the sweep**): §8.3
   (*"that did not run"*), §9 (*"nothing yet was"*) and §4.5 (*"0 rows"*, now dated and
   marked as not re-verified). ⚠️ **The systematic sweep remains to be done** — three
   instances found by external reading are not a census, and the lesson of today is precisely
   that declaring a sweep open is not the same as doing it.

   **Open and declared in the text, from the same opinion:** ~~the `52 = 52` reconciliation
   (§4.3.1 vs §4.3.2), the 25 probe slots (§4.3)~~ → ✅ **closed 2026-10-04 by identity
   measurement** (`_sprint-2026-10-04/A-recon-52-and-slots.md`,
   `measurement/sprint-recon-52-e-sondas.py`). The 52 are one `lessons.md` batch, missing
   identically on 2026-08-20, 08-21 and 08-22; the "2026-08-20: 85 → 33" was 2026-08-21. The 25
   slots are the five probes, identified by `brief_id`, which also add 5 probe-only chunks
   (organic distinct = 196). ~~the `POOL-ELEGIVEL` that covers one day for a claim about four
   (§4.3.1)~~ → ✅ closed 2026-10-04 by re-measurement from a preserved database, with a
   positive control (`_sprint-2026-10-04/A-recon-pool-elegivel.md`,
   `POOL-ELEGIVEL-2026-08-26-to-29.json`). ~~the comparability control of §5.7.2 that validates
   by count~~ → closed 2026-10-04 at identity level; ~~the `[MISSING]` DOI in Appendix D~~ →
   concept DOI cited, the version DOI comes with the deposit; ~~the pointers to
   `DEVIATIONS-FOR-PAPER.md` that Appendix D does not list among the deposited artifacts~~ →
   listed (`_sprint-2026-10-04/A-recon-5.7.2-appD.md`). The artifact census
   (`measurement/sprint-censo-artefatos-paperA.py`) still reports 1 missing input
   (`ts-350.txt`) and 10 Appendix D entries absent from the v1.0 deposit. The next deposit must
   fix both.

6. ~~⚠️ **the seven serial filters are not disaggregated** (opened 2026-09-21, from Codex's opinion —
   the only criticism of it that does not depend on a citation). §4.3.1 attributes the non-exposure of the
   **coverage channel** to path patterns; the **main pool**, 8 of the 10 slots, does not
   receive the same decomposition. The thesis «policy, not capacity» is sustained for the channel
   and **assumed** for the main one.~~ → ✅ **the seven serial filters of the main pool are now
   disaggregated** (§4.3.1, sprint 2026-10-04; `measurement/sprint-desagrega-filtros-pool-principal.py`,
   `_sprint-2026-10-04/A-filters-disaggregation.md`). The reconstruction on the frozen
   corpus reproduces the served briefs in 100% of the briefs of 2026-08-24 to 2026-09-07, and
   leave-one-out on it shows that no filter, lifted, widens the daily surface beyond 33 chunks; F3 (proxy pre-rank with `LIMIT 500`)
   removes 95.7% of the corpus and changes 0 briefs; F1 (scope routing) and F6 (quota split)
   narrow it to 8. The main pool is policy-bound (a deterministic top-k, no rotation), not
   capacity-bound (33 distinct chunks, 0.61% of 5,376 daily slots). Caveat: the Codex output
   naming "seven" was not preserved (only its receipt), so the seven are the stages read from
   `brief.ts`, not necessarily the reviewer's list.

~~(the old item 5 said:)~~ ⚠️ sweep of claims that have aged (opened on
   2026-09-21). Appendix A said that the interventional study "had not begun" — true
   on 2026-09-01, false since then; corrected. **That is not necessarily the only one**: any
   sentence written in the present tense about the state of the trial needs to be re-read before the deposit.
   It is not a substring search — it is a reading of the sections that talk about the trial (§4.5, Appendix A,
   Appendix C, §9).
