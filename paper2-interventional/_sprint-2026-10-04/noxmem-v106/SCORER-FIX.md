# Scorer fix for Section 6: each retrieved id is credited once (v1.0.6 input)

Date: 2026-10-04. Origin: `../noxmem-evidence/REVIEW.md`, finding Codex 1 (confirmed there).
Scope: the scorer and every Section 6 value recomputable from per-query outputs.
The manuscript is **not** edited here, and nothing was deposited.

> **Update 2026-10-04 (evening, after the Codex/Fable review):** `recompute_section6.py` had
> broken once the dataset zip was regenerated: it read the "legacy" scorer from
> `../noxmem-evidence/nox-mem-section6-evidence-1.0.0.zip`, which by then carried the fixed
> scorer, so it compared v1.0.6 with itself, reported 0 changes and labelled them v1.0.5
> (Codex finding 1). It now reads the v1.0.5 record from
> `legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip`, keeps the v1.0.5 and v1.0.6
> expectations apart, and asserts that they differ on exactly the ten checks of section 4.
> Sections 3 and 7 below describe the current state; `payload/verify_dataset.py` now exits 0.

## 1. The defect and the fix

`eval/q4-comparison/aggregate.py` (and its verbatim copy in the dataset payload) scored
binary relevance per **occurrence**:

```python
rels = [1 if r in gold_ids else 0 for r in retrieved_ids[:k]]          # nDCG@k
hits = sum(1 for r in retrieved_ids[:k] if r in gold_ids)              # recall@k
```

A top 10 that holds the same gold id twice earns two gains, so nDCG@10 and recall@10 can
exceed 1. In the rc4 Mem0 output, 3 LongMemEval queries do this:

| query | repeated gold id(s) | nDCG@10 old → fixed | recall@10 old → fixed |
|---|---|---|---|
| `07741c44` | `answer_7e9ad7b4_1`, `answer_7e9ad7b4_2` | 1.5706 → 0.9197 | 2.0 → 1.0 |
| `07741c45` | `answer_7e9ad7b4_1`, `answer_7e9ad7b4_2` | 1.5706 → 0.9197 | 2.0 → 1.0 |
| `2ebe6c90` | `answer_c9d35c00_2` | 0.7479 → 0.4838 | 1.5 → 1.0 |

**Rule now:** cut to the top k first. Within that cut, each id counts once, at the rank
of its first occurrence. A later repeat keeps its slot as a non-relevant entry and is
**not** replaced, so the item at rank k+1 never moves up. nDCG@k and recall@k are in [0, 1].
MRR cannot change, since the first relevant occurrence is always a first occurrence, and
no MRR value moved. The rule matches the `ndcg_once`/`recall_once` sensitivity block that
`payload/verify_dataset.py` already printed, and it gives the same ten changed values.

### Files changed

| file | change |
|---|---|
| `eval/q4-comparison/aggregate.py` | new `_first_occurrences()`; `ndcg_at_k`, `recall_at_k` and `reciprocal_rank` go through it |
| `../noxmem-evidence/payload/scripts/aggregate.py` | byte-identical copy of the harness file (a test enforces this) |
| `paper/measurement/recompute-rc4-categories.py` | docstring notes the fix; `PAPER` holds the v1.0.6 §6.4 values (Mem0 temporal 0.4565, adversarial 0.2930); the v1.0.5 values are kept in `PAPER_V105`; new `--out` |
| `tests/test_scorer_dedup.py` (new, here) | unit tests (section 2) |
| `recompute_section6.py` (new, here) | recomputes all Section 6 checks under both scorers and rebuilds the aggregates |

`payload/scripts/recompute-rc4-categories.repo-original.py` was left as it is. It holds no
scorer: it imports `aggregate.ndcg_at_k`, and its name marks it as a frozen copy of the
repository file at deposit time.

## 2. Test

```
python3 paper2-interventional/_sprint-2026-10-04/noxmem-v106/tests/test_scorer_dedup.py
Ran 7 tests ... OK
```

The tests run against both copies of the scorer:

- a duplicated single gold id gives nDCG = 1.0 (old: 1.6309) and recall = 1.0 (old: 2.0);
- a duplicated gold id that is not at rank 1 gives 1.0 (old: 1.5);
- with two gold ids and a repeat at rank 3, the expected value is exactly (L(2)+L(5))/(L(1)+L(2));
- no re-padding: with k = 3, a repeat at rank 2 does not pull the gold id at rank 4 into the top 3, and a gold id after a repeat keeps its original rank;
- lists without repeats give the same values as before;
- 2,000 random lists all stay within [0, 1];
- the harness and payload copies are byte-identical.

**Mutation check:** running the same tests against the legacy scorer (taken from the
v1.0.5 record `legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip`, with its sha256
equal to that zip's `SHA256SUMS`) fails 5 of 7. The two that
pass, no-repad and no-duplicates, cover behavior the legacy scorer already had.

## 3. Inputs and how each was pinned

`recompute_section6.py` checks 32 pinned inputs, and all of them match:

- the four rc4 and rc4-ablation outputs against `eval/q4-comparison/MANIFESTO-LASTRO.json`;
- the smoke outputs (`output/{nox_mem,mem0,zep}.json`), the 2026-09-10 outputs and the pinned `_aggregate.*` against `payload/PROVENANCE.json`;
- the payload `runs/**`, `verify_dataset.py` and `scripts/aggregate.py` against `payload/SHA256SUMS`;
- every member of the v1.0.5 record (`legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip`,
  extracted to a temporary directory that is removed on exit) against that zip's own `SHA256SUMS`.

It runs three legs. Any failure exits 1; `--check` runs all of them and writes nothing.

- **(A) v1.0.5.** The legacy scorer differs from the fixed one byte for byte. The v1.0.5
  record's stored per-query metrics equal the legacy scorer (14,952 scored queries). Its own
  verifier, with the v1.0.5 printed values, passes 135/135 under the legacy scorer. Rebuilding
  the run-time `_aggregate.json` and `_aggregate.md` of the local originals with the legacy
  scorer is **byte-identical** to the pinned files for all three runs. The legacy scorer scores
  6 queries above 1 (3 queries × 2 identical Mem0 files); if it scored none, the leg fails.
- **(B) v1.0.6.** The payload's stored per-query metrics equal the fixed scorer, and no query
  scores above 1. The payload verifier, with the v1.0.6 printed values, passes 135/135. The
  fixed rebuild of the rc4 and ablation aggregates equals the payload's shipped files.
- **(C) Cross.** Both verifiers hold the same 135 check ids; the retrieved ids and gold ids of
  every query are identical in the two records (only stored metrics differ). The printed values
  differ between v1.0.5 and v1.0.6 on exactly the ten checks of section 4, and the two scorers,
  applied to the same table, give different printed values on exactly that set.

Mutation: pointing the script back at the regenerated zip (the original defect) fails leg C
(0 changed against 10 expected) and leg A (legacy rebuild of rc4 and rc4-ablation differs from
the pinned run-time files), exit 1.

The machine-readable output is in `out/section6-old-vs-new.json` (keys `paper_v105`,
`legacy_scorer`, `paper_v106`, `fixed_scorer` per check), `out/duplicate-census.json` and
`out/recompute-rc4-categories.json`.

## 4. Section 6 values that change

The fix changes 10 of the 135 checks at printed precision: 9 distinct printed values, with
0.4337 counted twice (R11 and A05). They appear **21 times** in the manuscript. Line numbers
refer to `paper/paper-tecnico-nox-mem.md` (v1.0.5 working tree, 2026-10-04).

| manuscript location | quantity (check id) | old (v1.0.5) | new (fixed) |
|---|---|---|---|
| l. 1016, §6.3.2 table, Mem0 row | Mem0 LongMemEval nDCG@10 (R07) | 0.4061 | **0.4030** |
| l. 1016, §6.3.2 table, Mem0 row | its 95% CI half-width (R08) | ± 0.036 | **± 0.035** |
| l. 1016, §6.3.2 table, Mem0 row | Mem0 overall nDCG@10 (R11) | 0.4337 | **0.4331** |
| l. 1016, §6.3.2 table, Mem0 row | Mem0 overall CI (R12) | ± 0.016 | ± 0.016 (unchanged; raw 0.01558 → 0.01553) |
| l. 1020, §6.3.2 "Result" | Δ LongMemEval nox-mem − Mem0 (R17) | +0.119 | **+0.123** (printed 0.5255 − 0.4030 = 0.1225; unrounded 0.12253; both round to 0.123) |
| l. 1020, §6.3.2 "Result" | Δ LoCoMo (R18) | +0.055 | +0.055 (unchanged) |
| l. 1024, §6.3.2 ablation | "still outperforms Mem0 (0.4337)" (A05) | 0.4337 | **0.4331** |
| l. 1024, §6.3.2 ablation | "LongMemEval 0.5215 vs 0.4061" (Mem0 side; same quantity as R07) | 0.4061 | **0.4030** |
| l. 1045, §6.3.3 table, Mem0 row | nDCG@10 overall | 0.4337 | **0.4331** |
| l. 1045, §6.3.3 table, Mem0 row | LongMemEval | 0.4061 | **0.4030** |
| l. 1045, §6.3.3 table, Mem0 row | R@10 (E10) | 0.5852 | **0.5842** |
| l. 1069, §6.3.4 table, Mem0 row | nDCG@10 overall | 0.4337 | **0.4331** |
| l. 1069, §6.3.4 table, Mem0 row | LongMemEval | 0.4061 | **0.4030** |
| l. 1069, §6.3.4 table, Mem0 row | R@10 (E10) | 0.5852 | **0.5842** |
| l. 1115, §6.4 table, temporal | Mem0 nDCG@10 (C13) | 0.4570 | **0.4565** |
| l. 1115, §6.4 table, temporal | Δ (C14) | +0.093 | **+0.094** |
| l. 1116, §6.4 table, adversarial | Mem0 nDCG@10 (C18) | 0.2955 | **0.2930** |
| l. 1116, §6.4 table, adversarial | Δ (C19) | +0.142 | **+0.144** |
| l. 1120, §6.4 prose | "largest margins are on adversarial (+0.142) and temporal (+0.093)" | +0.142 / +0.093 | **+0.144 / +0.094** |
| l. 1120, §6.4 ablation sentence | "adversarial 0.4573 vs 0.2955; temporal 0.5571 vs 0.4570" | 0.2955 / 0.4570 | **0.2930 / 0.4565** |
| l. 1122, §6.4 bucket composition | "(nox-mem's largest margin, +0.142)" | +0.142 | **+0.144** |
| l. 1022, §6.3.2 (e) (a sentence, not a number) | "Scoring is by id, so a collision cannot mis-score a retrieval" | true only for the gold side | **false for the retrieved side.** Suggested replacement: "Scoring is by id. In 3 LongMemEval queries Mem0 returned both documents behind one gold id; the scorer used before v1.0.6 credited both, which v1.0.6 corrects by crediting each retrieved id once." |

Raw values under the fixed scorer:

| quantity | value |
|---|---|
| Mem0 rc4 LongMemEval | 0.403004 |
| Mem0 rc4 overall | 0.433102 |
| Mem0 rc4 R@10 | 0.584218 |
| §6.4 Mem0 temporal | 0.456456 |
| §6.4 Mem0 adversarial | 0.292985 |
| Δ temporal | 0.093724 |
| Δ adversarial | 0.144054 |
| nox-mem − Mem0 overall (not printed) | 0.06817 (was 0.06754) |

### What does not change (125 of 135 checks)

- every nox-mem value, including the rc4 and ablation arms, their CIs, R@10, MRR, p50 and §6.4 cells;
- every Mem0 LoCoMo value: 0.4407 ± 0.017 and Δ LoCoMo +0.055;
- every MRR, including Mem0 0.4092, and every latency;
- EverOS (all of §6.3.3 E01-E19) and Zep (Z01-Z18);
- the superseded smoke runs (S01-S13), the collision and back-fill counts (R19-R40), and the gold coverage of the ablation;
- §6.4 single-hop, multi-hop and open-domain for Mem0, with their deltas;
- all 13 yes/no statements: the 95% CIs stay disjoint on both datasets and overall (R16); nox-mem still leads every represented category (C26); the ablation still leads all five categories (A07); the ablation margin is ≥ +0.05 on both datasets (A11; LongMemEval margin now 0.1185); Zep still ranks third and its LongMemEval cell is still the table's lowest (Z09, Z10). **No ordering, sign or conclusion changes.** Every change lowers Mem0 and widens nox-mem's lead.

### The same values outside the manuscript (not edited by this task; `README.md` and `docs/COMPARISON.md` were updated on 2026-10-04 evening, see `APPLY-CODEX-FABLE.md`)

- `README.md` l. 58, 309, 311, 326 (0.4337, 0.4061, +0.119)
- `docs/COMPARISON.md` l. 280, 282
- `../noxmem-apelacao-pacote.md`, item 3 of the letter, which describes the defect with the example 0.4061 → 0.4030. After v1.0.6 this becomes a dated correction, as `../noxmem-evidence/REVIEW.md` already planned.
- `../noxmem-evidence/zenodo-metadata.json` and `payload/README.md` ("Further observations")

## 5. Which systems and runs had any duplicate ids

The census covers every local output that has per-query results (`out/duplicate-census.json`):

| output | system | n | queries with a repeated id in top 10 | of which the repeated id is gold | cited in §6? |
|---|---|---|---|---|---|
| `output/rc4/mem0.json` | Mem0 | 2,482 | **20** (all LongMemEval; every repeated id is one of the 8 ids shared by two offered documents) | **3** | yes (§6.3.2–§6.4) |
| `output/rc4-ablation/mem0.json` | Mem0 | 2,482 | **20** | **3** | yes (same file as rc4: same sha256) |
| `output/agentmemory_full.json` | agentmemory | 20 | **2** | **1** (`conv-26::q83`, LoCoMo; nDCG 0.6895 → 0.3562) | **no** (smoke of 2026-05-24; no §6 number comes from it) |
| `output/rc4/nox_mem.json`, `output/rc4-ablation/nox_mem.json` | nox-mem | 2,482 each | 0 | 0 | yes |
| `output-2026-09-10/evermind.json` | EverOS | 2,482 | 0 | 0 | yes |
| `output-2026-09-10/zep.json` | Zep | 2,482 | 0 | 0 | yes |
| `output/{nox_mem,mem0,zep}.json` (smoke) | nox-mem, Mem0, Zep | 20 each | 0 | 0 | yes (S01-S13) |
| `output/{agentmemory,evermind,hipporag2,lightrag}.json` | various | 5-20 | 0 | 0 | no |

Counting repeats over each full result list, instead of the top 10, gives the same counts. The canonical 2026-06-15 run (§6.3) and the capped smokes of §6.6 left no per-query
outputs, so they **cannot** be audited for repeats (declared in `verify_dataset.py`,
`NOT_RECOMPUTABLE`).

## 6. Regenerated aggregates (new location; the pinned originals are untouched)

The regenerated files are in `aggregates/<run>/_aggregate.{json,md}`. They were built from
the hash-verified local originals with the fixed `aggregate.py`, using the same sort and
render code as `aggregate.py main()`, which was not called because it writes into the
source directory.

| run | source (pinned, not modified) | pinned sha256 (json / md) | fixed sha256 (json / md) | differs? |
|---|---|---|---|---|
| rc4 | `eval/q4-comparison/output/rc4/` | `b8bd6e60…3178e` / `d93129ac…0ae5da` | `2eaaad39…e05486` / `33aa1501…41ec0` | Mem0 rows only |
| rc4-ablation | `eval/q4-comparison/output/rc4-ablation/` | `ff4cfcbe…62b85` / `3b3b5639…35ddc` | `533f625f…92289` / `faa7338f…76f07` | Mem0 rows only |
| 2026-09-10 | `eval/q4-comparison/output-2026-09-10/` | `4d220ec4…e79a2` / `354c2ef0…506a8` | identical | no (control) |

In both rc4 aggregates, the Mem0 changes are:

| field | old | new |
|---|---|---|
| overall nDCG | 0.4337 | 0.4331 |
| overall R@10 | 0.5852 | 0.5842 |
| LongMemEval nDCG | 0.4061 | 0.4030 |
| LongMemEval R@10 | 0.5141 | 0.5091 |
| adversarial | 0.2955 | 0.2930 |
| temporal (run-time label map) | 0.2760 | 0.2748 |

The `_aggregate.md` files keep the run-time LoCoMo label map, which §6.4 declares wrong.
The §6.4 numbers come from `recompute-rc4-categories.py`, whose v1.0.6 run is in
`out/recompute-rc4-categories.json` (exit 0). The versioned
`paper/measurement/out/recompute-rc4-categories.json` was **not** overwritten.

## 7. State as of 2026-10-04 evening

- **`payload/verify_dataset.py` exits 0** (`--manuscript paper/paper-tecnico-nox-mem.md`:
  135/135 equal to the paper, 12 groups declared not recomputable). The payload was
  regenerated with the fixed scorer: stored metrics of the 2 × 3 Mem0 queries, the two rc4
  `_aggregate.*` pairs, table `N`, `README.md`, `SHA256SUMS` and the zip
  `../noxmem-evidence/nox-mem-section6-evidence-1.0.0.zip`. The pre-fix zip is kept, renamed,
  as `legacy-input/nox-mem-section6-evidence-1.0.0.v105-scorer.zip`, and is the v1.0.5
  record this script reads. Nothing was deposited.
- **The manuscript** carries the 21 numeric occurrences and the rewritten (e) sentence
  (v1.0.6 working tree). `PARITY.txt` now checks the final text, after the Codex/Fable wording
  corrections: 19 of the 22 substitutions outside the 11 wording lines, the other 3 and the
  numbers added or removed on those lines in a separate leg (`parity-v106.py`, exit 0). Its
  first run, at 20:56, was on an intermediate text (sha256 `76d01388…`) and covered only the
  scorer pass.
- **The same defect class in other scorers:** the copies of `ndcg_at_k`/`recall_at_k` in
  `eval/` were given the same first-occurrence rule on 2026-10-04 evening; see
  `APPLY-CODEX-FABLE.md` (finding Fable E) for the list and the outputs each one feeds. No
  published number changes. The scorers under `paper/publication/baselines/` were not audited.
- **The unit test lives here,** not in `eval/q4-comparison/test/`. To move it there when the
  change is committed, change `ROOT = Path(__file__).resolve().parents[4]` to `parents[3]`.
