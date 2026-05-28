# EverMemBench Path B Full Results — nox-mem vs paper Table 4

## Headline

- **nox-mem 5-batch weighted average:** **62.22%** (1942/3121)
- **vs paper Table 4 (Gemini-3-Flash backbone):**
  - MemOS: 59.27%  (nox-mem +2.95%)  → **WIN**
  - MemoBase: 55.83%  (nox-mem +6.39%)  → **WIN**
  - Zep: 54.90%  (nox-mem +7.32%)  → **WIN**
  - Mem0: 52.12%  (nox-mem +10.10%)  → **WIN**

> Honest framing: nox-mem was measured on Gemini-2.5-Flash answer-LLM (cost-throttled). Paper Table 4 column uses Gemini-3-Flash, which is the strongest backbone in the published study. Comparing across LLM backbones is directional, not authoritative.

## Per-batch results

| batch | correct | total | accuracy | MC | OE |
|---|---:|---:|---:|---:|---:|
| 004 (Phase D, top-k=20) | 388 | 626 | 61.98% | 75.84% | 39.24% |
| 005 (Phase 3, top-k=20) | 374 | 610 | 61.31% | 74.67% | 40.00% |
| 010 (Phase 3, top-k=20) | 397 | 623 | 63.72% | 78.70% | 39.50% |
| 011 (Phase 3, top-k=20) | 385 | 633 | 60.82% | 71.14% | 43.70% |
| 016 (Phase 3, top-k=20) | 398 | 629 | 63.28% | 74.55% | 44.49% |
| **5-batch weighted** | **1942** | **3121** | **62.22%** | **74.96%** | **41.39%** |

## Per-dimension aggregate (5-batch weighted)

| dimension | correct | total | accuracy |
|---|---:|---:|---:|
| Fine-grained Recall | 490 | 1184 | 41.39% |
| Memory Awareness | 1066 | 1287 | 82.83% |
| Profile Understanding | 386 | 650 | 59.38% |

## Per-subdim aggregate (5-batch weighted)

| subdim | dimension | correct | total | accuracy |
|---|---|---:|---:|---:|
| F_HL | Fine-grained Recall | 208 | 388 | 53.61% |
| F_MH | Fine-grained Recall | 13 | 249 | 5.22% |
| F_SH | Fine-grained Recall | 191 | 247 | 77.33% |
| F_TP | Fine-grained Recall | 78 | 300 | 26.00% |
| MA_C | Memory Awareness | 407 | 500 | 81.40% |
| MA_P | Memory Awareness | 415 | 500 | 83.00% |
| MA_U | Memory Awareness | 244 | 287 | 85.02% |
| P_Skill | Profile Understanding | 134 | 221 | 60.63% |
| P_Style | Profile Understanding | 85 | 181 | 46.96% |
| P_Title | Profile Understanding | 167 | 248 | 67.34% |

## Iteration journey (batch 004 only)

| variant | overall | multi-hop (F_MH) | notes |
|---|---:|---:|---|
| PR #363 baseline (flat md) | 56.07% | 4.00% | Original flat-paragraph markdown |
| Phase B (structured per-turn) | 57.19% | 0.00% | Per-message blocks + context window |
| Phase C (day-group inline) | 53.83% | 0.00% | One chunk per (date,group); retrieval precision collapsed |
| **Phase D (top-k=20, Phase B mode)** | **61.98%** | **2.00%** | Search-side fix: top_k 10→20 per MemOS methodology (paper §3.3.4) |

## Cost summary

| Phase | Batches | Cost |
|---|---|---:|
| Phase B (PR #364) | 004 | ~$0.75 |
| Phase C | 004 | ~$0.65 |
| Phase D (top-k=20) | 004 | ~$0.75 |
| Phase 3 (top-k=20 parallel) | 005, 010, 011, 016 | ~$2.80 |
| **Total realised** | | **~$4.95** |

Cap: $10 USD (raised mid-session from $5). Soft target $8. Total well within. Detailed breakdown in `phaseB-cost-log.md`.

## Path B recommendations for paper §5

- Lead with the 5-batch weighted average vs MemOS/Zep/Mem0/MemoBase deltas.
- Disclose the LLM-backbone gap (Gemini-2.5-Flash vs paper's Gemini-3-Flash) upfront.
- Frame the Phase A→B→C→D iteration journey as ablations, not a single shot.
- Note that the F_MH (multi-hop) result reflects ingestion-side structure + search-side top_k.

## Future work (not in this round)

- Multi-query expansion (decompose multi-hop into chained single-hops at retrieval time).
- Cross-encoder reranking on top-20 candidates.
- Per-question top-k tuning via question-type classifier.
- Repeat run on Gemini-3-Flash backbone once cost budget allows.
