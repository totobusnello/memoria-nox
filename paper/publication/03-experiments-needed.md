# Experiments Needed — Pré-arXiv submission plan

> **Goal:** cobrir 5 gaps identificados em positioning. Cada experimento tem owner, effort, success criteria.

---

## Experiment Matrix

| # | Experiment | Effort | Priority | Closes Gap |
|---|---|---|---|---|
| E1 | BM25 (Pyserini) baseline | 4h | P0 | Gap #3 — strong baseline |
| E2 | BGE-M3 dense baseline | 4h | P0 | Gap #3 + Gap #5 (alt provider) |
| E3 | E5-mistral-7b baseline | 4h | P0 | Gap #3 |
| E4 | BEIR TREC-COVID corpus | 3h impl + 1h run | P0 | Gap #1 — second corpus |
| E5 | Stack Exchange 10K subset | 4h impl + 1h run | P0 | Gap #1 — third corpus |
| E6 | Ablation: FTS-only | 1h | P0 | Gap #4 |
| E7 | Ablation: FTS+semantic sem RRF (concat scores) | 2h | P0 | Gap #4 |
| E8 | Ablation: hybrid sem salience boost | 1h | P0 | Gap #4 |
| E9 | Ablation: hybrid sem section_boost | 1h | P0 | Gap #4 |
| E10 | Pain dimension validation (com vs sem pain) | 3h | P0 | Diferencial #1 empirical |
| E11 | External curator 10 queries (BEIR or human) | 3h | P1 | Gap #2 |
| E12 | Cross-agent intelligence quantification | 2h | P1 | Diferencial #3 |
| E13 | Shadow case study formal write-up | 2h | P1 | Diferencial #2 narrative |

**Total:** ~36h spread em 2-3 sprints semanais.

---

## Implementation outlines

### E1 — BM25 (Pyserini)
```python
# /paper/publication/baselines/bm25_baseline.py
from pyserini.search.lucene import LuceneSearcher
import json, sqlite3

def build_index(chunks_db: str, index_dir: str):
    """Export chunks → JSONL → Pyserini index"""
    conn = sqlite3.connect(chunks_db)
    rows = conn.execute("SELECT id, chunk_text FROM chunks").fetchall()
    # write JSONL: {"id": str, "contents": str}
    # subprocess: python -m pyserini.index.lucene --collection JsonCollection ...

def search(searcher, query: str, k: int = 10):
    hits = searcher.search(query, k=k)
    return [(int(h.docid), h.score) for h in hits]

# Run against same 50 golden queries, compute nDCG/MRR/Recall, compare
```

### E2 — BGE-M3
```python
# /paper/publication/baselines/bge_baseline.py
from FlagEmbedding import BGEM3FlagModel
import sqlite3, numpy as np

model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)
# Embed 64K chunks once → np.savez chunks_bge.npz
# Per-query: embed → cosine → top-k → nDCG/MRR
```

### E3 — E5-mistral
```python
# Similar a E2 mas com intfloat/e5-mistral-7b-instruct
# Requires GPU or Modal/Replicate API; estimar $5-10 trial
```

### E4 — BEIR TREC-COVID
- Download `beir` package: `pip install beir`
- Load TREC-COVID (corpus 171K, 50 queries)
- Run nox-mem com TEMP DB ingestando o corpus
- 3-batch each variant
- Cross-corpus result table

### E5 — Stack Exchange 10K
- Download Stack Exchange dump (techexchange/scifi/cooking — diverse topics)
- Sample 10K posts → chunks → ingest TEMP DB
- Curate 50 queries (mix factoid + how-to + opinion)
- 3-batch each variant

### E6-E9 — Ablations
- Simply set env vars: `NOX_HYBRID_DISABLE=1`, `NOX_RRF_DISABLE=1`, `NOX_SALIENCE_MODE=off`, `NOX_SECTION_BOOST_MODE=off`
- Run eval batch
- Tabela ablação: cada row = 1 component disabled

### E10 — Pain dimension validation
- Identificar 10-15 golden queries categorizadas como "post-incident questions" (Q47 withOpAudit, Q67 rsync delete, Q71 reindex incident lesson, etc — já no R01b)
- Variant A: salience com pain (current default)
- Variant B: salience com pain=1.0 uniform (counterfactual)
- Compare nDCG@10 nas 10-15 queries específicas
- Hypothesis: Δ nDCG ≥ 0.05 favorecendo pain-aware

### E11 — External curator 10 queries
- BEIR queries de outro corpus servem (different curator)
- OR: pedir Toto pra recrutar 1 amigo dev → 10 queries pra nox-mem corpus
- Run hybrid + compare vs internal-curator subset

### E12 — Cross-agent quantification
- SQL query no chunks DB:
  ```sql
  SELECT
    requesting_agent,
    source_file_agent,
    COUNT(*) as cross_hits
  FROM search_telemetry st
  JOIN chunks c ON c.id IN (json_each(st.top_chunk_ids))
  WHERE substring(c.source_file, 8, 5) != requesting_agent  -- different agent prefix
  GROUP BY requesting_agent, source_file_agent;
  ```
- Tabela: %% hits cross-agent vs same-agent

### E13 — Shadow case study formal
- Document Fase 1.7b-b salience activation:
  - 7d telemetry data: 191 promote / 16608 review / 45743 archive
  - Distribution analysis screenshot
  - Decision rationale
  - Counterfactual: incident 2026-04-25 (reindex sem dry-run → 183 entities damaged)
- 2-page case study appendix

---

## Required environment

```bash
# Python deps (separate venv from nox-mem)
pip install pyserini==0.36.0 FlagEmbedding==1.2.10 beir==2.0.0 datasets

# E5-mistral GPU OR API:
# OPÇÃO A: Modal Labs $5/mo trial → 1 GPU run
# OPÇÃO B: Replicate.com pay-per-use ~$0.01/run

# Hardware: BGE-M3 + BM25 rodam em CPU mac mini 16GB
# E5-mistral-7b precisa ≥16GB GPU OR API
```

---

## Success criteria (gates pra avançar pra writing)

| Sprint | Gate |
|---|---|
| W2 sprint completo | E1+E2 done, table inicial mostra hybrid nDCG ≥ BGE-M3 -10% |
| W3 sprint | E3+E4+E5 done, 3-corpora table consistente direção |
| W3 ablations | E6-E9 done, mostra cada layer contribui ≥0.03 nDCG |
| W3 diferenciais | E10 mostra Δ ≥ 0.05 favorecendo pain; E12 mostra ≥10% cross-agent hits |
| Otherwise | PIVOT — paper claim precisa reframe |

---

## Output artifacts

- `/paper/publication/results/` (gitignored se grandes)
  - `baselines-bm25.jsonl`
  - `baselines-bge.jsonl`
  - `baselines-e5.jsonl`
  - `corpus-beir-results.jsonl`
  - `corpus-stackexchange-results.jsonl`
  - `ablation-summary.csv`
- `/paper/publication/04-paper-arxiv-draft.md` — fed by these results in §5 Experiments
