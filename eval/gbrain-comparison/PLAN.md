# gbrain v0.40.6.0 — comparison plan

> **Status:** Research + planning. **NOT executed.** Task #17 (Lab Q1 Parte C).
> **Goal:** position nox-mem against gbrain's claimed **97.60% R@5 on LongMemEval `_s`**.

---

## 1. gbrain identification

| | |
|---|---|
| Repo (evals) | https://github.com/garrytan/gbrain-evals |
| Repo (engine) | https://github.com/garrytan/gbrain |
| Owner | Garry Tan (YC president, public face) |
| License | **MIT** (both repos) |
| Stars (evals) | 188 |
| Last push (evals) | 2026-05-24 |
| Quoted version | **v0.40.6.0** |
| Published report | `docs/benchmarks/2026-05-07-longmemeval-s.md` (gbrain version pinned `v0.28.8` at headline date; v0.40.6.0 snapshot 2026-05-23 confirms numbers held byte-identical across 20 releases) |
| Engine stack | TypeScript / Bun · PGLite (Postgres-in-WASM) · pgvector HNSW · OpenAI `text-embedding-3-large@1536` · Postgres FTS `ts_rank_cd` · RRF k=60 · cosine re-score (`0.7·rrf + 0.3·cos`) · optional Haiku query expansion |

**Adjacent ecosystem** (useful for context, not in this comparison):
- `quaid-app/quaid` (MIT) — competitor memory system that publishes head-to-head numbers against gbrain on MSMARCO (not relevant here, different corpus).

---

## 2. Surprising finding (lead with this)

The "97.60% on LongMemEval `_s` recall" headline is **real, MIT-licensed, fully reproducible, with a committed embedding cache** (~150MB SQLite of OpenAI vectors shipped in-repo). Cold-cache cost is ~$2 OpenAI + ~$1 Anthropic Haiku for the full 4-adapter sweep. **Re-runs cost ~$0.**

The metric is **Recall@5 at chunk granularity, no LLM judge, no QA-accuracy stage** — exactly the same family as nox-mem's existing LoCoMo/LongMemEval retrieval-recall harnesses. **Direct comparison is possible**, modulo embedding-stack parity (Gemini-3072 vs OpenAI-1536).

---

## 3. 97.60% reproduction recipe

### Harness
gbrain's own runner — **NOT** the original `xiaowu0162/LongMemEval` harness.
Path in repo: `eval/runner/longmemeval.ts` (672 LOC, NDJSON resume, 3-worker parallel).

```sh
git clone https://github.com/garrytan/gbrain-evals
cd gbrain-evals && bun install

mkdir -p ~/datasets/longmemeval
curl -Lo ~/datasets/longmemeval/longmemeval_s.json \
  https://huggingface.co/datasets/xiaowu0162/longmemeval/resolve/main/longmemeval_s

export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...    # only for hybrid+expansion adapter
bash eval/runner/longmemeval-batch.sh   # 4 adapters × 500 questions
```

### Adapter under test
`gbrain-hybrid` — `hybridSearch(engine, q, {limit: 5, expansion: false})`.
RRF k=60, source-aware boost, compiled-truth 2.0× boost. **No LLM in the retrieval loop.**

### Metric definition (verbatim from report §3)
> Did at least one ground-truth `answer_session_id` land in the **top-5 retrieved sessions**? Not QA accuracy. Pure binary set-membership at session granularity.

### Numbers we're targeting
| Adapter | R@5 (gbrain) |
|---|---|
| gbrain-hybrid (headline) | **97.60%** (488/500) |
| gbrain-vector (pure dense) | 97.40% (487/500) |
| gbrain-hybrid+expansion (Haiku) | 97.60% (null result vs hybrid) |
| gbrain-keyword (BM25 only) | 19.80% (99/500) |
| MemPalace raw (their baseline) | 96.6% |

---

## 4. nox-mem integration approach

### What we reuse
- `eval/longmemeval/` already exists (scaffold-stage, no published numbers per its own README).
- `eval/longmemeval/parser.ts` — handles the `xiaowu0162/longmemeval-cleaned` HuggingFace schema.
- `eval/longmemeval/run.ts` — CLI + API mode against an isolated `eval.db`.
- `eval/q4-comparison/lib/corpus_loader.py` — corpus_loader pattern (memory `[[shared-loader-canonical-pattern]]`).

### What needs to be added
1. **`gbrain-s-runner.ts`** — variant of `run.ts` that:
   - Targets the **`_s` split** (not `_oracle` like the current dry-run).
   - Loads from `xiaowu0162/longmemeval` (not `longmemeval-cleaned`) to match gbrain's source exactly.
   - Emits per-question records compatible with gbrain's chart pipeline (NDJSON with `{question_id, adapter, retrieved_session_ids, recall_at_5}`).

2. **Session-ID mapping layer.** gbrain operates at **session granularity**; nox-mem stores chunks. Need to map `chunk_id → session_id` via the original `haystack_session_ids[]` array per question. Same approach the existing harness already does at `run.ts:69` (`retrieved_session_ids: string[]` derived from chunk_id).

3. **Adapter parity matrix** (apples-to-apples):

   | nox-mem mode | Mirrors gbrain | Headline candidate |
   |---|---|---|
   | FTS5-only | gbrain-keyword | yes (baseline lower bound) |
   | Gemini dense only (vec0 cosine) | gbrain-vector | yes |
   | Hybrid FTS5 + Gemini + RRF k=60 | gbrain-hybrid | **headline** |
   | Hybrid + query-rewrite (already wired in q4 adapter via `NOX_QUERY_REWRITE=1`) | gbrain-hybrid+expansion | yes |

4. **No QA-accuracy stage.** Skip the LLM-judge call. Pure retrieval recall.

### Integration complexity: **MEDIUM**
- Code reuse: ~70% of `eval/longmemeval/` and ~30% of `eval/q4-comparison/adapters/nox_mem.py`.
- Net new: ~400-600 LOC (runner + 4 adapter configs + comparison aggregator).
- No external dependencies beyond what nox-mem already ships.

---

## 5. Cost estimate

### One-shot full `_s` run (n=500)
Assumes Gemini-3072 embedding stack (nox-mem default, OpenAI-1536 is not on the table):

| Item | Quantity | Unit cost | Total |
|---|---|---|---|
| Gemini embedding (corpus) | ~50 sessions × 500 Q × ~5 chunks/session × ~250 tokens | ~$0.000015/1k tokens | ~$2.30 |
| Gemini embedding (queries) | 500 × ~30 tokens × 4 adapters | ~$0.000015/1k tokens | ~$0.001 |
| Gemini Flash Lite query rewrite (one adapter, optional) | 500 Q × ~150 in + ~80 out tokens | tier 1 pricing | ~$0.03 |
| Compute (local M-series or VPS) | ~30 min hybrid + ~2h vector cold | — | $0 |
| **Total cold cache** | | | **~$2.35** |
| **Subsequent runs (cache hit)** | | | **~$0** |

We follow gbrain's pattern: ship a content-addressed embedding cache (SHA-256 keyed) in `eval/gbrain-comparison/cache/`. Size budget: ~100-150MB once warm (matches gbrain).

### Stratified smoke (n=30, 5 per category)
~$0.15 one-shot; ~$0 cached. Good for plumbing validation.

---

## 6. Phased execution plan

### Phase A — Smoke (1 session)
- Adapt `eval/longmemeval/run.ts` → `eval/gbrain-comparison/runners/longmemeval-s.ts`.
- Run **n=30 stratified** (5 per category × 6 categories) on the `_s` split.
- Validate session-id mapping, R@5 calculation, output NDJSON shape.
- Sanity: keyword adapter should land 15-25% (well below hybrid).
- Cost: ~$0.15. Effort: ~2-3h.

### Phase B — Small (1 session)
- Run **n=100 stratified** all 4 nox-mem adapters.
- Generate per-type table mirroring gbrain's §6 (knowledge-update / multi-session / single-session-* / temporal-reasoning).
- Compare against gbrain's published per-type numbers.
- Cost: ~$0.50. Effort: ~1h.

### Phase C — Full publish (1 session)
- Run **n=500** (full `_s` split) all 4 adapters.
- Generate `docs/benchmarks/2026-XX-XX-longmemeval-s-vs-gbrain.md` mirroring gbrain's report structure (§1 headline · §6 per-type · §10 repro · §11 methodology).
- Commit the embedding cache (~100MB) under git-LFS or gitignored with re-fetch script.
- Cost: ~$2.50. Effort: ~3-4h compute-supervised.

### Phase D — Comparison surface
- Add nox-mem row to `docs/COMPARISON.md` Q4 table.
- File `docs/DECISIONS.md` entry: "D52 — gbrain comparison protocol".
- Phase 2 GTM gate methodology already includes nDCG; adds R@5 row.

**Total wall-clock if all phases land in one workday:** ~6-9h with monitoring.

---

## 7. Honest comparison considerations

### Corpus parity: GOOD
Both systems hit the **same dataset, same SHA, same split** (`xiaowu0162/longmemeval._s`). No corpus-cap effect — gbrain runs full n=500.

### Metric parity: GOOD
**R@5** at session granularity, defined identically. We map nox-mem chunk hits → session IDs the same way the gbrain runner does.

### Embedding-stack parity: **NOT MATCHED — this is the disclosure**
- gbrain: OpenAI `text-embedding-3-large@1536`
- nox-mem: Gemini `gemini-embedding-001@3072`

These are **different embedding families** with different recall characteristics on conversational data. Honest framing: we publish nox-mem's number with the Gemini stack — the Autonomy pillar deliberately commits to no OpenAI dependency. The headline is "**X% with the OpenAI-free stack**", not "X% with the same stack as gbrain".

Optional Phase E: also run nox-mem in `eval/q4-comparison/adapters/nox_mem.py:hybrid` mode swapped to OpenAI embeddings for **direct stack-parity** apples-to-apples. Costs +$2-3 one-time. Filed as stretch goal, not blocking the headline.

### Retrieval-loop LLM parity: GOOD
- gbrain-hybrid: **no LLM in retrieval** (Haiku expansion is opt-in).
- nox-mem-hybrid: **no LLM in retrieval** (LLM query rewrite is opt-in, gated `NOX_QUERY_REWRITE=1`).
- We compare the no-LLM adapters head-to-head for the headline.

### Tuning surface: SAFE
gbrain explicitly says "no tuning on this benchmark" (report §9). Nox-mem will publish numbers **before** any tuning pass against `_s`. If we ever tune, we publish both numbers.

### Cherry-picking risk: LOW
- Same split, same n, same K — no degrees of freedom to game.
- Per-type breakdown surfaces weaknesses (we'll likely show the same `temporal-reasoning` gap gbrain documents).
- LLM judge: not used (no judge-side gaming possible).
- Memory `[[honest-cross-system-framing]]` applies: report MRR + nDCG@10 alongside R@5 even if R@5 is the headline.

### Risks
1. **Gemini 3072 may underperform OpenAI 3-large@1536 on `_s` conversational data**, leading to <97.60%. Honest fallback: publish whatever number, with the caveat note. A 90-95% R@5 with Autonomy-stack-only is still a strong narrative.
2. **Session-id mapping bug** (chunk → session) could give false-positive recall. Mitigation: validate against gbrain's published per-question NDJSON for the same 30 stratified questions.
3. **Cache poisoning** (different embeddings vs gbrain cache). Mitigation: our cache is keyed `(model, dimensions)` so it can't cross-contaminate gbrain's.

---

## 8. Out of scope (filed, not blocking)

- LongMemEval `_m` split (200 distractors per haystack). gbrain itself hasn't run this; honest move = wait until they publish.
- BrainBench (gbrain's in-house corpus). Different corpus, different metric family, not comparable.
- MSMARCO P@5/R@5 (`quaid-evals` vs `gbrain-evals` comparison). Different dataset, different signal.
- LLM-judge QA accuracy (handing JSONL to `evaluate_qa.py`). Filed for after the retrieval-recall headline lands.

---

## 9. References

- gbrain-evals repo: https://github.com/garrytan/gbrain-evals (MIT, 188 stars, pushed 2026-05-24)
- gbrain engine: https://github.com/garrytan/gbrain (MIT)
- Headline report: https://github.com/garrytan/gbrain-evals/blob/main/docs/benchmarks/2026-05-07-longmemeval-s.md
- v0.40.6.0 snapshot: `docs/benchmarks/2026-05-23-v0.40.6.0-snapshot.md` in gbrain-evals
- LongMemEval dataset: https://huggingface.co/datasets/xiaowu0162/longmemeval (MIT)
- LongMemEval paper: Di Wu et al., ICLR 2025, arXiv:2410.10813
- nox-mem existing LongMemEval harness: `eval/longmemeval/` (scaffold, no numbers)
- nox-mem existing q4 harness: `eval/q4-comparison/adapters/nox_mem.py` (hybrid + query-rewrite modes ready)
- Memory references: `[[honest-cross-system-framing]]`, `[[shared-loader-canonical-pattern]]`, `[[worktree-isolation-sparse-checkout-root-cause]]`

---

## 10. Decisions needed before execution

| # | Decision | Default proposal |
|---|---|---|
| 1 | Embedding stack — Autonomy-only (Gemini) vs. parity (OpenAI as well)? | Headline Gemini; OpenAI as Phase E stretch |
| 2 | Phase A target — n=30 or n=10? | n=30 (5 per category, full per-type sanity) |
| 3 | Cache commit policy — git-LFS, gitignored + script, or split repo? | gitignored + `scripts/download-embed-cache.sh` mirroring gbrain |
| 4 | Publishing surface — `docs/benchmarks/` like gbrain, or `docs/COMPARISON.md` only? | Both: standalone report + COMPARISON row |
| 5 | Run host — local M-series, VPS, or both? | Local M-series for development; VPS for the published cold-cache pass to match gbrain's hardware claim |

Toto sign-off needed on #1 (Autonomy stance) before Phase C ships.
