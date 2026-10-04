# Sprint 2026-10-04 · Task A — the "52 = 52" reconciliation and the "25 slots"

Two reconciliations that `MANUSCRIPT.md` declares open (list "O que falta", item 5,
"Abertas e declaradas no texto"). This report closes both by measurement. Neither the
manuscript nor any existing file was edited; proposed text changes are listed at the end
and returned as findings.

## Verdict

| open item | verdict |
|---|---|
| **52 = 52** (§4.3.1 vs §4.3.2) | **Same set, confirmed by identity.** The 52 chunks missing from the week (201 → 149) are exactly the 52 missing from each of 20/08, 21/08 and 22/08 (set equality, not count equality). They are one ingestion of `memory/lessons.md`: ids 308114–308165, contiguous, all `lesson`, all `created_at = 2026-08-20 02:02:03`, replaced by 53 new chunks (308444–308496) when the file was re-ingested at `2026-08-22 02:01:58`. Two statements in the text are wrong: (i) **"20/08: 85 → 33" is mislabeled.** 85 → 33 is **21/08**. On 20/08 the count is **87 → 35**, and on 22/08 it is **193 → 141**. (ii) Neither branch of the manuscript's dilemma holds. The deletion does not "concentrate in one day": the 52 were served across ~46 h on three UTC days. It is not a calendar coincidence either. |
| **25 slots** (§4.3) | **Confirmed by identity.** The window has exactly 5 briefs with ≠ 10 rows (5 rows each, 4,627 others have 10, 0 rows without `brief_id`). Their `brief_id`s match the five in `out/ancora-sondas.json` `sondas_excluidas` as a set. All five are `scope=global`, `agent=NULL`, on 2026-08-26 at 19:58:17–18 and 20:28:55–56 UTC. **New:** these probes also add **5 distinct chunks served nowhere else** (ids 307967–307970 from `memory/decisions.md`, 308443 from `memory/projects.md`, each served exactly once ever). The organic carousel is **196**, not 201. |

Side results, also measured:

- **The counterfactual's "lower bound" is now a measured value.** We restored the 52 deleted
  chunks from a backup taken while they existed. On all 201, zeroing the access term drops the three constants to
  **183 / 181 / 180**. On the 149 survivors the drop is 131 / 129 / 128, which the artifact reproduces exactly.
- **The 52 were served after they stopped existing in the main DB.** **966 slots in 483 briefs**
  served ids 308114–308165 at or after `2026-08-22 02:02:37`, the instant of a snapshot that has none of them. The last
  such slot was at `2026-08-22 19:07:46`. "Servidos e apagados depois" is therefore only partly
  true. About 37% of their 2,600 slots came after the deletion (966 / 2,600 = 37.2%).
- The 52 were all served by the **coverage channel**. Every brief that contains one contains exactly 2 of them (1,300 briefs × 2 = 2,600 slots), across all six agents.

## Sources and method

**No production DB was touched.** Every database was copied first and read only from the copy. The research
VPS `$NOX_LASTRO_HOST` (research VPS) has the trial DBs. Copies went to
`/var/tmp/sprint-A-recon/` (disk, not tmpfs). That directory was removed when done (`ls` →
"No such file or directory"). The originals' mtimes did not change and no `-wal`/`-shm` appeared.

| role | original | copy sha256 |
|---|---|---|
| serving state (`brief_log` + `chunks` ≈ §4.3's state) | `/var/backups/nox-mem/paper2-bancos-ensaio/corpus/e20260907T060001Z.db` | `4ec7e182…1fe721345`, which matches `p2-bancos-ensaio.sha256` |
| "pre" (the 52 still exist) | `/var/backups/nox-mem/daily-main/daily-main-main-20260821060004-…db.gz`, gunzipped into the copy | `40683f8e…8e724ffa` |
| "post" (the 52 gone) | `/var/backups/nox-mem/pre-op/kg-confirm-main-20260822020237-…db` | `fba69260…5dafc5c6` |
| (also inspected) | `/var/backups/nox-mem/pre-op/kg-confirm-main-20260823020009-…db` | not hashed. It has 0 of the 52, and `lessons.md` = 53 chunks created at 02:01:58 |

**Why the 2026-09-07 epoch stands in for the state §4.3 measured.** The manuscript's numbers were measured on production on 28–29/08. This epoch reproduces each of them exactly:
`chunks` = **67,187**, the §4.1 live corpus. The window gives **46,295 slots / 4,632 briefs / 201 distinct /
3 in 100% / top-10 47.16% / top-20 61.46%**, which equals `out/superficie.json`
`concentracao_do_brief`. It has **149** survivors, equal to `TOP-COUNTERFACTUAL-2026-08-29.json`
`candidatos_servidos_na_janela`. The `access_count` of 116467/112241/116107 is
911/414/363, equal to the artifact. The rerun counterfactual gives positions **2/131, 3/129, 5/128**,
equal to the artifact, at three pinned "now" values on 2026-08-29.
This is equivalence on every quantity checked, not a byte-level identity proof with production.

**Script:** `measurement/sprint-recon-52-e-sondas.py`, new and read-only (`mode=ro`). It was run as
`--serving-db e0907.db --pre-db d0821.db --post-db k0822.db --sondas out/ancora-sondas.json`.
Its full output is in `_sprint-2026-10-04/A-recon/RECON-52-e-sondas-2026-10-04.json`. The organic-only
variants (probes excluded) and the input hashes are in
`_sprint-2026-10-04/A-recon/ORGANICO-e-hashes-2026-10-04.txt`.

## 1. "52 = 52"

### 1.1 Per-day distinct served vs distinct that still exist (UTC day, `substr(served_at,1,10)`)

| day | distinct in `brief_log` | distinct that exist in `chunks` | missing | missing set == week's missing set |
|---|---:|---:|---:|---|
| 2026-08-19 | 35 | 35 | 0 | — |
| **2026-08-20** | **87** | **35** | **52** | **yes** |
| **2026-08-21** | **85** | **33** | **52** | **yes** |
| **2026-08-22** | **193** | **141** | **52** | **yes** |
| 2026-08-23 | 142 | 142 | 0 | — |
| 2026-08-24 … 27 | 141 / 141 / 146 / 141 | same | 0 | — |
| **week [20/08, 27/08)** | **201** | **149** | **52** | — |

Grouping by BRT day (`date(served_at,'-3 hours')`) gives the same counts for 20, 21 and
22/08: 87/35, 85/33 and 193/141. So the mislabel is not a timezone artifact.

The "33 vs 85" in the manuscript comes from a docstring in `measurement/regime-cobertura.py`
(lines 23–25: *"Numa primeira passagem, 20/08 apareceu com 33 distintos onde a contagem sobre
`brief_log` dava 85"*). No artifact was saved from that first pass (searched: `out/`,
`measurement/`, `BATCH-CYCLE-*.json`, the local lastro; the only occurrences of "33 distintos"
are that docstring and the two manuscript lines). The measured pair 85/33 belongs to **21/08**.

### 1.2 Identity of the 52

- ids **308114–308165**, contiguous (max − min + 1 = 52);
- in the "pre" DB (daily backup 2026-08-21 06:00 UTC, `brief_log` max `2026-08-21 05:52:07`):
  all 52 present, `source_file = memory/lessons.md`, `chunk_type = lesson`,
  `created_at = 2026-08-20 02:02:03` for all 52, importance/pain = 0.9/0.4 (42) and 0.9/0.9 (10);
- in the "post" DB (pre-op snapshot 2026-08-22 02:02:37 UTC, `brief_log` max `2026-08-22 01:52:05`):
  **0** present. `memory/lessons.md` is now **53** chunks, ids 308444–308496, `created_at =
  2026-08-22 02:01:58`. The 2026-09-07 epoch has that same 53-chunk set;
- so the deletion happened between 2026-08-21 06:00 and 2026-08-22 02:02:37 UTC. The replacement
  set was created at 02:01:58. That fits a re-ingest of `lessons.md` replacing that file's
  chunks;
- all **53** replacement chunks were served in the window, so the content of the 52 is
  among the 149 survivors under new ids.

### 1.3 How they were served

- first serve `2026-08-20 21:38:47`, last `2026-08-22 19:07:46`;
- **2,600 slots in 1,300 briefs**, exactly 2 per brief, which is the coverage channel's
  `freshSlots = 2`. By agent: atlas 370, boris 370, cipher 370, forge 370, lex 376, nox 744;
- **966 slots in 483 briefs at or after 2026-08-22 02:02:37**, the snapshot instant where they are
  proven absent from the main DB. The serving path kept handing out ids that no longer existed
  in `chunks` for about 17 h. Cause NOT MEASURED. It is consistent with serving from a
  snapshot taken before the re-ingest (see the memory note "Processo longo serve snapshot
  já PODADO"). We did not verify it.

### 1.4 What this does to the §4.3.2 dilemma

The manuscript offers two readings: "the same set, so all of the week's pruning concentrates in one day", or "an
unverified calendar coincidence". Neither holds. It is the same set, and it spans three days.
The coincidence the text worried about is real in a different form. Three different days
each lose exactly 52, because the same 52 coverage-channel chunks were served on all
three.

### 1.5 The counterfactual with the 52 restored

The §4.3.2 counterfactual, `contrafactual-do-topo.py`, uses the same formula and tie-break. The
recency term uses `julianday(now)`, and the original run did not record its instant, so
"now" was pinned to 2026-08-29 00:00:00, 12:00:00 and 23:59:59. All three give identical results.
The 52 enter with their own importance, pain, access_count and dates from the "pre" DB.

| population | 116467 (with → without access) | 112241 | 116107 | best rank of any of the 52 (without / with access) |
|---|---|---|---|---|
| 149 survivors (published) | 2 → **131** | 3 → **129** | 5 → **128** | — |
| **201 = 149 + 52 restored** | 2 → **183** | 3 → **181** | 5 → **180** | 12 / 32 |
| 144 organic survivors (probes excluded) | 2 → 126 | 3 → 124 | 4 → 123 | — |
| 196 organic, 52 restored | 2 → 178 | 3 → 176 | 4 → 175 | — |

The conclusion "they leave the top-10 and fall beyond rank 100" holds in every variant. The
published "lower bound" argument is borne out: restoring competitors moves the three down by 52
places. One caveat belongs in the text. The 52 are earlier versions of `lessons.md` whose 53
replacements are already among the 149, so the 201-population counts that content twice.
That is still the population that was served.

## 2. The 25 slots

| measured in window [2026-08-20, 2026-08-27) | value |
|---|---|
| histogram of rows per brief | 10 rows: **4,627** briefs · 5 rows: **5** briefs · nothing else |
| rows with `brief_id IS NULL` | 0 |
| the 5 short briefs, as a set | **==** `out/ancora-sondas.json` → `procedencia.sondas_excluidas` (5 ids) |
| their timing | 3 at 2026-08-26 19:58:17–18, 2 at 20:28:55–56 UTC; `scope=global`, `agent=NULL` |
| their content | each = the 3 constants (116467, 112241, 116107) + 2 other chunks |

So `25 = 5 × 5` is an identity, not just arithmetic. It also matches what §5.7.2 already
established for the replay's `serve_state`, where `descartadas_por_sonda: 25` appears in `ancora-sondas.json`.

**§4.3 table with the probes removed** (the "organic" column is new):

| | published (includes probes) | organic (probes excluded) |
|---|---:|---:|
| slots | 46,295 | **46,270** |
| briefs | 4,632 | **4,627** |
| deficit vs 10/brief | 25 | **0** |
| distinct chunks | 201 | **196** |
| present in 100% of briefs | 3 | 3 |
| top-10 share | 47.16% | 47.16% |
| top-20 share | 61.46% | 61.46% |
| share of the 3 constants | 30.02% | 30.00% |

The five probe-only chunks are 307967, 307968, 307969 and 307970 (`memory/decisions.md`, `decision`,
created 2026-08-20 02:01:18) and 308443 (`memory/projects.md`, `project`, created 2026-08-22
02:01:55). Each was served **exactly once ever**, inside a probe brief. They still exist, so
they are also among the 149 in the counterfactual population. Without them the population is 144, and
116107's served rank goes from 5 to 4.

The §2 claim *"sempre com 10 itens"* is true for every organic brief in the window and false
for exactly the five probes.

## Not measured

- **Production equivalence at byte level.** Not measured. The research-VPS epoch was used and
  matched every published quantity checked (above). Production `$NOX_PROD_HOST` was not touched.
- **Why the deleted ids kept being served for about 17 h.** Not measured (cause). Only the count (966 slots / 483 briefs) and the time bounds are measured.
- **Whether the 52 are part of the 152 "servidos e apagados depois" of §4.1.** Not measured,
  because it needs the 2026-08-28 production state for the full history. Out of scope.
- **Whether other days in the full brief_log history carry probe-only chunks.** Not measured.
  Only the §4.3 window was checked.
- **Probe identity for windows other than [20/08, 27/08).** Not measured.

## Proposed text changes

See the findings returned with this task. In short:

1. §4.3.1 (MANUSCRIPT l. 741–744): relabel 20/08 → 21/08 (85 → 33). State that 20/08 and 22/08
   lose the same 52, and that 966 of their 2,600 slots came after deletion.
2. §4.3.2 (l. 790–799): replace the "não conferimos" dilemma with the measured identity.
3. §4.3.2 (l. 802–806): replace "Quanto mais, não medimos" with the measured 180–183.
4. §4.3 (l. 613–625): replace "hypothesis" with the brief_id identity.
5. §4.3 table (l. 598–607): add the organic column or row, which gives 196 distinct.
6. §2 (l. 222–223): qualify "sempre com 10 itens".
7. "O que falta" item 5 (l. 2041–2042): mark both reconciliations closed, with a pointer to this
   report.
