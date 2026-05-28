# EverMemBench — Phase C Results (batch 004)

**Date:** 2026-05-28
**Adapter:** `eval/evermembench/adapter_nox_mem.py` — Phase C (day-group chunks)
**Batch:** 004 (10,222 messages, 254 days, 626 QA items)
**Run dir on VPS:** `/root/.openclaw/evermembench-runs/phaseB-004-1779984043` (kept Phase B prefix from script reuse)
**Isolation:** `NOX_DB_PATH=/root/.openclaw/evermembench-runs/phaseB-004-1779984043/nox-mem.db` (separate from prod 18802)
**Prod chunks before/after:** 69,135 / 69,135 (no contamination)

---

## TL;DR

Phase C **HURT** overall (53.83% vs Phase B 57.19%, -3.36 pts) and **failed to fix multi-hop** (still 0%). The hypothesis that multi-hop reasoning needs co-located turns in the same chunk was **falsified for this corpus + retrieval stack**. Bigger chunks substantially hurt single-hop precision (-37 pts) and temporal queries (-20 pts), without unlocking multi-hop reasoning.

**Gate verdict (per task brief gate criteria):**
> "Overall ≤ 57.19% AND multi-hop ≤ 4% → Phase C HURT — Phase 3 uses Phase B variant instead"

**Phase 3 (full 5 batches) will run with the Phase B variant.** The committed adapter keeps `DEFAULT_ADAPTER_MODE = "phaseB"` and exposes Phase C via `NOX_ADAPTER_MODE=phaseC` for future re-analysis.

---

## Three-Variant Comparison

| Category                       | PR #363 baseline | Phase B  | Phase C  | Δ Phase C vs B |
|--------------------------------|-----------------:|---------:|---------:|---------------:|
| Overall                        |           56.07% |   57.19% | **53.83%** |          -3.36 |
| MC (Multiple-Choice)           |           70.95% |   68.89% |   69.67% |          +0.78 |
| OE (Open-Ended)                |           31.65% |   37.97% |   27.85% |         -10.12 |
| F (Fine-Grained Recall)        |           31.65% |   37.97% |   27.85% |         -10.12 |
| F_SH (Single-Hop)              |              n/a |   85.71% | **48.98%** |         -36.73 |
| F_HL (Hard-Linked)             |              n/a |   43.59% |   51.28% |          +7.69 |
| F_TP (Temporal)                |           10.00% |   23.33% |    3.33% |         -20.00 |
| F_MH (Multi-Hop) **key gate**  |            4.00% |    0.00% |    0.00% |          +0.00 |
| MA (Memory Awareness)          |              n/a |   72.87% |   72.87% |          ±0.00 |
| MA_U (Updating)                |           84.48% |   74.14% |   63.79% |         -10.35 |
| P (Profile Understanding)      |              n/a |   61.07% |   63.36% |          +2.29 |

### Phase C sub-categories (full breakdown)

| Sub-category | Correct / Total | Accuracy |
|---|---:|---:|
| F_HL | 40/78 | 51.28% |
| F_MH | 0/50 | 0.00% |
| F_SH | 24/49 | 48.98% |
| F_TP | 2/60 | 3.33% |
| MA_C | 69/100 | 69.00% |
| MA_P | 82/100 | 82.00% |
| MA_U | 37/58 | 63.79% |
| P_Skill | 33/45 | 73.33% |
| P_Style | 12/37 | 32.43% |
| P_Title | 38/49 | 77.55% |

---

## Hypothesis Test — Multi-hop

**Hypothesis (Phase C design):** answering multi-hop questions requires the answer LLM to see multiple turns in the SAME chunk so it can stitch partial evidence across speakers/turns (paper §4.2 quote: *"answering correctly requires stitching together partial evidence that never co-occurs in a single exchange"*). Phase B's atomic per-turn chunks made this structurally impossible. Phase C groups by (date, group) so one chunk = one day's conversation in one group.

**Result:** Multi-hop stayed at **0/50 = 0.00%** — identical to Phase B. **Hypothesis falsified for this corpus + retrieval stack.**

**Why Phase C failed to unlock multi-hop (interpretation):**

1. **Retrieval precision collapsed.** Single-hop fell from 86% → 49%. With one chunk per (date, group), each chunk averages ~14 messages of mixed-topic conversation. The hybrid search struggles to surface the *right* day-group when the query asks about a specific narrow fact.
2. **Top-K=10 still doesn't recover the right day-group for multi-hop.** Multi-hop questions span multiple (date, group) pairs, and the day-group hits we DO return aren't the ones with the bridge facts. The "everything-in-one-chunk" structure fails to compensate for upstream retrieval miss.
3. **Date metadata diluted.** Temporal fell 23% → 3%. The `date:` field is now buried inside a ~14-turn block; FTS5 BM25 + Gemini embeddings give the chunk a lower temporal-match signal than Phase B's per-message blocks where the date was the highlight of every chunk.
4. **Updating semantics scrambled.** MA_U fell 74% → 64%. With the entire day in one chunk, the "old value vs new value" distinction inside a single day's conversation gets averaged out at retrieval time.

**The wins (compensating but small):**
- F_HL (Hard-Linked) **+7.69**: cross-turn linking does benefit when the linked turns are in the same chunk
- P (Profile) **+2.29**: bigger context helps style/skill inference
- MC overall **+0.78**: not a meaningful delta

Net: the +7.7 on Hard-Linked is dwarfed by -36.7 on Single-Hop and -20.0 on Temporal.

---

## Operational Notes

- **Chunks produced:** 752 (vs Phase B 1,140 per-message chunks vs Phase A baseline 1,140). nox-mem's segmenter further sub-divides each H2 day-group block when it exceeds an internal byte threshold, so the reduction is less than the day-group count (267 day-groups → 752 chunks ≈ 2.8 chunks per block).
- **Vectorize coverage:** 752/752 embedded (100%).
- **Search took:** 626 queries / ~280s = ~2.2 q/s with concurrency 3.
- **Answer took:** 626 answers via gemini-2.5-flash @ concurrency 4 = ~14 min.
- **Evaluate took:** 237 OE judge calls = ~2 min.
- **Total wall time:** ~22 min (1 batch).

### Result-file contamination incident (recovered)
First Phase C run reused stale `answer_results_004.json` from the prior Phase B run. The pipeline's incremental-resume logic skipped Answer regeneration. Detected via "Skipped 626 already answered questions" in eval.log + suspicious 57.03% overall (close to Phase B). Recovered by deleting `answer_results_004.json` + `evaluation_results_004.json` and re-running `--stages answer evaluate` against the Phase C `search_results_004.json` (which had been regenerated correctly).

**Lesson:** Phase 3 launcher must `rm -f eval/results/nox_mem/{answer,evaluation}_results_*.json` before each run when adapter mode changes. Added to follow-up TODO.

---

## Iteration History (transparency)

| Iteration | Mode | Overall | Multi-hop | Temporal | Updating | Verdict |
|---|---|---:|---:|---:|---:|---|
| Phase A (PR #363) | flat markdown | 56.07% | 4.00% | 10.00% | 84.48% | baseline |
| Phase B (on-VPS only) | H2-block per msg + context | **57.19%** | 0.00% | 23.33% | 74.14% | net win, multi-hop fail |
| Phase C (this PR) | one chunk per (date,group) | 53.83% | 0.00% | 3.33% | 63.79% | regression — Phase 3 stays on Phase B |

---

## Cost Log

| Item | Estimate |
|---|---:|
| Gemini embeddings (752 chunks × 3072d) | ~$0.10 |
| Search hybrid (626 queries) | ~$0.05 |
| Answer generation (626 × gemini-2.5-flash) | ~$0.30 |
| LLM-judge evaluation (237 OE items) | ~$0.20 |
| **Total Phase C batch 004** | **~$0.65** |

Under the $1.50 cap. Phase 3 cost estimate (Phase B variant × 5 batches): ~$3.25.

---

## Next Actions

1. Phase 3 launcher (separate PR) runs batches 001-005 with `NOX_ADAPTER_MODE=phaseB`.
2. Multi-hop remains 0% in Phase B — separate investigation needed. Candidates:
   - Retrieval-time chunk-stitching: expand each top-K hit's siblings before sending to the answer LLM (chunk-level "expand context" pass).
   - Answer-LLM-side multi-turn reasoning: send a larger top-K (20-30) with explicit instruction to cross-reference turns.
   - Re-investigate paper §4.2 — does EverMemBench publish what their multi-hop SOTA system (Letta or Memobase, 18.88% reported) does differently? Likely it's a graph-style or trajectory-style memory, not pure RAG.
3. Temporal regression in Phase C confirms date-as-prefix is essential — keep Phase B's `## [{time} | {group} | {speaker}]` H2 header in any future variant.
