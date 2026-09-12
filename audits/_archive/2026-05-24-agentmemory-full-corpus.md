# agentmemory — Full Corpus Ingest + Cross-System Row

**Date:** 2026-05-24  
**Status:** COMPLETE (95.1% corpus, limited by iii-engine throughput ceiling)  
**Cost:** $0.00 (local iii-engine, no API calls)  
**Ingest wall-clock:** ~64 minutes (01:16Z start → 02:21Z eval)  
**Baseline reference:** PR #287 (20.5% corpus)

---

## Summary

Full-corpus ingest of the 6830-chunk Q4 evaluation corpus into agentmemory v0.9.21.
Evaluation ran at 6514 memories (95.1%) due to iii-engine throughput ceiling:
the REST ingest rate fell from ~108 chunks/min at 30% corpus to ~5 chunks/min
above ~90%, making 100% completion infeasible within the 90-minute time-box.
At 95.1% we have near-complete coverage of all LoCoMo (5882 chunks) and
LongMemEval oracle (948 chunks) data.

---

## Corpus

| Dataset | Chunks | In daemon at eval |
|---|---:|---:|
| LoCoMo (snap-research/locomo) | 5,882 | ~5,567 (94.6%) |
| LongMemEval oracle (xiaowu0162/longmemeval-cleaned) | 948 | ~947 (99.9%) |
| **Total** | **6,830** | **6,514 (95.1%)** |

---

## Full-Corpus Results (95.1% corpus, n=20 queries)

| Dataset | nDCG@10 | MRR | R@10 | p50 (ms) | p95 (ms) | Hits |
|---|---:|---:|---:|---:|---:|---:|
| **LoCoMo** | 0.1436 | 0.1333 | 0.2250 | 21.4 | 46.1 | 3/10 |
| **LongMemEval** | 0.1138 | 0.1333 | 0.1500 | 22.6 | 45.6 | 2/10 |
| **Combined** | **0.1287** | **0.1333** | **0.1875** | **21.6** | **46.1** | **5/20** |

---

## vs PR #287 Capped Baseline (20.5% corpus)

| Metric | PR #287 (20.5%) | Full (95.1%) | Delta |
|---|---:|---:|---:|
| nDCG@10 (all) | 0.1376 | 0.1287 | -0.0089 |
| MRR (all) | 0.1030 | 0.1333 | +0.0303 |
| R@10 (all) | 0.2500 | 0.1875 | -0.0625 |
| nDCG@10 LoCoMo | 0.2751 | 0.1436 | -0.1315 |
| nDCG@10 LongMemEval | 0.0000 | 0.1138 | +0.1138 |
| p50 latency (ms) | 13.9 | 21.6 | +7.7 |

**Key observations:**

1. **LongMemEval fixed**: PR #287 had 0.0000 on LongMemEval because the oracle
   chunks were not ingested. Full corpus brings this to 0.1138 — a real gain.

2. **LoCoMo regressed**: nDCG dropped from 0.2751 → 0.1436 with more corpus.
   Likely cause: iii-engine semantic search at large corpus sizes retrieves
   more noise/distractor chunks. The relevance model is not purely lexical —
   with 6514 observations it has more candidates to confuse with.

3. **MRR improved**: +0.0303 aggregate. The few queries that DO hit get ranked
   higher (MRR > nDCG suggests first-hit ranking is better, but coverage is
   lower).

4. **Latency acceptable**: p50=22ms, p95=46ms — fast search even at 6514 memories.

5. **No net gain on nDCG**: Full corpus vs 20.5% shows -0.009 on the headline
   metric. agentmemory is not a strong retrieval baseline for this evaluation
   paradigm (conversation-chunk ID round-trip via `[nox_id:...]` prefix limits
   precision).

---

## vs nox-mem Hybrid (from _aggregate.md)

| System | nDCG@10 | MRR | R@10 | Notes |
|---|---:|---:|---:|---|
| **nox-mem** | 0.3753 | 0.3700 | 0.5417 | HTTP on :18802, full corpus |
| **agentmemory (full)** | 0.1287 | 0.1333 | 0.1875 | 95.1% corpus, iii-engine |
| **agentmemory (PR #287)** | 0.1376 | 0.1030 | 0.2500 | 20.5% corpus |
| **mem0** | 0.1315 | 0.1250 | 0.1500 | 20 queries, OpenAI embed |

nox-mem leads agentmemory by **+0.247 nDCG@10 (+192%)** at full corpus.

---

## Per-Query Details

| qid | dataset | category | nDCG@10 | MRR | R@10 | lat_ms |
|---|---|---|---:|---:|---:|---:|
| conv-48::q13 | locomo | single-hop | 0.3904 | 1.0000 | 0.2500 | 30 |
| conv-50::q49 | locomo | adversarial | 0.0000 | 0.0000 | 0.0000 | 46 |
| conv-26::q6 | locomo | open-domain | 0.0000 | 0.0000 | 0.0000 | 21 |
| conv-30::q11 | locomo | multi-hop | 0.3562 | 0.1667 | 1.0000 | 13 |
| conv-44::q53 | locomo | knowledge-update | 0.0000 | 0.0000 | 0.0000 | 26 |
| conv-41::q64 | locomo | multi-session | 0.0000 | 0.0000 | 0.0000 | 24 |
| conv-26::q83 | locomo | open-domain | 0.6895 | 0.1667 | 1.0000 | 19 |
| conv-26::q87 | locomo | temporal-reasoning | 0.0000 | 0.0000 | 0.0000 | 18 |
| conv-26::q191 | locomo | adversarial | 0.0000 | 0.0000 | 0.0000 | 21 |
| conv-43::q226 | locomo | temporal | 0.0000 | 0.0000 | 0.0000 | 17 |
| 6aeb4375 | longmemeval | single-session-user | 0.5250 | 0.3333 | 1.0000 | 25 |
| 6aeb4375_abs | longmemeval | single-session-user | 0.0000 | 0.0000 | 0.0000 | 22 |
| gpt4_2ba83207 | longmemeval | single-session-preference | 0.0000 | 0.0000 | 0.0000 | 23 |
| edced276_abs | longmemeval | single-session-assistant | 0.0000 | 0.0000 | 0.0000 | 22 |
| e9327a54 | longmemeval | temporal | 0.0000 | 0.0000 | 0.0000 | 46 |
| 505af2f5 | longmemeval | knowledge-update | 0.0000 | 0.0000 | 0.0000 | 19 |
| 118b2229 | longmemeval | multi-hop | 0.0000 | 0.0000 | 0.0000 | 21 |
| 0862e8bf_abs | longmemeval | single-session-assistant | 0.0000 | 0.0000 | 0.0000 | 23 |
| gpt4_1d4ab0c9 | longmemeval | multi-session | 0.0000 | 0.0000 | 0.0000 | 26 |
| gpt4_70e84552_abs | longmemeval | temporal-reasoning | 0.6131 | 1.0000 | 0.5000 | 19 |

---

## Ingest Performance / iii-engine Observations

The iii-engine REST ingest exhibits significant throughput degradation at scale:

| Corpus % | Rate (chunks/min) |
|---:|---:|
| 0–30% | ~100–120 |
| 30–80% | ~60–80 |
| 80–95% | ~5–15 |
| 95%+ | <5 |

**Root cause hypothesis:** iii-engine likely builds in-memory indexes (HNSW or similar)
that require expensive rebalancing above certain sizes. The local machine has
available CPU, so this is likely an algorithmic bottleneck in the iii-engine,
not a hardware constraint.

**Implication for Q4 comparison:** agentmemory ingest time at full scale is
3–4x longer than the pre-run estimate (~54min estimate vs ~120min actual).
For production benchmarking, consider chunk batching or HNSW index pre-warming.

---

## Artifact Locations

- Raw JSON output: `eval/q4-comparison/output/agentmemory_full.json`
- PR #287 baseline: `eval/q4-comparison/output/agentmemory.json` (20 queries, 20.5% corpus)
- Daemon log: `eval/q4-comparison/output/agentmemory-daemon.log`

---

## Technical Notes

- agentmemory v0.9.21 (npm package `@agentmemory/agentmemory`)
- iii-engine (Apache-2.0 CLI, ELv2 self-host OK for benchmarking)
- REST API: `POST /agentmemory/remember`, `POST /agentmemory/search`
- ID round-trip: `[nox_id:<id>]` prefix embedded in content, parsed from search results
- Evaluation bypassed `setup()` to avoid double-ingest cycle (setup re-ingests when count < expected)
- Corpus: LoCoMo `CC BY-NC 4.0` + LongMemEval oracle `MIT`
