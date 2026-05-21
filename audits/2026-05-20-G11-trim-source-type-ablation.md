# G11 — Trim SOURCE_TYPE_BOOST Ablation vs Hard Mutex

**Date:** 2026-05-20
**Branch:** `experiment/g11-trim-source-type`
**Question:** Post Hard Mutex deploy (PR #182), does trimming top SOURCE_TYPE_BOOST values (entity 2.0→1.3, lesson 1.8→1.2) add incremental value or is the mutex alone sufficient to neutralize redundancy with `section_boost compiled=2.0`?

**Verdict: REVERT TRIM — Hard Mutex (PR #182) alone is sufficient.** Trim degrades top-rank quality (nDCG -0.73%, MRR -1.58%) with only marginal gains in deeper retrieval (R@10 +0.82%, P@5 +1.15%). Single-hop category — where entity files most concentrate — loses 4.62% nDCG and 7.40% MRR. **D48 should close with mutex-only; do not deploy trim.**

---

## Setup

| Field | Value |
|---|---|
| DB | `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db` |
| Corpus | 69,495 chunks (g5.db prod 68k + 500 entity-eval-v2 chunks) |
| Endpoint | `http://127.0.0.1:18803/api/search` (isolated, NOT prod 18802) |
| Service | `node dist/api-server.js` via tmux, port 18803 |
| Driver | `entity_ablation_eval.py` (G3-patched, regex chunk-id extraction) |
| Queries | `queries.jsonl` n=100 (5 categories × 20: single-hop, multi-hop, temporal, open-domain, adversarial; 2 styles: natural-language + keyword) |
| Env A8 | `NOX_SALIENCE_MODE=active` (all default-on; Hard Mutex active by default) |
| dist source | `/root/.openclaw/workspace/tools/nox-mem/dist/search.js` swapped via sed, **restored after run** (verified `diff -q` clean) |
| Backup | `/tmp/g11-search.js.original-1779330411` |

### Code change isolated

`staged-1.7a/edits/search.ts` only:

```diff
 const SOURCE_TYPE_BOOST: Record<string, number> = {
+  // G11 trim experiment (2026-05-20): entity 2.0→1.3, lesson 1.8→1.2
   // Active keys (post-backfill 2026-05-19)
-  entity: 2.0,
-  lesson: 1.8,
+  entity: 1.3,
+  lesson: 1.2,
   skill: 1.5,
   ...
 };
```

All other values unchanged (`skill: 1.5`, `project-doc: 1.4`, `command: 1.4`, `legal-template: 1.3`, `personal-doc: 1.2`, `session/note: 1.0`, `external: 0.8`, `other/ocr-cache: 0.7`, `user_statement: 2.0`).

Hard Mutex (`NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE` not set) active in BOTH runs.

---

## Results

### Headline (n=100)

| Config | nDCG@10 | MRR | R@10 | P@5 | mean lat | p95 lat |
|---|---|---|---|---|---|---|
| **G11_baseline** (canonical, mutex ON) | **0.5376** | **0.5843** | 0.6083 | 0.1740 | 860ms | 1415ms |
| **G11_trim** (entity=1.3, lesson=1.2, mutex ON) | **0.5337** | 0.5751 | **0.6133** | **0.1760** | 896ms | 1431ms |
| **Δ (trim − baseline)** | **−0.0039 (−0.73%)** | **−0.0092 (−1.58%)** | +0.0050 (+0.82%) | +0.0020 (+1.15%) | +36ms | +16ms |

Top-rank quality degraded; deep retrieval marginally better.

### Per-category (nDCG@10)

| Category (n=20) | Baseline | Trim | Δ | Δ% |
|---|---|---|---|---|
| single-hop | 0.5405 | 0.5155 | −0.0250 | **−4.62%** |
| multi-hop | 0.6792 | 0.6692 | −0.0100 | −1.47% |
| temporal | 0.0000 | 0.0000 | 0 | n/a |
| open-domain | 0.7633 | 0.7633 | 0 | 0% |
| adversarial | 0.7051 | 0.7204 | +0.0153 | **+2.17%** |

Single-hop (highest entity concentration) hurt most. Adversarial improved slightly.

### Per-category (MRR)

| Category | Baseline | Trim | Δ% |
|---|---|---|---|
| single-hop | 0.4500 | 0.4167 | **−7.40%** |
| multi-hop | 0.9250 | 0.9000 | −2.70% |
| temporal | 0 | 0 | n/a |
| open-domain | 0.7875 | 0.7875 | 0% |
| adversarial | 0.7591 | 0.7712 | +1.59% |

### Per-style (nDCG@10)

| Style (n=50) | Baseline | Trim | Δ% |
|---|---|---|---|
| natural-language | 0.5487 | 0.5387 | −1.82% |
| keyword | 0.5265 | 0.5286 | +0.40% |

Natural-language queries (which benefit more from semantic prioritization of high-signal entity sources) hurt more by trim.

---

## Comparison vs spec-quoted G10 numbers

Spec quoted G10 baseline numbers (mutex ON normal values = `0.5478` nDCG@10, mutex OFF = `0.5435`). On VPS I could not find a G10 result file matching those numbers — only the failed run log (`g10-results-2026-05-20T161546/g10-ablations.log` aborted at preflight on a g5.db stub). The G9 ablation results in `results/A8_full_canonical.json` show **0.5387 nDCG@10** (same DB g9.db, same dist with mutex active by default, run 2026-05-20 ~16:00).

My G11_baseline (re-run today on the same setup) gave **0.5376** — within 0.2% of the G9 ablation A8, confirming reproducibility. The spec's `0.5478` for "G10 A8'" appears to be a different measurement or estimate; my fresh re-run is the cleanest control for the trim ablation.

**Bottom line:** baseline-vs-trim comparison is internally consistent (same DB, same code except 2 values, back-to-back run within minutes) — Δ is real, not measurement noise.

---

## Interpretation

### Hypothesis revisited

**Hypothesis G11:** trim top values reduces amplification redundant with section_boost compiled=2.0 after Hard Mutex (PR #182). Either improves nDCG or is neutral.

**Observed:** trim is **mildly harmful, not neutral**. nDCG -0.73%, MRR -1.58%. The harm concentrates on single-hop (-4.62%), the category where entity files dominate gold answers.

### Why trim hurt

Hard Mutex (PR #182) already kills `sourceTypeDelta` when `section` is populated — i.e. for the `compiled` truth chunk of every entity file, source_type boost was already returning 0. So the `entity: 2.0` boost only fires for entity-typed chunks where `section IS NULL` (e.g. legacy chunks, non-section-bearing rows). Trimming entity 2.0→1.3 reduced the boost on exactly those legacy entity rows that DO need to outrank generic notes.

For lesson chunks (no section_boost ever applies, since lessons aren't ingested via ingest-entity), the `lesson: 1.8` boost was the only signal lifting them above generic chunks. Cutting to 1.2 brought lessons closer to `personal-doc: 1.2` and `external: 0.8` — flattening the source-type prior right when it was most needed.

### Adversarial improvement is misleading

Adversarial +2.17% nDCG with trim looks like a win, but n=20 with single-hop -4.62% (n=20) net negative across whole suite. P@5 +1.15% and R@10 +0.82% suggest trim slightly improved ranking of items between rank 5-10 — not the top-3 region that nDCG@10 weights most.

### Mutex alone is the right design

PR #182 Hard Mutex resolves the original redundancy (entity+compiled double-boost) **without flattening the source-type prior** for chunks that legitimately need it. Trim attempts to solve the same problem but by globally reducing entity/lesson signal, which over-corrects.

---

## Verdict

**REVERT TRIM. KEEP CURRENT CANONICAL SOURCE_TYPE_BOOST VALUES.** Hard Mutex (PR #182) is the correct fix; trim is not additive.

This PR documents the negative result so future researchers do not re-run the same experiment. **Do not merge the code change** — it is intentionally left committed on the experiment branch as a historical reference for the audit.

---

## Action items (D48 final close)

1. **D48 close:** mark trim experiment as researched & rejected; mutex (PR #182) is the canonical resolution to G8/G9 redundancy finding.
2. **Paper update (claim 4, §5.5):** add a note that trim ablation was attempted post-mutex and rejected (Δ -0.73% nDCG@10 on g9.db n=100). Keep paper narrative: mutex resolves redundancy without sacrificing source-type prior strength.
3. **Reject PR (do not merge):** `experiment/g11-trim-source-type` branch is documentation-only. Comment with verdict and close without merge, OR merge audit doc + revert source change in a single follow-up.
4. **Consider next ablation (optional):** if redundancy concern still nags, the surgical alternative would be to leave `entity: 2.0` (legacy path) intact and only trim where MUTEX bypass cases exist. Requires log analysis of which corpus rows actually fire `sourceTypeDelta != 0` post-PR-#182. Probably not worth the effort given mutex result already validates +0.79% nDCG/+2.65% MRR.
5. **Cleanup VPS:** `/tmp/g11-search.js.*` and `/tmp/g11-runner.sh` can be removed (no production state touched; dist/search.js restored).

---

## Raw data references

- `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/G11_baseline_A8.json`
- `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/G11_trim_A8.json`
- Run log: `/tmp/g11-run.log` (also captured in PR description)
- Runner script: `/tmp/g11-runner.sh` (snapshot in commit history)

## Cleanup verification

VPS `dist/search.js` restored to canonical post-run:

```
$ diff -q /tmp/g11-search.js.original-1779330411 /root/.openclaw/workspace/tools/nox-mem/dist/search.js
$ grep -o "entity: [0-9.]*" /root/.openclaw/workspace/tools/nox-mem/dist/search.js | head -1
entity: 2.0
```

Prod `nox-mem-api` (pid 1778259, port 18802) was not interrupted; tmux `g11-api` session running on port 18803 was killed cleanly at the end of the runner. No memory/eval cross-contamination.
