# §6.4 Per-Category Mapping — Audit Document

**Purpose:** Destravar a tabela §6.4 "Per-category breakdown" do paper, que estava 100% `[deferred]`.
This document traces every bucket assignment to a native dataset field and records the measured
query distribution used to determine which §6.4 cells are `n/a`.

Generated: 2026-06-28. Regenerate with `python scripts/build_categorized_queries.py`.

---

## 1. Native Field Schemas

### 1.1 LoCoMo (`cache/raw/locomo10.json`)

- Top-level: list of 10 conversations
- Each conversation: `{ "sample_id", "qa": [...], "conversation", "event_summary", ... }`
- Each QA record: `{ "question", "answer", "evidence", "category", ["adversarial_answer"] }`
- **Category field:** `qa["category"]` — integer 1–5 (stored as int after `json.load`)
- **Evidence field:** `qa["evidence"]` — Python list of dia_id strings (e.g. `["D1:3"]`)
  - Some items are compound due to upstream data quirks (e.g. `"D8:6; D9:17"`)
  - Gold construction: split on `[;\s]+`, filter `D\d+:\d+`, normalize leading zeros, prefix `{sample_id}::`
- Total QA records in raw: 1986
- After GOLD-MATCH GUARD: **1982 emitted** (4 guard_miss — compound/malformed evidence with no corpus hit)

### 1.2 LongMemEval (`cache/raw/longmemeval_oracle.json`)

- Top-level: list of 500 question records
- Each record: `{ "question_id", "question_type", "question", "answer", "question_date", "haystack_session_ids", "haystack_sessions", "answer_session_ids" }`
- **Category field:** `question["question_type"]` — string
- **Gold field:** `question["answer_session_ids"]` — list of session_id strings
- Total records: 500; all 500 pass GOLD-MATCH GUARD (0 guard_miss)
- Includes 24 abstention-style questions (answer_session_ids contain `_abs_` segments); all matched in corpus

---

## 2. Category Mapping Table

### 2.1 LoCoMo category integer → §6.4 bucket

Source: `eval/locomo/dry-run-sample.json` `category_name` field (authoritative, used by the harness).
Cross-check: category 5 = 100% overlap with records that have `adversarial_answer` field (n=446, verified).

| Native `category` | §6.4 bucket  | n (raw) | Notes                                      |
|-------------------|--------------|--------:|--------------------------------------------|
| 1                 | single-hop   |     282 | single-session, single-evidence retrieval  |
| 2                 | multi-hop    |     321 | multi-evidence, cross-session              |
| 3                 | temporal     |      96 | time-anchored queries                      |
| 4                 | open-domain  |     841 | common-knowledge / long-horizon retrieval  |
| 5                 | adversarial  |     446 | `adversarial_answer` field always present  |
| —                 | numeric      |       0 | **No native numeric field — n/a**          |

### 2.2 LongMemEval `question_type` string → §6.4 bucket

Source: `longmemeval_oracle.json` `question_type` field (all 500 records).

| Native `question_type`     | §6.4 bucket  | n (raw) | Notes                                              |
|----------------------------|--------------|--------:|----------------------------------------------------|
| single-session-user        | single-hop   |      70 | single session, user-perspective query             |
| single-session-assistant   | single-hop   |      56 | single session, assistant-perspective; same structure |
| single-session-preference  | single-hop   |      30 | single session, preference recall                  |
| multi-session              | multi-hop    |     133 | evidence spans ≥2 sessions                         |
| temporal-reasoning         | temporal     |     133 | requires temporal ordering / dating                |
| knowledge-update           | adversarial  |      78 | **AMBIGUOUS — see §3**                             |
| —                          | open-domain  |       0 | **No native open-domain field — n/a**              |
| —                          | numeric      |       0 | **No native numeric field — n/a**                  |

---

## 3. Ambiguity Note: `knowledge-update` → `adversarial`

LME `knowledge-update` (n=78): tests whether the system tracks belief changes over time
(user states X, later corrects to Y; system must retrieve Y, not X).

This type has two competing mappings:
- **→ adversarial** (chosen): the prior state is a distractor; the core challenge is distractor
  rejection, which matches LoCoMo cat-5 semantics ("adversarial_answer" = the wrong answer
  the system must not return).
- **→ temporal**: the update introduces a temporal dependency (before/after); there is a time
  component to the reasoning.
- **NOT → open-domain**: the question requires memory context, not general world knowledge.

Chosen mapping: **adversarial**. Rationale: the retrieval failure mode (returning stale belief)
is structurally identical to LoCoMo adversarial (returning the planted wrong answer). The paper
should add a footnote acknowledging this imperfect cross-dataset alignment.

If the paper reviewer requests a different mapping, `lib/category_labeler.py` has a single-line
change at `LME_QUESTION_TYPE_MAP["knowledge-update"]`.

---

## 4. GOLD-MATCH GUARD: LoCoMo

4 QA records were dropped (guard_miss=4) because no evidence item resolved to a corpus chunk ID.
These are data quality issues in the upstream LoCoMo dataset, not pipeline bugs.

The 9 raw "miss" evidence items (before collapsing by QA) break down as:

| Sample   | Raw evidence item         | Resolved fragments         | In corpus? |
|----------|---------------------------|----------------------------|------------|
| conv-26  | `D8:6; D9:17`             | `D8:6`, `D9:17`            | Both ✓ (fixed by split) |
| conv-42  | `D10:19`                  | `D10:19`                   | Miss — corpus ends at D10:16 |
| conv-42  | `D`                       | (no valid fragments)       | Miss — malformed |
| conv-43  | `D:11:26`                 | (no valid fragments — triple colon) | Miss |
| conv-47  | `D4:36`                   | `D4:36`                    | Miss — not in corpus |
| conv-49  | `D9:1 D4:4 D4:6`         | `D9:1`, `D4:4`, `D4:6`    | All ✓ (fixed by split) |
| conv-49  | `D22:1 D22:2 D9:10 D9:11`| `D22:1`, `D22:2`, `D9:10`, `D9:11` | All ✓ (fixed by split) |
| conv-49  | `D21:18 D21:22 D11:15 D11:19` | (all 4)               | All ✓ (fixed by split) |
| conv-50  | `D30:05`                  | `D30:5` (normalized)       | ✓ (fixed by normalization) |

Net result: split + normalization rescued 5 of the 9 raw miss items. The 4 QAs with all-miss
evidence (conv-42 ×2, conv-43, conv-47) are excluded from the output JSONL.

---

## 5. Measured Distribution (Full Dataset)

Run: `python scripts/build_categorized_queries.py` on 2026-06-28.

| §6.4 bucket  | LoCoMo (n=1982) | LME (n=500) | Notes                               |
|--------------|----------------:|------------:|-------------------------------------|
| single-hop   |             282 |         156 |                                     |
| multi-hop    |             321 |         133 |                                     |
| temporal     |              92 |         133 |                                     |
| adversarial  |             446 |          78 | LME: knowledge-update (ambiguous)   |
| open-domain  |             841 |         n/a | no native field in LME              |
| numeric      |             n/a |         n/a | no native field in either dataset   |
| **TOTAL**    |        **1982** |     **500** |                                     |

**§6.4 cells that are n/a (no native field):**
- `LoCoMo × numeric`
- `LME × open-domain`
- `LME × numeric`

All remaining cells have n >> 10, so no additional n/a from the threshold rule when
running the full query set.

---

## 6. Critical Warning: Natural Order + --limit 100

The canonical 2026-06-15 run used `--limit 100` per dataset. The categorized JSONL files
are ordered by conversation/question source order, NOT stratified. Running with `--limit 100`
gives the following distribution:

### LoCoMo (first 100 of 1982 in natural order)

| §6.4 bucket  | n in first-100 | §6.4 status    |
|--------------|---------------:|----------------|
| single-hop   |             32 | OK             |
| multi-hop    |             37 | OK             |
| temporal     |             11 | OK (barely)    |
| adversarial  |              0 | **n/a** ← adversarial first appears at line 150 |
| open-domain  |             20 | OK             |

### LME (first 100 of 500 in natural order)

| §6.4 bucket  | n in first-100 | §6.4 status    |
|--------------|---------------:|----------------|
| temporal     |             60 | OK             |
| multi-hop    |             40 | OK             |
| single-hop   |              0 | **n/a** ← first appears at line 200 |
| adversarial  |              0 | **n/a** ← first appears at line 122 |

**Implication:** the canonical n=100 run cannot produce meaningful per-category metrics
for `LoCoMo × adversarial`, `LME × single-hop`, or `LME × adversarial`.

---

## 7. Recommendations for the §6.4 Run

**Option A — Run all queries (preferred for paper):**
```bash
# From eval/q4-comparison/
python runner.py \
  --systems nox_mem,mem0,agentmemory \
  --datasets locomo \
  --queries-file cache/queries-locomo-categorized.jsonl
  # no --limit → runs all 1982 LoCoMo queries

python runner.py \
  --systems nox_mem,mem0,agentmemory \
  --datasets longmemeval \
  --queries-file cache/queries-longmemeval-categorized.jsonl
  # no --limit → runs all 500 LME queries
```

**Option B — Stratified sample n=100 (faster, preserves all cells):**
Build a separate script that samples `min(n_available, target_per_cat)` per category
from the categorized JSONL, ensuring n≥10 per active cell. Minimum target per category: 20
(to give stable nDCG@10 estimates).

**Option C — Use a larger limit that clears all categories:**
- LoCoMo: `--limit 500` gives adversarial=112, temporal=21, all cells ≥ 10
- LME: `--limit 250` gives single-hop=50, adversarial=28, all cells ≥ 10

Recommended: **Option A** (full run) for the paper's final §6.4 numbers. Option C is
the fastest path to all-cells-valid if pod time is constrained.

---

## 8. Output Files

| File | Queries | Description |
|------|--------:|-------------|
| `cache/queries-locomo-categorized.jsonl` | 1982 | LoCoMo QAs with category_name + validated gold_chunk_ids |
| `cache/queries-longmemeval-categorized.jsonl` | 500 | LME questions with category_name + validated gold_chunk_ids |

Each line format:
```json
{
  "question_id": "conv-26::q0",
  "dataset": "locomo",
  "category_name": "multi-hop",
  "category_native": "2",
  "question": "...",
  "gold_chunk_ids": ["conv-26::D1:3"]
}
```

The runner picks up `category_name` via `_to_record()` → `QueryRecord.category`.

---

## 9. Source Files

| File | Role |
|------|------|
| `lib/category_labeler.py` | Pure mapping functions + MAPPING TABLE as module docstring |
| `scripts/build_categorized_queries.py` | Builder + GOLD-MATCH GUARD + distribution printer |
| `cache/raw/locomo10.json` | LoCoMo upstream raw (CC BY-NC 4.0, gitignored) |
| `cache/raw/longmemeval_oracle.json` | LME oracle raw (MIT, gitignored) |
| `cache/locomo.jsonl` | LoCoMo corpus cache (5882 chunks) |
| `cache/longmemeval.jsonl` | LME corpus cache (940 chunks, oracle split) |
| `eval/locomo/dry-run-sample.json` | Source of LoCoMo category_name ground truth |
