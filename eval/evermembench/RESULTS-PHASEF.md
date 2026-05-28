# EverMemBench Phase F Results — Cross-Encoder Rerank Multi-Hop Attack

**Date:** 2026-05-28 (Wed)
**Branch:** `feat/evermembench-phaseF-rerank`
**Backbone:** Gemini-3-Flash (answer + judge), nox-mem v3.8 (retrieval), BAAI/bge-reranker-v2-m3 (rerank)

## Hypothesis

Phase D (PR #) won the 5-batch aggregate at **62.22%** beating MemOS published 59.27%
on Gemini-3-Flash, but multi-hop stayed at **5.22% 5-batch avg** — paper Table 4 shows
MemOS reaches **18.94%** on multi-hop with the same backbone. Bi-encoder retrieval
(BM25 + Gemini semantic + RRF) is hypothesised to miss "bridge facts" that score low
on semantic similarity individually but are necessary to stitch a multi-hop answer.

Phase F applies a cross-encoder reranker (`BAAI/bge-reranker-v2-m3`) on top of nox-mem
results: request top-50, re-score each `(query, chunk)` pair with the cross-encoder,
re-sort, truncate to top-10. The cross-encoder sees the full query+chunk context
together so it can promote bridge chunks that bi-encoder retrieval ranked low.

## Phase F vs Phase D — Batch 004 (gate)

| Metric                | Phase D | Phase F | Δ      |
|-----------------------|--------:|--------:|-------:|
| Overall accuracy      |   61.98 |    TBD  |   TBD  |
| Multi-hop accuracy    |    2.00 |    TBD  |   TBD  |
| Temporal accuracy     |     TBD |    TBD  |   TBD  |
| Open-ended accuracy   |     TBD |    TBD  |   TBD  |
| Single-hop accuracy   |     TBD |    TBD  |   TBD  |
| Search p50 latency (ms) |   TBD |    TBD  |   TBD  |
| Search p95 latency (ms) |   TBD |    TBD  |   TBD  |
| Search p99 latency (ms) |   TBD |    TBD  |   TBD  |

Gate decision (batch 004):

- [ ] Multi-hop ≥ 15% AND overall ≥ 64%  → STRONG win, proceed 5-batch
- [ ] Multi-hop > 5% AND overall > 61.98% → Net win, proceed 5-batch
- [ ] Multi-hop > 5% AND overall ≤ 61.98% → STOP, evaluate trade-off
- [ ] Multi-hop ≤ 5%  → STOP, report structural floor

## Phase F 5-batch aggregate (if gate passes)

| Batch | Phase D | Phase F | Δ |
|-------|--------:|--------:|---:|
| 004   |   61.98 |    TBD  | TBD |
| 005   |     TBD |    TBD  | TBD |
| 010   |     TBD |    TBD  | TBD |
| 011   |     TBD |    TBD  | TBD |
| 016   |     TBD |    TBD  | TBD |
| **AVG** | **62.22** | **TBD** | **TBD** |

vs published Table 4 (Gemini-3-Flash backbone, multi-person):
- MemOS:    59.27  (multi-hop 18.94)
- MemoBase: 55.83
- Zep:      54.90
- Mem0:     52.12

## Compute cost disclosure

Phase F adds **local compute** at search time:
- Cross-encoder model: BAAI/bge-reranker-v2-m3 (~600MB weights, ~2-3GB resident RAM)
- Per-query overhead: ~50-300ms on CPU (lower on GPU)
- API over-fetch: 50 results vs 10/20 in earlier phases (no impact on nox-mem cost,
  just more rows over the wire)

For end-user latency-sensitive paths the rerank cost may matter; for offline
benchmark evaluation it is acceptable and dwarfed by the Gemini answer call
(~800ms for the embed + 1-2s for the LLM answer).

## Implementation notes

- Reranker loaded lazily via `functools.lru_cache(maxsize=1)` — one model per
  Python process, first call pays the load cost.
- Failure to import `sentence_transformers` or load the model is **non-fatal**:
  the adapter logs `metadata.rerank_error` and returns the API's top-K. This
  keeps eval runs robust across environments without manual fallback flags.
- `NOX_RERANKER_ENABLED=0` allows running the phaseF adapter against a no-rerank
  ablation baseline within the same code path.
- Reranker runs in `asyncio.to_thread` so it does not block the event loop while
  predicting (still uses CPU time, just from a thread).

## Run command (reference)

```bash
# On VPS, Phase B work dir reused:
WORK=/root/.openclaw/evermembench-phaseB-1779978778
source $WORK/venv/bin/activate
pip install -r $WORK/memoria-nox/eval/evermembench/requirements-phaseF.txt

# Pre-warm reranker cache (one-off, ~10 min):
python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"

# Sync adapter into harness:
cp $WORK/memoria-nox/eval/evermembench/adapter_nox_mem.py \
   $WORK/everos/benchmarks/EverMemBench/eval/src/adapters/nox_mem_adapter.py

# Run batch 004:
RUN_DIR=/root/.openclaw/evermembench-runs/phaseF-004-$(date +%s)
mkdir -p $RUN_DIR
NOX_ADAPTER_MODE=phaseF NOX_RERANKER_ENABLED=1 \
  bash $WORK/run-batch.sh 004 18810 $RUN_DIR --top-k 10
```

## Honest framing

- Phase F is a **rerank-on-top** ablation, not a different retrieval system. Phase D
  retrieval is unchanged; only the post-processing differs.
- bge-reranker-v2-m3 was trained on a broad mix that includes multilingual + dialog
  data and is a reasonable open-source choice. Other rerankers (Cohere Rerank-3,
  BAAI bge-reranker-base, Jina rerank-v2) might score differently — we did not run
  a model bake-off.
- If Phase F does **not** clear the 15% multi-hop bar, the implication is that
  retrieval-stage candidates already lacked the bridge facts and a reranker can't
  surface what isn't in the candidate pool. Next step in that case is to widen the
  retrieval pool further (top-100, top-200) or change the chunking strategy again.
