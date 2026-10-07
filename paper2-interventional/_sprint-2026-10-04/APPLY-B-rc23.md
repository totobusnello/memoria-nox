# APPLY B-rc23: whole-window sham result integrated, ballast extended (2026-10-07)

`B-v2-rc22.md` (`168ddd5d…`) was copied to `B-v2-rc23.md` (`ff46bd65…`), and only rc23 was
edited. No git write, no Zenodo write, no voices, no LLM API call, no production host. On the
research host (`$NOX_LASTRO_HOST`) the only action beyond reading was the documented summary step
(`JANELA-LANCAMENTO.md` §8 step 1, which writes `job-janela2/RESUMO.json` there); the pull was
an `rsync` from the host. The work directory on the host was **not** deleted. Parity:
`B-rc23/parity-rc23.py` (`167263a2…`) passes; `--self-test` caught 48 of 48 mutations and the
unmutated file passes.

## 1. The result, as pre-committed

The rule is the one fixed before either sham job ran (`sprint-resume-sham-v2.py` docstring;
§4.0.1b `K = 20` bullet; §4.0.1c; applied unchanged to `job-v2b`): statistic `mexeu` (states
whose brief changed) and total churn at the registered `w = 4`; `p = (1 + #{sham ≥ real}) /
(K + 1)`, ties counted against the real designation; `w = 100 000` the positive control,
reported and never tested. No statistic was chosen after the result.

| statistic, `w = 4`, 11,812 states | REAL | 20 shams (min–max) | shams ≥ REAL | ties with REAL | p |
|---|---:|---|---:|---:|---:|
| `mexeu` | **790** | 449–583 | 0 | 0 | **0.0476** (= 1/21, the floor) |
| `churn_total` | **868** | 484–612 | 0 | 0 | **0.0476** |

- Positive control (`w = 100 000`): REAL 894 (churn 1,006), shams 462–591; REAL's own
  `controle_positivo.veredito` = `PASSA`.
- Fidelity of REAL: control set equal to production in 11,812/11,812 states (all 18 epochs);
  churn and entering id at production's `w = 4` (09-12/14/15) in 2,016/2,016.
- 235 states per run without a bonus, all after 2026-09-20T22:51:23 (the designation's expiry).
- Determinism (`JANELA-LANCAMENTO.md` §8 step 2): REAL and every sham identical to `job-v2b` on
  the 2,016 shared states (4,032/4,032 records per run, 20/20 shams), and REAL identical to the
  200-state calibration sample (400/400). Therefore the window run is a superset of `job-v2b`
  minus `09-01`, not an independent replication; the manuscript says so in §4.0.1c, §7 and the
  Abstract.

## 2. Verification of the job

| check | result |
|---|---|
| `STATUS` | `CONCLUIDO 2026-10-07T02:09:46Z 21/21 validadas` |
| `RECIBO.txt` | 21 `VALIDADA`, every exit 0; last line `fim … 21/21 corridas validadas em 145793s` |
| `INSTRUMENTO.sha256` re-checked on the host after completion | 29/29 OK; 28 equal to `job-v2b`, line 6 = `cal/ts-janela-reconstruivel.txt` (`956e712e…`) |
| `BANCOS.sha256` re-checked | 2/2 OK, equal to `job-v2b` (corpus `23378a9e…`, vivo `25b17436…`) |
| runs vs `CONCLUIDO` (host) | 21/21 |
| summary (host, reader `22abd1b4…` = repo bytes) | exit 0, `RESUMO.json` `ec10bd52…` |
| pull to `B-sham-v2/job-janela2/` | 50/50 files sha256-equal to the host (`PULL.sha256`) |
| `job-janela2-runs.tgz` (`aa4fe1e0…`, packed locally) | unpacked, 21/21 against `RUNS.sha256` (= `CONCLUIDO`, `02c570de…`) |
| state set | `ts-janela.txt` 11,865 − `ts-janela-excluidos-53.txt` 53 = 11,812 = the states in `REAL.json` |
| content | ts, agent, ids and counts only; no episode text, no credential |

New files: `B-sham-v2/job-janela2/` (pulled; plus `RUNS.sha256`, `PULL.sha256`,
`DETERMINISMO.json` `f36f1325…`), `B-sham-v2/job-janela2-runs.tgz`,
`measurement/sprint-determinismo-janela2.py` (`317a844b…`), and a result section appended to
`B-sham-v2/JANELA-LANCAMENTO.md` (now `6cff1885…`, written before it was hashed into the
ballast). Nothing existing was overwritten.

## 3. Text changes (rc22 → rc23)

The ten `SHAM-JANELA` blocks were replaced and their markers removed (`<!-- SHAM-JANELA -->` still
appears once, inside a code span of the rc3/rc4 changelog, as history; it is not a marker).

| where | was | now |
|---|---|---|
| status header (block 1) + rc23 entry | second sham "is running … will be added before deposit" | run and reported in §4.0.1c; rc23 entry with the result, item 15/17 closed, "rc23 has not been reviewed" |
| Abstract (block 2) | one sham replay, `w = 4` epochs | two replays (132 vs 81–122; 790 vs 449–583), `p = 1/21` in both, the second contains the first's states |
| §4.0.1c (block 3) | first limit "is now running"; no window result | limit points to the result; new "The whole-window sham, run" (table, ties, positive control, fidelity, determinism, 235 no-bonus states) and "What it adds"; two rows of "What was measured"; the `dist/` row; "What this does to the claims"; artifacts |
| §7 (block 4) | scope = 2,646 states, not the whole window | both runs, the 2,016 shared states, what still lies outside |
| §8.3, §8.5 (blocks 5, 6) | `w = 4` epochs only | and again over the hash-verified window (without `09-01`) |
| B.1 (block 7) | "whole-window sham, running" | every number of the window result with its artifact |
| working list 8, 9, 15 (blocks 8–10) | 15 blocks the deposit; "is running"; item 15 open | 15 struck; "was run"; item 15 **Done** |
| §4.0.1b table, specificity row (outside blocks) | `w = 4` only | plus the window result |
| §1.1 (outside) | `ITT-PRELIMINAR.json` "not yet in the ballast manifest" | entered only in rc23, so the manifest does not date it |
| Appendix B (outside) | 19 cells "not yet in the ballast manifest"; manifest row "50 artifacts … not yet included"; ballast paragraph | "in the ballast manifest from rc23"; "SHA-256 hashes of the 115 artifacts currently covered … every artifact in this table (`B-censo/raw/` excepted)"; two new rows; paragraph rewritten (115, 79/79, 36/36) |
| working list 8, 10, 17, 24 (tail) | 17 open and blocking | 17 **Done**; 8 notes no listed blocker remains (the deposit itself is not done); 10 notes the entry; 24 rc23 not reviewed |
| changelog | — | block rc23, items 188–194 |

Not changed: anything in the H1 family, any heading, any earlier changelog line. Sweep for
sentences that anticipated the sham, outside the blocks: §4.0.1b row, §1.1, Appendix B, working
list 10 and 17 (all edited above); §9 and Appendix A had none.

## 4. Ballast (working list 15 and 17)

`LASTRO-B-item10.md` §7 procedure, label `item15-janela2`: pre-check → extend → additive copy
(`cp -Rp` local, `rsync -a` without `--delete` remote) → post-check.

| | before | after |
|---|---|---|
| manifest sha256 | `172c5382…` (kept in `manifestos-anteriores/`) | **`d310e4e9…`** |
| artifacts | 50 | **115** (+65; old 50 byte-identical) |
| bytes | 165 473 805 | 184 509 309 (176 MiB) |
| copied outside the repo, verified at the destination | 16 | **79**: local 79/79, off-machine 79/79 (79 examined = 79 local) |
| versioned, recomputed from `origin/main` | 34 | **36/36** (28 with a git object id + the 8 of 2026-09-21) |

- Pre-check `recibos/backup-20261007T120120Z.txt` (16/16 both legs, nothing copied); post-check
  `recibos/backup-20261007T120248Z.txt` (79/79 both legs), both exit 0; receipt
  `RECIBO-ITEM15-20261007T120404Z.txt`, sha256 `86dde98f…`, equal on both legs. No host in any file.
- The 65: `ITT-PRELIMINAR.json` (already in the ballast root), `checks-rc7/8/9/10/15` with scripts,
  `out/ITT-REGISTRADO{,-v2,-v3,-v4}-2026-10-05.json`, `measurement/estimador_itt_registrado.py`,
  `B-registered/` (directory: frozen scripts v1–v4, `RESULTADO*.md`, f3/f4, acceleration tests),
  `out/C12-EMPATES-REGISTRADO-2026-10-05.json`, the four registered Figure B1 sets
  (svg/png/run.json) and their scripts, `B-censo/` file by file **without `raw/`** (episode
  text), `STABILITY-TEST.md` (versioned), the four Zenodo snapshots, `receipts/`,
  `JANELA-LANCAMENTO.md`, `janela-lancamento/`, `job-janela2/{RESUMO.json, RUNS.sha256,
  RECIBO.txt, STATUS, INSTRUMENTO.sha256, BANCOS.sha256, PULL.sha256, DETERMINISMO.json}`,
  `job-janela2-runs.tgz`, `sprint-determinismo-janela2.py`, `sprint-resume-sham-v2.py` (versioned).
- Scanned before hashing: no IP, no full credential (two files name the `xoxp-`/`sk-` prefixes
  descriptively, as before).
- `_sprint-2026-10-04/figures` stays in the manifest as the 2026-10-05 directory entry (git
  version); the rc8–rc15 figure files enter as separate entries, as `LASTRO-B-item10.md` §6 asks.

## 5. Parity (`B-rc23/parity-rc23.py`)

- Pins `parity-rc22.py` at `143101dd…` and rc22 at `168ddd5d…`. **Note:** `APPLY-B-rc22.md`
  records `82b14a53…` for `parity-rc22.py`; the file on disk is `143101dd…`, so it was edited
  after that record. rc23 pins the bytes that exist.
- Carries every earlier lock (sweep, presence, status, qualifiers, headlines, hedges, integrity
  S…S22) with two declared exceptions that rc23 makes false on purpose: S19/L6 (manifest = 50
  entries, no rc15–rc19 path) is replaced by S23/M, and the two rc19 presence locks that pinned
  "not in the ballast manifest" are replaced by their rc23 forms.
- Inverts the sham check: rc22 must hold the ten blocks, rc23 no `SHAM-JANELA` marker.
- S23 re-derives every new number from the job files: `RESUMO.json` recomputed from its per-run
  counts with the pre-committed rule (and checked against its own test block), ties, positive
  control, fidelity; `DETERMINISMO.json`; the 21 runs inside the `.tgz` against `RUNS.sha256`;
  `STATUS`, `RECIBO.txt`; instrument and database pins against `job-v2b`; the 53 exclusions; the
  235 no-bonus states against the expiry; the manifest (115, 79/36, old 50 identical, the rc23
  names, no `raw/`) and the receipt. The result sentences are locked in the exact form those
  files produce.
- Removed numbers declared (ETA 2026-10-07T03:00Z ×3, the relaunch time ×2 where the result
  replaces it, 50/158/34/16/17 of the old ballast text, three file-name dates of the condensed
  ballast list); hedge deltas declared per hunk group.
- **Caveat:** S23/M and S23/RC read `~/Backups/paper2-ensaio-2026-09-21` (outside the repository,
  by design). Without it they are reported as NOT VERIFIED warnings, never as passed. S22 still
  reads the Codex receipt from `.remember/` or from the scrubbed copy in `receipts/` (untracked).
