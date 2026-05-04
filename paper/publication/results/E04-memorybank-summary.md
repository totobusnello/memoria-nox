# E04 — MemoryBank Evaluation: Adapter Ready, Awaiting VPS Execution

**Date:** 2026-05-04  
**Sprint:** W2  
**Paper section:** §5.2 Table 5 — Conversational episodic memory benchmark  
**Status:** Adapter written + deployed to local repo. VPS execution blocked (Bash disabled in agent session).

---

## Deliverables Created

| File | Status |
|---|---|
| `baselines/memorybank_adapter.py` | Done — 900+ lines, full pipeline |
| `baselines/MEMORYBANK-ADAPTER-SPEC.md` | Done — deployment commands, schema, failure modes |
| `results/memorybank-manifest.json` | Pending VPS run |
| `results/memorybank-nox-results.jsonl` | Pending VPS run |
| This summary | Partial — metrics TBD |

---

## Dataset Availability

GitHub repo `https://github.com/zhongwanjun/MemoryBank-SiliconFriend` was **publicly available** as of the last check (2026-05-04). The adapter does a `git clone --depth=1` as primary strategy. HuggingFace fallback (3 candidate IDs) activates if clone fails.

---

## VPS Execution: Exact Commands

Check load first:
```bash
ssh root@100.87.8.44 "cat /proc/loadavg"
```
Abort if 5-min avg > 3.5 (BEIR priority).

Copy adapter + run smoke test:
```bash
scp paper/publication/baselines/memorybank_adapter.py \
    root@100.87.8.44:/root/memorybank-baselines/

ssh root@100.87.8.44 "mkdir -p /root/memorybank-baselines && \
  python3.11 -m venv /tmp/memorybank-venv && \
  /tmp/memorybank-venv/bin/pip install -q requests && \
  tmux new-session -d -s memorybank-eval \
  'nice -n 19 ionice -c 3 \
   /tmp/memorybank-venv/bin/python /root/memorybank-baselines/memorybank_adapter.py download-only \
     --clone-dir /tmp/memorybank-repo \
     --db /tmp/nox-mem-memorybank.db \
     --manifest /tmp/memorybank-manifest.json \
     --n 3 \
   2>&1 | tee /tmp/memorybank-smoke.log; echo DONE'"
```

Monitor:
```bash
ssh root@100.87.8.44 "tail -f /tmp/memorybank-smoke.log"
```

Full pipeline after smoke passes:
```bash
ssh root@100.87.8.44 "nice -n 19 ionice -c 3 \
  /tmp/memorybank-venv/bin/python /root/memorybank-baselines/memorybank_adapter.py full \
    --clone-dir /tmp/memorybank-repo \
    --db /tmp/nox-mem-memorybank.db \
    --queries-output /tmp/memorybank-eval-queries.jsonl \
  2>&1 | tee /tmp/memorybank-full.log"
```

Vectorize + eval (requires nox-mem env + API):
```bash
ssh root@100.87.8.44 "set -a; source /root/.openclaw/.env; set +a; \
  NOX_DB_PATH=/tmp/nox-mem-memorybank.db \
  nice -n 19 ionice -c 3 \
  nox-mem vectorize --all 2>&1 | tee /tmp/memorybank-vectorize.log"

# Start API on TEMP DB (kills production API temporarily)
ssh root@100.87.8.44 "set -a; source /root/.openclaw/.env; set +a; \
  NOX_DB_PATH=/tmp/nox-mem-memorybank.db \
  node /root/.openclaw/workspace/tools/nox-mem/dist/index.js serve &"

ssh root@100.87.8.44 "nice -n 19 ionice -c 3 \
  /tmp/memorybank-venv/bin/python /root/memorybank-baselines/memorybank_adapter.py eval \
    --queries /tmp/memorybank-eval-queries.jsonl \
    --output  /tmp/memorybank-results.jsonl \
    --api-url http://127.0.0.1:18802 \
  2>&1 | tee /tmp/memorybank-eval.log"
```

Pull results:
```bash
scp root@100.87.8.44:/tmp/memorybank-results.jsonl \
    paper/publication/results/memorybank-nox-results.jsonl
scp root@100.87.8.44:/tmp/memorybank-manifest.json \
    paper/publication/results/memorybank-manifest.json
```

---

## Metrics (TBD — update after VPS run)

| Metric | nox-mem hybrid (MemoryBank) | nox-mem hybrid (in-domain, n=50) |
|---|---|---|
| nDCG@10 | **[TBD]** | 0.5213 |
| MRR | **[TBD]** | [in-domain baseline] |
| Recall@10 | **[TBD]** | [in-domain baseline] |
| Precision@5 | **[TBD]** | [in-domain baseline] |

### Per-Type Breakdown (TBD)

| Type | nDCG@10 | N |
|---|---|---|
| factual_recall | TBD | 20 |
| temporal_reasoning | TBD | 20 |
| sentiment_analysis | TBD | 20 |
| preference_inference | TBD | 20 |
| event_summary | TBD | 20 |

---

## §5.2 Prose Template (fill after run)

> "On MemoryBank (Zhong et al., 2023), a synthetic multi-session conversational memory benchmark with five question types, NOX-Mem hybrid retrieval achieves nDCG@10=[X] (MRR=[Y], R@10=[Z]) on a stratified 100-query subset (20 per type, seed=42, n=[N] sessions)."

---

## BEIR Session Check

The `_check_load_avg()` guard in the adapter reads `/proc/loadavg` and aborts at >3.5 (5-min).
**This runs before every expensive operation** — BEIR priority is enforced at the code level.
The adapter uses tmux `memorybank-eval` and will never touch `beir-trec`.

---

## Data Quirks to Watch

1. **Schema variants** — The adapter handles 8+ field name variants (`qa_pairs`/`QA`/`questions`, `conversations`/`dialogue`, `content`/`text`, etc.). Log at DEBUG level which variant was found.
2. **Memory item count** — If sessions have very few `memory_items` (1-2 each), corpus is small → high recall ceiling; nDCG may be inflated vs BEIR.
3. **evidence_coverage_pct** — Check manifest. If <60% of QA pairs link to evidence chunks, the evidence linking may need `require_evidence=False` (default) to preserve full n=100.
4. **Synthetic vs human** — MemoryBank is LLM-generated conversations. As an out-of-domain test it validates cross-distribution robustness but is less ecologically valid than LOCOMO would have been.

---

## If MemoryBank GitHub Also Fails

Write `E04-memorybank-LAUNCH-FAILED.md` and escalate with:
- **FRAMES** (Google DeepMind, 2024): `pip install datasets; datasets.load_dataset('google/frames-benchmark')`
- **DialFact** (Gupta et al., 2022): search HuggingFace `dial_fact`

~70% of `memorybank_adapter.py` is reusable for either fallback.
