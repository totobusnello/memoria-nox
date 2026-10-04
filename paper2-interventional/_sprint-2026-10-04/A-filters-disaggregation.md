# A — Disaggregating the main pool's serial filters (open item 6)

Sprint 2026-10-04. Closes, with measurement, item 6 of the final list of `MANUSCRIPT.md`
(*"the seven serial filters are not disaggregated"*): §4.3.1 decomposes the **coverage
channel** filter by filter; the **main pool** (8 of 10 brief slots) never got that
decomposition, so «policy, not capacity» was supported for the channel and **assumed** for
the main pool.

**Verdict, plainly.** The main pool is **not capacity-bound** at the level the paper
measures exposure, which is the day. Across a day it has **5,376 slots** and serves
**33 distinct chunks**, the same 33 on every measurable day from 2026-08-21 to 2026-09-21.
That is 0.61% of its slot capacity and 163 serves per distinct chunk. **None of the seven
filters is what holds it at 33.** Lifting any one of them, with the other six kept, never
raises the daily breadth above 33. Lifting two of them lowers it to 8. The breadth is
exactly `3 + 6 agents × 5`. The 3 slots are shared by every brief and the 5 are routed per
agent, so it is set by the routing and the quota, multiplied through a ranking that returns
the same arg-max for the same route in every brief. The ranking has no serve-history term,
and that is a design decision on record (`brief.ts:786-792`: mechanism A retired
2026-06-26 *"to keep relevance stable in the base brief"*). So the thesis holds for the main
pool too, but **the policy is a different one** from the coverage channel's. In the channel
it is an **eligibility predicate** (paths and an age window) that the slots exhaust. In the
main pool it is a **deterministic top-k without rotation**, and the slots never get close
to running out. The manuscript's wording should say which policy it means in each case.

One correction comes with it. The paper says three chunks appear in 100% of briefs, and in
the window measured here those 3 chunks are the **pinned high-pain floor (F7)**, not the
salience ranking converging. Without F7 two of the three would still be there.

---

## 1. Where the seven filters are (read from the deposited code)

Production call (`openclaw-vps/infra/docs/session-priming-f3.md`):
`GET /api/brief?scope=global&agent=<p>&format=text&n=10`, cron `7,22,37,52 * * * *` × 6
agents. The trial serving log agrees with it: every line has `scope: "global"` and 10 ids.
The only exceptions are 5 lines with `agent: null` and 5 ids, which are excluded.

| # | filter | code (deposited blob) | what it does with scope=global, agent=a, n=10 |
|---|---|---|---|
| F1 | scope routing | `serving-brief.ts:202-215, 521-539` | agent sub-pool sees only `sessions/<a>/%` (quota `ceil(n/2)=5`); scope sub-pool gets **no** path pattern for `global` (`:204`) and sees the whole corpus (quota `floor(n/2)=5`) |
| F2 | `since` window | `:371-374` | `updated_at >= now − since`. **Inactive**: the caller sends no `since` |
| F3 | proxy pre-rank + LIMIT | `:104, 377-390` | `0.55·imp + 0.10·pain + 0.1·[access>0]` DESC, `updated_at` DESC, **LIMIT 500** per sub-pool |
| F4 | exact re-rank | `:392-397`, `serving-salience.ts:246-263` | `calculateSalience(row, nowMs)` over the 500, stable sort |
| F5 | dedup | `:420-434` | exact id; exact `title\|one_liner`; near-dup containment ≥ 0.6 against what is already picked |
| F6 | quota + mainTarget | `:436, 453-468` | 5 + 5 quotas, both capped by `mainTarget = n − freshSlots = 8` |
| F7 | pinned high-pain floor | `:442-451, 819-821`; `serving-brief-diversity.ts:57` | items of the no-fresh "current" brief with `pain ≥ 0.9` are picked first |
| (F8) | text render cut, **after** `brief_log` | `:137, 867-881` | lines beyond `TOKEN_BUDGET = 1200` are not shown to the agent |

⚠️ **The list of seven comes from the code, not from the review.** The Codex review of
2026-09-21 that named "seven serial filters" kept only its receipt
(`memoria-nox/.remember/adversary-receipt-codex-2026-09-21T164555-79601.txt`, 435,935 output
bytes). I searched for its output by that timestamp under `~/Claude`, `~/.claude`,
`~/Backups` and `/private/tmp`, and only the receipt was found. Whether Codex's seven are
these seven is therefore **NOT VERIFIABLE**. The seven above are every stage between the
corpus and the 8 main slots in `buildBriefDiverse → pickDedup`. F8 is listed separately
because it acts after the exposure log.

## 2. Data and the choice of database

* **Primary: `corpus/p2-ord-ro-2026-08-26.db`** (sha256 `74ef0d30…`, matches
  `p2-bancos-ensaio.sha256`). This is the frozen corpus of the §4.3.1 period: **67,187**
  chunks (the "corpus vivo" of the §4.3.1 table) and `MAX(created_at) = 2026-08-24 01:06:35`
  (`DEVIATIONS-FOR-PAPER.md:645-651`). The main pool reads only `chunks`, so the right
  corpus is the one that was served on the §4.3.1 days (26–29/08), and this is it.
  §4 shows that the reconstruction from it reproduces those days exactly.
* **Secondary: `corpus-preservado-20260908.db`** (sha256 `b277bc96…`): 67,606 chunks,
  `MAX(created_at) = 2026-09-08 02:37:34`. It is the trial corpus (09-07…09-20), included so
  the result is not limited to the pre-trial week.
* Serving log: `~/Backups/paper2-ensaio-2026-09-21/p2-serving.ndjson` (sha256 `a25f9aef…`,
  19,572 lines), which is the trial lastro.

**Copy-first trail.** Both DBs were `cp`'d on the research VPS ($NOX_LASTRO_HOST) into
`/var/tmp/sprint-filtros-pp/`, sha-checked against the manifest on the copy, and used only
there. Opening the copy read-only still created `ord-0826.db-wal` and `-shm`, which is
exactly why the copy rule exists. The directory was `rm -rf`'d at the end and its absence
was verified (`ls: cannot access`). Production ($NOX_PROD_HOST) was not touched. No local DB
copy was made. Hashes: `A-filters-disaggregation/copies-sha256.txt`.

Script: `measurement/sprint-desagrega-filtros-pool-principal.py`. The DB runs used the
version with sha256 `ebedee81…`. The `--log-only` mode was added afterwards and the DB code
path is unchanged; the final file is `c4453580…`. Outputs are in
`_sprint-2026-10-04/A-filters-disaggregation/`:

| file | what |
|---|---|
| `out-ord0826.json` | epochs 2026-08-21…09-07 on the 08-26 corpus (09-02 has no brief in the log) |
| `out-pres0908.json` | epochs 2026-09-07…09-20 on the preserved trial corpus |
| `out-ord0826-tzm3-0828.json` | 08-28 re-run with zone-less dates parsed as UTC−3 (sensitivity) |
| `observed-main-from-log.json` | observation-only census from the serving log, no database |
| `diag-residual-mismatch.py`, `diag-out.txt` | the residual mismatches, attributed (§4) |

## 3. A defect of my own, caught before any number left

In the first full run the F3-lifted variant ("no LIMIT") reported 17 distinct chunks and 480
changed briefs. The cause was a bug. When a sub-pool had fewer rows than the shortlist size
k = 3000 (nox 520, boris 924, forge 1,414, lex 23), the threshold was set to `−inf`, the
shortlist came back **empty**, and those agents' 5 slots were silently backfilled from the
global pool. I found it by printing the picks, and no guard caught it. After the fix
(`+inf`), the script now raises if the shortlist is shorter than `min(k, n)`. **The correct
figure is 0 changed briefs** (§6). It is recorded here because the wrong number told a clean
story ("the LIMIT binds"), and that is exactly the kind of error that gets published.

## 4. Fidelity: does the reconstruction reproduce what was served?

Per brief, the reconstructed 8 main slots are compared with the 10 served ids
(`ids_controle`). A brief counts as *exact* when the 8 sit inside the 10 and leave exactly
the 2 coverage slots.

| corpus | epochs | briefs exact | slots of the reconstruction found in the served brief |
|---|---|---:|---:|
| 08-26 copy | 08-24 … 09-07 (14 epochs) | **100%** in every epoch (672/672; 441/441 on 09-03) | **100%** |
| 08-26 copy | 08-21 / 08-22 / 08-23 | 242/282 · 576/672 · 549/560 | 98.2% · 98.2% · 99.75% |
| 09-08 copy | 09-07 … 09-20 | 576/672 in every epoch | 98.2% |

**The residual mismatches are differences of corpus state, not of logic.** The mismatches
are always **boris** and always **one** slot, 96 briefs a day (`diag-out.txt`):

* 08-22: the copy has chunk 298048 with `access_count = 2` and
  `last_accessed_at = 2026-08-22T19:09Z`. That access happened **after** the 09:07 brief, so
  the copy ranks it above 285042, which is what was actually served.
* 09-08…09-20: the copy contains 309216, created `2026-09-08 02:20:50` with 3 accesses. The
  served corpus kept 298048. The 09-08 copy is not the served state for that one chunk.
* Control: the same diagnostic on 08-28 finds **no** mismatch.

TZ sensitivity: parsing zone-less timestamps as UTC−3 instead of UTC gives **identical**
fidelity, ids and leave-one-out on 08-28 (`out-ord0826-tzm3-0828.json`).

A caveat about the log that a naive reading would get wrong: `fresh_added` is logged from
the **treated** composition (`diffP2`, `brief.ts:855-859`). On the 14–38 briefs a day where
the control's fresh picks differ, `ids_controle − fresh_added` has 9 ids, not 8. On control
epochs after the 2026-09-03 logging fix it is `null`. Exactness is therefore tested as
"8 inside 10, leaving 2", never as `ids − fresh_added == recon`.

## 5. Series attrition, the §4.3.1 days (08-26 … 08-29 are identical; 08-28 shown)

`out-ord0826.json → per_epoch["2026-08-28"]`. The unit is distinct chunks over the epoch
(672 briefs; nox 192, the other five agents 96 each).

| stage | remaining | removed here | note |
|---|---:|---:|---|
| corpus | 67,187 | — | |
| F1 scope routing (union of sub-pool sources) | 67,187 | 0 | agent sources: atlas 3,805 · boris 924 · cipher 7,770 · forge 1,414 · lex 23 · nox 520 (Σ 14,456); scope source = whole corpus |
| F2 `since` | 67,187 | 0 | inactive |
| F3 proxy + LIMIT 500 (7 lists, union) | 2,860 | 64,327 (95.7%) | |
| F4 exact re-rank | 2,860 | 0 | reorders only |
| F5 dedup (during the picks) | — | 13 distinct near-dups rejected; 0 by exact key | 116466 and 116465 (other sections of pinned 116467's plan file, salience ranks 2–3 of the scope sub-pool) are among them, which follows from the pick order: neither was picked, neither was pinned, and no exact-key rejection occurred |
| F6 quota + mainTarget, with F7 | **33** | — | 8 per brief = 3 pinned + 5 agent |
| F7 pinned floor | 3 ids in 672/672 briefs | — | 112241, 116107, 116467, all `pain = 1.0`; they take all three of the scope sub-pool's slots (phase 0 = 2,016 picks = 3 × 672; phase 1 = 3,360 = 5 × 672) |
| (F8) render cut | 0 lines dropped | — | in every brief whose 10 rows exist in the copy (all briefs 08-23…09-07). On 08-21/22 some fresh ids no longer exist in the copy, so it is NOT MEASURED there |

**What the series table does not say.** F3 "removes" 95.7% of the corpus from candidacy, and
§6 shows it binds nothing. A per-filter count of exclusions is the wrong instrument for
"which filter limits exposure". It is reported because the review asked for attrition, and
the leave-one-out table below is what answers the question.

### Each filter alone, on the whole corpus (08-26 copy)

| filter alone | passes | |
|---|---:|---|
| F1 | 67,187 (union) / 14,456 (agent sources) | routes slots, excludes nothing from the union |
| F2 | 67,187 | inactive |
| F3 | 2,860 | 500 per sub-pool × 7, overlapping |
| F4 | 67,187 | reorder |
| F5, exact-key part | 54,574 distinct keys; 12,613 chunks share a key with a higher-salience chunk | near-dup part **NOT MEASURED**: greedy containment over 67k signatures is quadratic and only defined relative to the picked set |
| F6 | 8 slots per brief; 5,376 per day | |
| F7 | 535 chunks with `pain ≥ 0.9` | pinnable only if already in the current brief |

## 6. Leave-one-out: which filter binds?

Lift one filter, keep the other six, recompute all 672 briefs. These are the 08-26 copy's
values for 08-28. Every epoch from 08-24 to 09-07 gives identical values; the 09-08 copy
gives the same except F4 Jaccard 0.472 and F7 (below).

| lifted | briefs whose main set changes | mean Jaccard vs served | distinct main chunks / day |
|---|---:|---:|---:|
| none (as served) | — | 1 | **33** |
| F1 scope routing | 672 | 0.245 | **8** |
| F2 `since` | — | — | 33 (inactive, identical by construction) |
| F3 LIMIT 500 | **0** | 1.000 | 33 |
| F4 exact re-rank (proxy order instead) | 672 | 0.493 | 33 |
| F5 dedup (id-dedup kept) | 192 | 0.848 | 33 |
| F6 quota split (one merged ranking) | 672 | 0.245 | **8** |
| F7 pinned floor | 672 | 0.778 | 33 |

On the 09-08 copy, lifting F7 changes 665/672 briefs on 09-17 (34 distinct) and 0/672 on
09-18…09-20. As recency moves, the floor's 3 and the scope sub-pool's own top 3 converge, and
the floor becomes idle.

Reading: **no single filter, lifted, widens the daily surface.** F3, F4, F5 and F7 change
*which* chunks fill the slots, or none, and leave the breadth at 33. F1 and F6 are the only
filters that change the breadth, and they **narrow** it to 8, because without per-agent
routing every agent receives the same 8. Routing is the main pool's **only** source of
variety.

## 7. Capacity

| | main pool | coverage channel (§4.3.1) |
|---|---:|---:|
| slots per day | 5,376 (8 × 672) | 1,344 (2 × 672) |
| candidates the ranking admits | 67,187 (no eligibility predicate) | 108 |
| distinct served per day | **33** | 108 (100% of pool) |
| slots per distinct served | **162.9** | 12.4 |
| share of slot capacity spent on distinct chunks | **0.61%** | — (pool exhausted) |
| distinct per day if the same slots rotated (arithmetic) | 5,376 = 8.0% of corpus | 108 |

At the level of **one brief**, the main pool is capacity-bound in the trivial sense that
every top-8 is: there are 8 slots and about 67k candidates. At the level of **the day**,
which is the unit at which §4.1 measures exposure, it is not. The same slots could carry
5,376 distinct chunks, which would touch the whole corpus in about 12.5 days of rotation.
They carry 33 for a month. Capacity is a real ceiling, at 8.0% of the corpus per day, and
the observed point sits about 163× below it.

## 8. Observation-only cross-check (no database, no reimplementation)

`observed-main-from-log.json`, from `p2-serving.ndjson` alone, keeps only briefs whose
`ids_controle − fresh_added` has exactly 8 ids:

* **33 distinct main-slot chunks** in every measurable epoch (08-21, 08-22, 08-24 … 09-01,
  09-04 … 09-06, 09-08, 09-09, 09-12, 09-14 … 09-16, 09-19, 09-21), **8 per agent**, every
  agent. 08-23 shows 34, because 298048 enters for boris after the access bump in §4. The
  epochs whose lines carry `fresh_added = null` (09-03, 09-07, 09-10, 09-11, 09-13, 09-17,
  09-18, 09-20) are **NOT MEASURABLE** by this route and are not counted as zero.
* **Union over the whole window (08-21 … 09-21): 37.** That is the 33, plus 298048, plus 3
  new ids (309422, 309529, 311215) on 09-21.
* Distinct over **all 10 slots** is **141 on every day from 08-24 to 09-19**, and
  141 = 33 + 108. The two channels are disjoint and together are the whole daily surface,
  which independently corroborates §4.3.1's 108.

## 9. What the numbers force in the text

1. **«Policy, not capacity» survives for the main pool, but «policy» has to be specified
   per channel.** For coverage the policy is *which paths and ages are eligible*. For the
   main pool it is *a deterministic top-k with no serve-history term, routed by agent*. As
   written, the sentence implies one mechanism.
2. **The main pool's corpus-wide window is 3 slots, and those 3 are the high-pain floor.**
   With `pinned` taking phase 0, the scope sub-pool's quota is never reached in phase 1
   (of the 3,360 non-pinned slot-fills in a day it gets **0**; all 3,360 go to the agent sub-pools). The 3 chunks "in 100% of briefs" are
   112241, 116107 and 116467, pinned at `pain = 1.0`. This is established for the
   08-21…09-21 window. The 47.16% top-10 week of §4 was **not re-measured** here.
3. **The per-filter exclusion count is not evidence of binding.** F3 removes 95.7% of the
   corpus and binds nothing. If §4.3.1 is ever extended with an attrition table, it needs
   the leave-one-out column beside it.

## 10. NOT MEASURED / limits

* Whether Codex's "seven filters" are these seven: its output was not preserved (§1).
* F5 near-dup **alone** on the whole corpus (quadratic, relational).
* F8 render cut on 08-21/08-22 and on most of the 09-08 copy's briefs, where served fresh ids
  are absent from the copy. Only briefs with every row present are counted.
* The no-LIMIT variant shortlists the top 3,000 by vectorised salience before rescoring
  with the scalar function. A pick below rank 3,000 would need more than 2,990 dedup
  rejections in one brief, and the run saw 13 in total.
* `Date.parse` of zone-less timestamps follows V8 (local time). The serving host's TZ was
  not read (production was not touched). Both UTC and UTC−3 give identical results on
  08-28.
* Everything is on 6 agents × `scope=global` × `n=10`, the only call shape in the log. Other
  call shapes (`scope=<project>`, `since`) were not exercised by production in the window,
  and nothing here speaks to them.
