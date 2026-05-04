# MEMORYBANK-ADAPTER-SPEC — W2 Sprint

**Status:** Ready for deployment  
**Date:** 2026-05-04  
**Replaces:** LOCOMO (E04-locomo-LAUNCH-FAILED.md)  
**Paper section:** §5.2 Table 5 — Conversational episodic memory benchmark

---

## Purpose

MemoryBank (Zhong et al., 2023, arXiv:2305.10250) substitutes LOCOMO as the
conversational memory benchmark for critic issue C5 (external validity, single-corpus
mitigation). Together with BEIR TREC-COVID (external domain corpus, running) and the
in-domain golden set (n=60), MemoryBank gives 3 total corpora for §5.

---

## Dataset

| Property | Value |
|---|---|
| Citation | Zhong et al. (2023). MemoryBank: Enhancing Large Language Models with Long-Term Memory. arXiv:2305.10250 |
| GitHub | `https://github.com/zhongwanjun/MemoryBank-SiliconFriend` |
| Data path | `data/silicon_friend_memory_bank/*.json` |
| HF fallback IDs | `zhongwanjun/MemoryBank`, `zhongwanjun/silicon-friend`, `wanjun-zhong/MemoryBank` |
| Sessions | ~40 synthetic daily conversation sessions |
| Question types | 5: factual_recall, temporal_reasoning, sentiment_analysis, preference_inference, event_summary |
| Total QA pairs | ~200–400 (estimated; varies per release) |

### Session JSON Schema

Each session file (`data/silicon_friend_memory_bank/<session_id>.json`):

```json
{
  "session_id": "session_001",
  "date": "2023-01-01",
  "conversations": [
    {"role": "user", "content": "...", "timestamp": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "memory_items": [
    {"memory_id": "m001", "content": "Alice prefers oatmeal for breakfast.", "created_at": "..."}
  ],
  "qa_pairs": [
    {
      "question": "What does Alice prefer for breakfast?",
      "answer": "Oatmeal",
      "question_type": "preference_inference",
      "memory_ids": ["m001"]
    }
  ]
}
```

The adapter handles alternative field names (`dialogue`, `memories`, `QA`, `type`, etc.)
as observed in different versions of the repo.

---

## Adapter Architecture

### File

`paper/publication/baselines/memorybank_adapter.py`

### Pipeline (5 stages)

| Stage | Function | Output |
|---|---|---|
| 1. Acquire | `download_memorybank()` | `list[SessionData]` |
| 2. Chunk | `chunk_all_sessions()` | `list[ChunkRecord]` |
| 3. Index | `build_temp_db()` | SQLite DB + FTS5 |
| 4. QA extract | `extract_qa_records()` + `select_stratified_subset()` | 100-query JSONL |
| 5. Eval | `evaluate_all()` | per-query JSONL + aggregate metrics |

### Acquisition Strategy

1. `git clone --depth=1` from GitHub (primary, ~5 MB, <30 s)
2. HuggingFace `datasets.load_dataset()` (fallback, 3 candidate IDs)
3. `RuntimeError` with full diagnostic + alternates (FRAMES, DialFact)

### Chunking

Two chunk types per session:
- **Memory item chunks** (one per `memory_item`): direct retrieval targets; tagged with `memory_ids` in provenance JSON.
- **Conversation chunks** (~2000-char sliding window, 200-char overlap): same strategy as `locomo_adapter.py`.

Memory item chunks are intentionally small (verbatim memory text) so the retrieval system
can pinpoint exact memory items rather than large conversation blobs.

### Evidence Linking

Three-path relevance determination for each QA pair:
1. Direct `memory_ids` match → chunks whose `chunk_id` ends with `_mem_{memory_id}`.
2. Content substring match → chunks containing the gold memory item's full text (case-insensitive, ≥20 chars).
3. Answer substring fallback (≥30-char answers) → chunks containing the answer text.

### Stratified Subset (n=100)

- 20 per type × 5 types = 100 target
- Within-type shuffle with `seed=42` (reproducible)
- Backfill from unknown-type queries if total < 100
- No `require_evidence` by default (preserves all QA pairs including harder cases)

---

## Resource Constraints (VPS)

BEIR TREC-COVID is running in tmux `beir-trec`. All MemoryBank eval runs in tmux `memorybank-eval`.

| Constraint | Value |
|---|---|
| Niceness | `nice -n 19` |
| I/O class | `ionice -c 3` |
| CPU cap | `cpulimit --limit=100` (1-core) |
| Load avg abort | 5-min load > 3.5 → `sys.exit(1)` |
| tmux session | `memorybank-eval` (never `beir-trec`) |

The `_check_load_avg()` function reads `/proc/loadavg` (Linux) or `uptime` (macOS)
and aborts before any network/CPU-heavy operation.

---

## VPS Deployment Commands

```bash
# 0. Create venv (VPS)
python3.11 -m venv /tmp/memorybank-adapter-venv
source /tmp/memorybank-adapter-venv/bin/activate
pip install "requests>=2.31"

# 1. Copy adapter to VPS
scp paper/publication/baselines/memorybank_adapter.py root@100.87.8.44:/root/memorybank-baselines/

# 2. Check load before starting
ssh root@100.87.8.44 "cat /proc/loadavg"

# 3. Smoke test in tmux (must be <3.5 load)
ssh root@100.87.8.44 "tmux new-session -d -s memorybank-eval \
  'cd /root/memorybank-baselines && nice -n 19 ionice -c 3 \
   python memorybank_adapter.py download-only \
     --clone-dir /tmp/memorybank-repo \
     --db /tmp/nox-mem-memorybank.db \
     --manifest /tmp/memorybank-manifest.json \
     --n 3 \
   2>&1 | tee /tmp/memorybank-smoke.log'"

# 4. Monitor
ssh root@100.87.8.44 "tmux attach -t memorybank-eval"
# (or) ssh root@100.87.8.44 "tail -f /tmp/memorybank-smoke.log"

# 5. Verify smoke test
ssh root@100.87.8.44 "cat /tmp/memorybank-manifest.json | python3 -m json.tool | head -40"

# 6. Full pipeline (after smoke test passes)
ssh root@100.87.8.44 "tmux send-keys -t memorybank-eval \
  'nice -n 19 ionice -c 3 python memorybank_adapter.py full \
     --clone-dir /tmp/memorybank-repo \
     --db /tmp/nox-mem-memorybank.db \
     --queries-output /tmp/memorybank-eval-queries.jsonl' Enter"

# 7. Vectorize TEMP DB (after full pipeline, requires nox-mem + env)
ssh root@100.87.8.44 \
  "set -a; source /root/.openclaw/.env; set +a; \
   nice -n 19 ionice -c 3 cpulimit --limit=100 -- \
   NOX_DB_PATH=/tmp/nox-mem-memorybank.db \
   nox-mem vectorize --all 2>&1 | tee /tmp/memorybank-vectorize.log"

# 8. Start nox-mem API on TEMP DB (separate shell / tmux pane)
# NOTE: This replaces the production API temporarily. Restore after eval.
ssh root@100.87.8.44 \
  "set -a; source /root/.openclaw/.env; set +a; \
   NOX_DB_PATH=/tmp/nox-mem-memorybank.db \
   node /root/.openclaw/workspace/tools/nox-mem/dist/index.js serve &"

# 9. Run eval
ssh root@100.87.8.44 "nice -n 19 ionice -c 3 cpulimit --limit=100 -- \
  python /root/memorybank-baselines/memorybank_adapter.py eval \
    --queries /tmp/memorybank-eval-queries.jsonl \
    --output /tmp/memorybank-results.jsonl \
    --api-url http://127.0.0.1:18802 \
  2>&1 | tee /tmp/memorybank-eval.log"

# 10. Pull results back to local
scp root@100.87.8.44:/tmp/memorybank-results.jsonl \
  paper/publication/results/memorybank-nox-results.jsonl
scp root@100.87.8.44:/tmp/memorybank-manifest.json \
  paper/publication/results/memorybank-manifest.json
```

---

## Output Files

| File | Location | Content |
|---|---|---|
| Adapter | `paper/publication/baselines/memorybank_adapter.py` | Main script |
| Spec | `paper/publication/baselines/MEMORYBANK-ADAPTER-SPEC.md` | This file |
| Manifest | `paper/publication/results/memorybank-manifest.json` | Dataset stats (post-run) |
| Eval queries | `/tmp/memorybank-eval-queries.jsonl` (VPS) | 100 stratified queries |
| Results | `paper/publication/results/memorybank-nox-results.jsonl` | Per-query metrics |
| Summary | `paper/publication/results/E04-memorybank-summary.md` | Aggregate report |

---

## Expected Metrics (Range Estimates)

MemoryBank is synthetic with explicit `memory_items` as ground truth.
Memory item chunks are verbatim retrieval targets — expect higher recall than LOCOMO.
Expected range based on dataset characteristics:

| Metric | Expected Range | Notes |
|---|---|---|
| nDCG@10 | 0.55–0.75 | Memory item chunks are short, exact-match friendly |
| MRR | 0.55–0.80 | Direct memory_id linking helps |
| Recall@10 | 0.60–0.85 | Small corpus → high recall ceiling |
| Precision@5 | 0.15–0.35 | Low absolute (1-2 relevant per query, k=5) |

Comparison baseline: nox-mem hybrid in-domain golden = 0.5213 nDCG@10 (n=50).
MemoryBank is OOD for nox-mem, so expect lower or comparable depending on query complexity.

---

## Failure Modes and Mitigations

| Failure | Indicator | Mitigation |
|---|---|---|
| GitHub repo gone | `git clone` exits non-zero + HF all fail | RuntimeError with FRAMES/DialFact fallback advice |
| Empty data dir | `_discover_session_files` returns 0 files | Scan full clone dir, log warning, try HF |
| No QA pairs | `total_qa == 0` | Log error, check JSON schema variant |
| >40% zero evidence | Warning log | Loosen `_MIN_EVIDENCE_LEN`, check `memory_ids` field |
| Load avg > 3.5 | `_check_load_avg` | `sys.exit(1)` before any expensive op |
| API not running | `requests.post` raises | Clear error with setup instructions |
| Zero queries evaluated | `AssertionError` in `evaluate_all` | Check eval_queries_jsonl is non-empty |

---

## Fallback Datasets (if MemoryBank also unavailable)

1. **FRAMES** (Google DeepMind, 2024) — HuggingFace: `google/frames-benchmark`
   - Long-context factual retrieval, public, HF-hosted
   - ~800 queries × multi-hop reasoning

2. **DialFact** (Gupta et al., 2022) — conversational fact-checking
   - Public, HF search: `dial_fact` or `DialFact`
   - Dialogue-grounded factual claims with evidence references

Both require a new adapter, but ~70% of `memorybank_adapter.py` is reusable.

---

## Paper §5.2 Prose Template

Once metrics are obtained, drop into §5.2:

> "We evaluate on MemoryBank (Zhong et al., 2023), a synthetic conversational memory benchmark spanning {N} daily sessions with {M} QA pairs across five question types (factual recall, temporal reasoning, sentiment analysis, preference inference, and event summarization). NOX-Mem hybrid retrieval achieves nDCG@10={X:.3f} (MRR={Y:.3f}, R@10={Z:.3f}) on a stratified 100-query subset (20 per type, seed=42), demonstrating {comparison vs in-domain} cross-dataset generalization on episodic conversational memory."

---

## Relation to Other Experiments

| Experiment | Corpus | Status |
|---|---|---|
| In-domain golden | nox-mem production (n=60) | Done — nDCG=0.5213 |
| BEIR TREC-COVID | 171K biomedical abstracts | Running (tmux `beir-trec`) |
| **MemoryBank** | ~40 synthetic daily sessions | **Ready to deploy** |
| LOCOMO | Stanford human dialogues | Failed — HF 401 (E04) |
