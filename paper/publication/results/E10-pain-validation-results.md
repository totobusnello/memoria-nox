# Pain Dimension Validation — E10

> Generated: 2026-05-04 09:47 UTC | Runtime: 111s
> Script: `paper/publication/baselines/pain_dimension_validator.py`

## Setup

| Parameter | Value |
|---|---|
| Comparison | pain-aware (real values) vs pain=1.0 uniform |
| Metric | nDCG@10 (binary relevance) |
| N queries | 6 post-incident |
| Bootstrap | 6 samples × 10,000 resamples, seed=42 |
| Threshold | Δ ≥ 0.05 to confirm hypothesis |

## Per-Query Results

| Query ID | Query (truncated) | Category | Pain_real (mean) | pain-aware nDCG | pain=1.0 nDCG | Δ nDCG |
|---|---|---|---|---|---|---|
| Q47 | o que faz withOpAudit e quando usar | entity | 0.50 | 0.000 | 0.000 | +0.000 |
| Q52 | como rodar nox-mem reindex com segurança | procedure | 0.20 | 0.000 | 0.000 | +0.000 |
| Q67 | qual a regra sobre rsync delete | decision | 0.20 | 0.000 | 0.000 | +0.000 |
| Q71 | qual a primeira lição do incident reindex 2026-04- | temporal | 0.20 | 0.000 | 0.000 | +0.000 |
| Q85 | como Lex e Cipher se complementam em incidents | cross-agent | 0.50 | 0.000 | 0.000 | +0.000 |
| Q89 | como rotacionar a key Slack sem downtime | security | 0.20 | 0.000 | 0.000 | +0.000 |
| **Mean** | | | | **0.000** | **0.000** | **+0.000** |

## Aggregate Statistics

| Metric | Value |
|---|---|
| Mean Δ nDCG@10 (pain-aware − uniform) | +0.0000 |
| Queries improved (Δ > 0) | 0 / 6 |
| Queries degraded (Δ < 0) | 0 / 6 |
| Queries unchanged (Δ = 0) | 6 / 6 |
| Baseline mean nDCG@10 | 0.0000 |
| Ablated mean nDCG@10 | 0.0000 |

## Bootstrap Significance

Bootstrap 95% CI: [+0.000, +0.000]

- **Excludes zero:** NO
- **Mean Δ:** +0.0000
- **N samples:** 6 queries × 10,000 resamples
- **Seed:** 42 (reproducible)

## Verdict

**NOT_SUPPORTED**

Δ=+0.000 ≤ 0. Pain dimension does not improve retrieval on this query set. Paper must revise or remove this claim.

---

## Interpretation

The pain dimension in `salience = recency × pain × importance` improved retrieval on post-incident queries by Δ nDCG@10 = +0.0000.

The 95% bootstrap CI includes zero. N is small — this is directional evidence only. The paper should state this explicitly.

**Safety note:** This experiment ran on a TEMP DB copy. Prod DB was not modified.

**Audit log:** `pain_test_audit.log` (same directory as this report)
