# LOCOMO Adapter Spec — W2 Sprint

**Paper section:** §5.2 Table 5 — Conversational long-context memory benchmark
**Reference:** Maharana et al. (2024). LOCoMo: Long Context Modular Memory for LLMs. arXiv:2402.17753
**Adapter:** `locomo_adapter.py`

---

## Dataset Source

| Field | Value |
|---|---|
| HuggingFace dataset | `snap-stanford/locomo` |
| Split | `test` (fallback: first available split) |
| GitHub (alt source) | https://github.com/snap-stanford/locomo |
| Size | ~10 sessions, ~350 QA pairs total (~10 MB) |
| License | CC BY 4.0 |

LOCOMO dataset structure per row (session):
- `session_id` — int or string
- `conversation` — list of turn dicts: `{speaker, text, time, observation[]}`
- `qa` — list of QA dicts: `{question, answer, type, evidence[]}`

Question types: `single_hop`, `multi_hop`, `temporal_reasoning`, `open_domain`

---

## Subset Selection Logic

**Target: 100 queries = 25 per question type × 4 types**

Strategy: first-n (deterministic by dataset order, no random sampling).

1. Normalise raw type string (handles snake_case / space / hyphen variants).
2. Map `temporal_reasoning` → `temporal` (canonical short form).
3. For each of 4 canonical types: take first 25 QA records in session order.
4. If a type has <25 examples: include all available (logged as warning).
5. Total subset: ≤100 queries (can be <100 if dataset has thin type coverage).

Rationale for first-n over random: LOCOMO sessions are ordered by session_id
(effectively random across sessions), so first-n is reproducible without a seed
and avoids hyperparameter tuning concerns for the paper.

---

## Chunking Strategy

Mirrors nox-mem's production chunking:

| Parameter | Value |
|---|---|
| Target chunk size | 2000 characters |
| Overlap | 200 characters |
| Boundary preference | Paragraph (`\n\n`) within last 300 chars of buffer |

Each turn is rendered as: `[timestamp] Speaker: text\n  [obs] observation_text`
Observation sub-events (activities, locations) are included because they contain
factual content that may be evidence for QA pairs.

Each chunk records `turn_start` / `turn_end` indices for provenance.

---

## Relevance Criterion

A chunk is **relevant** to a QA pair if it contains at least one evidence span
(substring match, case-insensitive, minimum 20 chars).

Evidence spans come from LOCOMO's `qa[].evidence` field (raw conversation substrings).

Expected evidence coverage: ~60-80% of QA pairs will have at least one matching
chunk (remaining ~20-40% have evidence in sub-20-char phrases or exact timestamps).

---

## Expected Runtime

| Stage | Time |
|---|---|
| Download (first time) | 15-60 s (HuggingFace, ~10 MB) |
| Download (cached) | <3 s |
| Chunk + index (build-db) | 5-15 s (~200-400 chunks) |
| FTS5 dry-run (3 queries) | <2 s |
| Vectorize TEMP DB (VPS) | 10-20 min (Gemini, ~300 chunks) |
| Full eval (100 queries, HTTP API) | 3-10 min |
| Total (excl. vectorize) | <30 s for smoke test |

---

## Commands

### Smoke test (laptop, <30 s)

```bash
source /tmp/locomo-venv/bin/activate
python locomo_adapter.py download-only \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db \
    --manifest /tmp/locomo-manifest.json \
    --n 3
```

### Full eval pipeline (VPS)

```bash
# 1. Build TEMP DB
python locomo_adapter.py build-db \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db

# 2. Extract 100 eval queries
python locomo_adapter.py convert-queries \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db \
    --output /tmp/locomo-eval-queries.jsonl

# 3. Vectorize TEMP DB (VPS only, requires .env)
set -a; source /root/.openclaw/.env; set +a
NOX_DB_PATH=/tmp/nox-mem-locomo.db nox-mem vectorize --all
curl http://127.0.0.1:18802/api/health | jq .vectorCoverage

# 4. Restart nox-mem API pointing at TEMP DB (separate tmux window)
NOX_DB_PATH=/tmp/nox-mem-locomo.db node dist/index.js serve

# 5. Run evaluation
python locomo_adapter.py eval \
    --queries /tmp/locomo-eval-queries.jsonl \
    --output /tmp/locomo-results.jsonl \
    --api-url http://localhost:18802

# 6. Generate comparison table
python locomo_adapter.py compare \
    --nox /tmp/locomo-results.jsonl \
    --csv /tmp/locomo-comparison.csv
```

### End-to-end shortcut (steps 1-4)

```bash
python locomo_adapter.py full \
    --cache-dir ~/.cache/locomo \
    --db /tmp/nox-mem-locomo.db \
    --queries-output /tmp/locomo-eval-queries.jsonl
```

---

## Output Files

| File | Description |
|---|---|
| `/tmp/nox-mem-locomo.db` | TEMP SQLite DB (chunks + FTS5 index) |
| `/tmp/locomo-manifest.json` | Smoke test artifact: session/QA/chunk stats |
| `/tmp/locomo-eval-queries.jsonl` | 100 eval queries (stratified subset) |
| `/tmp/locomo-results.jsonl` | nox-mem per-query results |
| `/tmp/locomo-comparison.csv` | Cross-system table for paper |

Copy results to the aggregator:
```bash
cp /tmp/locomo-results.jsonl \
   paper/publication/results/locomo-nox-results.jsonl
```

---

## Integration Notes for Paper §5.2 Table 5

Table 5 expected format:

```
System          | nDCG@10 | MRR   | R@10  | P@5
----------------|---------|-------|-------|------
BM25 (Pyserini) |  ?.???  | ?.??? | ?.??? | ?.???
nox-mem hybrid  |  ?.???  | ?.??? | ?.??? | ?.???
```

Citation block for §5.2:
> "We evaluate on n=100 LOCOMO questions [Maharana et al., 2024], stratified
> 25 per question type (single-hop, multi-hop, temporal, open-domain). Sessions
> are chunked into ~2000-character segments with 200-character overlap. A chunk
> is marked relevant if it contains any of the gold evidence spans (min. 20 chars,
> case-insensitive substring match). Results are averaged across all 100 queries."

**Key differences vs BEIR (§5.3):**
- Corpus IS the conversation history (episodic memory, not external docs)
- Relevance via evidence span containment (not explicit qrel judgments)
- Questions test temporal/multi-hop reasoning over long conversational context
- Smaller corpus (~200-400 chunks vs 50K BEIR-COVID) — vectorize is fast

**Known limitation to acknowledge in paper:**
Evidence-span matching may under-count relevant chunks if evidence appears in
chunks partially overlapping turn boundaries. This is bounded by the 200-char
overlap and documented in the adapter's chunk_session docstring.

---

## Prerequisites

```bash
python3.11 -m venv /tmp/locomo-venv
source /tmp/locomo-venv/bin/activate
pip install "datasets>=2.19" "requests>=2.31"
```

No GPU dependencies. CPU-only. No BEIR or sentence-transformers required.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `snap-stanford/locomo` 404 | Dataset may require `datasets>=2.20`; try `pip install -U datasets` |
| Split `test` not found | Adapter falls back to first available split automatically |
| Evidence coverage <50% | Lower `_MIN_EVIDENCE_LEN` from 20 to 10 in adapter constants |
| FTS5 dry-run returns 0 hits | Verify DB was built with `build-db` before `download-only` |
| Vectorize fails silently | `set -a; source /root/.openclaw/.env; set +a` before running |
