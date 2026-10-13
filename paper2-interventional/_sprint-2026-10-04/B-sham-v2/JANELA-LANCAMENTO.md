# B — Sham v2 on the whole trial window: launch record (2026-10-05)

Owner decision: «rodar antes de depositar». This file records how the job `job-janela` was
rebuilt, checked and launched. Only `CONCLUIDO` is a result: no p is computed here, and none
may be computed before the job says CONCLUIDO.

Host: the research VPS (`$NOX_LASTRO_HOST`). Production was not touched. No git
command was run. Nothing in `/var/backups` was moved or deleted (copies only, `cp`).

## 0. Summary

| item | value |
|---|---|
| job | `/var/tmp/sprint-sham-v2-janela-w/job-janela`, tmux `sprint-sham-janela` |
| launched | 2026-10-05T02:17:59Z (REAL started 02:18:06Z) |
| states | **11,865** (`cal/ts-janela.txt`, sha256 `d8a43b11…`), 18 epochs, 2026-09-03T17:23:39Z → 2026-09-21T08:52:05Z |
| runs | REAL + 20 shams (`shams-impulsionavel/`, the same 20 as job-v2b), doses w = 4 and 100,000 |
| instrument | 28 of 29 `INSTRUMENTO.sha256` hashes equal to job-v2b; the 29th is the state list (by design) |
| banks | `BANCOS.sha256` equal to job-v2b: corpus `23378a9e…`, vivo `25b17436…` |
| fidelity | 120/120 records identical to job-v2b `REAL.json`; 200-state window sample byte-identical to `cal/REAL-amostra200.json` |
| cost measured | 1.572 s/state with 3 lanes + 6 kissat → 18,652 s (5.2 h) per run |
| ceiling / deadline | `SHAM_TETO_S=56000` per run, `SHAM_PRAZO_S=297000` (hard stop 2026-10-08T12:47:59Z) |
| CPU measured | 62.1 % over 5 min after launch (1 lane); 59.3 % over 4.5 min with 3 lanes. Both < 75 % |
| ETA | REAL ≈ 07:10Z 10-05; job ≈ **2026-10-06T19:30Z** (≈ 41 h, 16:30 BRT) if the host is not throttled |

## 1. What the window is, and what it is not

`cal/ts-janela.txt` is the set the REPORT (§3, §4) called "trial window, hash-proven corpus":
every state from the first brief after the serving process opened the `e20260903` inode
(2026-09-03T17:23:30Z) to the end of the trial. Checked against `in/p2-serving.ndjson` with
the replay's own filter (`tag == p2_outcome`, 10 control ids): 11,865 listed, 11,865 match.

| epochs in the set | states | production w |
|---|---:|---|
| 09-03 (partial) | 441 | 0 |
| 09-04 … 09-20 (17 days) | 672 each | 0, 2, 4 or 7.5 by epoch |
| of which w = 4 (09-12, 09-14, 09-15) | 2,016 | 4 |

**Not in the set: the 09-01 epoch (630 w = 4 states)**, which job-v2b did include. Its corpus
was served by an earlier process and has no hash proof (REPORT §1.1; it was validated only
empirically, 630/630). So the window run is not a superset of job-v2b: it shares 2,016 of
job-v2b's 2,646 states and adds 9,849.

## 2. Rebuilding the work directory

New directory `/var/tmp/sprint-sham-v2-janela-w` (the old `/var/tmp/sprint-sham-v2-w` was
deleted on 10-04 after archiving).

### 2.1 Banks and inputs (copied, then checked)

| source (`/var/backups/nox-mem/paper2-bancos-ensaio/…`) | copy | check |
|---|---|---|
| `corpus-SERVING-REAL-e20260903-recuperado.db` | `db/` | sha256 `23378a9e…5d04131` = job-v2b `BANCOS.sha256` and `p2-bancos-ensaio.sha256` |
| `sham-v2-2026-10-04/vivo-v2.db` | `db/` | sha256 `25b17436…be3b1e` = job-v2b `BANCOS.sha256` |
| `sham-v2-2026-10-04/{in,cal,shams-impulsionavel}/` | same names | 47/47 files OK against `sham-v2-2026-10-04/SHA256SUMS` |

Both `.db` copies are mode 0400 and the replay opens them read-only. The AppleDouble `._*`
files in the copy of `in/` were removed from the copy only.

### 2.2 `raiz/` (the instrument)

| file | source | sha256 | = job-v2b pin |
|---|---|---|---|
| `replay-oportunidade.mjs` | `measurement/` (repo) | `4f44e2b9…` | yes |
| `dist/api/brief.js` | rebuilt, below | `5341fc7f…` | yes |
| `dist/api/brief-diversity.js` | rebuilt | `c8501253…` | yes |
| `dist/paper2/brief-outcome.js` | rebuilt | `b60c0dae…` | yes |
| `src/api/brief.ts` | nox-workspace | `519fa6ab…` | yes |
| `sprint-roda-sham-v2.sh` | `measurement/` | `3e2cb9d9…` | (runner; not in the pin list) |
| `sprint-resume-sham-v2.py` | `measurement/` | `22abd1b4…` | (reader) |

**The `dist` rebuild.** REPORT §1.2 says the dist was rebuilt "from
`nox-workspace/tools/nox-mem/src`, brief path only, with tsc 5.9.3". Reproduced on the Mac:

- Source: `~/Claude/Projetos/nox-workspace/tools/nox-mem/src`, HEAD `16fa02e0`, clean tree
  for these files. The six brief-path sources last changed in `ac454e37` (2026-09-04), so they
  are the files job-v2b compiled.
- Files: `api/brief.ts`, `api/brief-diversity.ts`, `paper2/brief-outcome.ts`, `salience.ts`
  (`083399fc…`), `lib/epoch-shadow.ts` (`88a35047…`), `lib/shadow-tracker.ts` (`e4af5083…`).
  They import only `node:` builtins.
- Compiler: `tsc` 5.9.3 from nox-workspace `node_modules` (= lockfile), with the
  `tsconfig.json` options (`ES2022`, `ESNext`, `moduleResolution node`, `strict`,
  `esModuleInterop`, `declaration`, `skipLibCheck`, `noEmitOnError`, `rootDir src`).
- Result: the three pinned `.js` files come out **byte-identical** to the job-v2b pins.
  `epoch-shadow.js`, `shadow-tracker.js` and `salience.js` were never pinned, so their identity
  with the job-v2b build is **NOT MEASURED** by hash; §3 is the functional check.

**`node_modules`.** `raiz/package.json` (copy: `janela-lancamento/raiz-package.json`) has
`"type": "module"` and the exact lockfile versions `better-sqlite3 11.10.0` and
`sqlite-vec 0.1.10-alpha.1`, installed with `npm install` on the VPS (node 22.23.2). Measured
at load: SQLite 3.49.2, vec `v0.1.10-alpha.1`, the versions REPORT §1.2 gives.

**Pin check.** The 29 hashes the runner pins, computed on the new directory with
`cal/ts-w4.txt` in the state-list slot, equal job-v2b's `INSTRUMENTO.sha256` **29/29, in
order**. In the launched job (`janela-lancamento/job-janela-INSTRUMENTO.sha256`) line 6 is
`cal/ts-janela.txt` (`d8a43b11…`) and the other 28 are equal.

## 3. Fidelity before the job

Run with `janela-lancamento/run-cal-janela.sh` (job-v2b's `cal/run-cal.sh` with only the
directory changed), REAL designation, same flags as the runner.

| check | states | result |
|---|---:|---|
| w = 4 sample vs job-v2b `runs/REAL.json` (30 states that moved + 30 that did not, seed `sham-janela-fidelidade-2026-10-04`) | 60 (120 records, both doses) | **120/120 records identical**, key order included; 0 errors; 30 moved at w = 4 |
| window sample `cal/ts-janela-amostra200.txt` vs job-v2b-era `cal/REAL-amostra200.json` | 200 | **whole file byte-identical** after normalizing the work-dir path and `gerado_em` (sha256 `1902748f…` both) |
| the same 200, three runs at once | 3 × 200 | all three byte-identical to the above |

Files: `janela-lancamento/{ts-fidelidade-w4-60.txt,FID-w4-60.json,REAL-amostra200-janela.json}`.

## 4. CPU and the 7_problems guard

`/root/cpu_guard.sh` (read only, not edited) moves every `kissat` into the cgroup
`kissat_lim` and sets its quota to `560 % − 100 % × (number of node.real processes whose
cmdline contains "replay-oportunidade")`. The runner calls `node`, a wrapper that `exec`s
`/usr/bin/node.real … replay-oportunidade.mjs`, so every lane is counted. Seen in
`/root/cpu_guard.log`: `node=1 … quota=460%` at launch, `node=3 … quota=260%` during the
3-lane test. Lanes: 3 maximum (runner refuses more), `nice -n 10`. No kissat was killed or
paused.

Measured from `/proc/stat` with `janela-lancamento/mede-cpu.sh` ("used" = user + nice + system
+ irq + softirq over wall × 8 CPUs; steal reported separately):

| when | lanes | window | used | steal |
|---|---:|---|---:|---:|
| 3-lane test (TRI) | 3 | 272 s | **59.3 %** (4.75 of 8 CPUs) | 9.9 % |
| after launch | 1 (REAL alone) | 301 s | **62.1 %** (4.97 of 8 CPUs) | 9.6 % |

Both are under 75 %. The guard keeps kissat + node at 5.6 cores whatever the lane count, so
the 3-lane phase (from ≈ 07:10Z) should look like the TRI row. Steal of 5–21 % per 30 s
sample means the hypervisor is already taking some CPU.

## 5. Cost, ceiling, deadline, ETA

| run | states | wall | s/state |
|---|---:|---|---:|
| job-v2b calibration, unthrottled (REPORT §3) | 200 | 4:45 | 1.427 |
| today, 2 runs at once + 6 kissat | 200 | 4:56.5 | 1.483 |
| today, **3 runs at once** + 6 kissat | 200 | 5:14.2–5:14.8 | **1.572** |

- Per run: 11,865 × 1.572 = **18,652 s (5.2 h)**. REAL alone: ≈ 11,865 × 1.48 ≈ 17,600 s.
- Job: REAL alone, then 7 waves of shams (3,3,3,3,3,3,2) = ≈ 17,600 + 7 × 18,652 ≈ 148,000 s
  ≈ **41 h** → ETA ≈ **2026-10-06T19:30Z**. This is longer than the ≈ 36 h in REPORT §3,
  which used the unthrottled 1.37 s/state and no contention.
- `SHAM_TETO_S = 56000` = 2 × 18,652 × 1.5 for host throttling (15.6 h per run).
- `SHAM_PRAZO_S = 297000` ≈ 2 × the projected job (hard stop 2026-10-08T12:47:59Z).
- Risk: job-v2b saw the hypervisor slow runs about 10× (≈ 10 h instead of ≈ 65 min). No
  ceiling covers that. If it happens, a run hits 124, the job stops as ABORTADO, and the
  completion mode (§7) resumes it without rerunning validated runs.

## 6. Following it

```sh
ssh $NOX_LASTRO_HOST 'J=/var/tmp/sprint-sham-v2-janela-w/job-janela;
  cat $J/STATUS $J/HEARTBEAT; tail -5 $J/RECIBO.txt; tail -3 $J/PROGRESSO.ndjson'
ssh $NOX_LASTRO_HOST 'tail -3 /root/cpu_guard.log; bash /var/tmp/sprint-sham-v2-janela-w/raiz/mede-cpu.sh 300 30'
ssh $NOX_LASTRO_HOST 'tmux attach -t sprint-sham-janela'   # read only; Ctrl-b d to detach
```

- `STATUS` = `RODANDO …` while running. A `HEARTBEAT` older than ~2 min with `RODANDO` means
  the orchestrator died (SIGKILL, reboot): INCOMPLETE, never "did not move".
- `PROGRESSO.ndjson`: compare `cpu_s` with `parede_s`; utime here includes steal (REPORT,
  diag), so use `raiz/sprint-sham-v2-host-throttle.sh` to check real CPU delivery.
- Console: `/var/tmp/sprint-sham-v2-janela-w/job-janela-console.log`.

## 7. Resuming (only if `STATUS` = ABORTADO or the orchestrator died)

Read `RECIBO.txt` for the cause first. Then run only the runs not validated, in a new job
directory, with the runner's completion mode (it re-checks that instrument and banks are
byte-identical to `job-janela`, re-validates and copies the validated runs):

```sh
ssh $NOX_LASTRO_HOST
W=/var/tmp/sprint-sham-v2-janela-w; cd $W
ls job-janela/runs/*.json | grep -v tmp          # validated runs
# write the missing runs literally in SHAM_CORRIDAS (REAL too, if it is missing):
tmux new-session -d -s sprint-sham-janela-b "cd $W && SHAM_W=$W SHAM_TETO_S=56000 SHAM_PRAZO_S=297000 \
  SHAM_PARALELO=3 SHAM_TS_FILE=$W/cal/ts-janela.txt SHAM_ESTADOS_ESPERADOS=11865 \
  SHAM_OUT=$W/job-janela-b SHAM_DIR=$W/shams-impulsionavel SHAM_JOB_REF=$W/job-janela \
  SHAM_CORRIDAS='SHAM-0xx SHAM-0yy' bash $W/raiz/sprint-roda-sham-v2.sh >> $W/job-janela-b-console.log 2>&1"
```

## 8. After CONCLUIDO (and only then)

1. `cd /var/tmp/sprint-sham-v2-janela-w && python3 raiz/sprint-resume-sham-v2.py --log in/p2-serving.ndjson --job job-janela --json job-janela/RESUMO.json`
   (exits 3 if not CONCLUIDO or any hash fails).
2. Determinism check: the 2,016 w = 4 states shared with job-v2b must have records identical
   to job-v2b `runs/REAL.json` (and to `cal/REAL-amostra200.json` for those 200).
3. Pull `job-janela/` (and the runs as a `.tgz`) into this folder; per-file hash match before
   deleting the work dir.

## 9. Files

`janela-lancamento/`: `lanca-job-janela.sh` (launcher, as run), `run-cal-janela.sh`,
`mede-cpu.sh`, `raiz-package.json`, `job-janela-{INSTRUMENTO,BANCOS}.sha256`,
`ts-fidelidade-w4-60.txt`, `FID-w4-60.{json,time}`, `REAL-amostra200-janela.{json,time}`,
`TRI{1,2,3}-amostra200.time`, `TRI-cpu.txt`, `CPU-pos-lancamento-1lane.txt`, `T0-fid`.

## Relançamento 2026-10-05T09:39:53Z (`job-janela2`, 11.812 estados)

A primeira tentativa (`job-janela`, lançada 02:17:59Z) **abortou** às 06:48:20Z: a corrida REAL
terminou com exit 0 mas devolveu 11.812 de 11.865 estados nas duas doses. Os 53 que faltam são
todos do agente `nox` (52 em 2026-09-21, 1 em 2026-09-06) e trazem o erro do replay
«brief não localizado no brief_log por (agent, segundo, 10 ids) — corte rowid impossível». É
propriedade do dado (o estado servido não é reconstruível), igual para a designação REAL e para
todo sham, logo excluí-los não depende do desfecho. O validador do runner fez o que devia:
parcial não é resultado.

- Lista nova: `cal/ts-janela-reconstruivel.txt`, 11.812 estados, sha256 `956e712e…`.
- Excluídos: `janela-lancamento/ts-janela-excluidos-53.txt`, sha256 `fd0bb5cd…` (lista original
  `cal/ts-janela.txt`, `d8a43b11…`, intacta).
- Lançador: `janela-lancamento/lanca-job-janela2.sh` (idêntico ao anterior salvo lista, contagem e
  diretório de saída). Job abortado preservado em `job-janela-abortado-1/` na VPS.
- ETA: REAL ~4,5 h + 7 ondas de ~5,2 h ⇒ CONCLUIDO por volta de **2026-10-07T03:00Z** (00:00 BRT).
- A declarar no Paper B: janela = 18 épocas de 09-03 17:23:39Z a 09-21, sem a época 09-01 (corpus
  sem prova por hash) e sem os 53 estados de corte impossível.

## Result (`job-janela2`, CONCLUIDO 2026-10-07T02:09:46Z, 21/21 validated)

Recorded 2026-10-07, after `CONCLUIDO`, following §8 steps 1–3. The statistic, the p rule and
the positive control are those pre-committed for the sham (`sprint-resume-sham-v2.py`
docstring; MANUSCRIPT-B §4.0.1b/§4.0.1c; the rule already applied to `job-v2b`, REPORT §7).
Nothing was chosen after seeing the result.

**Completion.** `STATUS` = `CONCLUIDO 2026-10-07T02:09:46Z 21/21 validadas`; `RECIBO.txt` ends
`fim 2026-10-07T02:09:46Z -- 21/21 corridas validadas em 145793s` (SHAM-017/018/019 exit 0,
durations 18,160 / 17,783 / 17,706 s). Every run exit 0, 0 errors, 11,812 states × 2 doses.

**Hashes, re-checked on the host after completion.** `INSTRUMENTO.sha256` 29/29 OK
(`42e8df86…`; 28 equal to job-v2b's pins, line 6 = the state list
`cal/ts-janela-reconstruivel.txt`, `956e712e…`, by design); `BANCOS.sha256` 2/2 OK and equal to
job-v2b's (corpus `23378a9e…`, vivo `25b17436…`); the 21 runs 21/21 against `CONCLUIDO`
(`02c570de…`, copied as `RUNS.sha256`). The state list equals `cal/ts-janela.txt` (11,865)
minus `ts-janela-excluidos-53.txt` (53), set for set, and equals the states in `REAL.json`.

**Step 1 (summary).** `python3 raiz/sprint-resume-sham-v2.py --log in/p2-serving.ndjson --job
job-janela2 --json job-janela2/RESUMO.json` on the host (reader `22abd1b4…`, the repo's bytes):
exit 0, `RESUMO.json` sha256 `ec10bd52…`.

| statistic, `w = 4`, 11,812 states | REAL | 20 shams (min to max) | shams ≥ REAL (ties included) | p = (1 + #shams ≥ REAL) / 21 |
|---|---:|---|---:|---:|
| `mexeu` (states whose brief changed) | **790** | 449 to 583 | **0** (0 ties) | **0.0476** |
| `churn_total` | **868** | 484 to 612 | **0** (0 ties) | **0.0476** |

- Sorted sham `mexeu`: 449, 452, 460, 463, 467, 474, 481, 487, 498, 505, 520, 521, 523, 529, 545,
  547, 557, 561, 572, 583. Sorted sham `churn_total`: 484, 486, 487, 489, 506, 508, 530, 531, 536,
  544, 550, 558, 567, 568, 580, 590, 596, 596, 612, 612. No sham equals REAL on either
  statistic; the ties that exist are between shams (`churn_total` 596 and 612 twice each).
- p is at its floor for K = 20 (`1/21`), as in job-v2b.
- **Positive control** (`w = 100000`, reported, never tested): REAL moves **894** states (churn
  1,006), the shams 462 to 591. Every run moves states at that dose, and REAL's own
  `controle_positivo.veredito` is `PASSA`. REAL's dose response is 790 → 894.
- **Fidelity of REAL to production:** control set equal in **11,812/11,812** states (every epoch,
  09-03 441/441 … 09-20 620/620; 09-06 671/671); at production's own `w = 4` (epochs 09-12, 09-14,
  09-15) churn and entering ids equal in **2,016/2,016**.
- 235 states of every run carry 0 boosts: all after 2026-09-20T22:51Z, i.e. after the
  designation's eligibility expiry (`out/expiracao-designados-2026-09-09.json`), for REAL and
  sham alike. The other 11,577 carry 19.

**Step 2 (determinism).** `measurement/sprint-determinismo-janela2.py` (`317a844b…`) →
`job-janela2/DETERMINISMO.json` (`f36f1325…`), exit 0: REAL against job-v2b `runs/REAL.json`,
**4,032/4,032** records identical (the 2,016 shared states × 2 doses, key order included);
against `calibration/REAL-amostra200.json`, **400/400** (all 200 sampled states are in the
11,812); each of the 20 shams against the same sham of job-v2b (same designation hash),
**4,032/4,032**, 20/20. The window run therefore contains job-v2b's 2,016 states of
09-12/14/15 unchanged: it is not an independent replication of job-v2b, it is a superset of it
minus epoch 09-01.

**Step 3 (pull).** `job-janela2/` pulled with `rsync` (read-only on the host): **50/50** files
equal by sha256 to the host's (list `job-janela2/PULL.sha256`). Runs packed locally as
`job-janela2-runs.tgz` (`aa4fe1e0…`, 15,557,679 bytes, 21 `.json` + 21 `.log`); unpacked and
re-checked 21/21 against `RUNS.sha256`. The runs hold ts, agent, ids and counts only: no episode
text, no credential. The work directory on the host was **not** deleted.

**Reading, as pre-committed.** No sham reached REAL on either statistic, so `p = 1/21 = 0.0476`,
the floor at K = 20. Over the whole hash-verified trial window (18 epochs, every arm, `w = 4`
replayed in every state) the change the dose makes to what is served is larger for the
designated items than for any of the 20 matched shams. REAL exceeds the largest sham by 207
states (790 vs 583); the shams' 449–583 is what a matched designation produces. Three limits of the
job-v2b result carry over unchanged (shams from the 36 boostable items; match on severity and
bonus mass, not signature group; p at its floor). The state-set limit narrows: the set is now
the trial window, not the configured whole log (whose shadow-phase states have no
identifiable corpus), and it still excludes epoch 09-01 and the 53 states whose cut cannot be
reconstructed. It says nothing about outcomes.
