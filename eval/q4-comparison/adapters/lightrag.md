# LightRAG adapter — Q4 COMPARISON

> **Repo:** [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) — MIT, ~35k stars
> **Paper:** [arXiv:2410.05779](https://arxiv.org/abs/2410.05779) — EMNLP 2025
> **Stack:** Python SDK (`lightrag-hku`), networkx default storage, async-first
> **Pin:** `lightrag-hku==1.4.10` (verified 2026-05-24)

## Why LightRAG matters for Q4

LightRAG's differentiator is **LLM-summarized incremental KG merge**: when
a new document brings in an entity/relation that already exists, LightRAG
calls the LLM to fuse descriptions into a single coherent summary rather
than deterministic dedup (nox-mem's pattern). Trades ingest cost for
denser entity context at query time. Head-to-head measurement feeds
DECISIONS.md on whether to adopt the pattern in v3.9.

Also relevant: LightRAG is the **only Q4 system with a published
benchmark on its README** (along with EverMind), so a fair comparison
strengthens the paper's external validity.

## Install

```bash
pip install 'lightrag-hku==1.4.10'
# Gemini integration ships in lightrag.llm.gemini (added v1.3.0).
# Defensive fallback uses google-generativeai directly if module missing.
pip install google-generativeai  # only needed for fallback path
```

## Configuration (Autonomy parity with nox-mem)

| Component   | Choice                          | Why                                                                |
| ----------- | ------------------------------- | ------------------------------------------------------------------ |
| LLM         | `gemini-2.5-flash`              | Same family as nox-mem prod KG extractor (apples-to-apples)        |
| Embeddings  | `gemini-embedding-001` (3072d)  | Bit-identical to nox-mem prod vector dim — no embedding confound   |
| Graph store | networkx (in-process)           | Keeps setup leaf — no Neo4j daemon. ~9k entities fits easily       |
| Vector DB   | nano-vectordb (LightRAG default)| In-process, persisted to JSON; matches networkx footprint          |
| Working dir | `eval/q4-comparison/cache/lightrag/` | Gitignored, regenerable, idempotent re-runs                    |

Env vars:

```bash
GEMINI_API_KEY=...                   # required (Autonomy parity)
LIGHTRAG_MODE=mix                    # default (see "Query modes" below)
LIGHTRAG_INGEST_LIMIT=200            # smoke runs (omit for full corpus)
LIGHTRAG_FORCE_REINGEST=1            # wipe working dir + re-ingest
LIGHTRAG_USE_OPENAI_FALLBACK=1       # fall back if Gemini integration breaks
LIGHTRAG_GEMINI_LLM=gemini-2.5-flash # override LLM model
LIGHTRAG_GEMINI_EMBED=models/gemini-embedding-001
LIGHTRAG_WORKING_DIR=/custom/path    # override default cache location
```

## Query modes — default `mix`

LightRAG exposes 5 modes via `QueryParam(mode=...)`:

| Mode      | Surface                              | When                                                  |
| --------- | ------------------------------------ | ----------------------------------------------------- |
| `naive`   | Pure vector RAG, no KG               | Baseline (no graph)                                   |
| `local`   | Entity-centric KG neighborhood       | Faster, smaller context, good for single-hop queries  |
| `global`  | Community-centric high-level rels    | Long-range queries spanning many entities             |
| `hybrid`  | local + global fused                 | KG-only, no raw chunks                                |
| **`mix`** | **hybrid + vector chunks**           | **LightRAG's flagship — paper headline number**       |

Default is `mix` because:

1. **Paper parity:** LightRAG's published nDCG@10 numbers use mix.
2. **Spec §5 (Q4 plan):** "each system uses native defaults". Mix is what
   LightRAG ships configured for in their README quickstart.
3. **Recall surface:** Mix is the highest-recall mode, fairest comparison
   against nox-mem's hybrid (FTS5 + dense + RRF).

Override per run via `LIGHTRAG_MODE=local` for entity-only ablation, or
`LIGHTRAG_MODE=naive` for the pure-vector baseline (useful for the paper's
"KG contribution" attribution).

## Cost estimate — full LoCoMo + LongMemEval ingest

Corpus size: ~5,882 LoCoMo turns + ~4,000 LongMemEval sessions ≈ **9,882 chunks**.

Per-chunk pipeline (LightRAG default config, gemini-2.5-flash):

| Step                              | Tokens in / out      | Cost           |
| --------------------------------- | -------------------- | -------------- |
| Embedding (gemini-embedding-001)  | ~250 in              | $0.000015      |
| Entity + relation extraction LLM  | 1500 in / 800 out    | $0.000353      |
| Incremental merge LLM (amortized) | ~500 in / 200 out × 1.4 collisions/entity | $0.000063 |
| Community report LLM (batched end)| ~one report/community| (~$0.50 total) |
| **Per-chunk subtotal**            | —                    | **~$0.00043**  |

- **Total ingest:** 9,882 × $0.00043 ≈ **$4.25** + ~$0.50 community batch
  → **~$5 one-time** (cached on disk, reused across runs).
- **Search:** 1 embed + 1 LLM rerank ≈ $0.0002/query × 350 queries ≈ **$0.07**.

Compare to:
- nox-mem (Gemini embeddings only, no LLM at ingest): ~$0.15 for the same corpus.
- mem0 (OpenAI embeddings + extraction LLM): ~$13-15.
- LightRAG sits between: more expensive than nox-mem (LLM extraction at
  ingest), cheaper than mem0 (Gemini Flash << GPT-4o), denser KG than both.

**Smoke runs** with `LIGHTRAG_INGEST_LIMIT=200`: ~$0.10 total — safe for
iteration.

## Idempotency

`setup()` skips re-ingest if `working_dir/kv_store_full_docs.json` exists
and contains ≥1 doc. To wipe and re-ingest:

```bash
LIGHTRAG_FORCE_REINGEST=1 python eval/q4-comparison/runner.py --systems lightrag
```

## Search contract

```python
search(query: str, k: int = 10) -> list[dict]
# Returns: [{id, score, text, source}, ...]
```

- `id`: parsed from `[nox_id:<id>] ` prefix embedded at ingest. Falls back
  to LightRAG's internal `chunk_id` / `entity_name` if prefix missing
  (e.g., on entity-level results from `mode=local`).
- `score`: LightRAG's vector similarity. If backend returns `distance`
  (lower=better), converted to `1 - distance`. If neither, defaults to 0.
- `text`: chunk content with prefix stripped.
- `source`: `file_path` or `source` field if LightRAG surfaces it.

## Validate

```bash
cd ~/Claude/Projetos/memoria-nox
GEMINI_API_KEY=... python -m eval.q4-comparison.adapters.lightrag
# Should print {"ok": true, "version": "1.4.x", "notes": "..."}
```

## Caveats

1. **`lightrag.llm.gemini` may not ship in every minor.** Pinned 1.4.10
   has it; older versions may need the `google-generativeai` fallback path
   (the adapter handles this automatically).
2. **Embedding dim mismatch on first ingest = full rebuild.** If you
   switch `LIGHTRAG_GEMINI_EMBED` between 3072d models and 768d models
   the working dir must be wiped (`LIGHTRAG_FORCE_REINGEST=1`).
3. **networkx + JSON storage scales to ~50k entities.** At Q4 corpus size
   (~9k chunks producing ~5-10k entities) we're well inside the comfort
   zone. For prod use Neo4j (not needed for benchmark).
4. **`mix` mode is slow on first query of a session** (community detection
   on cold cache). Subsequent queries in the same process are ~10× faster.
   The Q4 runner times each query externally so this shows up as a long
   tail on cold latency — note in paper §3.
5. **No `ingest()` separate from `setup()`.** LightRAG's API conflates
   "create index" and "ingest"; `setup()` handles both atomically.

## References

- README: <https://github.com/HKUDS/LightRAG#quickstart>
- Gemini integration: <https://github.com/HKUDS/LightRAG/blob/main/lightrag/llm/gemini.py>
- Incremental KG merge paper §4: <https://arxiv.org/abs/2410.05779>
- Q4 execution spec: `specs/2026-05-23-Q4-comparison-execution-plan.md`
- Consolidated paper inputs: `docs/paper-inputs-consolidated-2026-05-24.md`
