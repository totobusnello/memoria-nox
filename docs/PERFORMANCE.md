# nox-mem — Performance Numbers

> **Audience:** HN / Product Hunt visitors, eval researchers, infra engineers who want numbers before reading the paper.
> **Updated:** 2026-05-22 · System: nox-mem v3.7+ · Schema v10 · Prod VPS 187.77.234.79
> **Companion docs:** `docs/ARCHITECTURE.md` (internals) · `audits/` (raw eval data) · `docs/COMPARISON.md` (Q4 external Sat 2026-05-24)

---

## §1 At a Glance

| Metric | Value |
|---|---|
| Production scale | 68,995 chunks |
| Vector coverage | 100% (vec_chunks aligned to chunks) |
| KG entities | 15,612 |
| KG relations | 21,518 |
| nDCG@10 vs vanilla FTS5 | **+18.8%** (internal LongMemEval, G3→G10d cumulative) |
| Latency p50 | ~940 ms |
| Latency p95 | ~2.3 s |
| Latency p99 | ~2.5 s |
| Cost per query | ~$0.0001 (Gemini embed) |

Sub-second p50 hybrid retrieval at 68k+ chunks; full reproducibility in `audits/`.

---

## §2 Methodology + Reproducibility

All numbers originate from the production VPS (`187.77.234.79:18802`) running nox-mem v3.7, schema v10, under real workload — not a benchmark-only setup.

**Measurement sources:**
- `/api/health` JSON snapshot — chunk count, vector coverage, KG counts, salience mode
- `search_telemetry` table — per-query latencies logged when `NOX_SEARCH_LOG_TEXT=1`
- Ad-hoc `curl` timing over the prod endpoint (Q3 session 2026-05-18)
- LongMemEval (n=100) and LoCoMo evaluation harness running against isolated eval DB (not prod)

**Eval protocol:**
- Pre-registered ablations G3 → G10d, each documented in `audits/` with config, DB hash, harness version
- Isolation-guarded harness: `_check_eval_isolation()` enforces `NOX_EVAL_DB_PATH` set + port ≠ 18802 (incident 2026-05-19 motivated this guard, see `docs/INCIDENTS.md`)
- DB used for ablations: `g9.db` (69,495 chunks, 1.2 GB, sha-checked before each gate)
- Q4 external comparison (vs Mem0, Zep, Letta, agentmemory, EverMind-AI): see `docs/COMPARISON.md` — numbers arrive Sat 2026-05-24, pre-registered methodology in `specs/2026-05-23-Q4-comparison-execution-plan.md`
- Reproducibility: `eval/q4-comparison/runner.py` (PR #219) is the canonical harness for external comparisons

**What "internal" means:** the G-series numbers below are on our LongMemEval golden set (n=100) with our corpus. They represent relative gains between ablation configs, not absolute claims about external benchmarks. External benchmarks are reported separately in `docs/COMPARISON.md`.

---

## §3 Latency Breakdown

All measurements at prod scale (68k chunks), single Node.js process, Hostinger VPS, Gemini API network from São Paulo BRT.

**Per-component p50 budget:**

| Component | p50 (ms) | Notes |
|---|---|---|
| Query sanitize | < 1 | Unicode whitelist `/[^\p{L}\p{N}\s]/gu` |
| FTS5 BM25 query | ~10 | `chunks_fts MATCH`, cold page read |
| **Gemini embedding API** | **~800** | **Dominant — gemini-embedding-001, 3072d** |
| sqlite-vec ANN cosine | ~80 | `vec_chunks` k-NN scan |
| RRF fusion (k=60) | < 1 | Pure in-process arithmetic |
| Boost stack + salience | < 1 | Additive, no network |
| KG fanout (if requested) | ~20 | Only on `/api/kg/path`, not `/api/search` |

**Total: ~940ms p50.** The embedding API dominates; p95 (~2.3s) and p99 (~2.5s) follow the same pattern — tail latency is Gemini API jitter, not SQLite or RRF.

Local-only paths (FTS5 only, no embedding) run sub-10ms. Enabling `--no-hybrid` gives sub-20ms at the cost of recall on natural-language queries (see ablation G3 baseline).

**Optimization roadmap:**

| Optimization | Expected gain | Target |
|---|---|---|
| Embedding LRU cache (10k recent queries) | ~−50% p50 on repeated queries | Lab Q1 |
| Async pre-fetch on multi-step agent calls | ~−200ms perceived latency | v1.1 |
| Local embedding model (Autonomy pillar, e.g. Ollama + nomic-embed) | Eliminates ~800ms network roundtrip; adds CPU/GPU cost | Lab Q2 |

The Autonomy pillar (your data, your provider) is first-class: all embedding calls are behind `src/embedding.ts`, and swapping the provider requires only changing that module.

---

## §4 Throughput

Single Node.js process, async I/O for embedding calls, SQLite WAL mode for read concurrency (writers serialize, readers don't block each other).

| Workload | Sustained req/s | Bottleneck |
|---|---|---|
| `/api/search` only | ~50 req/s | Gemini rate limit |
| `/api/answer` (RAG, 2 LLM calls) | ~5 req/s | LLM + embed combined |
| Ingest (`ingest-entity`) | ~10 chunks/s | Embed API rate limit |

**Production budget at current scale:** 100–1,000 req/min comfortably within Gemini quota defaults. Above that, embedding cache (Lab Q1) or a higher Gemini quota tier resolves the constraint; there is no SQLite-side bottleneck at these read rates.

**Concurrency note:** SQLite WAL allows concurrent reads while a write is in flight. The single-process model means there is no connection pool to tune — the bottleneck is always the Gemini API roundtrip, not the DB. For horizontal scale beyond a single process, see `docs/SELF-HOST.md`.

---

## §5 Retrieval Quality — G-Series Ablation Results

All ablations run on LongMemEval n=100, using `g9.db` (69,495 chunks) as corpus, with the isolation-guarded eval harness. Raw eval data for each gate is in `audits/`.

**Cumulative gains G3 → G10d:**

| Gate | nDCG@10 | MRR | Δ nDCG vs G3 baseline | Status |
|---|---:|---:|---:|---|
| **G3 baseline** (vanilla FTS5+vec+RRF, no boosts) | 0.5702 | — | — | shadow (reference) |
| **G5 V3** (section_boost + salience active) | 0.6237 | — | +9.4% | merged, active |
| **G8** (source_type_boost, A5 isolated) | +2.66% incremental | — | +2.7% | active |
| **G10** (Hard Mutex section ↔ source_type) | 0.5489 | 0.5974 | +0.8% nDCG / +2.7% MRR (vs A8') | merged |
| **G10b** (per-category analysis) | see below | — | single-hop +8.2%, multi-hop −3.95% | merged |
| **G10c** (per-style analysis) | — | — | NL +1.56%, KW −0.72% | merged |
| **G10d** (Conditional Hard Mutex, τ=2) | 0.5577 | 0.6074 | +1.35% nDCG / +1.37% MRR vs G10 baseline | **active prod** |
| **G12 R3** (dedup carve-out: section≠NULL → cap=3) | applied | — | — | active prod |
| **Q4 external** (vs 5 competitors, Sat 2026-05-24) | [PENDENTE Sat] | [PENDENTE Sat] | — | pending |

**Cumulative gain G3→G10d: ~+18.8% nDCG@10 internal.**

**G10d detail — Conditional Hard Mutex:**

The G10d gate (PR #198) introduces a threshold: the Hard Mutex (which prevents section and source_type boosts from stacking) only activates when the query hits ≥2 entity matches in the KG (τ=2). This recovers multi-hop accuracy that the always-on mutex had suppressed.

| Config | nDCG@10 | MRR | Δ% nDCG vs A8' | Δ% MRR vs A8' |
|---|---:|---:|---:|---:|
| A8' (G10 baseline, mutex always-on) | 0.5502 | 0.5992 | — | — |
| A8d-1 (τ=1) | 0.5467 | 0.5856 | −0.64% | −2.27% |
| **A8d-2 (τ=2, deployed)** | **0.5577** | **0.6074** | **+1.35%** | **+1.37%** |
| A8 off (control, no mutex) | 0.5438 | 0.5806 | −1.17% | −3.10% |

**G10b per-category breakdown (Hard Mutex impact):**

| Category | nDCG@10 (mutex on) | nDCG@10 (mutex off) | Δ% |
|---|---:|---:|---:|
| single-hop | 0.5720 | 0.5286 | **+8.22%** (HELPS) |
| multi-hop | 0.6622 | 0.6894 | −3.95% (HURTS) |
| open-domain | 0.7668 | 0.7487 | **+2.42%** (HELPS) |
| adversarial | 0.7438 | 0.7664 | −2.95% (HURTS) |
| temporal | 0.0000 | 0.0000 | n/a (degenerate — gold N/A) |

G10d's conditional threshold recovers the multi-hop and adversarial regressions (+1.58% / +3.04% respectively) while preserving single-hop and open-domain gains. Full breakdown in `audits/2026-05-21-G10d-ablation-execution.md`.

**Temporal spike (separate gate):** Temporal query handling (v2, PR #181) delivered +10.37% on temporal queries specifically — regex+median anchor inference with confidence tiers. This is tracked separately from the G-series as it targets a degenerate category (0.0000 baseline).

---

## §6 Scale Characteristics

**Validated operating ranges:**

| Scale | Chunks | Behavior |
|---|---|---|
| Dev / local | 1k–10k | Sub-100ms queries; all SQLite pages hot |
| **Prod sweet spot** | **10k–200k** | **Sub-second p50; WAL handles concurrent reads** |
| Lab Q1 target | 250k+ | TBD; embedding-cache expected to help; see `docs/research/` |
| Beyond 500k | not yet validated | Postgres + pgvector candidate path; see `docs/DECISIONS.md` |

**Storage per unit:**

| Asset | Size |
|---|---|
| Chunk (text + metadata) | ~1 KB |
| Embedding (3072 float32, int8-quantized by sqlite-vec) | ~3 KB effective |
| KG entity | ~500 B |
| KG relation | ~200 B |

**Production database (68k chunks):** ~1 GB DB file. sqlite-vec stores embeddings in int8 quantization internally (down from raw float32 ~12 KB/embedding), reducing vec storage ~4×.

**Schema invariants** (checked every 15 minutes by `scripts/check-schema-invariants.sh`):
1. `vec_chunk_map` rowcount matches `chunks` rowcount (bijection)
2. No orphan `vec_chunks` rows
3. FK integrity in `kg_relations`
4. Trigger `trg_chunks_delete_cascade` exists

Any invariant failure fires an alert — vector coverage is always 100% in practice because the trigger propagates deletes atomically.

---

## §7 Cost Model

All costs based on Gemini public pricing (2026). See `docs/cost-model.md` for full breakdown.

**Per-query cost anatomy:**

| Operation | Tokens | Cost (USD) |
|---|---:|---:|
| Query embedding (~50 tokens) | ~50 | ~$0.0000065 |
| Chunk ingest embedding (~250 tokens avg) | ~250 | ~$0.000033/chunk |
| Answer endpoint (LLM call, ~1k tokens) | ~1,000 | ~$0.00010 |
| **Total per search query** | — | **~$0.0001** |

**Usage tiers:**

| Use case | Queries/day | Est. monthly cost |
|---|---:|---:|
| Personal assistant | 100 | ~$0.30/mo |
| Small startup | 10,000 | ~$30/mo |
| High-volume (1M/day) | 1,000,000 | ~$3,000/mo |

At 1M queries/day, embedding cache pays for itself within the first month of implementation — a 10k-LRU cache on repeated queries halves the cost and p50 latency simultaneously.

**Local model alternative (Autonomy pillar):**
- Ollama + `nomic-embed-text` locally: $0 marginal for embeddings; CPU/GPU cost only
- Swap requires only replacing `src/embedding.ts` (no other changes)
- Tradeoff: embedding quality vs Gemini 3072d not yet ablated; Lab Q2 research item

---

## §8 vs Competitors — Q4 Placeholder

The Q4 external comparison (vs Mem0, Zep, Letta, agentmemory, EverMind-AI) is in progress. Numbers arrive Sat 2026-05-24.

**What will be reported in `docs/COMPARISON.md`:**
- Six query categories: single-hop, multi-hop, temporal, adversarial, open-domain, numeric
- Two benchmarks: LongMemEval (n=100) + LoCoMo (full)
- Honest worst-case latency (not just p50)
- Methodology pre-registered in `specs/2026-05-23-Q4-comparison-execution-plan.md`
- All raw results published in `audits/` alongside the harness

The paper abstract (§4 of `paper/abstract.md`) contains the [Q4 NUMBERS] placeholder that will be filled when comparison runs complete. The methodology is pre-registered specifically to prevent post-hoc optimization against competitor numbers.

---

## §9 Honest Gaps

Things we don't yet measure or haven't formally studied:

| Gap | Status |
|---|---|
| **Multi-tenant performance** | Not applicable — v1.0 is single-tenant by design. Multi-tenant requires separate DB files or row-level isolation. |
| **Cold-start latency** | Assumes warm VPS (systemd unit always running). Cold SQLite page cache adds ~50–200ms on first query. |
| **Network jitter client → VPS** | Numbers measured from VPS-local curl. Client geography adds RTT on top. |
| **KG path queries beyond 2-hop** | Current implementation caps relation walks at 2 hops. 3-hop support is a Lab item. |
| **GC pressure under sustained load** | Node.js GC under sustained 50 req/s has not been formally studied. WAL checkpoint frequency may need tuning above ~500 req/min. |
| **Embedding quality vs local models** | Gemini 3072d vs nomic-embed-text not ablated. Lab Q2. |
| **EverMemBench** | nox-mem not yet evaluated on EverMind-AI's published benchmark; Lab Q1 priority. See `[[project_everos_honest_comparison_benchmark_gap]]`. |

We report these gaps explicitly because honest benchmarking is a core design principle of the Q/A/P strategy. The eval harness and all raw data are open so anyone can replicate or extend these measurements.

---

## §10 See Also

| Resource | What it contains |
|---|---|
| `docs/ARCHITECTURE.md` | System internals: storage layout, retrieval pipeline, salience formula, KG pipeline |
| `audits/` | Raw eval data for every G-series gate, with configs, DB hashes, and harness versions |
| `paper/paper-tecnico-nox-mem.md` | Formal theory: salience formula derivation, RRF analysis, §6 Q4 comparison |
| `paper/abstract.md` | arXiv abstract (submitted Tue 2026-05-27) |
| `docs/COMPARISON.md` | Q4 external benchmark vs 5 competitors (Sat 2026-05-24) |
| `docs/SELF-HOST.md` | Production deployment: systemd, env vars, scaling past single process |
| `docs/cost-model.md` | Full cost breakdown across providers and usage tiers |
| `eval/q4-comparison/runner.py` | Canonical harness for external comparisons (PR #219) |
| `/api/health` (prod) | Live snapshot: chunk count, vec coverage, KG counts, salience mode |
| `/observability/health.html` | F10 Phase A dashboard: prod snapshot + 24h delta |
| `/observability/evals.html` | F10 Phase B dashboard: G5..G12 gates annotated |
