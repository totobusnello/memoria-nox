# E2 multilingual-e5-base baseline — final results

**Run date:** 2026-05-04 13:05 BRT
**Model:** `intfloat/multilingual-e5-base` (278M params, 768d, multilingual PT+EN)
**Pipeline:** sentence-transformers >=5.0 with mandatory `passage:`/`query:` prefixes
**Corpus:** 61.257 chunks embedded (.npz cache 162MB)
**Queries:** 60 golden (50 main + 10 held-out)
**Hardware:** VPS Hostinger 8-core CPU
**Total runtime:** ~6h embed + 1s eval (cache hit)

## Aggregate metrics (n=60)

| Metric | Value |
|---|---|
| nDCG@10 | **0.3070** |
| MRR | 0.3720 |
| Recall@10 | 0.3708 |
| Precision@5 | 0.1067 |

## Comparison with other baselines (paper §5.2 Table 5)

| Sistema | nDCG@10 | MRR | Recall@10 | Δ vs nox-mem hybrid |
|---|---|---|---|---|
| FTS5 vanilla (BM25) | 0.0123 | 0.0200 | 0.0100 | −0.5090 |
| BM25 Pyserini (Anserini-tuned) | 0.1475 | 0.1549 | 0.2083 | −0.3738 |
| **multilingual-e5-base (768d)** | **0.3070** | **0.3720** | **0.3708** | **−0.2143** |
| **nox-mem hybrid (FTS+Gemini+RRF, 3-run)** | **0.5213 ± 0.0004** | 0.4889 ± 0.0028 | 0.6800 ± 0.0047 | baseline |

**nox-mem hybrid achieves +0.2143 nDCG@10 over the strongest open-source dense baseline (multilingual-e5-base) — a 1.7× relative improvement.**

## Per-category breakdown

| Category | E5 | nox-mem hybrid | BM25 Pyserini | Winner |
|---|---|---|---|---|
| concept (n=15) | 0.4062 | 0.656 | 0.2393 | hybrid +0.250 |
| **cross-agent (n=4)** | **0.3816** | **0.369** | 0.0511 | **E5 +0.013** ⭐ |
| decision (n=6) | 0.4212 | 0.542 | 0.2062 | hybrid +0.121 |
| entity (n=11) | 0.2716 | 0.459 | 0.1357 | hybrid +0.187 |
| procedure (n=13) | 0.1722 | 0.619 | 0.1053 | hybrid +0.447 |
| security (n=6) | 0.3410 | 0.594 | 0.1597 | hybrid +0.253 |
| **temporal (n=4)** | **0.2500** | **0.233** | 0.0000 | **E5 +0.017** ⭐ |
| negative (n=1) | 0.0000 | 0 | 0 | tie |

## Key findings

### Where hybrid dominates
- **procedure** (Δ +0.447): domain-specific commands/sequences (e.g. "como rodar nox-mem reindex") benefit from FTS lexical match boost
- **security** (Δ +0.253), **entity** (Δ +0.187): proper nouns and identifiers indexed precisely by FTS
- **concept** (Δ +0.250), **decision** (Δ +0.121): hybrid layering adds value when both lexical and semantic signals are present

### Where E5 wins (HONEST DISCLOSURE)
- **cross-agent** (E5 +0.013): semantic similarity surfaces cross-agent context better than FTS-boosted hybrid
- **temporal** (E5 +0.017): date/time semantic understanding outperforms keyword matching

These are narrow wins (Δ ≤ 0.02, n=4 each) but methodologically honest: the paper should NOT claim hybrid is universally superior. The aggregate +0.2143 lift is driven by the 5 categories where domain identifiers matter.

## Implication for paper §5.2

Update Table 5 with E5 row populated. Add per-category discussion noting:
1. Hybrid 1.7× over strongest dense baseline (E5)
2. Two categories where dense alone wins (cross-agent, temporal) — small n, narrow margins
3. Hybrid advantage strongest where domain identifiers/keywords matter (procedure +0.447)

## Honest cost disclosure

- E5 embed time: ~6h on 8-core CPU (4.0 chunks/s avg, batch_size=32, max_length=1024)
- E5 eval time: <1s after cache (60 queries × dot product against 61K vectors)
- E5 corpus cache size: 162 MB
- Reproducibility: `pain_experiments/e5_multilingual_baseline.py full --db <snapshot> --queries golden-queries.jsonl`

## Comparison summary for paper §5.2 prose

> "On 60 internally-curated golden queries, NOX-Supermem hybrid (FTS5 + Gemini 3072d + RRF, k=60) achieves nDCG@10 = 0.5213 ± 0.0004, outperforming the strongest external baselines: BM25 Pyserini (0.1475, +3.5×) and multilingual-e5-base (0.3070, +1.7×). Per-category analysis (Table 6) shows hybrid dominance in five categories where domain identifiers matter (procedure, security, entity, concept, decision); two categories (cross-agent, temporal, n=4 each) show small advantages for dense-only retrieval (Δ ≤ 0.02), suggesting hybrid is operationally superior on this corpus rather than universally optimal."
