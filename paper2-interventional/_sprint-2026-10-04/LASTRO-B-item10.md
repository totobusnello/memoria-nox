# Ballast gap (working list item 10): closed 2026-10-05

Scope: the 24 artifacts marked † in Appendix B of `B-v2-rc5.md` (lines 1608–1616), plus, by the
coordinator's decision (option A), the five unmarked `out/` rows of 2026-09-09/10 that sat above the
manifest row and had never been hashed, and `B-sham-v2/RESUMO.txt`, cited in B.1. The manuscript
was **not** edited; the text the editor applies is in §4 and §5. No git writes, no Zenodo, no
production host. The off-machine host comes from `$NOX_LASTRO_HOST`, read at run time from the
`com.toto.nox-mem.verifica-lastro` LaunchAgent, and is written in no file.

## 1. What was added

`~/Backups/paper2-ensaio-2026-09-21/MANIFESTO-LASTRO-P2.json`, extended twice. It was never
regenerated.

| | 2026-09-21 | + `item10` | + `item10-b` (final) |
|---|---|---|---|
| sha256 | `556ef20c…` | `8f264b5d…` | **`172c5382…`** |
| artifacts | 20 | 44 (+24) | **50** (+6) |
| bytes | 161 608 733 (154 MiB) | 165 451 225 | **165 473 805 (158 MiB)** |
| copied outside the repo, verified at destination | 12 | 16 (+4) | **16** |
| versioned in the repo | 8 | 28 (+20) | **34** (+6) |

- The old entries are **byte-identical** at each step (20/20, then 44/44), and the earlier
  `extensoes` record is unchanged. Both previous versions are kept in `manifestos-anteriores/`
  (`…556ef20c8d5b.json`, `…8f264b5d8cd8.json`) at the origin and on both legs.
- Hash method: the file hash and `sha256_dir()` are **imported** from
  `scripts/manifesto-lastro-p2.py` (one implementation). The remote leg runs that same script via
  `--hash-dir`.
- Tool: `scripts/estende-lastro-p2.py` (untracked). It only appends. It classifies each path as
  (a) already in the ballast root; (b) versioned, meaning clean against `HEAD` **and** identical
  in `origin/main`, recorded with commit and git object id; or (c) not versioned, copied into
  `<root>/<label>/<rel>` so that `backup-lastro-p2.sh` takes it to both legs. It never
  overwrites a destination that holds different content.
  ⚠️ **Do not run `manifesto-lastro-p2.py` without `--hash-dir`.** It rebuilds the manifest from
  `MANUSCRIPT-B.md` Appendix B, and the rebuild deletes every extension.
- An extender defect was caught by its own guard. On the second extension the first attempt
  aborted with "entradas antigas NÃO ficariam byte-idênticas", because the end of the array was
  searched with `rsplit` and, once the first extension existed, it matched the closing bracket
  of `extensoes`. Nothing was written. The search now takes the first `\n  ]` after the opening,
  and the guard aborted correctly.

The 30 new entries, by leg:

| leg | n | entries |
|---|---|---|
| local + off-machine | 4 | `ITT-SENSIB-PRECOMPROMETIDA.json` (`0191ee54…`, already in both copies since 09-22 through the root rsync, now **in the manifest** and verified); `item10/out/C12-EMPATES-POR-BRACO-2026-10-05.json` (`8e5a1a91…`); `item10/out/C12-EMPATES-COMO-FAILURE-2026-10-05.json` (`1307de2b…`); `item10/measurement/sprint-c12-empates-por-braco.py` (`322162f1…`). The last three are untracked in `paper2-interventional/` |
| git `origin/main` `90d70586` (`item10`) | 20 | the 3 NOGO probes; `B-replay-fidelity/` (dir, 11 files); `sprint-replay-estratos.mjs`; `sprint-replay-fidelidade-resumo.py`; the 2 figure scripts; `figures/` (dir, 7 files); `figB2-item7-crosscheck-20000.json`; `sprint-figB-item7-crosscheck.py`; `B-sham-v2/REPORT.md`; `job-v2b/RESUMO.json`; `job-v2b-runs.tgz`; `job-v2b/RUNS.sha256`; `fidelity-110/` (dir, 7 files); the 3 `power-*.json`; `checks.py` |
| git `origin/main` `90d70586` (`item10-b`) | 6 | `out/CONTROLES-2026-09-10.json`; `out/H1C-POWER-REALIZADO-2026-09-10.json`; `out/H1C-POWER-FRACIONARIA-2026-09-10.json`; `out/H1C-POWER-SEM-0903-2026-09-10.json`; `out/expiracao-designados-2026-09-09.json`; `B-sham-v2/RESUMO.txt` |

Full sha256 per entry: the manifest and the receipts below.

## 2. Counts (N of N, recomputed at the destination)

Each extension followed the same order, which avoids the "rsync before check" trap: verify, then
extend, then copy additively, then verify.

| step | local (`…-COPIA/artefatos`) | off-machine | git (`origin/main`) |
|---|---|---|---|
| pre-check `556ef20c…`, nothing copied | **12/12** | **12/12** (12 examined = 12 local) | — |
| post-check `8f264b5d…` | **16/16** | **16/16** | **20/20** (`item10`) |
| pre-check `8f264b5d…`, nothing copied | **16/16** | **16/16** | — |
| post-check `172c5382…` (final) | **16/16**, 0 diverge, 0 missing | **16/16**, 16 examined = 16 local | **6/6** (`item10-b`), **20/20** (`item10`) |
| manifest file on each leg | `172c5382…` ✓; `556ef20c…`, `8f264b5d…` kept | same | — |

The git leg recomputes sha256 over the content of `origin/main` (`git show` for files,
`git archive` + `sha256_dir` for directories) and checks that the git object id matches. Final
total: **50 = 16 copied and verified at the destination on both legs, plus 34 versioned and
verified against `origin/main`**.

The off-machine host was identified by capability, not by address: no `/root/.openclaw`,
`nox-mem-api` inactive, and it already holds `paper1-lastro-rc4`. All copies were additive: no
`--delete`, and only `item10/`, `manifestos-anteriores/`, the manifest and the receipts were
transferred.

## 3. Receipts

All are under `~/Backups/paper2-ensaio-2026-09-21/` and each is also copied to both legs. None
contains the host.

- `RECIBO-ITEM10-20261005T125933Z.txt`: the first extension (24)
- `RECIBO-ITEM10B-20261005T130316Z.txt`: the second extension (6), with the final counts
- `recibos/backup-20261005T125749Z.txt`, `…125933Z.txt`: pre-check and post-check of the first
  extension, both exit 0
- `recibos/backup-20261005T130243Z.txt`, `…130316Z.txt`: pre-check and post-check of the second
  extension, both exit 0

## 4. Text for the editor: strike item 10

Replace working-list item 10 with:

```
10. ~~**Ballast gap**: add `ITT-SENSIB-PRECOMPROMETIDA.json` and the artifacts marked † in
    Appendix B to `MANIFESTO-LASTRO-P2.json` and to both verified copies.~~ → **Done,
    2026-10-05**: 30 entries appended without regenerating the manifest: the 24 † rows, the
    five `out/` rows of 2026-09-09/10 that had never been hashed, and `B-sham-v2/RESUMO.txt`.
    The existing entries are byte-identical. It now hashes **50** artifacts (165 473 805 bytes
    = 158 MiB; sha256 `172c5382…`, previous versions kept). The 4 new ones that live outside
    the repository (`ITT-SENSIB-PRECOMPROMETIDA.json` and the three C12 files) are in both
    copies, **16/16 recomputed at the destination on each leg**, after a pre-check on both legs
    with nothing copied (receipts `RECIBO-ITEM10-20261005T125933Z.txt`,
    `RECIBO-ITEM10B-20261005T130316Z.txt`). The other 26 are versioned, **26/26** recomputed
    from `origin/main`. The whole-window sham (item 15) and `JANELA-LANCAMENTO.md` are not yet
    in it; they enter together when the job completes.
```

In item 8: `Blocked by ~~9 (valid sham) and~~ 10 (ballast gap) and 15` →
`Blocked by ~~9 (valid sham) and 10 (ballast gap) and~~ 15`.

In item 1, at the end of the 2026-10-04 caveat: `Open as item 10.` →
`Open as item 10; closed 2026-10-05.`

## 5. Text for the editor: Appendix B without the caveat

With the five `out/` rows hashed, the sentence "every artifact above" holds without exception.

1. Row `MANIFESTO-LASTRO-P2.json` (line 1607), replace the whole row with:
   `| \`MANIFESTO-LASTRO-P2.json\` | sha256 of every artifact in this table, for loss detection |`
   This is literally true: every row of the table is in the manifest except the manifest
   itself, which does not hash itself by design.
2. Rows 1609–1616: delete the leading `† ` (eight rows).
3. Row `ITT-SENSIB-PRECOMPROMETIDA.json` (1608): delete the leading `† ` and replace
   `Not in the manifest, and not listed here before v2` with `Not listed here before v2`.
4. The **Caveat** paragraph under B.1: replace its first two sentences, through
   `… versioned in the repository.`, with:

```
**Caveat.** Several of these are **outside the repository** and several are large.
`scripts/manifesto-lastro-p2.py` hashed the first 20 (154 MiB) on 2026-09-21;
`scripts/estende-lastro-p2.py` appended 30 more on 2026-10-05 without regenerating it, for 50
artifacts and 158 MiB. `scripts/backup-lastro-p2.sh` copies the 16 that live outside the
repository, with the hash recomputed **at the destination**; the other 34 are versioned in the
repository.
```

   In the next sentence, `(2026-09-22 01:48Z): local **12/12**, off-machine **12/12**` →
   `(2026-09-22 01:48Z, and again 2026-10-05 13:03Z after item 10): local **12/12** then
   **16/16**, off-machine **12/12** then **16/16**`.
5. Changelog, one line: "Appendix B: † caveat dropped; the manifest now covers every row of the
   table, 50 artifacts (working list 10; `LASTRO-B-item10.md`)."

## 6. What is left, deliberately

- `B-sham-v2/JANELA-LANCAMENTO.md` (cited in B.1, **not versioned**) is **not** in the manifest,
  by decision: it will still change when `job-janela2` completes. It enters in the same step as
  the job's outputs (§7).
- `figures/` is hashed as a directory. Item 11 regenerates the B1 SVG, which changes that hash.
  After it, add a new entry under a new label (never edit the existing one) and verify again.
- The three C12 files are dated today and untracked. If they change before the deposit, the
  verification will show them as divergent. That is intended: re-extend under a new label.

## 7. Commands

Prelude, every time. The host stays in the environment, never in a file:

```sh
cd ~/Claude/Projetos/memoria-nox && git fetch -q origin
export NOX_LASTRO_HOST=$(plutil -extract EnvironmentVariables.NOX_LASTRO_HOST raw \
  ~/Library/LaunchAgents/com.toto.nox-mem.verifica-lastro.plist)
O=~/Backups/paper2-ensaio-2026-09-21; C=$O-COPIA/artefatos
D=/var/backups/nox-mem/paper2-lastro-ensaio/artefatos
```

Generic flow (verify, extend, copy additively, verify):

```sh
bash scripts/backup-lastro-p2.sh --verificar            # must be N/N on both legs BEFORE
python3 scripts/estende-lastro-p2.py --rotulo <LABEL> --dry-run <REL...>
python3 scripts/estende-lastro-p2.py --rotulo <LABEL> <REL...>
# additive copy, no --delete; <LABEL>/ exists only if something unversioned was copied
cp -Rp $O/<LABEL> $C/ ; cp -p $O/MANIFESTO-LASTRO-P2.json $C/ ; cp -Rp $O/manifestos-anteriores/. $C/manifestos-anteriores/
rsync -a -e "ssh -o ConnectTimeout=15 -o BatchMode=yes" $O/<LABEL> $O/manifestos-anteriores \
  $O/MANIFESTO-LASTRO-P2.json "$NOX_LASTRO_HOST:$D/"
bash scripts/backup-lastro-p2.sh --verificar            # local N/N, remote N/N, examined = local
```

**Whole-window sham (`job-janela2`, CONCLUIDO expected about 2026-10-07T03:00Z), together with
`JANELA-LANCAMENTO.md`.** Run only after `JANELA-LANCAMENTO.md` §8 steps 1–3 are done: the resume
exits 0, the determinism check passes, and `job-janela2/` plus the runs `.tgz` are pulled into
`B-sham-v2/` with per-file hashes matching. Write the final result into `JANELA-LANCAMENTO.md`
**before** hashing it. The paths below assume the job-v2b layout; adjust them to what was
actually pulled.

```sh
S=_sprint-2026-10-04/B-sham-v2
python3 scripts/estende-lastro-p2.py --rotulo item15-janela2 --dry-run \
  $S/job-janela2/RESUMO.json $S/job-janela2/RUNS.sha256 $S/job-janela2-runs.tgz \
  $S/JANELA-LANCAMENTO.md $S/janela-lancamento
# then the same without --dry-run, then the generic copy and --verificar above
```

If they are committed and pushed first, they enter as versioned (git leg). If not, they are
copied into `$O/item15-janela2/` and go to both legs. Either way, a new receipt gives N/N per leg.
