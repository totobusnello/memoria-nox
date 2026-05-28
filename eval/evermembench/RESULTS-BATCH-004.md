# EverMemBench batch 004 — nox-mem results (Gemini-only stack)

**Run date:** 2026-05-28
**System:** nox-mem v3.8 (hybrid: FTS5 + sqlite-vec + RRF)
**Stack:** Gemini-only (answer + judge = `gemini-2.5-flash`, embeddings = `gemini-embedding-001`)
**Corpus:** 10,222 dialogue messages → 1,140 chunks (87 chunks/day avg) → 1,140 vectors (100% coverage)
**Questions:** 626 (389 MC + 237 OE)

---

## Headline

**56.07% overall accuracy (351/626)**

- **Multiple choice:** 70.95% (276/389)
- **Open-ended:** 31.65% (75/237)

---

## Honest framing (required disclosure)

> This run uses `gemini-2.5-flash` for both answer generation and OE judgment,
> substituted for the upstream EverMemBench default (`openai/gpt-4.1-mini` answer
> + `gemini-3-flash-preview` judge via OpenRouter). Numbers are **not directly
> comparable** to EverOS-published EverMemBench leaderboard entries. To compare
> against published numbers on the same methodology, re-run with `LLM_API_KEY=sk-or-v1-...`
> and the default `pipeline.yaml` (provider blocks restored).
>
> Additionally:
> - **Gemini-2.5 reasoning behaviour:** the `gemini-2.5-flash` model consumes
>   ~20+ "thinking" tokens before emitting visible output, so the
>   `max_tokens=1000` default in pipeline.yaml leaves ~980 tokens for the actual
>   answer. This is sufficient for both answer + judge in practice.
> - **Concurrency override:** pipeline.yaml `answer.concurrency` raised from 1 → 4
>   (and `evaluate.concurrency` from 20 → 8 for rate-limit safety on paid
>   Gemini tier). This impacts wall-clock time, not accuracy.
> - **Provider block removal:** Gemini OpenAI-compat shim rejects OpenRouter-style
>   `extra_body.provider` payloads with HTTP 400. The default `pipeline.yaml`
>   provider block was deleted for this run (first-attempt root cause that
>   caused 50 min of single-question retries before discovery).

---

## Per-category breakdown

### Major categories

| Major | Total | Correct | Accuracy |
|-------|-------|---------|----------|
| **F** (Factuality)       | 237 |  75 | 31.65% |
| **MA** (Memory Access)   | 258 | 194 | 75.19% |
| **P** (Personalisation)  | 131 |  82 | 62.60% |

### Minor categories

| Minor | Total | Correct | Accuracy |
|-------|-------|---------|----------|
| **U** (Updating)          |  58 | 49 | **84.48%** |
| **MA_P** (Profile lookup) | 100 | 79 | 79.00% |
| **Title** (Personalisation) | 49 | 37 | 75.51% |
| **Skill**                 |  45 | 30 | 66.67% |
| **MA_C** (Constraint)     | 100 | 66 | 66.00% |
| **HL** (Hallucination)    |  78 | 42 | 53.85% |
| **SH** (Single-hop)       |  49 | 25 | 51.02% |
| **Style**                 |  37 | 15 | 40.54% |
| **TP** (Temporal)         |  60 |  6 | **10.00%** |
| **MH** (Multi-hop)        |  50 |  2 | **4.00%** |

### Key observations

- **Strength: Memory-access (75.19%)** — nox-mem hybrid retrieval handles
  Constraints, Profile lookups, and Updating queries well.
- **Weakness: Multi-hop reasoning (4.00%)** — the hybrid pipeline retrieves
  isolated chunks; cross-chunk reasoning relies entirely on the LLM and
  consistently fails on dependency-chain questions.
- **Weakness: Temporal queries (10.00%)** — TP category requires
  cross-day reasoning ("X days after Y"). nox-mem's `temporal-spike-v2`
  feature is geared for entity-scoped recency, not multi-message timeline
  reconstruction.
- **Personalisation Style (40.54%)** — style-mimicry questions need access
  to writing patterns across many messages; single-shot retrieval misses
  that distributional signal.

---

## Cost

- **Vectorize:** $0 (free tier within prod Gemini key headroom)
- **Answer (626 calls, Gemini-2.5-flash):** Estimated ~$0.60
- **Evaluate (237 OE judge calls):** Estimated ~$0.15
- **Total LLM spend:** **~$0.75** (well under $1.50 cap)
- **Cache benefit:** 23.3% answer-cache hit rate (146/626) from Gemini's
  context caching — reduced effective cost vs. naïve calculation.

Per-run measurement precision is limited because the Gemini AI Studio
dashboard does not attribute spend to individual API calls within a single
key. Cost is computed from observed token usage in the harness debug
output × Gemini pricing ($0.30/$2.50 per 1M in/out tokens).

---

## Comparison to EverOS-published numbers

EverOS publishes batch-by-batch accuracy in their EverMemBench paper
appendix + leaderboard. The placeholder table below is incomplete until
the paper §C reference numbers are extracted; **direct comparison is
methodologically invalid until we re-run with the default OpenRouter stack**
(see honest framing above).

| System | Batch 004 | Notes |
|--------|-----------|-------|
| EverCore           | TODO | (from paper §C) |
| Mem0               | TODO | (from paper §C) |
| Memos              | TODO | (from paper §C) |
| Zep                | TODO | (from paper §C) |
| Memobase           | TODO | (from paper §C) |
| **nox-mem (this)** | **56.07%** | Gemini-only stack, 626 q, single-tenant fresh DB |

**Action item:** open follow-up issue to fetch EverOS-published batch 004
numbers from arXiv:2602.01313 §C or the project's leaderboard JSON. Without
that we cannot say whether 56.07% is competitive, parity, or
under-performing.

---

## Reproducibility

Hardware/infra:
- VPS: Hostinger 187.77.234.79 (isolated nox-mem instance on port 18810)
- DB path: `/root/.openclaw/evermembench-runs/evermembench-004-<TS>.db`
  (cleaned up post-run)
- Prod nox-mem on :18802 untouched throughout (69,135 chunks before/after)

Run timing:
- **Add stage:** 17.2s (10,222 messages → 1,140 chunks)
- **Vectorize:** 70s (1,140 chunks × 3,072d Gemini embeddings)
- **Search stage:** ~3.5min (626 queries, hybrid mode, concurrency=3)
- **Answer + Evaluate:** 15.3 min (concurrency=4 answer, 8 evaluate)
- **Total wall clock:** ~22 min (after pipeline.yaml fix)

Setup gotchas encountered (documented for future runs):
1. **`nox-mem serve` does not exist** — use
   `node dist/api-server.js` directly with `NOX_DB_PATH` + `NOX_API_PORT` env.
2. **op-audit guard** (PR #358) restricts `NOX_DB_PATH` to
   `/var/backups/` or `/root/.openclaw/` prefixes. Cannot use `/tmp/`.
3. **Schema migration drift:** fresh DB from `nox-mem stats` stops at v15;
   v18 columns (`retention_days`, `pain`, `section`, `section_boost`) and KG
   tables (`kg_entities`, `kg_relations`) must be added manually via SQL.
4. **Adapter `--source` flag:** the bootstrap PR's adapter passed `--source`
   to `nox-mem ingest`; current CLI does not accept it. Removed from argv.
5. **Search response shape:** the prod API returns a top-level JSON array,
   not `{results: [...]}`. Adapter patched to handle both shapes.
6. **`chunk_text` vs `content` field:** API returns `chunk_text`; adapter
   updated to extract from either.
7. **`provider` block** (the big one): Gemini OpenAI-compat shim rejects
   `extra_body.provider` with HTTP 400. The default pipeline.yaml `provider:
   {order, allow_fallbacks}` blocks must be removed for Gemini direct.

---

## Next steps

- [ ] Fetch EverOS-published batch 004 number from arXiv:2602.01313 §C
- [ ] Investigate MH/TP weaknesses — likely need answer-primitive temporal
      extension (see `feedback_temporal-spike-v2-win`) + graph-walk
      multi-hop joining (parking-lot Lab Q1)
- [ ] If batch 004 result above ~50% holds vs published numbers (TBD), run
      batches 005, 010, 011, 016 (same recipe) for full 5-batch comparison
      (est. ~$3-4 total)
- [ ] OpenRouter parity Phase 2: re-run batch 004 with `LLM_API_KEY=sk-or-v1-...`
      + default `pipeline.yaml` for apples-to-apples vs published numbers
