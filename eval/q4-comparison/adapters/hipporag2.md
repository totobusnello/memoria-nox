# HippoRAG2 adapter — installation + operating notes

> Q4 COMPARISON adapter for [HippoRAG2](https://github.com/OSU-NLP-Group/HippoRAG)
> (OSU NLP Group, MIT licensed). SOTA graph-based RAG with entity-centric KG +
> Personalized PageRank scoring. Most direct external comparator for nox-mem's
> KG + section/entity-boost layer.

## Why this adapter exists

The Q4 cross-system comparison covers six retrieval paradigms (mem0, Zep, Letta,
agentmemory, EverMind, and nox-mem itself). Adding HippoRAG2 fills the
**graph-based RAG** slot — the only paradigm previously unrepresented and the
one most architecturally adjacent to nox-mem's KG layer.

Including HippoRAG2 in the table answers the reviewer question
*"how does nox-mem compare to SOTA graph RAG?"* with a measurement, not a
hand-wave.

## Install

```bash
pip install 'hipporag>=2.0.0a3,<2.1'
export OPENAI_API_KEY=sk-...
```

Heavy install (~1.2 GB site-packages: torch, sentence-transformers, scipy,
networkx, openai). Recommended in a dedicated venv if the runner host is
RAM-constrained.

**Optional local backend (no OpenAI quota burn):**

```bash
# Run vLLM with a local OpenAI-compatible chat endpoint
vllm serve meta-llama/Llama-3.1-8B-Instruct --port 8000

export HIPPORAG_LLM_BASE_URL=http://localhost:8000/v1
export HIPPORAG_LLM_MODEL=meta-llama/Llama-3.1-8B-Instruct
# Embeddings still go through OpenAI by default; override via:
export HIPPORAG_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5  # local ST model
```

## Version pin

`hipporag>=2.0.0a3,<2.1` (current as of 2026-05-24).

HippoRAG2 is still on the alpha track (2.0.0a1 → a2 → a3) and the constructor
kwargs have drifted across releases. The adapter probes the installed signature
via `inspect.signature` and remaps `save_dir / working_dir / storage_dir` to
the accepted form — but pinning is still recommended for reproducibility.

## Env knobs

| Variable                    | Default                       | Purpose                                                          |
| --------------------------- | ----------------------------- | ---------------------------------------------------------------- |
| `OPENAI_API_KEY`            | *(required)*                  | OpenAI key for OpenIE + embeddings (default LLM/embed backend).  |
| `HIPPORAG_SAVE_DIR`         | `.hipporag-store`             | Persistence dir (graph pickle + embedding store).                |
| `HIPPORAG_LLM_MODEL`        | `gpt-4o-mini`                 | OpenIE / generation model.                                       |
| `HIPPORAG_EMBEDDING_MODEL`  | `text-embedding-3-small`      | Dense retrieval embedding model.                                 |
| `HIPPORAG_LLM_BASE_URL`     | *(OpenAI default)*            | Override LLM endpoint (vLLM / Together / local).                 |
| `HIPPORAG_INGEST_LIMIT`     | *(unlimited)*                 | Cap corpus chunks for smoke/cost-controlled runs (e.g., `200`).  |
| `HIPPORAG_FORCE_REINGEST`   | unset                         | Force re-index even if save dir non-empty.                       |

## Cost estimate (full Q4 corpus)

Ingest dominates the cost because HippoRAG2 runs OpenIE (one LLM call per
chunk) + embeds the chunk + each extracted entity:

|                                | Default backend            | Estimate (LoCoMo + LongMemEval, ~9,882 chunks) |
| ------------------------------ | -------------------------- | ---------------------------------------------- |
| OpenIE triple extraction (LLM) | gpt-4o-mini                | ~$7.90                                         |
| Passage embeddings             | text-embedding-3-small     | ~$0.30                                         |
| Entity embeddings (3–5× chunk) | text-embedding-3-small     | ~$1.00 – $1.50                                 |
| **Total ingest**               |                            | **~$9 – $11**                                  |

Retrieval is essentially free (PPR + dense lookup, no LLM call per query) at
~10–50 ms per query post-ingest.

Smoke runs: `HIPPORAG_INGEST_LIMIT=200` → ~$0.20 total spend.

## Idempotency

HippoRAG2 persists the entity KG (pickle) + embedding store to
`HIPPORAG_SAVE_DIR`. `setup()` short-circuits when the save dir is non-empty
unless `HIPPORAG_FORCE_REINGEST=1`. Re-runs of the harness are cheap.

To wipe and re-ingest:

```bash
rm -rf eval/q4-comparison/.hipporag-store
HIPPORAG_FORCE_REINGEST=1 python eval/q4-comparison/runner.py --adapter hipporag2
```

## ID round-trip

HippoRAG2's passage-id surface drifted between alpha versions. The adapter
mirrors the agentmemory adapter pattern: each chunk is indexed with content
prefix `[nox_id:<id>]` and `search()` parses the prefix back from retrieved
passages. This works regardless of whether upstream surfaces native
`passage_ids` (post 2.0.0a3) or only the bare passage text.

## Caveats

- **No Neo4j required.** HippoRAG2 dropped Neo4j support in v2 (HippoRAG1 had
  it). The current implementation uses `networkx` in-memory + pickle persistence.
- **Heavy deps.** Install pulls torch + sentence-transformers + scipy + openai.
  Plan for ~1.2 GB on disk and ~2 GB RAM at index time.
- **OpenAI default.** Defaults are `gpt-4o-mini` (OpenIE) + `text-embedding-3-small`
  (retrieval), matching mem0/Letta's fair-comparison baseline. vLLM / local
  paths are documented above but not the canonical Q4 run.
- **Alpha API churn.** `index() / insert_to_graph() / add_documents()` and
  `save_dir / working_dir / storage_dir` rename'd across 2.0.0a1→a3. The
  adapter probes via getattr + signature inspection and falls through; if
  upstream renames again, pin to the documented commit.
- **Indexing latency.** OpenIE is the bottleneck at ~1–2 sec/chunk on
  gpt-4o-mini. Full corpus ingest takes 2–5 hours wall-clock. Budget overnight
  if running fresh; subsequent runs are near-instant thanks to disk persistence.

## References

- Repo: <https://github.com/OSU-NLP-Group/HippoRAG>
- Paper (HippoRAG, NeurIPS 2024): <https://arxiv.org/abs/2405.14831>
- Paper (HippoRAG 2, Feb 2025): <https://arxiv.org/abs/2502.14802>
- nox-mem KG layer comparison: see `docs/COMPARISON.md` (PR #346 pending review)
