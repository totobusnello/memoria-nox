# B — Why the sham replay has no power: replay-fidelity test (sprint 2026-10-04)

**Hypothesis under test** (declared, unmeasured, `docs/HANDOFF.md` entry of 2026-09-23):
*the serve-state derived today does not reproduce the ties in `last_served` that existed at
the time, so the strata become singletons and the subordinate coordinate (where the bonus
enters) never decides, for any dose.*

## Verdict: **REFUTED** — the zero comes from the corpus, and the cut makes it worse

| claim of the hypothesis | measured (22 states; 09-01 and 09-02) | |
|---|---|---|
| the derived serve-state loses ties that existed | with the exact cut (`rowid`), the derived serve-state **is** production's: production's `would_enter` ties with its `would_leave` in **22/22** states, and the replay reproduces production's control, churn and entering id in **22/22** | ✗ |
| the strata become singletons | in the corpus the sham used, the stratum at the fresh-slot boundary is the **largest** in the pool: **60** never-served chunks (`last_served = NULL`) in **22/22** states, with **0** designated chunks in it | ✗ |
| therefore no dose decides | true, but for a different reason: no designated chunk sits in the stratum that decides. The first designated chunk is at pool position **60–66** | (✓ effect, ✗ cause) |

**What the zero actually is.** It has two causes, and each one alone is enough to produce it:

1. **Wrong corpus (the main cause).** The sonda and `roda-sham.sh` run on
   `corpus-preservado-20260908.db`, but that is not the corpus that served the trial.
   It holds 60 `memory/lessons.md` chunks that were re-ingested on 2026-09-07 and that
   production never had. Every one of them is never-served, so they sort first and fill
   both fresh slots in every state. The served corpus (`corpus-SERVING-REAL-e20260903-recuperado.db`,
   fd-recovered) has **0** never-served chunks in the pool.
2. **Inclusive cut (makes it worse).** `--corte inclusivo` puts the brief's own serves into
   its serve-state. Even with the served corpus, this cut reproduces production's control in
   only **2/22** states and `w = 100 000` moves only **1/22**. With the exact `rowid` cut the
   same numbers are **22/22** and **22/22**.

With both fixed (served corpus + `rowid` cut), the replay **has power**. It reproduces
production exactly (control, churn and entering id, 22/22) and responds to the dose:
**17/22** states move at `w = 2` and **22/22** at `w = 100 000`.

This is not a new mechanism. DEVIATIONS §10.14–§10.15 already measured it on 2026-09-09:
on the recovered corpus `mexeu(2) = 20`, `mexeu(10⁵) = 37`, matching production's
`churn > 0 = 20`; on the realigned corpus `0 / 0`; cause, a never-served cohort holding the
`freshSlots`. The sondas of 2026-09-23 and `roda-sham.sh` were then pinned to a corpus from
the realigned family, and the HANDOFF hypothesis reopened a question §10.15 had already
answered.

## 1. What the replay does (read from code, not assumed)

`measurement/replay-oportunidade.mjs` (sha256 `4f44e2b9…`, the same as
`/root/.openclaw/scripts/p2/replay-oportunidade.mjs`):

- **Serve-state** (`serveStateDerivado`, l. 252): it copies `brief_log` from `--vivo` into
  a scratch DB, cut by `served_at < T` (`estrito`, the default), `served_at <= T`
  (`inclusivo`) or `id < min(id of the brief's own rows)` (`rowid`, the only exact cut;
  l. 519–572). The comment at l. 268–276 already warns that `inclusivo` *"destroys exactly
  the strata of `last_served` that the boost breaks ties in"*.
- **Corpus**: `--corpus` is read-only, and every candidate pool comes from it.
- **Coverage order** (serving `dist/api/brief.js:441–530`, `brief-diversity.js:99`):
  `NULL` (never served) first, then `last_served ASC`. Ties are broken by
  `salience + boost`, which makes the bonus purely intra-stratum (Prop. 1). `freshSlots = 2`.
- **sonda3** (`out/NOGO-replay-sonda3-2026-09-23.json`, provenance block): `corte_serve_state:
  "inclusivo"`, `corpus: corpus-preservado-20260908.db`, `vivo:` the live production DB.
  `roda-sham.sh` pins the same corpus and the same cut (`COMUM=(… --corpus
  …corpus-preservado-20260908.db … --corte inclusivo …)`).

## 2. Measurements

All numbers below come from `measurement/sprint-replay-fidelidade-resumo.py`, whose output is
saved verbatim in `B-replay-fidelity/RESUMO.txt`. Exceptions are labelled at the point of use.

### 2.1 sonda3 never reproduced production's control (132 states, artifact only)

| measure | value |
|---|---|
| states where replay control = production control (as a set) | **0 / 132** |
| overlap of the two 10-id sets | 8 ids in 109 states, 7 in 23 |
| production `fresh_added` ids found in the replay control | **0 in all 132** |
| ids in the replay control that are not in production's | `309062` (132), `309034` (123), `309216` (23), `309117` (9) |
| production's `would_enter` / `would_leave` id present in the replay control | 0 / 0 |

So the replay's fresh slots were filled by chunks production never put there. The
"132 states" never were the states production served.

### 2.2 Production never served the chunks the replay put in the fresh slots

- Production log (`~/Backups/paper2-ensaio-2026-09-21/p2-serving.ndjson`, 19 572 lines)
  contains 93 distinct ids above 308 752, and the **earliest serve of any of them is
  2026-09-21T09:52:04Z**, after the trial. The 4 ids in 2.1 appear **0** times.
- Corpus copies, queried on the research VPS (single `sqlite3 -readonly` session, on
  copies):

| corpus | chunks | MAX(id) | MAX(created_at) | 309034 / 309062 |
|---|---:|---:|---|---|
| `corpus-SERVING-REAL-e20260903-recuperado.db` (fd-recovered, what served) | 67 187 | 308 752 | 2026-08-24 01:06:35 | absent |
| `corpus/e20260907T060001Z.db` | 67 187 | 308 752 | 2026-08-24 01:06:35 | absent |
| `corpus-preservado-20260908.db` (what sonda3 and `roda-sham.sh` use) | 67 606 | 309 497 | 2026-09-08 02:37:34 | present: `memory/lessons.md`, created 2026-09-07 23:01:36, importance 0.9 |

Inference, not a direct measurement: the serving process stayed on the fd-pinned corpus
until after 2026-09-20. DEVIATIONS §10.14 records that the realignment restart stayed
disarmed, and production served no id above 308 752 before 2026-09-21. §10.15 adds that a
never-served `lessons.md` cohort is drained within ~1.2 h of normal serving. So 60 chunks
like these could not have stayed unserved for days had they been in the served corpus.

### 2.3 The 2×2 replay: corpus × cut (22 states, unmodified `replay-oportunidade.mjs`)

States: the 22 of the 132 dated 2026-09-01 (14) and 2026-09-02 (8). `--vivo` is a copy of
`corpus-preservado-20260908.db`, whose `brief_log` runs up to 2026-09-08 05:52:04. It
stands in for the live DB, and the check holds: with the sonda3 configuration it reproduces
sonda3's replay control **22/22**, ids and order. Designation sha256 `0a04d2d4…` = sonda3's.
Production `w` in these states = 4 (used by `campo`); `dose` uses the default `[2, 100000]`.

| corpus | cut | `campo`: control / churn / entering id = production | `dose` w=2 moved | `dose` w=100 000 moved |
|---|---|---|---:|---:|
| preservado | inclusivo *(sonda3 / sham config)* | 0 / 0 / 0 of 22 | 0/22 | **0/22** |
| preservado | rowid | 0 / 0 / 0 of 22 | 0/22 | **0/22** |
| **served** | inclusivo | 2 / 1 / 0 of 22 | 0/22 | 1/22 |
| **served** | **rowid** | **22 / 22 / 22 of 22** | **17/22** | **22/22** |

`boosts_emitidos = 19` in every run, so the designation loaded and the bonus was emitted,
as in sonda3. Errors: 0 in all 8 runs. Wall clock was about 1 min per run.

### 2.4 Stratum structure (the hypothesis itself) — `measurement/sprint-replay-estratos.mjs`

Global coverage pool built by the **real** `fetchFreshCandidates` from the serving `dist`.
Each member's `last_served` is re-read with the code's own `MAX(served_at)` query. Same 22
states, three cuts. Medians, with ranges in brackets.

| corpus | cut | pool | never-served | boundary stratum size | boundary is NULL | states with ≥1 designated in boundary stratum | first designated position | production enter ties leave | singleton strata / state |
|---|---|---:|---:|---|---:|---:|---|---:|---|
| served | **rowid** (= production's state) | 108 | 0 | 4 [3–4] | 0 | **22/22** | 2 [0–3] | **22/22** | 0 [0–1] |
| served | estrito | 108 | 0 | 4 [2–4] | 0 | 18/22 | 2 [1–5] | 22/22 | 0 [0–1] |
| served | inclusivo | 108 | 0 | 2 [1–4] | 0 | 9/22 | 2.5 [0–6] | 8/22 | 0 [0–2] |
| preservado | rowid | 115 | **60** | **60** [60–60] | **22** | **0/22** | 61 [60–63] | 22/22 | 4.5 [3–7] |
| preservado | inclusivo *(sham config)* | 115 | **60** | **60** [60–60] | **22** | **0/22** | 62 [60–66] | 8/22 | 5 [3–8] |

"Production enter ties leave" depends only on the serve-state cut, not on the corpus. That
is why it is identical across corpora for the same cut.

How to read this:

- **Production's state** (served corpus, `rowid` cut) has the ties the mechanism needs. The
  boundary stratum has 4 members in 21/22 states, holds 1–3 designated chunks in 22/22, and
  the tie Prop. 1 requires holds in 22/22. Ties were not lost.
- **The inclusive cut thins them.** The boundary stratum drops to median 2, the states with
  a designated chunk in it drop from 22 to 9, and the enter/leave tie drops from 22 to 8:
  the brief's own serve stamps the entering id with `last_served = T`. This is the only
  place the "lost ties" idea has any truth, and it is secondary, because with the right
  corpus the inclusive cut still moves 1/22 (2.3).
- **The preserved corpus has the opposite of singletons at the boundary.** A 60-member NULL
  stratum, with no designated chunk in it, takes both fresh slots in every state and every
  cut. Singletons do increase elsewhere in that pool (median 4.5 vs 0), but they sit
  **behind** position 60, where nothing is decided. This is the §10.15 cohort.

## 3. Scope: what was not measured

- **110 of the 132 states (09-12 to 09-16): NOT MEASURED** in 2.3 and 2.4. The
  `brief_log` rows after 2026-09-08 05:52:04 exist only in the live production DB (or its
  pre-op snapshots). Copying a production snapshot off the host was **denied by the session's
  permission policy**, and the task rules prefer not touching production. For these states
  only 2.1 and 2.2 hold, and both are measured: 309062 sits in the replay control in 132/132
  states, and production never served it. That the dose would also work there with the
  served corpus and `rowid` cut is an **expectation, not a measurement**.
- The serving `dist` used was copied (read-only `tar`) from production on 2026-10-04.
  `src/api/brief.ts` sha256 `519fa6ab…` equals sonda3's `fonte_brief_ts_sha256`, and the
  source is unchanged since 2026-09-03. `dist/` was rebuilt on 2026-09-29. The 6 modules on
  the brief path import only `node:` builtins. Whether the rebuilt `dist/api/brief.js` is
  byte-identical to the build that served was **NOT MEASURED**. The 22/22 exact reproduction
  is the functional check.
- **No sham was run.** §4 below is a prediction from Prop. 1 plus the strata measured here.

## 4. Consequence for the sham, and a defect in the sham generator

- `roda-sham.sh` as written (`corpus-preservado` + `inclusivo` + `--w 4`) has no power:
  the real arm is 0 by the measurement in 2.3, so `p = 1.0` by construction.
- **Worse, it is biased, not just blind.** `measurement/gera-shams.py` draws shams from
  the 115-chunk pool of `corpus-preservado` (it asserts `len(cand) == 115`). That pool minus
  the 19 real designated leaves 96 candidates. Sixty of those 96 are the never-served chunks
  production never had, and in that corpus they form the boundary stratum, the only stratum
  where a bonus decides. Arithmetic from these counts (hypergeometric, 19 of 96 with 60
  "special"): expected 11.9 of them per sham; P(a sham contains none) = 1.5 × 10⁻¹⁰. So on
  that corpus, shams can move and the real designation cannot. Running the test would
  produce a spurious "sham ≥ real", which reads as **failed specificity**. Not run; this is
  a prediction.
- A valid sham needs: (i) `--corpus corpus-SERVING-REAL-e20260903-recuperado.db`;
  (ii) `--corte rowid`; (iii) the sham pool redrawn from that corpus's 108-chunk pool
  (minus the 19 real ones = 89); (iv) a `--vivo` holding `brief_log` through 2026-09-20,
  which today means a copy of production's `brief_log`. The cost per run (22 states, about
  1 min) makes the full set cheap once (iv) is available.

## 5. MANUSCRIPT-B status check (read-only; nothing edited)

The "sham not executed, and why" text **does not exist**. What is there is stale or wrong:

| line | current text | problem |
|---|---|---|
| 396 | table row: specificity (sham) `🔄 running since 2026-09-22 01:40Z` | it is not running and was never completed |
| 424–431 | `🔄 It is now running …`, expected wall clock ≈ 5 h | stale; the run queue was abandoned on 2026-09-23 (HANDOFF) |
| 440–444 | "Our SQL … returns **115** eligible chunks, and the replay independently observes `pool: 115`" | 115 is the pool of the **preserved** corpus; the served pool is **108** (2.4, 22/22 states) |
| 446–450 | "`corpus-preservado-20260908.db`, the deliberately preserved corpus of the trial … the comparison is internal, real against sham on **one** corpus, which is what specificity needs" | factually wrong: it is not the corpus that served (§10.10, §10.14; 2.2 here), and "one corpus" does not save the comparison when the real arm is 0 by construction on it (2.3) |
| 931 | `🔴 Still open: the sham replay` | should say "not executed, and why", with this artifact |

## 6. Provenance

| artifact | content |
|---|---|
| `B-replay-fidelity/out-{campo,dose}-{preservado,servido}-{inclusivo,rowid}.json` | the 8 replay runs (unmodified `replay-oportunidade.mjs`, `--sem-assert`, so NO-GO and partial-fidelity exits do not abort) |
| `B-replay-fidelity/estratos-{servido,preservado}.json` | per-state stratum structure, 3 cuts |
| `B-replay-fidelity/RESUMO.txt` | output of the summary script; every table above |
| `measurement/sprint-replay-estratos.mjs` | stratum instrument (real `fetchFreshCandidates`) |
| `measurement/sprint-replay-fidelidade-resumo.py` | recomputes every number from the artifacts |

Inputs:

- the trial DBs on `$NOX_LASTRO_HOST:/var/backups/nox-mem/paper2-bancos-ensaio/`, **copied** to
  `/var/tmp/sprint-Breplay-fid/` and worked on as copies; that directory was **removed**
  afterwards. The originals were re-verified 4/4 against `p2-bancos-ensaio.sha256` after the
  work;
- `p2-serving.ndjson` and `DESIGNATION-2026-08-26.json` from the local lastro;
- production: read-only `tar` of `dist/`, `src/api`, `src/paper2` and 3 `node_modules`
  packages; read-only `ls`/`sha256sum`/`grep`. No production DB was opened.

Run line (each of the 8 runs differs only in `--modo`, `--corpus`, `--corte`):

```
nice -n 10 node replay-oportunidade.mjs --modo {campo|dose} --raiz <copied nox-mem> \
  --corpus <copy> --vivo <copy of corpus-preservado> --corte {inclusivo|rowid} \
  --t-ref 2026-09-01T00:00:00Z --excluir-briefs <empty file> --log-campo p2-serving.ndjson \
  --so-ts-file <the 22 ts> --designacao DESIGNATION-2026-08-26.json \
  --designacao-sha256 0a04d2d4… --tmp-base /var/tmp/sprint-Breplay-fid --sem-assert --out …
```

(`--t-ref` is ignored by `campo`/`dose`: those modes take each state's instant from the log.)

## 7. Draft text for MANUSCRIPT-B (not applied)

**(a) §4.0.1b table, row at line 396 — replace the status cell with:**

> ⛔ **not executed — the instrument as configured had no power** (§4.0.1c)

**(b) Replace lines 424–452 (from "🔄 It is now running" through "Artifact:
`CONTROLES-JANELA-COMPLETA-2026-09-21.json`.") with:**

> #### 4.0.1c The specificity control was not executed, and why
>
> The design was 21 replays (`measurement/roda-sham.sh`): the real designation as baseline
> and 20 sham designations of 19 non-designated chunks, at the same `w`. `K = 20` is the
> smallest number of shams that lets a randomization test reject at 5% (`1/21 = 4.8%`). We
> did not run it, because a three-minute probe showed the configured instrument could not
> detect the effect it was meant to test.
>
> **The probe.** We replayed the 132 states in which production recorded
> `ids_tratado ≠ ids_controle`. The replay returned `churn = 0` in all of them, even at
> `w = 100 000` (`out/NOGO-replay-sonda3-2026-09-23.json`). Its *control* set matched
> production's in **0 of 132** states, and production's fresh-slot chunks appeared in
> **none** of them.
>
> **The cause, measured.** The sham was pinned to `corpus-preservado-20260908.db`. That
> corpus was preserved from the live database on 2026-09-08, **after** 60 `memory/lessons.md`
> chunks were re-ingested, so it is not the corpus that served the trial. The serving
> process kept the corpus it had opened on 2026-09-03 (§10.10), recovered from its file
> descriptor as `corpus-SERVING-REAL-e20260903-recuperado.db`. Its serving log is
> consistent with that through the end of the trial: no chunk id above that corpus's
> maximum (308 752) was served before 2026-09-21. In the preserved corpus, those 60 chunks are
> never-served and therefore lead the coverage order: a 60-member stratum with no
> designated chunk in it fills both fresh slots in every state. The bonus is additive and
> acts only inside a stratum (Prop. 1 of §5), so no `w` can move a designated chunk. A
> second, smaller defect sits on top: the cut `served_at <= T` includes the brief's own
> serves in its own serve-state.
>
> **The control of the diagnosis.** On the 22 states for which the trial's `brief_log`
> survives off the production host, the same unmodified replay with the **served** corpus
> and the exact cut (`id < first row of the brief`) reproduces production's control set,
> churn and entering chunk in **22 of 22** states, and responds to dose: **17/22** states
> move at `w = 2` and **22/22** at `w = 100 000`. With the preserved corpus it moves
> **0/22** at either dose, under either cut. With the served corpus and the inclusive cut it
> moves 1/22.
>
> **Why we did not run the sham on the configured corpus anyway.** Its result was known in
> advance and would have been misleading in a known direction. The real arm is 0 by
> construction, so `p = 21/21 = 1.0` is not evidence about specificity. Worse, the shams
> were drawn from that corpus's 115-chunk pool, which contains the 60 never-served chunks.
> A sham is expected to contain about 12 of them, and those are exactly the chunks a bonus
> *can* move there, so shams would move and the real designation could not. That would read
> as failed specificity, and the failure would be the corpus's.
>
> **What a valid run needs**, declared rather than done: the served corpus; the exact cut;
> shams redrawn from the served pool (108 chunks, 89 non-designated); and a copy of the
> trial's `brief_log` through 2026-09-20, which exists only on the production host. At about
> one minute per 22 states, cost is not the obstacle.
>
> Artifacts: `out/NOGO-replay-sonda{2,3}-2026-09-23.json`;
> `_sprint-2026-10-04/B-replay-fidelity.md` with its runs in `B-replay-fidelity/`;
> `measurement/sprint-replay-estratos.mjs`; `measurement/sprint-replay-fidelidade-resumo.py`.
> DEVIATIONS §10.14–§10.15 had measured the same mechanism on 2026-09-09; the sham was
> nevertheless configured on the corpus that §10.15 shows to be blind, and we record that
> as our error.
>
> ⚠️ **Limitation, declared.** The corpus of the published anchor (`e20260826T060003Z.db`)
> no longer exists; it was pruned.

**(c) Line 931, item 3 — replace "🔴 Still open: the sham replay, …" with:**

> ⛔ **The sham was not executed** (§4.0.1c): on the corpus it was configured for, the real
> arm is 0 by construction. On the served corpus, the replay reproduces production 22/22 and
> responds to dose. The remaining blocker is a copy of the trial's `brief_log`.
