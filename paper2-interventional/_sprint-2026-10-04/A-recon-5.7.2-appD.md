# Paper A — §5.7.2 identity control, Appendix D DOI, and artifact census

Sprint 2026-10-04, task A. Target: `paper2-interventional/MANUSCRIPT.md` (137,417 B,
2,058 lines as read on 2026-10-03). **No existing file was edited and no git command
was run.** Everything below comes from a file or a command named next to it.

New files written:

| file | what |
|---|---|
| `measurement/sprint-comparabilidade-identidade-572.py` | identity-level comparability control for §5.7.2 (reads existing artifacts only) |
| `measurement/sprint-censo-artefatos-paperA.py` | census of every path the manuscript cites (adapted from `scripts/censo-lastro-do-manuscrito.py`) |
| `_sprint-2026-10-04/A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json` | output of the first script |
| `_sprint-2026-10-04/A-recon-evidence/CENSUS-PAPERA-ARTIFACTS.json` | output of the second script (88 rows) |
| `_sprint-2026-10-04/A-recon-evidence/zenodo-record-22181415.json`, `zenodo-versions-22181415.json`, `zenodo-record-22110203.json` | public Zenodo API responses (HTTP 200, fetched 2026-10-03) |
| `_sprint-2026-10-04/A-recon-evidence/deposited-22181415/` | 5 files downloaded from the published Paper A record; md5 of each equals the checksum Zenodo publishes (`MANIFEST.json` 6b30ceaf…, `MANUSCRIPT.md` a0807670…, `DEVIATIONS-FOR-PAPER.md` 24c64c3c…, `artefatos.zip` 003960b8…, `scripts.zip` 2f60d64c…) |

Total size of the sprint evidence: under 1 MB (no DB copies were made; none were needed).

---

## (a) §5.7.2 — the comparability control, at identity level

### What the text says now

§5.7.2 (l. 1356–1360) validates that the 30/08 corpus is comparable to the published
26/08 one by a **count**: the no-exclusion arm returns 17/350 on both. The paragraph
added on 2026-09-21 (l. 1323–1332) points out that the same section shows totals can
hide nearly disjoint sets (17 vs 13 sensitive states, 1 in common), so a count control
is the kind of evidence the section itself disqualifies.

### What a content-level check is

The question is not "does the 30/08 corpus give the same number" but "does it give the
same **states**, with the same **ids**, and the same **undosed ranking**". Four levels,
all computable from artifacts already on disk (no replay rerun, no DB opened):

| level | predicate |
|---|---|
| L1 state key | `(ts, agent, rowid_corte)` equal element by element, 350/350 |
| L2 sensitive set | the **set** of states with `churn > 0` is identical (not just its size) |
| L3 per state | `churn`, `would_enter`, `would_leave` identical in each of the 350 states |
| L4 control arm | `ids_controle_replay` (top-10 served at w = 0) identical as an ordered list, 350/350 |

L4 is the most informative: the control arm depends on corpus + serve-state and **not**
on the dose, so it isolates the corpus swap from the intervention.

Artifacts compared (provenance read from each file's `procedencia`):

| id | file | corpus | corpus sha256 (1st MB) |
|---|---|---|---|
| A | `out/gran-seg.json` (w = 100000, seg) | `e20260826T060003Z.db` | `56826f69…` |
| A' | `out/dose-350-v3.json`, w = 100000 slice | `e20260826T060003Z.db` | `56826f69…` |
| C | `out/c-350-v3.json` (mode `campo`, w = 2; carries `ids_controle_replay`) | `e20260826T060003Z.db` | `56826f69…` |
| B | `out/CEILING-PROBE-EXCLUSION-none-2026-08-30.json` | `e20260830T060001Z.db` | `3679bca8…` |
| P | `out/CEILING-PROBE-EXCLUSION-probes-2026-08-30.json` | `e20260830T060001Z.db` | `3679bca8…` |
| S | `out/sens-01.json` (other designation, w = 100000) | `e20260826T060003Z.db` | `56826f69…` |

A, A', C, B and P share `designacao_sha256` `0a04d2d4…`; S (`sens-01`) carries
`72e54b2b…`, an alternative designation by construction. All six share
`fonte_brief_ts_sha256` `27dbe996…` and `corte_serve_state` `rowid`. S is used only
for the positive check on L4, which must not depend on the designation.

### Result

Command: `python3 measurement/sprint-comparabilidade-identidade-572.py _sprint-2026-10-04/A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json` → exit 0.

| pair | L1 | sensitive (x / y / common) | L2 | L3 | L4 ordered |
|---|---:|---|---|---:|---:|
| **A vs B** (26/08 vs 30/08, dose arm) | 350 | 17 / 17 / **17** | **identical** | **350** | — |
| A' vs B | 350 | 17 / 17 / 17 | identical | 350 | — |
| **C vs B** (26/08 vs 30/08, control arm) | 350 | 11 / 17 / 11 (different doses, expected) | — | — | **350** |
| C vs S (same corpus, other dose + designation) — positive check on L4 | 350 | 11 / 22 / 8 | — | — | 350 |
| **B vs P** (negative control: exclusion) | 350 | 17 / 13 / **1** | differs | 321 | **1** |

Reading:

* **The corpus swap is inert at identity level.** The same 17 states are sensitive on
  both corpora, with the same entering and leaving ids in every one of them, and the
  undosed top-10 is identical, in order, in all 350 states.
* **Instrument checks.** (i) Negative control: the probe-exclusion arm reproduces the
  published "1 in common" and breaks L4 in 349/350 states, so the comparison can see a
  difference when there is one. (ii) Positive check: within the 26/08 corpus, two runs at
  different doses and designations have identical control lists (350/350), so L4 depends
  on corpus + serve-state only. (iii) Mutation: changing one entering id in B while keeping
  the count at 17 makes the script exit 1 (`L3 = 349`). The mutation was run in memory
  (monkeypatched loader); no artifact was modified.

What this does **not** establish: that the two corpora are byte-identical (their hashes
differ); anything outside these 350 states, this designation, and second granularity;
or the **level** of the ceiling under probe exclusion on the original 26/08 corpus,
which §5.7.2 already declares unrecoverable.

Observation, not interpreted and not proposed as text: in B vs P, the undosed control
top-10 differs in 349 of 350 states, and in each of those by exactly 2 swapped ids. The
only identical state is the latest one (`2026-08-27T08:52:13.260Z`).

---

## (b) The `[FALTA]` DOI in Appendix D

### What DOI is meant

The sentence (l. 1837–1838) asks for *"a DOI of a deposit that contains **this**
manuscript and the artifacts at the cited version"*, and adds *"today the latest
deposit is v1.12, earlier than all of this"*.

* It is **not** the pre-registration. OSF `yf7d2` / Zenodo `10.5281/zenodo.22110203` is
  the Interventional Memory registration v1.12 (public API: title *"Interventional
  Memory: A Pre-Registered Randomised Crossover…"*, version 1.12, published 2026-08-26,
  concept `10.5281/zenodo.21964093`). Appendix A already cites it correctly.
* It is the **Paper A deposit**, and that deposit **already exists**:
  `10.5281/zenodo.22181415`, version **1.0**, concept DOI **`10.5281/zenodo.22181414`**,
  published 2026-08-30T21:39:24Z, 13 files, title identical to this manuscript.
  Source: public API `GET /api/records/22181415` → 200 (saved in the evidence dir);
  `versions?allversions=true` → total **1**. Also recorded in
  `deposit/paperA/POST-PUBLISH.md` and `docs/HANDOFF.md:1327`.

So the clause *"today the latest deposit is v1.12"* has been **false since
2026-08-30T21:39:24Z**. It is an aged sentence of the kind item 5 of "O que falta" is
hunting, and the deposited v1.0 manuscript carries the same sentence (deposited
`MANUSCRIPT.md` l. 1738–1739), i.e. the published record states that the latest deposit
predates itself.

### Does the DOI for *this* version exist?

No. The deposited `MANUSCRIPT.md` is 126,564 B (1,914 lines, sha256 `e59f0073…`); the
current one is 137,417 B (2,058 lines, sha256 `8c3e1169…`). The deposited
`DEVIATIONS-FOR-PAPER.md` is 18,933 B and ends at §9; the current one is 204,857 B and
contains the §10.29–§10.34 that Appendix A (l. 1766) points to. The version DOI for the
text being edited now **only comes with the future deposit** (a new version under
concept `22181414`; per D-2026-09-23, Paper A goes to deposit first).

Two ways to remove the `[FALTA]` before that deposit, both outside this task:

1. cite the **concept DOI** `10.5281/zenodo.22181414` now — it resolves to the latest
   version, so it will point to the new version once published; or
2. create the new-version draft on Zenodo and **pre-reserve** its DOI, then cite the
   version DOI. This writes to Zenodo and needs Toto's go-ahead; not done here.

Option 1 is proposed below because it needs no external action and stays true after
the deposit.

---

## (c) Artifact census — every path the manuscript cites

Command: `python3 measurement/sprint-censo-artefatos-paperA.py --json _sprint-2026-10-04/A-recon-evidence/CENSUS-PAPERA-ARTIFACTS.json` → exit 1 (one MISSING).

### How it extracts (so that "zero" is interpretable)

* Every backtick span in the manuscript, split on whitespace and `|`; a word qualifies
  if it has a known file extension or ends in `/`. Bare names (no slash) are kept —
  the Paper 1 extractor required a slash and would have dropped most of Paper A's
  citations. Line anchors (`brief.ts:588`) are stripped; brace sets and globs expanded.
* Plus a regex pass over plain text (outside backticks) for `name.ext` tokens. It found
  one plain-only mention (`fig2-concentracao.py`).
* Excluded with reason, and listed in the JSON: `.ndjson` (extension only, 2 lines) and
  21 slash tokens without extension (`17/350`, `20/08`, `/api/brief`, `entities/%`,
  `sessions/%`, `10.5281/zenodo.22110203`, …).
* Looked up in: the repo (`paper2-interventional/`, its `out/`, `measurement/`,
  `measurement/out/`, then unique basename anywhere in `memoria-nox`); the local trial
  lastro `~/Backups/paper2-ensaio-2026-09-21/`; the published deposit v1.0 (published
  `MANIFEST.json` + the two zip listings); and, for `*.ts`, the nox-mem source trees
  `~/Claude/Projetos/nox-supermem/nox-mem/src` and `~/Claude/Projetos/nox-workspace/tools/nox-mem/src`.
* "Versioned" is read from `.git/index` (format v2, 2,290 entries) by parsing the file —
  no git command.
* Controls: a sentinel path injected into the text must come out MISSING (it did);
  bare `DEVIATIONS-FOR-PAPER.md` must resolve (it did); `out/gran-{seg,min,hora,dia}.json`
  must expand to 4 resolved files (it did).

### Totals

83 distinct cited tokens → 88 expanded paths:

| status | n |
|---|---:|
| found in repo (all versioned) | 77 |
| found in the nox-mem serving source tree (outside this repo) | 5 |
| outside by declaration | 5 |
| **MISSING** | **1** |

### Missing, and outside-by-declaration

| path | lines | status | where searched / note |
|---|---|---|---|
| `ts-350.txt` | 1126 | **MISSING** | repo, local lastro, research VPS `/var/backups/nox-mem` (maxdepth 4, `find -name`, read-only). Cited as the `--so-ts-file` input of the `porque` run; `out/porque-350-v3.json` does not hash it (its `fonte_brief_ts_sha256` hashes the script's source, not this list — sha256 of the 350 `ts` of `out/c-350-v3.json` in 6 orderings/terminations does not match it). Reconstructible in principle from the `ts` fields of the 350-state artifacts; that the reconstruction equals the original is **NOT MEASURED**. |
| `e20260826T060003Z.db` | 1150, 1366, 1532, 1937 | outside by declaration | epoch snapshot; §5.7.2 states it was rotated. Not in local lastro, not in research VPS `/var/backups/nox-mem` (maxdepth 4). Production VPS not touched. |
| `campo-churn.json`, `campo-churn-sem-exclusao.json` | 1382 | outside by declaration | §5.7.2 places them on the serving machine and declares the pair unusable. Not in repo, local lastro, or research VPS. Production VPS not touched. |
| `lessons.md`, `memory/lessons.md` | 645, 704, 709, 1432 | outside by declaration | corpus file of the production memory workspace, not a paper artifact |

Serving source cited by line (`brief.ts`, `src/api/brief.ts`, `brief-diversity.ts`,
`src/api/brief-diversity.ts`, `search.ts`) exists in the nox-mem source trees. The v1.0
deposit carries renamed copies of `brief-diversity.ts` and `search.ts`
(`serving-brief-diversity.ts`, `serving-search.ts`) but **no copy of `brief.ts`**,
which the manuscript cites at `:135,642,645`, `:588`, `:612-614`, `:642`. Whether the
cited line numbers still point at the cited code is **NOT MEASURED** (existence only).

### Cited by the text but not listed in Appendix D

40 repo paths. Grouped:

* **Documents the text sends the reader to** (none deposited in v1.0 except DEVIATIONS):
  `DEVIATIONS-FOR-PAPER.md` (l. 19, 660, 1766, 1798, 2045 — deposited in v1.0 only as an
  18,933 B version without §10.29–§10.34), `SUPERFICIE-2026-08-27.md`,
  `REPLAY-OPORTUNIDADE-2026-08-27.md`, `REMEDIATION-2026-08-27.md`,
  `PROTOCOL-CALIBRATION-2026-08-27.md`, `CORPUS-FREEZE.md`, `RELATED-WORK.md`,
  `REVISAO-ADVERSARIAL-2026-09-21.md`.
* **§5.7.2's own artifacts**: `out/CEILING-PROBE-EXCLUSION-none-2026-08-30.json`,
  `out/CEILING-PROBE-EXCLUSION-probes-2026-08-30.json`, `out/ancora-sondas.json`,
  `out/ancora-sem-exclusao.json` (all deposited in v1.0, none in the Appendix D table).
* **§4.1–§4.2 and §6 artifacts with their scripts**: `out/FLOOR-COMPOSITION-2026-08-29.json`
  (`composicao-do-piso.py`), `out/EXPOSURE-BY-COHORT-2026-08-29.json`
  (`exposicao-por-coorte.py`), `out/SIZE-AXIS-GAP-2026-08-29.json`
  (`lacuna-no-eixo-de-tamanho.py`), `out/SIZE-ROBUSTNESS-2026-08-30.json`
  (`robustez-tamanho-exposicao.py`), `out/SIZE-EXPOSURE-15-2026-08-29.json`
  (`fig1-capacidade.py`), `out/TOP-COUNTERFACTUAL-2026-08-29.json`
  (`contrafactual-do-topo.py`), `out/WARNING-DENSITY-2026-08-30.json`
  (`densidade-de-avisos.py`), `out/CLAIM-COVERAGE-2026-08-29.json`
  (`censo-de-alegacoes-sem-guarda.py`), `out/c-350.json`, `claims_check.py`,
  `censo-de-universos-no-paragrafo.py`, `survey-string-count.py`.
* **Figures**: `out/fig0-arquitetura.svg` … `out/fig3-dose-resposta.svg` and the three
  `fig{1,2,3}-*.py` scripts.

### Listed in Appendix D but not in the v1.0 deposit

`CEILING-GRANULARITY-2026-08-28.json`, `CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json`,
`TIEBREAK-EXPOSURE-2026-08-29.json`, `POOL-ELEGIVEL-2026-08-28.json`,
`CHANNEL-ATTRIBUTION-2026-08-29.json`, `BATCH-CYCLE-2026-08-28.json`,
`BATCH-CYCLE-2026-08-29.json`, `PREDICTION-2026-08-29.md`, `gatilho-saturacao.sh`,
`implantacao/`. These are the consolidated artifacts behind §4.3.1, §5.7 and §5.7.1
headline tables. Checked against the published `MANIFEST.json` (120 items) and against
`unzip -l` of the published `artefatos.zip` (57 files) and `scripts.zip` (53 files):
zero matches for `GRANULARITY`, `TIEBREAK`, `POOL-ELEGIVEL`, `CHANNEL`, `BATCH`,
`PREDICTION`, `gatilho-saturacao`, `implantacao`. (The three `CEILING` hits in
`artefatos.zip` are the two `CEILING-PROBE-EXCLUSION-*` files and `MAIN-POOL-CEILING`.)

### Appendix D's location claim is wrong

*"Tudo em `measurement/`"* (l. 1822): of the artifacts the table lists, 7 live at the
root of `paper2-interventional/` (`CEILING-*`, `TIEBREAK-*`, `POOL-ELEGIVEL-*`,
`BATCH-CYCLE-*` ×2, `PREDICTION-*`), the `out/*` ones in `paper2-interventional/out/`, and
only `CHANNEL-ATTRIBUTION-2026-08-29.json` and the scripts in `measurement/`.
The claim *"com `--assert-json` travando cada número citado"* was **NOT MEASURED**.

---

## Side finding — the local copy of the deposit manifest no longer describes the deposit

`deposit/paperA/POST-PUBLISH.md` says the local `MANIFEST.json` is *"the only local proof
of what was effectively deposited"* and *"never recompute an item"*, and reports
*"0 of 121 items diverge"* on 2026-09-07.

Measured today: the published `MANIFEST.json` has **120** items (md5 `6b30ceaf…`,
matches Zenodo); the local `deposit/paperA/MANIFEST.json` has **121** items (md5
`b139a8ff…`). One extra item (`out/ORDEM-SEQUENCIAS-2026-09-07.json`) and **7 items
whose bytes/sha256 differ**: `MANUSCRIPT.md`, `DEVIATIONS-FOR-PAPER.md`,
`claims_check.py`, `SERVING-CODE-MANIFEST.md`, `measurement/auditoria-da-cadeia.py`,
`measurement/ordem.mjs`, `measurement/replay-oportunidade.mjs`. For `MANUSCRIPT.md`
and `DEVIATIONS-FOR-PAPER.md`, the **published** manifest matches the **published**
files (126,564 B / `e59f0073…`; 18,933 B / `0a900adf…`), and the local manifest does not
(126,563 B / `339dbcd6…`; 44,978 B / `afb6ffaf…`). So the "0 of 121" was measured against
a manifest that had already been recomputed — the failure mode POST-PUBLISH warns about.
The authoritative copy is now `A-recon-evidence/deposited-22181415/MANIFEST.json`.
Not fixed here (no edits to existing files allowed); flagged for whoever prepares the
next deposit.

---

## Proposed text (English, for the translated manuscript)

### P1 — §5.7.2, replace l. 1356–1360 (the count-level control)

> ⚠️ **The control that makes the comparison with the published number valid — at the
> level of identity, not count.** The no-exclusion arm, run on the 30/08 corpus, returns
> 17/350 = 4.86%, the value published on the 26/08 corpus. A matching total alone would be
> the kind of evidence this section has just disqualified — 17 and 13 sensitive states
> share only one — so the comparison was redone state by state over the existing
> artifacts (`measurement/sprint-comparabilidade-identidade-572.py`,
> `COMPARABILITY-IDENTITY-5.7.2.json`). The 350 state keys `(ts, agent, rowid_corte)`
> coincide 350/350; the sensitive set is the same 17 states, not merely 17 states; in
> each of the 350 states the ids that would enter and leave are identical; and the
> undosed control arm — the top-10 served at w = 0, which depends on corpus and
> serve-state but not on the dose — is identical, in order, in 350/350 states
> (`out/c-350-v3.json` on 26/08 against the 30/08 arm). Changing the corpus moves neither
> the count, nor which states are sensitive, nor the undosed ranking. The check can see a
> difference when there is one: applied to the probe-exclusion arm it keeps 1 of 17
> sensitive states and 1 of 350 control lists, and a mutation that keeps the count at 17
> but changes one entering id makes it fail. Without this control the difference would be
> attributable to the corpus as much as to the probes. What it does not recover is the
> **level** of the ceiling under exclusion on the original corpus, which stays
> unrecoverable (below).

### P2 — §5.7.2, l. 1323–1332 (the 2026-09-21 red paragraph)

Remove from the body and move to Appendix H as a closed correction:

> **H-x · §5.7.2 — the comparability control checked a count, in the section whose finding
> is that counts do not identify sets.** Raised by adversarial review on 2026-09-21: the
> control validating the cross-corpus comparison was the equality 17/350 = 17/350, while
> three lines earlier the same section showed equal totals hiding nearly disjoint sets.
> Closed on 2026-10-04 by an identity-level control over the existing artifacts — same
> 17 sensitive states, same entering and leaving ids in 350/350 states, same undosed
> top-10 in 350/350 — with a negative control (the exclusion arm breaks identity) and a
> mutation test. The conclusion did not change; the evidence for it did.

### P3 — Appendix D, replace l. 1837–1838 (the `[FALTA]`)

> Deposit: Zenodo, concept DOI **10.5281/zenodo.22181414** (resolves to the latest
> version). Version 1.0 (`10.5281/zenodo.22181415`, 2026-08-30) holds an earlier text of
> this manuscript (126,564 B) and an earlier `DEVIATIONS-FOR-PAPER.md` that stops at §9;
> it does **not** contain the §10.29–§10.34 cited in Appendix A, nor the consolidated
> artifacts of §4.3.1, §5.7 and §5.7.1 listed above. The version that matches this text
> is the next one under the same concept DOI. **[TODO at deposit: insert its version DOI
> here.]**

(If Toto pre-reserves the version DOI on Zenodo before deposit, cite that DOI instead and
drop the TODO.)

### P4 — Appendix D, replace l. 1822 (location claim)

> Scripts are in `measurement/`. Artifacts are in `out/`, in `measurement/`
> (`CHANNEL-ATTRIBUTION-2026-08-29.json`) and at the root of `paper2-interventional/`
> (`CEILING-*`, `TIEBREAK-*`, `POOL-ELEGIVEL-*`, `BATCH-CYCLE-*`, `PREDICTION-*`).

(Keep the `--assert-json` clause only if verified; it was not checked here.)

### P5 — Appendix D, rows to add after l. 1835

| what | script | artifact |
|---|---|---|
| probe-exclusion axis of the ceiling (§5.7.2) | `replay-oportunidade.mjs --excluir-briefs` | `out/CEILING-PROBE-EXCLUSION-{none,probes}-2026-08-30.json` · `out/ancora-sondas.json` · `out/ancora-sem-exclusao.json` |
| identity-level comparability control (§5.7.2) | `sprint-comparabilidade-identidade-572.py` | `COMPARABILITY-IDENTITY-5.7.2.json` |
| floor composition, cohort exposure (§4.1) | `composicao-do-piso.py` · `exposicao-por-coorte.py` | `out/FLOOR-COMPOSITION-2026-08-29.json` · `out/EXPOSURE-BY-COHORT-2026-08-29.json` |
| size axis (§4.2) | `lacuna-no-eixo-de-tamanho.py` · `robustez-tamanho-exposicao.py` · `fig1-capacidade.py` | `out/SIZE-AXIS-GAP-2026-08-29.json` · `out/SIZE-ROBUSTNESS-2026-08-30.json` · `out/SIZE-EXPOSURE-15-2026-08-29.json` |
| top-of-pool counterfactual (§4.3.2) | `contrafactual-do-topo.py` | `out/TOP-COUNTERFACTUAL-2026-08-29.json` |
| verifier coverage and warning density (§6.1, App. H) | `claims_check.py` · `censo-de-alegacoes-sem-guarda.py` · `censo-de-universos-no-paragrafo.py` · `densidade-de-avisos.py` | `out/CLAIM-COVERAGE-2026-08-29.json` · `out/WARNING-DENSITY-2026-08-30.json` |
| survey count (§1) | `survey-string-count.py` | — |
| figures 0–3 | `fig0-arquitetura.py` · `fig1-capacidade.py` · `fig2-concentracao.py` · `fig3-dose-resposta.py` | `out/fig{0..3}-*.svg` |
| strict-cut field replay (§3.3) | `replay-resumo.py --campo-estrito` | `out/c-350.json` |
| deviations from the registration, and the interventional results until Paper B exists | — | `DEVIATIONS-FOR-PAPER.md` |
| source notes the text cites | — | `SUPERFICIE-2026-08-27.md` · `REPLAY-OPORTUNIDADE-2026-08-27.md` · `REMEDIATION-2026-08-27.md` · `PROTOCOL-CALIBRATION-2026-08-27.md` · `CORPUS-FREEZE.md` · `RELATED-WORK.md` · `REVISAO-ADVERSARIAL-2026-09-21.md` |

The section numbers in the "what" column come from the census line numbers mapped to the
manuscript headings, not from re-reading each claim. Check them when you integrate.

### P6 — §5.3 area, l. 1126 (`ts-350.txt`)

> `replay-oportunidade.mjs --modo porque --corte rowid --so-ts-file ts-350.txt` aborts if a
> single entry has no partner. (`ts-350.txt` is the list of the 350 state timestamps; it was
> not kept and its hash was not recorded. The same 350 timestamps are the `ts` fields of
> `out/c-350-v3.json`; that they are byte-for-byte the original input is not verified.)

Alternative: regenerate `ts-350.txt` from `out/c-350-v3.json`, rerun `porque`, and require
`estados_com_mudanca = 17` and `proposicao_1_sobrevive = true` as in
`out/porque-350-v3.json` (needs the 26/08 corpus, which is rotated, so it is probably
**not runnable**; not attempted).

### P7 — Appendix A, l. 1766

> … live in `DEVIATIONS-FOR-PAPER.md` §10.29–§10.34 (in the version deposited with this
> text; the v1.0 deposit predates them) until Paper B exists.

### P8 — "O que falta", item 5, l. 2043–2045

> ~~the count-level comparability control of §5.7.2~~ → closed 2026-10-04 (identity-level,
> P1); ~~the DOI `[FALTA]` of Appendix D~~ → concept DOI cited, version DOI comes with the
> deposit; ~~the `DEVIATIONS-FOR-PAPER.md` pointers missing from Appendix D~~ → listed. The
> artifact census (`sprint-censo-artefatos-paperA.py`) still reports 1 missing input
> (`ts-350.txt`) and 10 Appendix D entries absent from the v1.0 deposit; both must be fixed
> by the next deposit.

---

## NOT MEASURED

* Whether every number in the Appendix D artifacts is locked by `--assert-json` (the claim at l. 1822).
* Whether the line anchors into `brief.ts` / `search.ts` / `brief-diversity.ts` still point at the cited code (census checks existence only).
* Whether the cited artifacts contain what the manuscript says they contain (census checks existence and reach, not correspondence) — except the §5.7.2 artifacts in (a), whose content was compared.
* Contents of the production VPS (not touched): the 26/08 epoch snapshot and the `campo-churn*` pair were searched only in the repo, the local lastro, and the research VPS `/var/backups/nox-mem` to depth 4.
* Interpretation of the B-vs-P control-list difference (349/350 states, 2 ids each).

## Reproduce

```sh
cd ~/Claude/Projetos/memoria-nox/paper2-interventional
python3 measurement/sprint-comparabilidade-identidade-572.py _sprint-2026-10-04/A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json   # exit 0
python3 measurement/sprint-censo-artefatos-paperA.py --json _sprint-2026-10-04/A-recon-evidence/CENSUS-PAPERA-ARTIFACTS.json          # exit 1 (ts-350.txt)
curl -s https://zenodo.org/api/records/22181415 | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["doi"], d["conceptdoi"], d["metadata"]["version"])'
```
