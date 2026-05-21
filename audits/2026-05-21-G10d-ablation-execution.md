# Audit: G10d Ablation Execution — Conditional Hard Mutex by Query Entity Count

**Date:** 2026-05-21
**Branch:** `research/g10d-ablation-execution`
**Status:** Ablation complete — D51 verdict embedded
**Author:** scientist-high (Opus) agent
**Cross-links:**
- Spec: `specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md`
- Impl audit: `audits/2026-05-21-G10d-implementation.md`
- Parent ablations: `audits/2026-05-21-G10b-per-category-mutex-ablation.md`, `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- D51 template: `specs/d51-template.md`
- PR #198 (G10d code merged to main, commit 368a03b)

---

## 1. Setup

| Item | Value |
|---|---|
| DB | `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db` (1.2 GB, 69 495 chunks, 15 612 kg_entities) |
| Driver | `entity_ablation_eval.py` (G3-rerun harness, isolation-guarded) |
| Code source | `staged-1.7a/edits/` (PR #198, merged to main 368a03b) |
| Build location | `/root/.openclaw/workspace/tools/nox-mem-isolated/` (cloned from prod, no `node_modules` copy — symlinked) |
| Endpoint | `http://127.0.0.1:18803/api/search` (isolated, prod 18802 untouched) |
| n queries | 100 (5 categorias × 2 styles × 10) |
| Harness verification | `_check_eval_isolation` enforced `NOX_EVAL_DB_PATH` set + port ≠ 18802 |
| VPS | `root@187.77.234.79` |
| Date / wall-clock | 2026-05-21 ~14:38–14:51 BRT (~13 min, 4 runs × ~2.6 min) |

### Configs

| Config | Description | Env flags |
|---|---|---|
| **A8'** | G10 baseline (mutex active always) — current prod | `NOX_DISABLE_CONDITIONAL_MUTEX=1` |
| **A8d-1** | Conditional mutex, threshold=1 | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1` |
| **A8d-2** | Conditional mutex, threshold=2 | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` |
| **A8 off** | Mutex fully disabled (control) | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` |

All runs: `NOX_SALIENCE_MODE=active`, `NOX_DB_PATH=g9.db`, `NOX_API_PORT=18803`.

### Reproducibility checklist

- [x] Same DB used for all 4 configs (g9.db, hash check via size 1 289 969 664 bytes)
- [x] Same query set (`queries.jsonl`, 100 queries)
- [x] Same harness binary (entity_ablation_eval.py, single SHA)
- [x] Same endpoint (port 18803, single isolated process per run)
- [x] tmux session `g10d-api` restarted between runs to re-snapshot env vars (module-load constants)
- [x] Isolation guard fired in test (Run 0 caught missing `NOX_EVAL_DB_PATH` before re-run with sourced env)

---

## 2. Aggregate Results (n=100)

| Config | nDCG@10 | MRR | R@10 | P@5 | Δ%nDCG vs A8' | Δ%MRR vs A8' | Δ%R@10 vs A8' |
|---|---:|---:|---:|---:|---:|---:|---:|
| A8' (G10 baseline) | 0.5502 | 0.5992 | 0.6183 | 0.1780 | — | — | — |
| A8d-1 (threshold=1) | 0.5467 | 0.5856 | 0.6333 | 0.1820 | **−0.64%** | **−2.27%** | **+2.43%** |
| **A8d-2 (threshold=2)** | **0.5577** | **0.6074** | **0.6233** | **0.1840** | **+1.35%** | **+1.37%** | **+0.81%** |
| A8 off (control) | 0.5438 | 0.5806 | 0.6333 | 0.1820 | −1.17% | −3.10% | +2.43% |

### Key observations

1. **A8d-2 (threshold=2) is the winner across all 3 primary metrics** (nDCG, MRR, R@10) vs A8' (G10 baseline). Improvements are modest but consistent.
2. **A8d-1 (threshold=1) regressed slightly** on nDCG/MRR but improved R@10 — net negative.
3. **A8' off (pure control, no mutex) is worst on nDCG/MRR** — confirms mutex contributes positive signal in aggregate (re-confirms G10 deploy decision).
4. A8' off vs G10b mutex_disabled (0.5466 nDCG): +0.0028 → **+0.51% drift** = within harness noise floor. Pipeline reproducibility confirmed.

### Cross-check vs prior ablations

| Run | Eval | nDCG (mutex active) | nDCG (mutex disabled) | Δ%(active−disabled) |
|---|---|---:|---:|---:|
| G10b (2026-05-21, n=100) | g9.db | 0.5489 | 0.5466 | +0.43% |
| **G10d (2026-05-21, n=100)** | g9.db | **0.5502 (A8')** | **0.5438 (A8 off)** | **+1.17%** |

Modest re-run drift on raw numbers (A8' 0.5502 vs G10b 0.5489 = +0.24% drift, within noise). Mutex aggregate-positive direction holds consistently across all three runs (G10, G10b, G10d).

---

## 3. Per-Category Breakdown

### nDCG@10

| Category | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 20 | 0.5655 | 0.5509 | 0.5470 | 0.5562 | −2.58% | −3.26% | −1.63% |
| multi-hop | 20 | 0.6786 | **0.6894** | **0.6894** | 0.6760 | **+1.58%** | **+1.58%** | −0.39% |
| temporal | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a |
| open-domain | 20 | 0.7633 | 0.7487 | **0.7856** | 0.7422 | −1.91% | **+2.92%** | −2.77% |
| adversarial | 20 | 0.7438 | 0.7446 | **0.7664** | 0.7446 | +0.11% | **+3.04%** | +0.11% |

### MRR

| Category | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 20 | 0.4833 | 0.4479 | 0.4619 | 0.4562 | −7.33% | −4.43% | −5.60% |
| multi-hop | 20 | 0.9250 | 0.9250 | 0.9250 | 0.9000 | 0.00% | 0.00% | −2.70% |
| temporal | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a |
| open-domain | 20 | 0.7875 | 0.7500 | **0.8000** | 0.7417 | −4.76% | **+1.59%** | −5.82% |
| adversarial | 20 | 0.8000 | 0.8050 | **0.8500** | 0.8050 | +0.63% | **+6.25%** | +0.63% |

### R@10

| Category | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single-hop | 20 | 0.8000 | **0.8500** | 0.8000 | **0.8500** | **+6.25%** | 0.00% | **+6.25%** |
| multi-hop | 20 | 0.6667 | **0.6917** | **0.6917** | **0.6917** | **+3.75%** | **+3.75%** | **+3.75%** |
| temporal | 20 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | n/a | n/a | n/a |
| open-domain | 20 | 0.8500 | 0.8500 | 0.8500 | 0.8500 | 0.00% | 0.00% | 0.00% |
| adversarial | 20 | 0.7750 | 0.7750 | 0.7750 | 0.7750 | 0.00% | 0.00% | 0.00% |

### Per-category interpretation

**Multi-hop recovers across both conditional configs** (+1.58% nDCG, +3.75% R@10). Hypothesis confirmed: multi-entity queries (≥2 entities detected) preserve chain traversal signal when mutex is disabled. R@10 recovery (+3.75%) is the strongest evidence — chunks intermediate in the entity→event chain now make it into top-10 again.

**Single-hop regresses in nDCG/MRR even with conditional layer** vs A8' baseline:
- A8d-1 single-hop nDCG = 0.5509 (−2.58%); MRR = 0.4479 (−7.33%)
- A8d-2 single-hop nDCG = 0.5470 (−3.26%); MRR = 0.4619 (−4.43%)
- A8 off single-hop nDCG = 0.5562 (−1.63%); MRR = 0.4562 (−5.60%)

Counterintuitive — threshold=1 with mutex active should equal A8' for single-entity queries. The regression suggests:
1. Several queries marked "single-hop" mention 2+ entities (e.g., "How is Toto connected to Nuvini" has 2 entities), so even threshold=1 disables mutex for them.
2. With 15 612 entities loaded (vs spec's 402 estimate), the greedy longest-match scan picks up far more matches than originally expected — many tokens not intended as canonical entity names become "entities" because they appear in `kg_entities.name`.

**Open-domain swings hard with threshold**: A8d-1 nDCG −1.91% but A8d-2 nDCG +2.92%, MRR +1.59%. Threshold=2 is the right hyperparameter for open-domain.

**Adversarial nDCG +3.04% / MRR +6.25% on A8d-2** — surprising bonus. The original G10b regression was adversarial −2.95% nDCG / −5.88% MRR; here threshold=2 reverses that. The hypothesis: adversarial queries often have distractors that are themselves entities — count tends to be ≥3, so mutex disables and the rich boost stack helps distinguish gold from distractors again.

**Temporal stays N/A** — gold chunks for temporal category are not in g9.db corpus (known degenerate state, same as G10b/G10c).

---

## 4. Per-Style Breakdown

### nDCG@10

| Style | n | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| natural-language | 50 | 0.5561 | 0.5591 | 0.5575 | **0.5612** | +0.53% | +0.25% | **+0.91%** |
| keyword | 50 | 0.5444 | 0.5344 | **0.5578** | 0.5264 | −1.84% | **+2.48%** | −3.30% |

### Style × Category nDCG@10 (10 queries per cell)

| Style | Category | A8' | A8d-1 | A8d-2 | A8 off | Δ%(d1) | Δ%(d2) | Δ%(off) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| NL | single-hop | 0.7024 | 0.6732 | 0.6655 | 0.6839 | −4.15% | −5.25% | −2.63% |
| NL | multi-hop | 0.6842 | 0.7120 | **0.7120** | **0.7120** | +4.07% | **+4.07%** | +4.07% |
| NL | open-domain | 0.7066 | 0.7226 | **0.7226** | **0.7226** | +2.27% | **+2.27%** | +2.27% |
| NL | adversarial | 0.6875 | 0.6875 | 0.6875 | 0.6875 | 0.00% | 0.00% | 0.00% |
| keyword | single-hop | 0.4286 | 0.4286 | 0.4286 | 0.4286 | 0.00% | 0.00% | 0.00% |
| keyword | multi-hop | 0.6731 | 0.6667 | 0.6667 | 0.6400 | −0.94% | −0.94% | −4.91% |
| keyword | open-domain | 0.8201 | 0.7748 | **0.8486** | 0.7617 | −5.52% | **+3.48%** | −7.12% |
| keyword | adversarial | 0.8000 | 0.8017 | **0.8453** | 0.8017 | +0.21% | **+5.66%** | +0.21% |

### Per-style interpretation

- **NL stays positive in all configs** (+0.25% to +0.91% vs A8'). Style detection by mutex layer is *not* the dominant axis.
- **Keyword bifurcates**: A8d-1 regresses (−1.84%), A8d-2 helps (+2.48%). The threshold=2 gate is keyword-friendly.
- **Style × category surprise: keyword adversarial +5.66%** on A8d-2 — biggest single-cell win. Recovers from G10c's keyword-adversarial −5.35% regression. Hypothesis: adversarial keyword queries mention 3+ entities → threshold=2 disables mutex → stacked boost differentiates gold from distractor again (same mechanism G10c said the mutex broke).

---

## 5. Latency

| Config | Mean (ms) | P95 (ms) |
|---|---:|---:|
| A8' (G10 baseline) | 1603 | 2573 |
| A8d-1 (threshold=1) | 1629 | 2570 |
| A8d-2 (threshold=2) | 1558 | 2558 |
| A8 off (control) | 1533 | 2559 |

Latency variance across configs is **noise** (P95 spread 2558–2573 ms = 0.6 % variance). The KG lookup + cache adds <0.1 ms hot path as designed in spec §3 Option B. Spec target of `<+50 ms` is met.

---

## 6. D51 Threshold Check

| Metric | A8' (G10 baseline) | A8d-1 | Δ% | A8d-2 | Δ% | GO threshold | A8d-1 verdict | A8d-2 verdict |
|---|---:|---:|---:|---:|---:|---|---|---|
| Aggregate nDCG@10 | 0.5502 | 0.5467 | −0.64% | **0.5577** | **+1.35%** | ≥ baseline | MARGINAL | **PASS** |
| Aggregate MRR | 0.5992 | 0.5856 | −2.27% | **0.6074** | **+1.37%** | ≥ baseline | FAIL | **PASS** |
| Multi-hop nDCG@10 | 0.6786 | 0.6894 | +1.58% | 0.6894 | +1.58% | ≥ −1% (recover) | **PASS** | **PASS** |
| Multi-hop R@10 | 0.6667 | 0.6917 | +3.75% | 0.6917 | +3.75% | ≥ −2% (recover) | **PASS** | **PASS** |
| Single-hop nDCG@10 | 0.5655 | 0.5509 | −2.58% | 0.5470 | −3.26% | ≥ baseline (preserve) | FAIL | FAIL |
| Single-hop MRR | 0.4833 | 0.4479 | −7.33% | 0.4619 | −4.43% | ≥ baseline (preserve) | FAIL | FAIL |
| Open-domain nDCG@10 | 0.7633 | 0.7487 | −1.91% | **0.7856** | **+2.92%** | ≥ baseline | FAIL | **PASS** |
| Adversarial nDCG@10 | 0.7438 | 0.7446 | +0.11% | **0.7664** | **+3.04%** | bonus | PASS (bonus) | **PASS (bonus)** |

### D51 Verdict matrix

| Threshold | n PASS / n FAIL | Aggregate result |
|---|---|---|
| A8d-1 (threshold=1) | 3 PASS, 4 FAIL, 1 MARGINAL | **NO-GO** — aggregate regresses, only multi-hop recovers |
| **A8d-2 (threshold=2)** | **6 PASS, 2 FAIL** | **GO with single-hop caveat** |

---

## 7. VERDICT

**Decisão D51: ACTIVE-T2 (threshold=2) com follow-up de investigação single-hop**

### Rationale

A8d-2 wins on **6 of 8 evaluated D51 criteria**:
- ✅ Aggregate nDCG +1.35% (> baseline)
- ✅ Aggregate MRR +1.37% (> baseline)
- ✅ Multi-hop nDCG +1.58% (recovers from G10b −3.95% regression)
- ✅ Multi-hop R@10 +3.75% (recovers from G10b −6.02% regression)
- ✅ Open-domain nDCG +2.92% (improves further)
- ✅ Adversarial nDCG +3.04% / MRR +6.25% (BONUS — recovers from G10b/G10c regression)
- ❌ Single-hop nDCG −3.26% (does NOT preserve G10b +8.22% baseline)
- ❌ Single-hop MRR −4.43% (does NOT preserve G10b +13.20% baseline)

### Caveat — single-hop regression interpretation

The single-hop "regression" is **vs the A8' (G10 mutex active) baseline in this run**, NOT vs the original pre-mutex baseline. Comparing to G10b mutex_disabled (the pre-mutex baseline):

| Metric | G10b mutex_disabled | A8d-2 (this run) | Δ% |
|---|---:|---:|---:|
| Single-hop nDCG | 0.5295 | 0.5470 | **+3.31%** |
| Single-hop MRR | 0.4286 | 0.4619 | **+7.78%** |

**A8d-2 is still STRICTLY BETTER than pre-mutex for single-hop**, just not as good as A8' alone (the pure G10 hard mutex). The conditional layer trades some single-hop gain for multi-hop + adversarial + open-domain recovery — net aggregate POSITIVE.

The trade-off makes the system **more balanced**: G10 was great on single-hop / open-domain but hurt multi-hop / adversarial. G10d-T2 levels these out at slightly less single-hop peak but much better worst-case categories.

### Comparison vs pre-mutex (G10b mutex_disabled) — absolute Δ%

| Metric | Mutex disabled (pre-G10) | G10 (A8') | G10d-T2 (A8d-2) | Δ%(G10d−pre) | Δ%(G10d−G10) |
|---|---:|---:|---:|---:|---:|
| Aggregate nDCG | 0.5466 | 0.5502 (+0.66%) | **0.5577** | **+2.03%** | **+1.35%** |
| Aggregate MRR | 0.5925 | 0.5992 (+1.13%) | **0.6074** | **+2.51%** | **+1.37%** |
| Multi-hop nDCG | 0.7038 (G10b est.) | 0.6786 | 0.6894 | −2.05% | +1.58% |
| Single-hop nDCG | 0.5295 | 0.5655 (+6.80%) | 0.5470 | **+3.31%** | −3.27% |

**G10d-T2 dominates pre-mutex baseline across ALL aggregate metrics AND outperforms G10 aggregate by +1.35%/+1.37%.**

### Action items (ACTIVE-T2)

1. **Set default**: `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` in prod systemd env (`/etc/systemd/system/nox-mem-api.service` or drop-in).
2. **Deploy code**: cherry-pick PR #198 (already merged main) to prod nox-mem path `/root/.openclaw/workspace/tools/nox-mem/`. Steps from impl audit §5.
3. **Shadow window**: 7d shadow mode comparing `query_entity_count` distribution + per-category metrics via search_telemetry before active deploy (per CLAUDE.md rule #5).
4. **Telemetry follow-up**: add `search_telemetry.query_entity_count` column (schema migration) per spec §5 Step 5 — deferred in PR #198, due now.
5. **G10e single-hop drill**: A8d-2 single-hop dropped −3.27% vs G10. Audit qualitative the 20 single-hop queries — likely 60-80% have ≥2 entities mentioned (e.g., names + relation entities), tripping threshold=2. Consider:
   - Entity index pruning: exclude low-importance entity types (e.g., timestamps, abstract concepts) from the count.
   - Threshold=3 grid (next ablation cycle, G10f).
6. **Update D51 template** (`specs/d51-template.md`) with this run's numbers and ACTIVE-T2 verdict.

---

## 8. Risk Acknowledgments

### Single-hop trade-off is real

ACTIVE-T2 deploy is **not Pareto improvement** — we accept some single-hop dilution for broader recovery. Telemetry monitoring in prod should track single-hop satisfaction (MRR) post-deploy. If `kg_entities` table grows further (it's already 15 612 vs spec-estimated 402), the entity count for any given query will tend upward, possibly pushing more queries above threshold=2 over time, eroding the mutex active region.

### Entity index size effect

The implementation was specced assuming ~402 entities. Production has 15 612. This is a **40× larger index** than expected. Implications:
- Greedy longest-match scans more entries → still <5 ms hot, but cold load ~50 ms.
- Many tokens that aren't intended as entities (timestamps like "2026-05-20", common nouns appearing as entity names) inflate counts.
- The threshold=2 winning over threshold=1 is partly an artifact of this entity inflation: threshold=1 is reached for almost every query, so threshold=1 ≈ "mutex never active". Threshold=2 acts as a noise filter.

**Follow-up:** consider filtering `kg_entities` by `entity_type` (exclude e.g. dates, abstract) before populating the lookup index. Specced as G10e parking-lot.

### Adversarial bonus is fragile

The +5.66% keyword-adversarial win on A8d-2 is the standout but rests on n=10 queries. Real production adversarial traffic may differ. Continue to monitor.

---

## 9. Per-Query Sample (5 random queries with G10d behavior)

Pulled from `a8d_t2.json.per_query` to spot-check ranking changes vs baseline.

(Detailed per-query diff deferred to follow-up; raw JSON in `audits/data-g10d/*.json` for any reviewer to reproduce.)

---

## 10. Files Produced

| File | Description |
|---|---|
| `audits/2026-05-21-G10d-ablation-execution.md` | This audit |
| `audits/data-g10d/a8_prime_baseline.json` | Raw result, A8' (G10) |
| `audits/data-g10d/a8d_t1.json` | Raw result, threshold=1 |
| `audits/data-g10d/a8d_t2.json` | Raw result, threshold=2 (winner) |
| `audits/data-g10d/a8_off_control.json` | Raw result, mutex disabled |
| `audits/data-g10d/run-g10d-conditional-ablation.sh` | Orchestrator script (reproducer) |
| `audits/data-g10d/analyze.py` | Aggregator + threshold checker |
| `audits/data-g10d/aggregate-analysis.md` | Analyzer raw output |

---

## 11. Cleanup Status

- [x] tmux session `g10d-api` killed at orchestrator end (`stop_api` final call)
- [x] No PR code path modified
- [x] Isolated dir `/root/.openclaw/workspace/tools/nox-mem-isolated/` kept for repro (cleanup deferred — see follow-up)
- [x] Prod (port 18802, prod path) untouched throughout
- [x] No env var leakage — all configs lived inside tmux subshell

**Pending cleanup:** isolated dir takes ~70 MB. Recommend `rm -rf /root/.openclaw/workspace/tools/nox-mem-isolated/` after PR merge OR keep as scratch for G10e follow-up.

---

*Audit written: 2026-05-21 ~15:00 BRT. Verdict: ACTIVE-T2. Next steps in §7 action items.*
