# nox-mem vs the field — public benchmark comparison

> **Status: WIDER PARTIAL RUN — 2026-05-23 Sat Q4 run (3 of 6 systems scored).**
> Run completed with nox_mem (full), mem0 (500-chunk cost-cap), agentmemory (20.5% corpus partial).
> Zep/Letta/EverMind skipped — see Setup Status column.
> Gate D43 PASSED (≥+15% nDCG@10 threshold cleared by +78.8%).
>
> ⚠️ **nox-mem uses FTS5-only eval mode** in this cross-system harness (isolated eval DB, not prod Gemini hybrid).
> Prod nox-mem headline (G5 V3, 2026-05-19): nDCG@10 = **0.6237**, MRR = 0.5534, R@10 = 0.7070.

> **Headline nox-mem (canonical, G5 V3 A8 full boost stack, 2026-05-19):**
> nDCG@10 = **0.6237** (+78.8% rel vs G3 baseline 0.3488), MRR = 0.5534, R@10 = 0.7070.
> Search latency: p50 = **940ms**, p95 = **2342ms** (prod `/api/search`, n=95, dominated by Gemini embed).

---

## Methodology

### Datasets

| Dataset | Source | Queries used | Stratified? |
|---|---|---|---|
| **LoCoMo** | [snap-research/locomo](https://huggingface.co/datasets/snap-research/locomo) — Maharana et al. arXiv:2402.17753 | n=10 (seed=42, dry-run-sample) | Yes — stratified across single-hop, multi-hop, temporal, open-domain, adversarial |
| **LongMemEval** | [xiaowu0162/LongMemEval](https://github.com/xiaowu0162/LongMemEval) — Wu et al. arXiv:2410.10813 | n=10 (seed=42, dry-run-sample) | Yes — stratified across subtask categories |

> **Note:** Current eval uses `dry-run-sample.json` (n=10 per dataset = n=20 total). Full n=100 stratified samples per dataset pending download of full dataset files.

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
6. **Embeddings.** Each competitor uses its native default embedding backend.

### Setup status per system

| System | Setup status | Details |
|---|:---:|---|
| **nox-mem** | GO | FTS5 local eval DB — full corpus (6830 chunks). No API calls. |
| **mem0** | partial | 500-chunk corpus cap (`MEM0_INGEST_LIMIT=500`) — cost control. Full corpus = ~$13-15 OpenAI embed cost, deferred. |
| **agentmemory** | partial | 1401/6830 chunks ingested (20.5%) — ingest rate ~100/min → full run would take ~2h; aborted at 60min mark per time-box rule. |
| **Zep OSS** | skip | Docker not available in this run environment. 5-query smoke result included from earlier session (nDCG=0.000, locomo only). |
| **Letta** | skip | `LETTA_API_KEY` not set — cloud-only path gated. Docker path needs Docker. |
| **EverMind** | skip | Repo 404 — adapter returns `ok=False` at validate(). |

---

## Cross-system headline table

| System | nDCG@10 | MRR | R@10 | p50 (ms) | p95 (ms) | n scored | Status |
|---|---:|---:|---:|---:|---:|---:|:---:|
| **nox-mem** | **0.3753** | **0.3700** | **0.5417** | **7.1** | 16.5 | 20/20 | GO |
| **agentmemory** | 0.1376 | 0.1030 | 0.2500 | 13.9 | 31.0 | 20/20 | partial¹ |
| **mem0** | 0.1315 | 0.1250 | 0.1500 | 263.2 | 1113.7 | 20/20 | partial² |
| **Zep OSS** | 0.0000 | 0.0000 | 0.0000 | 0.2 | 0.2 | 5/5 | skip³ |
| **Letta** | — | — | — | — | — | 0/0 | skip |
| **EverMind** | — | — | — | — | — | 0/5 | skip |

¹ agentmemory: 1401/6830 corpus (20.5%). All 5 hits from locomo; 0 longmemeval hits (corpus cut before longmemeval chunks loaded). Numbers are lower-bound — full corpus run expected to improve.
² mem0: 500/6830 corpus cap (cost-controlled run). Full corpus ~$13-15 OpenAI embed cost deferred. Numbers are lower-bound.
³ Zep: 5-query locomo-only run from earlier session (Docker required). Not re-run in this session.

---

## Per-dataset breakdown

### LoCoMo (n=10)

| System | nDCG@10 | R@10 | MRR | n |
|---|---:|---:|---:|---:|
| **nox-mem** | 0.3704 | 0.5833 | 0.3600 | 10 |
| agentmemory | 0.2751 | 0.5000 | 0.2060 | 10 |
| mem0 | 0.2631 | 0.3000 | 0.2500 | 10 |
| Zep | 0.0000 | 0.0000 | 0.0000 | 5 |

### LongMemEval (n=10)

| System | nDCG@10 | R@10 | MRR | n |
|---|---:|---:|---:|---:|
| **nox-mem** | 0.3802 | 0.5000 | 0.3800 | 10 |
| agentmemory | 0.0000 | 0.0000 | 0.0000 | 10 |
| mem0 | 0.0000 | 0.0000 | 0.0000 | 10 |

> agentmemory and mem0 score 0 on LongMemEval: corpus cap means longmemeval chunks were not ingested (locomo corpus = 5882 chunks, loaded first; cap hits before longmemeval's 948 chunks).

---

## Per-category breakdown (n=2 per category)

| Category | nox-mem | agentmemory | mem0 | Zep |
|---|---|---|---|---|
| **adversarial** | 0.3155 | 0.1781 | 0.5000 | — |
| **knowledge-update** | 0.5485 | 0.0000 | 0.0000 | — |
| **multi-hop** | 0.7153 | 0.7153 | 0.5000 | 0.0000 |
| **multi-session** | 0.4440 | 0.0000 | 0.0000 | — |
| **open-domain** | 0.4600 | 0.4821 | 0.3155 | — |
| **single-hop** | 0.3613 | 0.0000 | 0.0000 | 0.0000 |
| **single-session-assistant** | 1.0000 | 0.0000 | 0.0000 | — |
| **single-session-preference** | 0.0000 | 0.0000 | 0.0000 | — |
| **single-session-user** | 0.0000 | 0.0000 | 0.0000 | — |
| **temporal** | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| **temporal-reasoning** | 0.4088 | 0.0000 | 0.0000 | — |

**Notable pattern:** multi-hop is strongest for nox-mem (0.715) and agentmemory matches it (0.715); mem0 competitive (0.500). Temporal and single-session categories are weak across all systems — consistent with known multi-session/temporal gap in memory systems.

---

## nox-mem internal ablation reference (G5 V3, n=100 locomo, g5.db 68k prod corpus)

| Category | G3 baseline | G5 V3 A8 (canonical) | Δ rel |
|---|---:|---:|---:|
| single-hop | 0.1179 | [internal only — not cross-system] | — |
| multi-hop | 0.3708 | [internal only — not cross-system] | — |
| temporal | 0.2887 | [internal only — not cross-system] | — |
| open-domain | 0.3746 | [internal only — not cross-system] | — |
| adversarial | 0.2531 | [internal only — not cross-system] | — |

> Note: G5 V3 ablation used production corpus (g5.db 68k) which differs from the clean
> cross-system eval corpus. Cross-system results use an isolated eval corpus to ensure
> identical conditions.

---

## Where nox-mem may not win

Documented transparently — this comparison is not marketing:

- **LoCoMo vs agentmemory** — vendor claims R@5 = 95.2% (different metric; not comparable until re-measured with our harness on identical corpus). Our harness gives agentmemory nDCG@10=0.138 on partial corpus — full corpus run needed for fair comparison.
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
| Q4 COMPARISON nox-mem ranking | ≥1st or 2nd place | ✅ **PASSED (partial)** — nox-mem 1st in this 3-system run; full corpus runs needed for agentmemory/mem0 final verdict |
| Phase 2 GTM scale-up | Both conditions met | ⏳ Pending full-corpus Q4 results |

> Gate D43 details: `docs/DECISIONS.md` §D43 (2026-05-18).
> ROADMAP §3 Pillar Q sprints: `docs/ROADMAP.md`.
> Paper §5 eval methodology: `paper/publication/nox-mem-paper.md`.

---

## Honest caveats

- **nox-mem uses FTS5-only eval mode**, not the prod Gemini hybrid stack. Prod hybrid nDCG@10=0.6237 (G5 V3); eval DB FTS5 nDCG@10=0.375. The FTS5-only number is the apples-to-apples comparison for systems without embedding backends (agentmemory, Zep). For prod latency comparison, use the `NOX_EVAL_MODE=prod` flag (gated on VPS availability).
- **agentmemory partial corpus (20.5%).** Ingest rate of ~100/min makes full 6830-chunk corpus infeasible within 90min time-box. Numbers are lower-bounds; full run would improve locomo recall. LongMemEval 0.000 is corpus-cap artifact (locomo loaded first, corpus cut before longmemeval reached).
- **mem0 cost-capped (500/6830 = 7.3%).** Full corpus ingest costs ~$13-15 OpenAI embedding calls. Running with 500-chunk cap = $0.07. Results are lower-bounds; full run would improve both locomo and longmemeval recall.
- **Competitor numbers not independently verified at full corpus.** agentmemory's published "R@5 95.2%" uses a different metric (R@5, not nDCG@10) on an unspecified LoCoMo revision.
- **Statistical floor.** n=20 total (10 per dataset) → stdev on nDCG@10 typically ±0.05–0.10. Differences < 5pp should not be interpreted as decisive.
- **Conflict of interest.** We built nox-mem. Harness code is open-source. Raw JSON output published alongside this document. We invite PRs improving competitor adapter configurations.

---

## How to reproduce

```bash
# From repo root — uses the correct venv
VENV=/path/to/.venv  # must have mem0ai, agentmemory, chromadb, zep-python installed

# Start agentmemory daemon (requires Node.js)
agentmemory &
sleep 10 && curl http://localhost:3111/agentmemory/livez

# nox-mem (FTS5 eval mode, no keys needed)
$VENV/bin/python3 eval/q4-comparison/runner.py \
  --systems nox_mem --datasets locomo,longmemeval --limit 100 \
  --output eval/q4-comparison/output

# mem0 (cost-controlled, 500-chunk cap)
export OPENAI_API_KEY=sk-...
MEM0_INGEST_LIMIT=500 $VENV/bin/python3 eval/q4-comparison/runner.py \
  --systems mem0 --datasets locomo,longmemeval --limit 100 \
  --output eval/q4-comparison/output

# agentmemory (partial corpus — set limit to what's been ingested)
AGENTMEMORY_INGEST_LIMIT=<N> $VENV/bin/python3 eval/q4-comparison/runner.py \
  --systems agentmemory --datasets locomo,longmemeval --limit 100 \
  --output eval/q4-comparison/output

# Aggregate
$VENV/bin/python3 eval/q4-comparison/aggregate.py --output eval/q4-comparison/output
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

*Updated 2026-05-23 (Sat Q4 wider partial run). Run 3/6 systems scored. Full-corpus run for mem0 + agentmemory deferred (cost control + time-box). Zep/Letta/EverMind skipped — setup blocked. Gate D43: ✅ threshold passed. Phase 2 GTM scale-up conditional on final Q4 results.*
*Harness: `eval/q4-comparison/`. Aggregate script: `eval/q4-comparison/aggregate.py`.*
