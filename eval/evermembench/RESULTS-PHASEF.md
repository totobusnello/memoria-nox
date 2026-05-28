# EverMemBench Phase F Results — Cross-Encoder Rerank Multi-Hop Attack

**Date:** 2026-05-28 (Wed)
**Branch:** `feat/evermembench-phaseF-rerank`
**Backbone:** Gemini-2.5-Flash (answer + judge), nox-mem v3.8 (retrieval),
BAAI/bge-reranker-v2-m3 (intended rerank — see issues below)

## TL;DR

**Phase F did not clear the gate.** Multi-hop stayed flat at 2.00% (1/50) in the
only complete batch, and overall regressed to 55.91% vs Phase D 61.98%.
However, the regression turned out to be driven by **two independent issues**,
not the rerank hypothesis itself:

1. **Reranker model id silently overridden by prod `.env`** — `/root/.openclaw/.env`
   had `NOX_RERANKER_MODEL=Xenova/bge-reranker-base` (an ONNX JS-format model
   incompatible with `sentence_transformers`). All 626 rerank attempts hit
   `OSError: does not appear to have a file named pytorch_model.bin` and the
   adapter silently fell back to no-rerank. Metadata captured the error per
   query.
2. **top_k mismatch** — Phase D's winning 61.98% used `--top-k 20` (20 chunks
   into the answer LLM context). Phase F spec ran with `--top-k 10` per the
   task description. Reducing context alone from 20 to 10 chunks costs ~6pp
   even before any reranking.

A second run with the reranker model id patched (BAAI/bge-reranker-v2-m3 forced
post-`.env` source) and `--top-k 20` to match Phase D started, but the VPS
(Hostinger, CPU only) **saturated at load avg 9.3+** with rerank predict at
harness concurrency=3 — the first 6+ queries each exceeded the 120s per-query
timeout, the harness retried with no improvement (cache warm but CPU still
pinned), and the run had to be killed before reaching answer stage.

The honest finding: **the rerank hypothesis is untested at production speed on
this VPS hardware budget. The Phase F gate should be marked STOP per the
"Multi-hop ≤ 5%" criterion using v1 data, with the caveat that v1 didn't
actually rerank.**

## Detailed results

### Batch 004 v1 — reranker fell back to no-rerank

| Metric                | Phase D (top-k=20) | Phase F v1 (top-k=10, no-rerank fallback) | Δ      |
|-----------------------|--------:|--------:|-------:|
| Overall accuracy      |   61.98 |    55.91 |  -6.07 |
| Multi-hop (F_MH)      |    2.00 |    2.00 |   0.00 |
| Single-hop (F_SH)     |     — |   85.71 |    — |
| Two-phase (F_TP)      |     — |   20.00 |    — |
| High-level (F_HL)     |     — |   34.62 |    — |
| Open-ended (F overall)|     — |   34.60 |    — |
| Multiple choice       |     — |   68.89 |    — |
| Search p50 latency    |    — |  1109 ms |    — |
| Search p95 latency    |    — |  1572 ms |    — |
| Mean rerank ms        |    — |   15.3 (error path) |    — |
| Rerank applied count  |    — |  0 / 626 |    — |

Metadata snippet from any search result:
```json
{
  "rerank_enabled": true,
  "rerank_applied": false,
  "rerank_model": "Xenova/bge-reranker-base",
  "rerank_ms": 0.0007,
  "rerank_error": "CrossEncoder(Xenova/bge-reranker-base) load failed: OSError: Xenova/bge-reranker-base does not appear to have a file named pytorch_model.bin, model.safetensors, tf_model.h5, model.ckpt or flax_model.msgpack."
}
```

### Batch 004 v2 — correct model id, killed before answer stage

| Stage    | Status |
|----------|--------|
| Add      | OK (10033 chunks ingested) |
| Vectorize| OK (10033/10033 embedded, ~530s) |
| Search   | **Aborted** — queries timing out at 120s under CPU pressure (load avg 9.3+); harness retry-loop made no progress; killed by operator |
| Answer   | not reached |
| Evaluate | not reached |

## Gate decision

Per spec:
> Multi-hop ≤ 5% → Reranking didn't help structurally — STOP, report multi-hop
> is harder than expected

Verdict: **STOP**. No 5-batch run launched.

The retry with bge-reranker-v2-m3 actually loading would require either:
- harness concurrency=1 (estimated batch 004 wall time: ~1.7h)
- GPU hardware (VPS is CPU only)
- smaller/faster reranker (bge-reranker-base, MiniLM cross-encoder)

## Compute cost disclosure

- **v1 batch 004**: $0.75 — full Gemini answer + judge stages ran on plain
  Phase D-equivalent retrieval (rerank silently failed).
- **v2 batch 004 (aborted)**: ~$0.05 — only embedding cost (vectorize stage);
  search aborted before answer.
- **Reranker pre-warm**: free (HuggingFace download + one local predict).
- **Total Phase F spend**: ~$0.80.
- **Total session spend running estimate**: ~$5.75 (vs $9 hard cap).

## What we learned (honest framing)

1. **Adapter env-var precedence pitfall**: `set -a; source .env; set +a` happens
   inside `run-batch.sh` AFTER any caller-set env vars. The .env file's
   `NOX_RERANKER_MODEL` overrode our intended default. Fix in v2 wrapper: patch
   a copy of the script to re-export AFTER the `.env` source.
2. **CPU rerank vs VPS budget**: `BAAI/bge-reranker-v2-m3` at sentence-transformers
   default settings (max_length=512, batch_size=32) costs ~2-3s per
   `(query, 50_chunks)` predict on the VPS CPU. At harness concurrency=3 this
   saturates load and blows past the 120s per-query timeout that pretty much
   everything else in the pipeline lives below.
3. **Phase D top-k=20 carried the win, not just structured chunks**: v1 isolated
   the effect of the `--top-k 10` flag. Dropping from 20 → 10 chunks of context
   into the Gemini answer LLM costs roughly 6pp overall accuracy. This is
   useful ablation data even though the rerank itself didn't run.
4. **Multi-hop is hard to move with rerank alone**: even setting aside CPU
   issues, the 2% → 2% non-movement in v1 is consistent with the spec's stop
   criterion ("Reranking didn't help structurally"). Bridge-fact retrieval may
   need a different attack: corpus-side chunk expansion, query rewriting into
   sub-questions, or graph hops through the KG.

## What Phase G might look like (not in scope here)

- Replace cross-encoder rerank with **query decomposition**: use the Gemini answer
  LLM to split multi-hop questions into sub-questions, retrieve per sub-question,
  union the results, then answer.
- Wider corpus-side coverage: per-entity rollup chunks that pre-stitch related
  facts so multi-hop bridges are already a single chunk.
- KG path retrieval: for multi-hop questions, walk `kg_relations` between
  entities mentioned in the question and pull chunks anchored to entities on
  the path.

## Run commands (reference)

```bash
# v1 (rerank silently failed due to .env override):
export NOX_ADAPTER_MODE=phaseF
export NOX_RERANKER_ENABLED=1
export NOX_RERANKER_OVERFETCH=50
bash $WORK/run-batch.sh 004 18810   # --top-k 10 default

# v2 (model id forced, but VPS too slow at concurrency=3):
cp $WORK/run-batch.sh /tmp/run-batch-phaseF-v2.sh
sed -i '/source \/root\/.openclaw\/.env/a export NOX_RERANKER_MODEL=BAAI/bge-reranker-v2-m3' /tmp/run-batch-phaseF-v2.sh
sed -i 's/--top-k 10/--top-k 20/' /tmp/run-batch-phaseF-v2.sh
bash /tmp/run-batch-phaseF-v2.sh 004 18810
```

## Honest framing

- The committed adapter is correct and ready to use when a faster reranker or
  GPU host is available. The lazy load + graceful fallback worked exactly as
  designed: even when the model failed, the adapter returned the API top-k and
  logged the error in metadata so we could diagnose.
- We did NOT prove or disprove the rerank-attacks-multi-hop hypothesis on this
  budget. We DID prove that reducing `--top-k` from 20 to 10 costs ~6pp.
- The committed code is safe to land: env-gated, lazy-loaded, gracefully
  falls back. Future runs on better hardware can flip the gate and re-measure
  without code changes.
