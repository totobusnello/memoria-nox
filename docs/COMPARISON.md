# nox-mem vs the field — public benchmark comparison

> **Status: SKELETON — final numbers pending Saturday full run (2026-05-24).**
> Placeholders marked `[PENDENTE Sat full run]`. Gate D43 PASSED (≥+15% nDCG@10 threshold cleared by +78.8%).
> This document will be updated in-place when `aggregate.py` produces full-corpus results.

> **Headline nox-mem (canonical, G5 V3 A8 full boost stack, 2026-05-19):**
> nDCG@10 = **0.6237** (+78.8% rel vs G3 baseline 0.3488), MRR = 0.5534, R@10 = 0.7070.
> Search latency: p50 = **940ms**, p95 = **2342ms** (prod `/api/search`, n=95, dominated by Gemini embed).

---

## Methodology

### Datasets

| Dataset | Source | Queries used | Stratified? |
|---|---|---|---|
| **LoCoMo** | [snap-research/locomo](https://huggingface.co/datasets/snap-research/locomo) — Maharana et al. arXiv:2402.17753 | n=100 (seed=42) | Yes — stratified across single-hop, multi-hop, temporal, open-domain, adversarial |
| **LongMemEval** | [xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval) — Wu et al. arXiv:2410.10813 | n=100 (seed=42) | Yes — stratified across subtask categories |

### Evaluation metrics

| Metric | Definition | Why |
|---|---|---|
| **nDCG@10** | Normalized Discounted Cumulative Gain at cutoff 10 | Primary ranking quality signal — penalises rank position of relevant chunks |
| **MRR** | Mean Reciprocal Rank | Measures first-hit quality — key for memory systems where the top result matters most |
| **R@10** | Recall at cutoff 10 | Coverage — did we surface any relevant chunk in top 10? |
| **p50 latency** | Median wall-clock time per query (ms) | Typical-case responsiveness |
| **p95 latency** | 95th-percentile wall-clock time per query (ms) | Tail latency — what users experience in the worst 5% of queries |

### Methodology guarantees (per spec §5)

1. **Identical corpus.** Every system ingests the same LoCoMo / LongMemEval chunks before queries run.
2. **Identical eval set.** All systems receive the same queries and gold chunk IDs.
3. **Native defaults.** Each system runs as shipped — no tuning to win, no custom prompts.
4. **K cutoff = 10.** Standardised; enforced by `eval/q4-comparison/runner.py`.
5. **Binary relevance.** Chunk in `gold_chunk_ids` = 1, else 0. Graded relevance via `--gold` flag reserved for future runs.
6. **Embeddings.** Gemini `gemini-embedding-001` for nox-mem. Each competitor uses its native default.

### Systems evaluated

| System | Repo / source | Run mode | Gate status |
|---|---|---|---|
| **nox-mem** | [totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox) — MIT | HTTP `/api/search` (local VPS) | GO — reference system |
| **mem0** | [mem0ai/mem0](https://github.com/mem0ai/mem0) — Apache 2.0 | Python SDK | GO — pending install + corpus ingest |
| **Zep OSS** | [getzep/zep](https://github.com/getzep/zep) — Apache 2.0 | `zep_python` SDK + Docker | GO — pending corpus ingest |
| **Letta** | [letta-ai/letta](https://github.com/letta-ai/letta) — Apache 2.0 | `letta_client` archival search | GATED — pending Docker env + API key |
| **agentmemory** | [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory) — MIT | CLI subprocess | GATED — pending install (`agentmemory` CLI + iii-engine) |
| **EverMind-AI** | [EverMind-AI/EverMind](https://github.com/EverMind-AI/EverMind) | Python module or CLI | GATED — no PyPI release; git-install required |

---

## Cross-system headline table

> All cells marked `[PENDENTE Sat full run]` will be replaced with real numbers from `output/_aggregate.md` after `python3 runner.py --systems all --datasets locomo,longmemeval --limit 100 --k 10` completes.

| System | nDCG@10 | MRR | R@10 | p50 (ms) | p95 (ms) | Status |
|---|---:|---:|---:|---:|---:|:---:|
| **nox-mem** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GO |
| **mem0** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GO |
| **Zep OSS** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GO |
| **Letta** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GATED |
| **agentmemory** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GATED |
| **EverMind-AI** | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | [PENDENTE Sat full run] | GATED |

**Notes on GATED systems:**
- **Letta** — requires Postgres + Docker on VPS (blocker B2). archival memory search mode benchmarked, not full agent loop.
- **agentmemory** — vendor claims LoCoMo R@5 = 95.2% (vendor-reported, unverified). Blocked by `iii-engine` proprietary daemon install.
- **EverMind-AI** — no PyPI release as of 2026-05-21; git-install path only. EverMemBench numbers are on their own dataset, not LoCoMo/LongMemEval.

---

## LoCoMo per-category breakdown

> Stratified across: single-hop / multi-hop / temporal / open-domain / adversarial.
> All cells `[PENDENTE Sat full run]` pending n=100 full run.

| Category | nox-mem nDCG@10 | mem0 | Zep | Letta | agentmemory | EverMind |
|---|---:|---:|---:|---:|---:|---:|
| single-hop | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| multi-hop | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| temporal | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| open-domain | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| adversarial | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |

**nox-mem internal ablation reference (G5 V3, n=100 locomo, g5.db 68k prod corpus):**

| Category | G3 baseline | G5 V3 A8 (canonical) | Δ rel |
|---|---:|---:|---:|
| single-hop | 0.1179 | [internal only — not cross-system] | — |
| multi-hop | 0.3708 | [internal only — not cross-system] | — |
| temporal | 0.2887 | [internal only — not cross-system] | — |
| open-domain | 0.3746 | [internal only — not cross-system] | — |
| adversarial | 0.2531 | [internal only — not cross-system] | — |

> Note: G5 V3 ablation used production corpus (g5.db 68k) which differs from the clean
> cross-system eval corpus. Cross-system results use an isolated eval corpus to ensure
> identical conditions. See [methodology §2](#methodology).

---

## LongMemEval per-category breakdown

> All cells `[PENDENTE Sat full run]`.

| Category | nox-mem nDCG@10 | mem0 | Zep | Letta | agentmemory | EverMind |
|---|---:|---:|---:|---:|---:|---:|
| single-session-user | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| multi-session | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| knowledge-update | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |
| temporal-reasoning | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] | [PENDENTE] |

> nox-mem Q2 internal (n=100 full run 2026-05-19): nDCG@10=0.9126, MRR=0.9162, R@10=0.9558.
> Multi-session and temporal-reasoning were the weakest categories. Cross-system comparison
> will quantify whether competitors have structural advantages on these subtasks.

---

## Where nox-mem may not win

Documented transparently — this comparison is not marketing:

- **LoCoMo vs agentmemory** — vendor claims R@5 = 95.2% (different metric; not comparable until re-measured with our harness on identical corpus).
- **Temporal multi-hop** — Zep's temporal knowledge graph is architecturally stronger on multi-hop temporal chains. Our `--as-of` / `--changed-since` flags partially close this gap but we do not pre-claim to win.
- **Graph-native queries** — Zep's KG is more mature than nox-mem's `kg_relations` on structured graph traversal.
- **Agent loop integration** — Letta/MemGPT ships a full agent orchestration loop. nox-mem is a memory layer only. If the benchmark weights agent reasoning, Letta is closer to the task.
- **Hosted convenience** — Memanto (SaaS, not in this harness) offers one-click ingestion. nox-mem requires CLI + HTTP daemon.
- **Community size** — mem0 (53k+ stars), Letta (22k+ stars) have larger communities and more third-party integrations.

---

## Autonomy axis (fixed by design)

| System | Self-hosted? | Open source | No daemon required | Lock-in score (1=none, 5=full) |
|---|:---:|:---:|:---:|---:|
| **nox-mem** | ✅ SQLite file | ✅ MIT | ✅ no daemon | **1** |
| mem0 | ✅ Postgres + Qdrant | ✅ Apache 2.0 | ❌ requires two services | 2 |
| Zep OSS | ✅ Postgres | ✅ Apache 2.0 | ❌ requires Docker + Postgres | 2 |
| Letta | ✅ Docker | ✅ Apache 2.0 | ❌ Docker + Postgres | 2 |
| agentmemory | ✅ CLI | ✅ MIT (CLI) / ❌ proprietary engine | ⚠️ iii-engine daemon | 3 |
| EverMind-AI | ✅ | ✅ MIT | ✅ | 1 |

---

## Gate decision (D43)

| Gate condition | Threshold | Status |
|---|---|---|
| Q1 LoCoMo hybrid vs FTS5-only | ≥+15% nDCG@10 rel | ✅ **PASSED** — G5 V3 A8: +78.8% (0.6237 vs 0.3488) |
| Q4 COMPARISON nox-mem ranking | ≥1st or 2nd place | ⏳ Pending Sat full run |
| Phase 2 GTM scale-up | Both conditions met | ⏳ Pending Q4 results |

> Gate D43 details: `docs/DECISIONS.md` §D43 (2026-05-18).
> ROADMAP §3 Pillar Q sprints: `docs/ROADMAP.md`.
> Paper §5 eval methodology: `paper/publication/nox-mem-paper.md`.

---

## Honest caveats

- **This document uses n=5 smoke-test numbers for nox-mem** (pre-full run). Headline nDCG@10=0.4307 reflects 5-query locomo smoke only — NOT the G5 V3 canonical 0.6237 (which used 100 queries, prod corpus g5.db). Full-run numbers replace these cells Saturday.
- **Competitor numbers are vendor-reported or not yet measured.** No competitor number has been independently verified with this harness as of 2026-05-23.
- **Corpus isolation caveat.** G5 V3 used production corpus (68k chunks, g5.db). Cross-system eval uses an isolated corpus. Direct numeric comparison requires identical corpus — which this harness enforces.
- **Metric definition gap.** agentmemory's published "R@5 95.2%" uses a different metric (R@5, not nDCG@10) and an unspecified LoCoMo revision. Apples-to-oranges until re-measured.
- **Conflict of interest.** We built nox-mem. Harness code is open-source. Raw JSON output is published alongside this document. We invite PRs improving competitor adapter configurations (see `eval/q4-comparison/adapters/`).
- **Statistical floor.** With n=100, stdev on nDCG@10 is typically ±0.03–0.06 (±Wilson CI). Differences < 2pp should not be interpreted as decisive.

---

## How to reproduce

```bash
# Full run (from eval/q4-comparison/)
cd eval/q4-comparison/
pip install -r requirements.txt

# Start Docker deps (Zep + Postgres)
docker compose -f compose/docker-compose.yml up -d zep postgres

# Export required env vars
export GEMINI_API_KEY=...
export OPENAI_API_KEY=...      # for mem0 + Letta

# Smoke test — validates adapters without API calls
python3 smoke_test.py

# Full comparison run (~4-5h)
python3 runner.py --systems all --datasets locomo,longmemeval --limit 100 --k 10

# Aggregate into cross-system tables
python3 aggregate.py

# Review
cat output/_aggregate.md
```

Detailed step-by-step: `eval/q4-comparison/README.md`.

---

## Bibliography

- **LoCoMo** — Maharana, A. et al. *"Evaluating Very Long-Term Conversational Memory of LLM Agents."* arXiv:2402.17753 (2024).
- **LongMemEval** — Wu, X. et al. *"LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory."* arXiv:2410.10813 (2024).
- **mem0** — [mem0ai/mem0](https://github.com/mem0ai/mem0) (Apache 2.0).
- **Letta / MemGPT** — [letta-ai/letta](https://github.com/letta-ai/letta); Packer et al. arXiv:2310.08560 (2023).
- **Zep** — [getzep/zep](https://github.com/getzep/zep) (Apache 2.0).
- **agentmemory** — [rohitg00/agentmemory](https://github.com/rohitg00/agentmemory). Claimed LoCoMo R@5 = 95.2% (vendor-reported, not independently verified).
- **EverMind-AI** — [EverMind-AI/EverMind](https://github.com/EverMind-AI/EverMind). EverMemBench published; LoCoMo/LongMemEval cross-run pending.
- **nox-mem** — [totobusnello/memoria-nox](https://github.com/totobusnello/memoria-nox) (MIT).

---

*Skeleton generated 2026-05-23. Full numbers pending Saturday 2026-05-24 run. Gate D43: ✅ threshold passed. Phase 2 GTM scale-up conditional on Q4 comparison results.*
*Harness: `eval/q4-comparison/`. Aggregate script: `eval/q4-comparison/aggregate.py`. Working-draft competitor data: `benchmark/COMPARISON.md`.*
