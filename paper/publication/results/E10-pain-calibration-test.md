# Pain Calibration Test — E10 follow-up

> Generated: 2026-05-04 11:58 UTC | Runtime: 16s
> Script: `paper/publication/baselines/pain_calibration_test.py`

## Hypothesis

If 89% pain=default is the limiting factor, artificial spread should show
measurable Δ. Specifically:

- **H1**: Real pain (89% default) shows ~0 Δ vs ALL artificial spreads
  → CONFIRMED if calibration is the root cause of null effect
- **H2**: Bimodal (0.1/1.0 max contrast) > uniform → calibration spread matters
- **H3**: Log-scale (0.01–10.0) > uniform → dynamic range matters

## Setup

| Parameter | Value |
|---|---|
| Mode | FTS5 BM25 × pain ONLY (no Gemini, no RRF) |
| Scoring | composite = (−bm25_score) × pain |
| Real DB | `nox-mem-snapshot-20260504-0616.db` (read-only) |
| Temp DBs | 3 copies in /tmp/, deleted after run |
| Queries | `golden-queries.jsonl` (60 total) |
| Bootstrap | 10,000 resamples, seed=42 |
| Significance threshold | Δ ≥ 0.05 AND CI excludes 0 |
| Directional threshold | Δ ≥ 0.01 |

## Distributions tested

| Distribution | N chunks | Min | Max | Avg | Median | Top histogram buckets |
|---|---|---|---|---|---|---|
| real | 61,257 | 0.200 | 1.000 | 0.235 | 0.200 | 0.2×54794 | 0.3×861 | 0.5×4852 | 0.8×3 | 1.0×747 |
| uniform | 61,257 | 0.100 | 1.000 | 0.548 | 0.500 | 0.1×6043 | 0.2×6214 | 0.3×6203 | 0.4×6161 | 0.5×6237 | 0.6×6112 | 0.7×6057 | 0.8×6135 | ... |
| bimodal | 61,257 | 0.100 | 1.000 | 0.551 | 1.000 | 0.1×30530 | 1.0×30727 |
| logscale | 61,257 | 0.010 | 10.000 | 1.447 | 0.320 | 0.0×14349 | 0.1×9704 | 0.2×4439 | 0.3×2976 | 0.4×2260 | 0.5×1827 | 0.6×1510 | 0.7×1338 | ... |

## Pairwise comparisons

| Comparison | Mean Δ nDCG@10 | 95% CI lower | 95% CI upper | CI excl. 0 | Verdict |
|---|---|---|---|---|---|
| real vs uniform | +0.0148 | +0.0000 | +0.0399 | NO | **DIRECTIONAL** |
| real vs bimodal | +0.0087 | -0.0047 | +0.0307 | NO | **INSIGNIFICANT** |
| real vs logscale | +0.0095 | -0.0020 | +0.0307 | NO | **INSIGNIFICANT** |
| uniform vs bimodal | -0.0062 | -0.0185 | +0.0000 | NO | **INSIGNIFICANT** |
| uniform vs logscale | -0.0053 | -0.0159 | +0.0000 | NO | **INSIGNIFICANT** |

## Per-variant nDCG@10 (n=60)

| Distribution | Mean nDCG@10 | FTS recall rate |
|---|---|---|
| real | 0.0148 | 8.3% |
| uniform | 0.0000 | 8.3% |
| bimodal | 0.0062 | 8.3% |
| logscale | 0.0053 | 8.3% |

## Queries with FTS recall (the only ones where pain can matter)

| Q | Query | Category | real nDCG | uniform nDCG | bimodal nDCG | logscale nDCG |
|---|---|---|---|---|---|---|
| Q45 | como funciona monkey-patch do Issue 62028 do OpenC | entity | 0.000 | 0.000 | 0.000 | 0.000 |
| Q51 | o que é monkey-patch fratricide | concept | 0.000 | 0.000 | 0.000 | 0.000 |
| Q62 | quem é o Toto | entity | 0.613 | 0.000 | 0.000 | 0.000 |
| Q73 | o que é graph-memory plugin | entity | 0.277 | 0.000 | 0.370 | 0.317 |
| Q83 | como o KG é populado | procedure | 0.000 | 0.000 | 0.000 | 0.000 |

## Verdict

### H1 [REFUTED]

Some real-vs-artificial pairs show non-trivial Δ: ['real vs uniform']. Max |Δ|=0.0148. Real pain distribution is not equivalent to artificial spreads — calibration may matter in the FTS-retrievable query subset.

### H2 [REFUTED]

Bimodal does not outperform uniform: Δ=+0.0062. Maximum contrast calibration provides no measurable benefit over random uniform. Pain signal is fundamentally weak in FTS-only mode regardless of spread.

### H3 [REFUTED]

Log-scale does not outperform uniform: Δ=+0.0053. Wider dynamic range (0.01–10.0) provides no measurable benefit over uniform 0.1–1.0. Dynamic range is not the limiting factor.

## Implication for paper §6.3 future work

**Mixed results** (H1=REFUTED, H2=REFUTED, H3=REFUTED).

> §6.3 recommended framing: *'Pain calibration shows mixed evidence.
> Artificial spread experiments suggest the signal is sensitive to
> distribution shape but the effect is constrained by FTS recall limits.
> Future work should co-optimize recall (BM25 query expansion or
> denser indexing) with pain re-calibration.'*

---

**Safety:** Prod DB not modified. Real snapshot opened read-only.
3 temp DBs created in /tmp/ and deleted (try/finally).
**Runtime:** 16s
