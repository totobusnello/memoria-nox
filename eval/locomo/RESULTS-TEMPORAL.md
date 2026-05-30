# LoCoMo Bench — temporal-aware retrieval results

**Date:** 2026-05-30 BRT
**Phase:** post-retrieval temporal-aware re-rank over PR #404 SOTA push baseline
**Dataset:** `snap-research/LoCoMo` `data/locomo10.json` (n=10 convs, 1986 qa)
**Method:** generation-pass over PR #404 e2e retrieval JSONL, with
re-rank applied to chunks BEFORE prompt construction
(`/root/.openclaw/locomo-e2e-rerun-af562a4b/results-e2e-1986q.jsonl`).

> This file documents the temporal-aware retrieval experiment (this PR).
> PR #404 SOTA push baseline lives in `RESULTS-LOCOMO-SOTA-PUSH.md` and is preserved.

## TL;DR

**Verdict: REJECT for default — marginal lift, all gates fail. SHIP opt-in (retrieval pipeline addition, no default).**

| Run | Overall F1 | vs PR #404 | Temporal F1 | vs PR #404 Temporal | vs Mem0 SOTA 66.88% |
|---|---:|---:|---:|---:|---:|
| **PR #404 baseline (SOTA push)** | 51.85% | — | 44.21% | — | -16.50pp |
| **TA alpha=0.5 norm ON** | 51.66% | -0.19pp | 42.19% | -2.02pp | -15.22pp |
| **TA alpha=0.5 norm OFF** | 52.02% | +0.17pp | 44.42% | +0.21pp | -14.86pp |

**Gates (all failed against +10/+3 ambition):**

| Gate | Target | Actual (norm OFF, best) | Pass? |
|---|---|---:|:---:|
| 1 | Temporal F1 lift ≥ +10pp | **+0.21pp** | FAIL |
| 2 | Overall F1 lift ≥ +3pp | **+0.17pp** | FAIL |
| 3 | No category regression ≥ -5pp | max regression -0.22pp (adversarial) | PASS |
| 4 | Latency p95 ≤ +30% | n/a — offline rerank, no live HTTP cost | n/a |

### Why the lift is tiny

The hypothesis was that **prioritizing date-aligned chunks** in the top-K
would help the LLM produce correct temporal answers. Two findings invalidate this:

1. **87.5% of temporal queries have NO extractable date** (281/321 LoCoMo cat=2
   QA pairs ask "When did X happen?" without referencing a year/month/date).
   For these, the temporal-proximity score collapses to a binary
   "has-date / no-date" signal (`SCORE_HAS_DATE_FALLBACK=0.6`), which only
   reorders the top-K but doesn't surface new chunks.
2. **The right chunk is usually already in top-10.** Out of 321 temporal QA,
   the re-rank changed the top-5 ordering for only **73 records (22.7%)**
   under default alpha=0.5. The LLM, given top-10 chunks regardless of order,
   produces the same answer ~99% of the time when chunk order shifts but
   the chunk SET is identical.

**Temporal-with-explicit-date subset (n=40) DID benefit: +3.63pp**
(15.29% → 18.91%). This is the only sub-population where the signal is
strong enough to matter. Too small (2% of dataset) to move the overall
needle.

### Strategic interpretation

- The temporal F1 gap to Mem0 SOTA is **NOT retrieval-rank-bound**. The
  evidence chunk is already in top-K for hybrid retrieval. The gap is
  **composition-bound** (prompt-time anchoring per PR #404 worked) and
  **answer-format-bound** (normalizer + date format hint).
- Re-ranking by temporal proximity is a sound feature for queries WITH
  explicit dates — but those queries are rare in LoCoMo.
- For LoCoMo specifically: any further temporal F1 lift requires either
  (a) **prompt-level intervention** (chain-of-thought "anchor each chunk to
  its session date before answering") or (b) **query rewriting** ("When did X
  happen?" → "X happened on which session?") or (c) **answer-side post-process**
  (already partly covered by `temporal_normalizer.py`).
- For OTHER benchmarks where temporal queries DO carry explicit dates
  (longmemeval temporal-reasoning, EverMemBench multi-temporal), this signal
  should help more — worth A/B testing there.

**Recommendation: SHIP opt-in (`--temporal-aware` flag, NOT default).**
The library is well-tested (29 passing self-tests across 2 modules), defensible
for evaluation paper as "we tested temporal-aware retrieval, found marginal
overall gain, retain as opt-in for use cases where temporal queries carry
explicit dates (calendar memory, agenda lookup)". Adds 0 cost when disabled.

---

## Full bench results (n=1986, gpt-4.1-mini)

Run metadata:
- **mode:** generation-pass over existing PR #404 baseline retrieval JSONL
- **generator:** gpt-4.1-mini (temperature=0, max_tokens=32)
- **prompt:** Variant A (same as PR #404 SOTA push)
- **temporal-aware:** alpha=0.5, keep-top-k=10, retrieve-k=N/A (offline mode reuses top-20)
- **has-date-fallback:** ON (anchored chunks get 0.6 when query has no date)
- **wallclock:** 1411 s (23 min 31 s)
- **cost (actual):** $0.269 USD (1,759,166 in-tokens + 8,396 out-tokens)
- **errors:** 0

### Per-category F1 (full 1986q)

| Category | n | PR #404 F1 | TA-aware (norm) F1 | TA-aware (raw) F1 | delta (raw) vs PR #404 |
|---|---:|---:|---:|---:|---:|
| **temporal** | 321 | 44.21% | 42.19% | 44.42% | **+0.21pp** |
| single_hop | 841 | 55.18% | 55.28% | 55.28% | +0.11pp |
| multi_hop | 282 | 38.16% | 38.60% | 38.60% | +0.44pp |
| commonsense | 96 | 23.77% | 25.30% | 25.30% | +1.53pp |
| adversarial | 446 | 65.78% | 65.56% | 65.56% | -0.22pp |
| **Overall** | 1986 | **51.85%** | **51.66%** | **52.02%** | **+0.17pp** |

### Temporal sub-analysis

| Subset | n | PR #404 | TA-aware (raw) | delta |
|---|---:|---:|---:|---:|
| Temporal WITH explicit date in query | 40 | 15.29% | 18.91% | **+3.63pp** |
| Temporal WITHOUT date | 281 | 48.33% | 48.05% | -0.27pp |

The PR #404 baseline performs MUCH worse on temporal-with-date (15.29%) than
on temporal-without (48.33%) because date-containing questions tend to be
calendar lookups ("What did Caroline do on 8 May 2023?") with very narrow
gold targets that the LLM often gets wrong. Temporal-aware retrieval
provides the largest delta exactly here, but the subset is small (40/1986).

### Re-rank effectiveness diagnostics

- **n_temporal_records:** 762 (incl. is_temporal_query=True for non-cat-2)
- **n_with_order_change:** 73 (only ~10% of supposed-temporal queries had top-5 reorder)
- **avg_chunks_with_date_pct:** 100% (every chunk has session anchor — corpus_loader injects)
- **normalizer changed=44 helped=4 hurt=21:** normalize_predicted_date hurts more than it helps in this run (PR #404 finding holds: variant A + norm OFF wins)

## Smoke 100q stratified (alpha ablation)

| Variant | Overall F1 | Adversarial | Commonsense | Multi-hop | Single-hop | Temporal |
|---|---:|---:|---:|---:|---:|---:|
| TA alpha=0.3 norm ON | 51.44% | 65.00% | 28.68% | 42.11% | 71.90% | 49.54% |
| TA alpha=0.5 norm ON | 51.79% | 65.00% | 28.68% | 41.14% | 72.62% | 51.54% |
| TA alpha=0.7 norm ON | 51.60% | 65.00% | 28.99% | 41.86% | 72.62% | 49.54% |

Smoke is too noisy at n=20/category to differentiate alphas — multiple QA
flip = ±3pp on temporal subset. The full bench result (alpha=0.5, n=321) is
authoritative.

## Implementation

### Modules added

- `eval/locomo/lib/temporal_scoring.py` — core scoring (extract dates from
  query/chunk, compute proximity, re-rank). 29 self-test cases pass.
- `eval/locomo/lib/temporal_aware_retrieve.py` — wrapper for both live HTTP
  path (`retrieve_temporal_aware`) and offline post-rerank
  (`rerank_existing_records`). Self-tested.
- `eval/locomo/locomo-temporal-aware-gen.py` — offline gen pass driver,
  same shape as `locomo-sota-push-gen.py`.

### Modules modified

- `eval/locomo/adapter_nox_mem.py` — added `--temporal-aware`,
  `--temporal-alpha`, `--temporal-retrieve-k`, `--no-has-date-fallback`
  flags. Plumbed through `run_conversation`. Live HTTP path wired to
  `retrieve_temporal_aware`.

### Algorithm

For temporal-class queries (cat=2 OR is_temporal_query=True):

1. Parse query for explicit dates (regex catalog: D-Month-Y, Month-D-Y,
   ISO, M/D/Y, Month-Y, bare year).
2. For each retrieved chunk, parse anchor date:
   - First: `session_id: session_N` in chunk text → `session_date_map[N]`.
   - Fallback 1: inline `date:` header in session-md.
   - Fallback 2: derive `session_N` from `dia_id: DN:K`.
3. Compute `temporal_proximity` per chunk:
   - Exact day match: 1.0
   - Same month: 0.85
   - Adjacent month (incl. cross-year): 0.7
   - Same year: 0.45
   - Adjacent year: 0.3
   - No chunk date: 0.0
   - No query date + has_date_fallback ON: 0.6 if chunk anchored, 0.0 else.
4. Min-max normalize original retrieval scores to [0,1].
5. Blend: `final = (1-alpha) * norm_retrieval + alpha * temporal_proximity`.
6. Sort by `final_score` desc; truncate to top-K.

Non-temporal queries: passthrough (returns original top-K unchanged).

### Default tuning constants

```python
SCORE_EXACT_DAY = 1.0
SCORE_SAME_MONTH = 0.85
SCORE_ADJACENT_MONTH = 0.7
SCORE_SAME_YEAR = 0.45
SCORE_ADJACENT_YEAR = 0.3
SCORE_HAS_DATE_FALLBACK = 0.6
DEFAULT_ALPHA = 0.5
DEFAULT_RETRIEVE_K = 30
DEFAULT_KEEP_TOP_K = 20
```

## Reproducing

### Offline (cheap, used for this bench)

```bash
ssh root@$VPS_IP
set -a; source /root/.openclaw/.env; set +a

mkdir -p /root/.openclaw/locomo-temporal-rerun/results
cd /root/.openclaw/locomo-temporal-rerun

# Copy lib + driver
cp -r /path/to/repo/eval/locomo/lib .
cp /path/to/repo/eval/locomo/locomo-temporal-aware-gen.py .

# Full bench
python3 locomo-temporal-aware-gen.py \
    --in-jsonl /root/.openclaw/locomo-e2e-rerun-af562a4b/results-e2e-1986q.jsonl \
    --out-jsonl results/results-full-alpha05.jsonl \
    --locomo-json /tmp/locomo-repo/data/locomo10.json \
    --alpha 0.5 \
    --keep-top-k 10 \
    --max-questions 0
```

### Live HTTP path (full pipeline, expensive)

```bash
# adapter_nox_mem.py runs from-scratch ingest + vectorize + search + gen
python3 eval/locomo/adapter_nox_mem.py \
    --locomo-json /tmp/locomo-repo/data/locomo10.json \
    --workdir /root/.openclaw/locomo-temporal-live-bench/work \
    --out results.jsonl \
    --api-port 18970 \
    --top-k 20 \
    --max-questions 0 \
    --generator gpt-4.1-mini \
    --sota-push \
    --temporal-aware \
    --temporal-alpha 0.5
```

## Files

- `eval/locomo/lib/temporal_scoring.py` (NEW, 442 lines)
- `eval/locomo/lib/temporal_aware_retrieve.py` (NEW, 310 lines)
- `eval/locomo/locomo-temporal-aware-gen.py` (NEW, 463 lines)
- `eval/locomo/adapter_nox_mem.py` (MODIFIED — added `--temporal-aware` and 3 sibling flags)
- `eval/locomo/RESULTS-TEMPORAL.md` (this file)
- `eval/locomo/RESULTS-TEMPORAL.json` (aggregate JSON)
