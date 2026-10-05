# B — Sham v2: fidelity on the 110 missing states, a corrected sham, its cost, and the launch (sprint 2026-10-04)

Follows `_sprint-2026-10-04/B-replay-fidelity.md` (phase 1). Numbers are recomputed by
`measurement/sprint-sham-v2-resumo.py` from the artifacts in this folder; its output is
`RESUMO.txt`. Exceptions are labelled where they occur.

## 0. Verdicts

| question | answer |
|---|---|
| Replay reproduces production on the 110 states (09-12..09-16)? | **Yes, 110/110**: control set, churn, entering id and boost count. Instrument positive control on 09-01/02: 22/22. |
| Responds to dose there? | `w=2` 87/110 · `w=4` **110/110** (= production 110/110) · `w=100000` 110/110 |
| Which corpus served each state; does it exist? | **One file for all 110, and it exists**: the fd-pinned `e20260903T060001Z.db` inode, sha256 `23378a9e…` = `corpus-SERVING-REAL-e20260903-recuperado.db`. The daily epochs were never read by the serving process. |
| Sham corrected? | New generator, runner, test and summarizer. Test: **13/13 pass**, including a mutation case. |
| Unexpected defect | Only 36 of the 89 non-designated pool chunks can receive any bonus (`p2_verdict` gate). A draw from all 89 would bias the test toward "real > sham". v2 draws from the 36, severity-matched. |
| Cost | Full REAL run on the `w=4` states: **1:00:31 wall, 1.372 s/state**. Job projection (21 runs, 3 cores): **≈8.1 h**. |
| Launched? | **Yes**: tmux `sprint-sham-v2` on $NOX_LASTRO_HOST, 2026-10-04T02:48:05Z, ETA ≈11:00Z, hard deadline 14:48:05Z. |

## 1. Fidelity on the 110 states

### 1.1 Corpus per state

`gatilhos.ndjson` (local lastro `~/Backups/paper2-ensaio-2026-09-21/`) logs
`serving_fd_sha256s`: the sha256 of the bytes the serving process held open, read through
`/proc/<pid>/fd` (§10.17–§10.19).

- One value only, `[23378a9ea83cd27d…]`, in 12 daily readings from 2026-09-10T09:12:16Z to
  2026-09-21T09:12:14Z, with `serving_fd_n = 1` in all.
- `p2-bancos-ensaio.sha256` gives the served copy as `23378a9e…0d04131`: **equal**. The
  preserved copy is `b277bc96…`: different.
- `alinhamento_do_serving` reads `RED corpus-DELETADO-e-vivo-so-pelo-fd` in all 164 hourly
  readings from 09-14 14:25Z to 09-21 09:09Z.

A restart would open a newer epoch, and an fd cannot return to a deleted inode. So a constant
sha means there was no restart. §10.10 had already measured the same inode on 09-08 and dated
the process start to 09-03 17:23:30Z. So **every state from 2026-09-03T17:23:30Z to
2026-09-21T09:12:14Z was served by this file**. The 110 states sit inside that window.

States before 09-03 17:23:30Z were served by an earlier process whose corpus was never
recorded and was pruned. For 09-01 the corpus is validated empirically: 630/630 (§3). For the
shadow phase it is **NOT MEASURED**, and those states are not used.

### 1.2 Instrument

- **Serving code.** Production was not touched. The `dist` was rebuilt on $NOX_LASTRO_HOST from
  `nox-workspace/tools/nox-mem/src`, brief path only, with tsc 5.9.3, better-sqlite3 11.10.0
  (SQLite 3.49.2) and sqlite-vec 0.1.10-alpha.1 (lockfile versions).
  - Source sha256 that match: `brief.ts 519fa6ab…` = sonda3's `fonte_brief_ts_sha256`;
    `brief-outcome.ts b3a3b1a8…`, `brief-diversity.ts 34c9aee5…` and `salience.ts 083399fc…`
    match `SERVING-CODE-MANIFEST.md`.
  - `epoch-shadow.ts` and `shadow-tracker.ts`: **NOT MEASURED** against the host.
  - Byte identity of the rebuilt `dist` with the serving one: **NOT MEASURED**. Functional
    identity: 132/132 here and 2,646/2,646 in §3.
- **`--vivo` = `vivo-v2.db`.** A copy of the `brief_log` export plus `p2_verdict`, with 280 rows
  copied from the preserved corpus.
  - The export's rows `id ≤ 622 964` hash-equal the served corpus's `brief_log`, and rows
    `id ≤ 656 634` hash-equal the preserved corpus's.
  - `p2_verdict` is hash-equal in the 09-03 and 09-08 copies. All 280 rows were written
    2026-08-21 22:51:23.
  - `p2_verdict` after 09-08: **NOT MEASURED**. Boosts match production in every state checked.
- The replay script is the unmodified `replay-oportunidade.mjs`, run with `--corte rowid`.

### 1.3 Results (`fidelity-110/`)

| run | states | control | churn | entering | boosts = prod | errors |
|---|---:|---:|---:|---:|---:|---:|
| campo 09-01/02 | 22 | 22 | 22 | 22 | 22 | 0 |
| campo 09-12..16 | 110 | **110** | **110** | **110** | 110 | 0 |

| dose on the 110 | moved | churn total | churn & entering = prod |
|---|---:|---:|---:|
| `w=2` | 87 | 97 | 85 |
| `w=4` | **110** | 122 | **110** |
| `w=100000` | 110 | 126 | 106 |

The real-code pool (`sprint-pool-ids-v2.mjs`) is the same 108-chunk set in all 132 states. All
19 designated chunks and all 36 boostable non-designated chunks are in it in every state.

Side note: sonda3's 132 states are the changed states of the **w=4 epochs only**
(22 + 32 + 46 + 32). The active epochs have **335** changed states in all. `docs/HANDOFF.md`
(09-23) calls the 132 "all".

## 2. Corrected sham

The old `gera-shams.py`, `roda-sham.sh` and `testa-roda-sham.sh` are untouched. New files:
`sprint-gera-shams-v2.py`, `sprint-pool-ids-v2.mjs`, `sprint-roda-sham-v2.sh`,
`sprint-testa-roda-sham-v2.sh`, `sprint-resume-sham-v2.py`, `sprint-sham-v2-resumo.py`.

### 2.1 Generator

- **Corpus.** The served one, checked by a full-file sha256.
- **Pool as a set, two routes.** The generator's SQL uses the predicate of
  `src/api/brief.ts:637-646`, with `COALESCE(source_date, created_at)` (v1 used `created_at`
  alone). It must equal the real-code pool **as a set** (v1 compared counts only). Result:
  108 = 108.
- **Boostability.** `boostsParaCandidatos` gives a bonus only to designated ids with a
  `p2_verdict` row of severity S1–S4 and `written_at ≤ epoch − 1 d`. The bonus is
  `w · 0.043 · pain(sev)`.

  | | count |
  |---|---:|
  | pool | 108 |
  | real designated in pool | 19 (S1 10, S2 9; bonus mass 0.301·w) |
  | non-designated | 89 |
  | boostable non-designated | **36** (S1 23, S2 13) |

- **Mode `impulsionavel`** (used): 19 drawn from the 36, stratified 10 S1 + 9 S2. Bonus mass is
  0.301·w for every sham. Pairwise overlap between shams: 6–14 ids, mean 10.4. Overlap with the
  real designation: 0. Seeds: `sha256("p2-sham-v2-2026-10-04|i")`. Files are in
  `shams-impulsionavel/`.
- **Mode `todos`** (the literal draw from the 108-pool; generated, **not run**): 4–10 boostable
  members per sham, bonus mass 0.0645–0.1505·w (21–50 % of the real). The non-boostable members
  get bonus 0 by code.

### 2.2 Runner (`sprint-roda-sham-v2.sh`)

- **Instrument:** served corpus, `--corte rowid`, `--vivo vivo-v2.db`, the shams from §2.1,
  `--w 4 --w 100000`, an explicit state list with a required expected count.
- **Order and stops:** REAL runs first and alone. Any non-zero exit (124 = our ceiling or
  deadline), an exit with no output, or an invalid output stops the set and kills the runs in
  flight.
- **Limits:** parallelism ≤ 3 (refused above), `nice -n 10`. `SHAM_TETO_S` (per run) and
  `SHAM_PRAZO_S` (wall deadline) are both required.
- **Finished vs. stopped in the middle:** outputs go to `runs/<x>.tmp.json` and are promoted to
  `runs/<x>.json` only if the state count equals the expected count at both doses and no item
  has `erro`. `STATUS` is one line, rewritten atomically: `RODANDO` / `CONCLUIDO` / `ABORTADO`.
  The file `CONCLUIDO` (with sha256) exists only if all 21 runs validated. A SIGKILL leaves
  `RODANDO` with a stale `HEARTBEAT`. `sprint-resume-sham-v2.py` exits 3 unless the job is
  CONCLUIDO and every hash matches.
- **Instrument pinned:** sha256 of the script, dist, source, state list, log, designations,
  corpus and vivo. Checked before every launch and at the end.
- **Progress files:** `PROGRESSO.ndjson`, `HEARTBEAT`, and `RECIBO.txt`.

### 2.3 Test — 13/13, 0 failures

Run on the research VPS (bash 5.3, uutils timeout 0.8.0). Output:
`TEST-sprint-testa-roda-sham-v2.txt`.

1. Refuses without ceiling or deadline.
2. REAL at 124 → stop, 0 shams.
3. REAL exit 0 with no output → stop.
4. A sham at 124 → the set stops and the next sham is never launched.
5. Happy path → CONCLUIDO, hashes verify.
6. Partial output → rejected, no promoted file, ABORTADO.
7. The deadline cuts a run → ABORTADO.
8. SIGTERM → the in-flight run is killed and logged as NOT MEASURED.
9. An instrument file changes mid-job → abort.
10. At most 3 concurrent runs (measured 3); 4 refused.
11. Refuses to overwrite an existing job directory.
12. SIGKILL → RODANDO, no CONCLUIDO.
13. **Mutation:** without the guards, cases 2 and 6 fail.

## 3. Cost (`calibration/`)

| run | states | wall | CPU | s/state |
|---|---:|---|---:|---:|
| REAL, 1 state | 1 | 10.2 s | 11 s | (setup) |
| REAL, 200 sampled from the 09-03→09-21 window | 200 | 4:45 | 281 s | 1.427 |
| **REAL, all `w=4` epoch states** | **2,646** | **1:00:31** | 3,592 s (sys 52 %) | **1.372** |

The full REAL run reproduces production in **2,646/2,646** states: control in every epoch
(09-01 630/630, 09-12/14/15 672/672 each), and churn plus entering at `w=4` 2,646/2,646. It
moves **132** states at `w=4`, exactly production's 132, and 155 states at `w=100000`.

Projections for 21 runs (`K = 20`, from MANUSCRIPT-B §4.0.1b and `roda-sham.sh`; PREREG-DRAFT
and DEVIATIONS fix no `K`), 3 lanes, REAL first. The wall formula is REAL + 7 waves.

| state set | states | per run | wall | CPU-h | fits 12 h? |
|---|---:|---:|---:|---:|---|
| **w=4 epochs (launched)** | 2,646 | 1.01 h | **≈8.1 h** | 21.2 | yes |
| trial window, hash-proven corpus | 11,865 | ≈4.5 h | ≈36 h | ≈95 | no |
| whole log, as `roda-sham.sh` configured | 19,567 | ≈7.5 h | ≈60 h | ≈157 | no (and ~8k shadow states have no identifiable corpus) |

The slowdown when 3 runs share the host (plus 4 `kissat`) is **NOT MEASURED**. The margin to the
deadline is about 48 %.

## 4. Launch

- **Where and when:** $NOX_LASTRO_HOST, tmux `sprint-sham-v2`, launcher `lanca-job.sh` (copied here),
  launched 2026-10-04T02:48:05Z.
- **Settings:** `SHAM_TETO_S=7200` (2× the measured 3,631 s), `SHAM_PRAZO_S=43200`,
  `SHAM_PARALELO=3`, states `cal/ts-w4.txt` (2,646).
- **ETA:** ≈11:00Z. Hard stop at 14:48:05Z.
- **Bank hashes at start:** corpus `23378a9e…`, vivo `25b17436…`.
- **Why this set.** It is the registered "same `w`" (4). The epochs were randomized, so the
  selection does not depend on the outcome. The corpus is verified in every state. Production
  is directly checkable here. This is a narrower set than `roda-sham.sh`, and it is declared as
  a deviation from the configured (not pre-registered) instrument.
- **Follow it:**
  `ssh $NOX_LASTRO_HOST 'cat /var/tmp/sprint-sham-v2-w/job/STATUS /var/tmp/sprint-sham-v2-w/job/HEARTBEAT; tail /var/tmp/sprint-sham-v2-w/job/RECIBO.txt'`.
  Only `CONCLUIDO` is a result.
- **After CONCLUIDO:**
  1. Run `python3 raiz/sprint-resume-sham-v2.py --log in/p2-serving.ndjson --job job --json job/RESUMO.json`.
  2. Determinism check: `job/runs/REAL.json` `detalhe` must equal `cal/REAL-w4.json`.
  3. Pull `job/` into this folder.
  4. `rm -rf /var/tmp/sprint-sham-v2-w`.
- **Ready command for the larger set** (not launched; ≈36 h): same launcher with
  `SHAM_TS_FILE=$W/cal/ts-janela.txt SHAM_ESTADOS_ESPERADOS=11865 SHAM_TETO_S=32600 SHAM_PRAZO_S=150000 SHAM_OUT=$W/job-janela`.

## 5. Not established

- Corpus before 2026-09-03 17:23:30Z, other than 09-01, which is empirical.
- `p2_verdict` after 09-08.
- Byte identity of the `dist`.
- The slowdown under contention.

The sham result is in section 7.

## 6. Provenance and housekeeping

- **Inputs.** Originals in `/var/backups/nox-mem/paper2-bancos-ensaio/`, only copied (`cp`) and
  re-verified: 5/5 sha OK afterwards, no -wal/-shm. Work dir `/var/tmp/sprint-sham-v2-w/`
  (1.4 GB), kept for the job: raiz/dist, corpus copy, `vivo-v2.db`, shams, `cal/`. The
  preserved-corpus copy, the export copy and the intermediate fid/pool directories were deleted.
- **Local artifacts:** `fidelity-110/`, `shams-impulsionavel/`, `shams-todos/MANIFESTO`,
  `calibration/` (incl. `REAL-w4.json.gz`), `TEST-…txt`, `RESUMO.txt`, `lanca-job.sh`.
- **Not touched:** no git command; no MANUSCRIPT or existing file edited; production
  ($NOX_PROD_HOST) untouched.

## 7. Result (job `job-v2b`, CONCLUIDO 2026-10-04T23:47:06Z, 21/21 validated)

K = 20 shams, w = 4.0, 2,646 brief states (the w = 4 epochs). Statistic: number of states whose
brief changed (`mexeu`) and total churn, REAL designation against 20 shams matched on severity
and boost mass, drawn from the 36 boostable items.

| statistic | REAL | 20 shams (min to max) | shams >= REAL | p = (1 + #shams >= REAL) / (K + 1) |
|---|---:|---|---:|---:|
| `mexeu` | 132 | 81 to 122 | 0 | 0.0476 |
| `churn_total` | 146 | 84 to 132 | 0 | 0.0476 |

Positive control (w = 100,000): REAL 155, shams 81 to 122.
Fidelity of the REAL run to production: 2646/2646 states, 0 divergences;
the REAL run is byte-identical in its dose detail to the calibration run (`calibration/REAL-w4.json.gz`).

Reading: no sham reached the REAL designation on either statistic, so p = 1/21 = 0.0476, the floor
for K = 20. To be declared with it: the state set is restricted to the w = 4 epochs (a declared
deviation from the configured instrument); shams were drawn from the 36 boostable items; p at the
floor says REAL exceeded every sham, not by how much in probability.

Throttling: SHAM-012 to 014 ran under host CPU throttling (~10 h 15 min each, against ~65 min
unthrottled); the replay is deterministic, so this changed timing only.

Artifacts: `job-v2b/` (summary, receipts, hashes; `RUNS.sha256`), `job-v2b-runs.tgz` (the 21 runs),
`job-v1.sha256` (the inherited 13 runs, identical bytes inside `job-v2b`). VPS work dir deleted
2026-10-04 22:45 BRT after a per-file hash match with the local copy; the irreplaceable inputs
(`vivo-v2.db`, `in/`, `cal/`, shams, diag) were moved to
`/var/backups/nox-mem/paper2-bancos-ensaio/sham-v2-2026-10-04/` with `SHA256SUMS`.
