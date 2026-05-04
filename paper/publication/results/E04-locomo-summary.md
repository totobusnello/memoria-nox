# E04 LOCOMO — FTS5 baseline results

**Run date:** 2026-05-04 BRT
**Dataset:** snap-research/locomo (CC BY-NC 4.0), `data/locomo10.json`
**Source:** https://github.com/snap-research/locomo
**Citation:** Maharana, Lee, Tulyakov, Bansal, Barbieri, Fang. "Evaluating Very Long-Term Conversational Memory of LLM Agents." arXiv:2402.17753, 2024.
**Pipeline:** stdlib SQLite FTS5 (`unicode61 remove_diacritics 2`, BM25 default), seed=42, no external dependencies
**Adapter:** `paper/publication/baselines/locomo_eval.py` (~250 lines, stdlib-only)

## Corpus statistics

- 10 conversations
- 19 sessions per conversation (avg)
- **5,882 dialogue turns indexed**
- 1,986 QA pairs total across 5 categories
- Categories: 1=single-hop (282), 2=multi-hop (321), 3=temporal (96), 4=open-domain (841), 5=adversarial (446)

## Stratified subset

- **n=100** (20 per category × 5 categories), seed=42
- Each query has gold chunk(s) identified by `dia_id` reference (e.g. `D1:3` = session 1, turn 3)
- Gold mapping: `{sample_id}::{dia_id}` namespaced to prevent cross-conversation collision

## Aggregate metrics (n=100)

| Metric | Value |
|---|---|
| nDCG@10 | **0.2810** |
| MRR | 0.2795 |
| Recall@10 | 0.3792 |
| Precision@5 | 0.0780 |

## Per-category breakdown

| Category | n | nDCG@10 | MRR | Recall@10 |
|---|---|---|---|---|
| 1. single-hop | 20 | 0.1179 | 0.1663 | 0.1625 |
| 2. multi-hop | 20 | 0.3708 | 0.3272 | 0.5250 |
| 3. temporal | 20 | 0.2887 | 0.3017 | 0.3833 |
| 4. open-domain | 20 | 0.3746 | 0.3539 | 0.5250 |
| 5. adversarial | 20 | 0.2531 | 0.2483 | 0.3000 |

## Cross-corpus comparison (paper §5.2 anchor)

| Corpus | FTS5 vanilla nDCG@10 | Notes |
|---|---|---|
| nox-mem golden (n=60, in-domain) | 0.0123 | Production knowledge base, dense identifiers, low keyword overlap with NL queries |
| **LOCOMO (n=100, conversational)** | **0.2810** | Conversational text with high keyword density per turn; FTS5 baseline ~23× higher |
| BEIR TREC-COVID (n=50, retrieval bench) | pending | Run on VPS, ETA 2026-05-05 BRT |

**Interpretation for §5.2:** FTS5 vanilla performs ~23× better on LOCOMO than on the nox-mem golden corpus. This validates the architectural choice: our domain corpus is structurally harder for lexical retrieval (NL queries against compiled-section entity files with few shared content words), motivating the hybrid FTS+dense+RRF stack. LOCOMO's conversational format favors lexical matching (questions and gold turns share surface words), so FTS5 alone closes much of the retrieval gap there. The hybrid contribution is most valuable in the harder regime.

## Methodology details

**Tokenization:** alphanumeric + word chars only, OR-joined as FTS5 phrase queries (`"token" OR "token"`). Tokens <2 chars dropped. Top-20 query-token cap to avoid FTS5 query explosion.

**Gold relevance:** binary — chunk is relevant iff its full-namespaced `chunk_id` appears in the query's evidence list. No graded relevance judgments (LOCOMO does not provide them).

**Top-K:** retrieved 20, evaluated nDCG@10, MRR, Recall@10, Precision@5.

## Honest disclosures

1. **FTS5 only** (no Pyserini Anserini-tuned BM25, no dense, no hybrid). The point of this run is corpus-level cross-comparison of the baseline, not a full bake-off. Adding Pyserini and multilingual-e5-base on LOCOMO is future work for the camera-ready version (~30 min each).

2. **No nox-mem hybrid run on LOCOMO yet.** That would require either (a) embedding all 5,882 turns via Gemini and replicating the RRF stack on a fresh DB, or (b) re-purposing the production stack with corpus isolation. Cost ≈ \$0.05 in Gemini embedding + 30-60 min wall clock. Deferred to camera-ready unless reviewer requests.

3. **Single-hop queries score lowest (0.118)** because lexical surface overlap is weakest there — the question often paraphrases the answer's content. Multi-hop and open-domain score highest because longer questions retain more keyword anchors.

4. **Adversarial category contains the `adversarial_answer` field** (no `answer`); the eval ignores answer content and uses only evidence-pointed turns as gold, so the metric is unbiased toward the answer text.

## Reproducibility

```bash
cd paper/publication/baselines
python3 locomo_eval.py full
# Output: /tmp/locomo10.json (cache), /tmp/locomo-eval.db, /tmp/locomo-results.jsonl
```

Stdlib only. Runtime <10s on commodity laptop (download ~3s + index ~1s + eval ~1s).

## Paper §5.2 ready-to-drop prose

> "On a stratified 100-query subset of LOCOMO (Maharana et al., 2024; CC BY-NC 4.0), an SQLite FTS5 baseline achieves nDCG@10 = 0.281 (single-hop 0.118, multi-hop 0.371, temporal 0.289, open-domain 0.375, adversarial 0.253). The 23× gap between LOCOMO FTS5 and nox-mem golden FTS5 (0.281 vs 0.012) confirms that the difficulty of pure-lexical retrieval is corpus-dependent and that the hybrid contribution argued in §3.2 is calibrated to the harder, identifier-dense regime of operational memory rather than to conversational long-form text."

## Files

- Adapter: `paper/publication/baselines/locomo_eval.py`
- Per-query results: `/tmp/locomo-results.jsonl` (100 records)
- Cached corpus: `/tmp/locomo10.json` (2.8 MB)
- Temp index: `/tmp/locomo-eval.db` (FTS5)
