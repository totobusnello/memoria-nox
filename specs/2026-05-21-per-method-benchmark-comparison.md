# Per-method Benchmark — nox-mem vs Mem0/Zep/EverCore/HyperMem

> **Apples-to-apples comparison** rodando nox-mem (post-Wave A) e 4 competitors no MESMO dataset, MESMO protocolo, MESMO evaluator. Fecha "benchmark gap" memory cravada há semanas.

**Status:** SPEC — implementation pending, gated em D49 phase 2 completion (avoid disrupting shadow telemetry)
**Data:** 2026-05-21
**ID novo:** Q4b (parte do pilar Q — Quality; sucessor lógico de G10/G11)
**Owner:** Toto (decisão); scientist agent (execução planejada); Forge (review final paper §5.6)
**Esforço estimado:** ~25-35h (4-6h spec ✅ + 20-30h impl/exec)
**Dependências:**
- D49 phase 2 closed (não pode rodar com shadow ativo — contamina latency/scores)
- Wave A merged ✅ (PR #182, G10/G10b/G10c validated)
- Eval harness R01a ✅
- Memory hard rule `[[eval-harness-must-explicit-isolate-db]]` (NOX_DB_PATH guard)
**Bloqueia:**
- Paper §5.6 (head-to-head numbers)
- GTM README hero claim "we beat the state of the art" (ou honest "we trail by X%")
- Q/A/P closure — pilar Q final milestone
**Cross-ref:**
- `docs/ROADMAP.md` §pilar Q
- `docs/DECISIONS.md` D43 (Q4 gate Phase 2 OPEN)
- `paper/paper-tecnico-nox-mem.md` §5.5 (post-G10c update)
- `audits/2026-05-21-G10b-per-category-mutex-ablation.md`
- `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- Memory: `[[benchmark-gap-longmemeval-locomo]]`, `[[everos-honest-comparison-benchmark-gap]]`, `[[everos-benchmark-publisher-competitor]]`, `[[qap-pillars-strategic-decision]]`

---

## 1. Problema

A memory line cravada em `[[benchmark-gap-longmemeval-locomo]]` documenta o gap há semanas:

> Competitors reportam standardized benchmarks (LongMemEval, LoCoMo, EverMemBench); nox-mem usa golden set custom ~10 queries (depois expandido pra n=78 pós-cleanup). Sem harness comparable não dá pra responder "nossos números são melhores?"

A line companion em `[[everos-honest-comparison-benchmark-gap]]` cravou que rodar nox-mem no EverMemBench fecha o gap + dá número comparable vs **EverCore 83% LongMemEval / 93% LoCoMo** e **HyperMem 92.73% LongMemEval**.

Hoje (2026-05-21):
- Wave A deployed (+18.8% nDCG@10 vs baseline custom n=78) → Q4 gate Phase 2 OPEN (D43)
- G10/G10b/G10c validated mutex section ↔ source_type (+0.79% nDCG agg / +2.65% MRR)
- Paper v1.2 está bom **internamente** — mas §5 ainda compara contra nossos próprios baselines, não contra estado da arte

**Sem o per-method benchmark:**
- GTM materials não podem afirmar "we beat X" — só "we improved +18.8% over our prior baseline"
- Paper §5.6 fica incompleto; reviewer arXiv vai pedir comparison cross-system
- Q/A/P pilar Q (Quality — "números #1") não fecha — está parado em "número 1 vs nós mesmos", não vs world
- Investor/board pitch fica vulnerável a "ok, mas vs Mem0?" → resposta "não rodamos" mata credibilidade

**Apples-to-apples principle:** competitor papers reportam números em datasets com protocolos divergentes (LLM-judge diferentes, top-k diferentes, retrieval pool sizes diferentes). Comparar **publicados** seria cherry-pick. A única forma defensável é **rodar todos com mesmo dataset + mesmo evaluator + mesmas métricas em isolamento**.

---

## 2. Objetivo

Gerar **apples-to-apples** benchmark numbers comparando 5 sistemas em 2-3 datasets standardized:

| Sistema | Versão alvo | Status setup |
|---|---|---|
| **nox-mem** | post-Wave A (commit pós-PR #182, G10/G10b/G10c validated) | ✅ Live (post D49 phase 2) |
| **Mem0** | latest release (docker pull) | 🔲 TBD |
| **Zep** | latest open-source release (docker compose) | 🔲 TBD |
| **EverCore** (EverMind-AI) | latest tag (5-service docker stack per memory) | 🔲 Heavy |
| **HyperMem** | latest release (repo clone) | 🔲 TBD |

| Dataset | Tamanho | Acesso | Métricas-alvo |
|---|---|---|---|
| **LongMemEval** | 500 queries, ~30 sessions/user | HuggingFace public dataset | nDCG@10, MRR, Recall@10, P@5, LLM-judge accuracy |
| **EverMemBench** | TBD (~200-500 per memory `[[everos-benchmark-publisher-competitor]]`) | HF dataset (EverMind-AI org) | nDCG@10, MRR, Recall@10 |
| **LoCoMo** (optional) | n=10 conversational episodes | HF dataset | Episode-level recall, multi-hop accuracy |

**Goal numérico:** publicar tabela 5×3 (sistemas × datasets) com **valores reais** + **stddev de 3 runs** + **cost USD por sistema**. Fechar paper §5.6.

---

## 3. Methodology — rigid protocol

### 3.1 Princípios não-negociáveis

1. **Mesmo dataset frozen** — golden queries idênticas por sistema. Sem variant do mesmo benchmark; usar versão imutável (HF snapshot SHA-pinned).
2. **Mesmo evaluator** — LLM-as-judge (GPT-4o ou Gemini 2.5 Flash) com prompt idêntico por dataset + scoring rubric idêntico. Para nDCG/MRR/Recall: gold-chunk matching exato (não LLM-judge).
3. **Mesmo retrieval pool size** — top-10 across all systems (k=10). Para LLM-judge accuracy: top-5 contexto pro evaluator.
4. **Isolation total** — cada sistema roda em **DB separada + porta API separada + processo separado**. Sequential execution, não paralelo (evita resource contention).
5. **3 runs by system × dataset** — reportar mean ± stddev. Mata variabilidade LLM-judge não-determinístico.
6. **Cost tracking** — logar custo USD (embedding API calls + LLM calls) por run. Total cost = embedding ingest + retrieval calls + LLM-judge.
7. **Hardware comparable** — mesma VPS (45.43.85.86 ou IP atual) ou local Mac M-class. NUNCA misturar hardware entre sistemas.

### 3.2 Per-system setup checklist

```
[ ] Clean DB / index dir
[ ] Same chunking strategy (TBD: each system uses own — documented as limitation)
[ ] Same embedding model when possible (Gemini 3072d for nox-mem; document where competitors differ)
[ ] Ingest LongMemEval / EverMemBench corpus via system's native API
[ ] Verify ingestion completeness (count chunks/messages/turns post-ingest)
[ ] Run smoke test (3 queries hand-picked) before full eval
[ ] Run full eval 3×, save raw JSON per run
[ ] Aggregate mean ± stddev per metric
[ ] Tear down (rm -rf docker volumes, free disk)
```

### 3.3 LLM-judge prompt (template)

```
You are evaluating a memory retrieval system. Given:
- Query: {query}
- Gold answer (from dataset): {gold_answer}
- Retrieved context (top-5 from system): {context}

Score 0-2:
- 2: Context fully supports answering the query equivalent to gold
- 1: Context partially supports (missing 1-2 key facts)
- 0: Context insufficient or wrong

Output JSON: {"score": <0|1|2>, "reasoning": "<brief>"}
```

Cost projection: 500 queries × 3 runs × 5 systems × 1 LLM call = **7500 LLM-judge calls** per dataset.
- Gemini 2.5 Flash Lite: ~$0.00015/1K tokens × ~2K tokens/call ≈ **$2.25 per dataset full sweep** (cheap)
- GPT-4o: ~$2.50/1M input × ~2K tokens/call ≈ **$37.50 per dataset full sweep** (recommended for paper credibility)

**Decisão:** GPT-4o como judge **principal**; Gemini 2.5 Flash como **sanity-check secondary judge** (kappa-agreement entre judges como QC metric).

### 3.4 Multi-testing correction

Com 5 sistemas × 3 datasets × 4 métricas = **60 comparisons**:
- Apply **Benjamini-Hochberg FDR** at α=0.05 across all pairwise comparisons
- Report both raw and adjusted p-values
- Pairwise Welch t-test (não-paired, unequal variance — sistemas diferentes)

Effect size: Cohen's d para nDCG@10 deltas. Magnitude interpretation: small (0.2) / medium (0.5) / large (0.8).

---

## 4. Datasets — acesso e protocolo

### 4.1 LongMemEval

- **Repo:** github.com/xiaowu0162/LongMemEval (Wu et al. 2024)
- **HF dataset:** `xiaowu0162/longmemeval` (public, free)
- **Queries:** 500 split em 7 categorias (single-session-user, single-session-assistant, multi-session, temporal-reasoning, knowledge-update, single-session-preference, abstention)
- **Session length:** mean ~30 sessions/user × ~10 turns/session
- **Standard metric (paper):** answer accuracy via GPT-4 judge contra gold answer
- **Public leaderboard:** competitors self-report — EverCore 83%, HyperMem 92.73%
- **Risk:** GPT-4 judge non-determinism → reportar 3-run stddev mandatório
- **Pre-req:** HF `datasets` lib + free tier sufficient (no gated access)

### 4.2 EverMemBench

- **Repo:** github.com/EverMind-AI/EverOS (Apache 2.0, 5k stars)
- **HF dataset:** procurar `EverMind-AI/evermembench` ou similar (TBD via WebSearch real)
- **Size:** TBD (memory line indica "publica HF dataset" mas size não cravado)
- **Standard metric:** custom — verificar EverOS docs antes de rodar
- **Risk:** EverMemBench pode ter retrieval format específico do EverOS que penaliza outros sistemas — flag como methodology constraint
- **Pre-req:** clone repo + ler eval script + entender scoring rubric ANTES de rodar

### 4.3 LoCoMo (optional, Phase F+)

- **Repo:** github.com/snap-research/locomo (Maharana et al. 2024)
- **Dataset:** 10 long-form conversational episodes (35 turns avg), multi-hop
- **Metric:** episode-level recall + multi-hop reasoning accuracy
- **Risk:** small n=10 → high variance, complementary not primary
- **Decision:** correr apenas se Phase C/D/E deliver clean results; senão skip

---

## 5. Per-system integration sketches

> **All snippets below are pseudocode / illustrative.** Real commands depend on each project's current release docs at impl time.

### 5.1 nox-mem (baseline, isolated copy)

```bash
# Clone main DB to isolated path
cp -p /root/.openclaw/workspace/tools/nox-mem/nox-mem.db /tmp/bench/nox-mem-bench.db

# Re-ingest LongMemEval corpus (custom format → entity files)
NOX_DB_PATH=/tmp/bench/nox-mem-bench.db \
  nox-mem ingest /tmp/bench/longmemeval-corpus/ --batch

# Run eval via existing harness (extended w/ LongMemEval format support)
NOX_DB_PATH=/tmp/bench/nox-mem-bench.db \
  NOX_ALLOW_PROD_INGEST=0 \
  python eval/run_longmemeval.py --port 18803 --runs 3 --judge gpt-4o
```

Pre-req: extend `eval/` harness pra ler LongMemEval JSON schema (não nosso golden set format). ~2h work.

### 5.2 Mem0

```bash
# Docker setup (Mem0 server)
docker pull mem0ai/mem0:latest
docker run -d -p 8000:8000 -v /tmp/bench/mem0-data:/data \
  -e OPENAI_API_KEY=$OPENAI_API_KEY mem0ai/mem0

# Ingest via Python client
pip install mem0ai
python eval/ingest_to_mem0.py --corpus longmemeval --endpoint http://localhost:8000
python eval/run_eval.py --system mem0 --endpoint http://localhost:8000 --runs 3
```

Setup complexity: **LOW** (single docker container, well-documented API).

### 5.3 Zep

```bash
# Zep open-source (docker-compose with PostgreSQL backend)
git clone https://github.com/getzep/zep
cd zep && docker-compose up -d
# Wait for migrations
python eval/ingest_to_zep.py --corpus longmemeval --endpoint http://localhost:8001
python eval/run_eval.py --system zep --endpoint http://localhost:8001 --runs 3
```

Setup complexity: **MEDIUM** (postgres + zep server + embedding worker).

### 5.4 EverCore / EverMind-AI

```bash
# Per memory [[everos-benchmark-publisher-competitor]] — 5-service docker stack
git clone https://github.com/EverMind-AI/EverOS
cd EverOS && docker-compose -f docker-compose.bench.yml up -d
# Services: api / embedding / vector-store / kg-store / llm-proxy
# Wait ~5min for all services healthy
curl http://localhost:9000/health  # gate

python eval/ingest_to_evercore.py --corpus longmemeval
python eval/run_eval.py --system evercore --endpoint http://localhost:9000 --runs 3
```

Setup complexity: **HIGH** (5 services, custom config, possibly GPU-deps for embeddings).

### 5.5 HyperMem

```bash
# TBD pending real research — assume similar pattern
# May require model weights download (multi-GB) if cross-encoder reranker bundled
git clone https://github.com/<hypermem-repo>  # confirm via WebSearch
cd hypermem && pip install -e .
python eval/ingest_to_hypermem.py --corpus longmemeval
python eval/run_eval.py --system hypermem --runs 3
```

Setup complexity: **TBD** (likely MEDIUM-HIGH if reranker model is bundled).

---

## 6. Eval runner skeleton (pseudocode)

> **NOT to be implemented in this spec** — design only. Lives in separate Phase B spec/impl session.

```python
# eval/run_per_method_benchmark.py
import json, time, statistics, hashlib
from pathlib import Path
from typing import Literal

SYSTEMS = ['nox-mem', 'mem0', 'zep', 'evercore', 'hypermem']
DATASETS = ['longmemeval', 'evermembench', 'locomo']  # locomo optional
METRICS = ['ndcg@10', 'mrr', 'recall@10', 'p@5', 'llm_judge_accuracy']
RUNS = 3

def isolation_guard(system: str):
    """Sanity check before each run."""
    # nox-mem: NOX_DB_PATH must be /tmp/bench/, not prod
    # Others: docker container must be running
    # Common: assert API endpoint responds 200 OK
    ...

def ingest(system: str, dataset: str) -> dict:
    """Ingest dataset corpus into system's storage. Returns stats."""
    # Per-system adapter
    ...
    return {'chunks_ingested': N, 'duration_s': T, 'cost_usd': C}

def retrieve(system: str, query: str, k: int = 10) -> list[dict]:
    """Query system, return top-k chunks with scores."""
    # Per-system adapter — normalize response shape
    ...

def score_run(system: str, dataset: str, run_idx: int) -> dict:
    """Run all queries, compute metrics, save raw JSON."""
    queries = load_dataset(dataset)
    results = []
    for q in queries:
        retrieved = retrieve(system, q['query'], k=10)
        gold = q['gold_chunk_ids']
        results.append({
            'query_id': q['id'],
            'retrieved': [r['id'] for r in retrieved],
            'scores': [r['score'] for r in retrieved],
            'gold': gold,
            'latency_ms': r.get('latency_ms'),
        })
    # Compute metrics
    metrics = compute_metrics(results, gold_set=queries)
    # LLM-judge accuracy (separate sweep, sequential to save quota)
    judge_acc = llm_judge_accuracy(system, dataset, results, judge='gpt-4o')
    metrics['llm_judge_accuracy'] = judge_acc
    out_path = f'audits/data-benchmark/{dataset}/{system}/run{run_idx}.json'
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps({'metrics': metrics, 'results': results}, indent=2))
    return metrics

def aggregate(system: str, dataset: str) -> dict:
    """Mean ± stddev across 3 runs."""
    runs = [json.load(open(f'audits/data-benchmark/{dataset}/{system}/run{i}.json'))['metrics']
            for i in range(RUNS)]
    return {m: {'mean': statistics.mean([r[m] for r in runs]),
                'stddev': statistics.stdev([r[m] for r in runs])}
            for m in METRICS}

def main():
    for dataset in DATASETS:
        for system in SYSTEMS:
            isolation_guard(system)
            ingest(system, dataset)
            for run_idx in range(RUNS):
                score_run(system, dataset, run_idx)
            aggregate(system, dataset)
        # Tear down each system between datasets to free resources
        teardown_all()
    # Final cross-system aggregation
    write_comparison_table()
    write_significance_tests()  # Welch t-test + Benjamini-Hochberg FDR

if __name__ == '__main__':
    main()
```

---

## 7. Output artifacts

### 7.1 Raw data layout

```
audits/data-benchmark/
├── longmemeval/
│   ├── nox-mem/
│   │   ├── run0.json    # full results + metrics
│   │   ├── run1.json
│   │   ├── run2.json
│   │   └── aggregate.json
│   ├── mem0/...
│   ├── zep/...
│   ├── evercore/...
│   └── hypermem/...
├── evermembench/...
└── locomo/...
```

### 7.2 Summary audit

`audits/YYYY-MM-DD-per-method-benchmark.md` (estimated 2026-06-15 if start mid-Junho):

#### Comparison table template (empty — to fill at exec time)

| System | LongMemEval nDCG@10 | LongMemEval Judge Acc | EverMemBench nDCG@10 | LoCoMo nDCG@10 | Cost USD | Setup hours |
|---|---|---|---|---|---|---|
| nox-mem (Wave A) | _ ± _ | _ ± _ | _ ± _ | _ ± _ | $_ | _ |
| Mem0 | _ ± _ | _ ± _ | _ ± _ | _ ± _ | $_ | _ |
| Zep | _ ± _ | _ ± _ | _ ± _ | _ ± _ | $_ | _ |
| EverCore | _ ± _ | _ ± _ | _ ± _ | _ ± _ | $_ | _ |
| HyperMem | _ ± _ | _ ± _ | _ ± _ | _ ± _ | $_ | _ |

#### Statistical significance template

| Comparison | nDCG@10 Δ | Cohen's d | p-raw | p-FDR | Significant @ α=0.05? |
|---|---|---|---|---|---|
| nox-mem vs Mem0 (LongMemEval) | +_pp | _ | _ | _ | _ |
| nox-mem vs Zep (LongMemEval) | +_pp | _ | _ | _ | _ |
| nox-mem vs EverCore (LongMemEval) | +_pp | _ | _ | _ | _ |
| nox-mem vs HyperMem (LongMemEval) | +_pp | _ | _ | _ | _ |
| ... | | | | | |

#### Honest writeup section

- **Where nox-mem wins:** [fill]
- **Where nox-mem loses:** [fill]
- **Methodology caveats:**
  - Each system uses own chunking strategy (not normalized)
  - Embedding models differ (nox-mem: Gemini 3072d; competitors vary)
  - LLM-judge non-determinism (kappa between GPT-4o ↔ Gemini judges reported)
  - Dataset-specific corpus formats may favor certain systems
- **Follow-up actions:** [fill — e.g. "investigate why Mem0 wins multi-session category"]

---

## 8. Risks & mitigations

| Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Methodology differences across published papers (cherry-pick prone) | HIGH | HIGH | Re-run TUDO localmente, não comparar publicados |
| LLM-judge non-determinism | HIGH | MEDIUM | 3 runs mandatory + stddev reported + kappa entre 2 judges |
| Setup competitor system fails (broken docker, missing deps) | MEDIUM | HIGH | Allocate 2h budget per system; document failures honestly em "Setup hours" col |
| Cost overrun | LOW | MEDIUM | Budget cap $200 (3 datasets × 5 systems × $13 GPT-4o) + Gemini fallback |
| EverCore 5-service stack OOM on VPS | MEDIUM | HIGH | Run em local Mac M-class se VPS RAM insuficiente; document hardware delta |
| Cross-contamination entre runs | MEDIUM | CRITICAL | Strict isolation: docker stop + rm volume entre runs; nox-mem usa NOX_DB_PATH guard |
| HuggingFace dataset access gated | LOW | LOW | Verify access prior to Phase B; LongMemEval e LoCoMo são open |
| EverMemBench dataset não publicado / proprietary | MEDIUM | MEDIUM | Fall back to LongMemEval + LoCoMo only; document |
| Shadow telemetry D49 phase 2 contaminates nox-mem run | HIGH (if not gated) | HIGH | Gate FIRMLY em D49 phase 2 closed before nox-mem benchmark (this spec is gated already) |
| nox-mem perde em todas as métricas | MEDIUM | HIGH (reputational) | Report honest; convert into product roadmap input. Memory `[[everos-honest-comparison-benchmark-gap]]` cravou: "either way: closes benchmark gap, defensible answer" |

---

## 9. Estimated effort

| Phase | Description | Hours |
|---|---|---|
| **A — this spec** | Design + INDEX update + PR | 1-2h ✅ |
| **B — runner skeleton** | Implement `eval/run_per_method_benchmark.py` + isolation guards + per-system adapter interface | 4-6h |
| **C — Mem0 + Zep** | Docker setup + ingest adapter + smoke + full eval × 3 runs × 2 datasets | 6-10h |
| **D — EverCore + HyperMem** | Heavy stack setup + ingest + run; budget 4h per system | 8-12h |
| **E — nox-mem run** | After D49 phase 2 closes — isolated DB ingest + run × 3 × 2 datasets | 2-4h |
| **F — Writeup + paper §5.6** | Aggregate audits + significance tests + paper update + GTM messaging | 4-6h |
| **TOTAL** | | **~25-40h** |

---

## 10. Phasing & gates

```
A — Spec (THIS PR)              ─────[merge → INDEX updated]
                                       │
                                       ▼
B — Runner skeleton             ─────[separate spec/impl session, ~1 week post-A]
                                       │
                                       ▼
C — Mem0 + Zep integration      ─────[low setup cost → first competitor numbers]
                                       │
                                       ▼   ┌─── if Mem0/Zep already beat us materially:
                                       │   │    pause D — investigate before more setup
                                       │   │
                                       ▼   ▼
D — EverCore + HyperMem         ─────[heavy stack — only if C completed clean]
                                       │
                                       ▼
   GATE: D49 phase 2 closed (no shadow contamination)
                                       │
                                       ▼
E — nox-mem run                 ─────[LAST — avoids contaminating own shadow telemetry]
                                       │
                                       ▼
F — Writeup + paper §5.6        ─────[aggregate + significance tests + publish]
```

**Hard gate E:** nox-mem run MUST happen after D49 phase 2 closes. Memory `[[d49-phase-2-shadow-telemetry]]` (if exists) or HANDOFF.md check required before Phase E start.

**Cancel criteria:**
- If Phase C reveals **infrastructure problem with eval harness itself** (não com sistemas competitor) → halt + fix harness before D/E
- If cost projection exceeds $500 after Phase C real data → re-budget with Toto before Phase D
- If two consecutive competitor setups fail → escalate methodology to Toto before sinking more time

---

## 11. Success criteria

When fully executed (post-Phase F):

1. **Comparison table populated** with 5 systems × 3 datasets × 4-5 metrics + cost + setup hours
2. **Statistical significance** reported with FDR-corrected p-values + Cohen's d
3. **Raw JSON** preserved in `audits/data-benchmark/` (reproducible)
4. **Paper §5.6** updated with honest head-to-head numbers
5. **GTM messaging** updated:
   - IF nox-mem ≥ competitors em majority of metrics: README hero claim defensible
   - IF nox-mem < competitors: honest comparison page + roadmap item targeting closure
6. **Memory line closed:** `[[benchmark-gap-longmemeval-locomo]]` superseded by audit reference
7. **Q/A/P pilar Q closure:** "números #1" claim either validated or honestly downgraded

---

## 12. Open questions (for Toto resolution before Phase B start)

- [ ] **Judge choice:** GPT-4o primary + Gemini 2.5 Flash QC (default proposed), or single Gemini for cost? → default GPT-4o salvo override
- [ ] **Hardware:** VPS (45.43.85.86 / current IP) or local Mac M-class? EverCore 5-service stack pode forçar local. → default VPS, escalate se RAM insuficiente
- [ ] **Cost cap:** $200 default proposto. Toto aprovar? → default $200
- [ ] **Phase B owner:** scientist-high or executor-high? Spec recommends scientist-high (analysis-heavy). → default scientist-high
- [ ] **Re-include LoCoMo?** spec marca optional. → default skip Phase A-E, add em Phase F+ se time permite
- [ ] **Publish dataset:** após gerar raw data, publicar HF mirror (nox-mem-evidence/per-method-bench-2026-05) pra repro externo? → default yes (Autonomy pillar — transparency)

---

## 13. NÃO FAZEMOS (anti-scope)

- ❌ NÃO comparar vs published numbers — só re-run local same protocol
- ❌ NÃO comparar SaaS systems com closed APIs (sem repro local impossível) — só open-source
- ❌ NÃO usar custom golden set nox-mem aqui — esse benchmark é "vs world", não "vs nós"
- ❌ NÃO incluir reranker D01 (Cohere) na config nox-mem — Wave A baseline é a config production, reranker entra em benchmark separado se ativado
- ❌ NÃO rodar antes de D49 phase 2 closed — shadow telemetry corrompe scores
- ❌ NÃO normalizar chunking entre sistemas — cada sistema usa o próprio (documentado como methodology constraint, não bug)
- ❌ NÃO incluir LangChain/LlamaIndex/Haystack — esses são frameworks RAG genéricos, não memory systems comparáveis ao escopo nox-mem

---

## 14. Appendix — dataset URLs e access notes (TBD validation)

| Dataset | URL provável | Acesso | License | Validation pending |
|---|---|---|---|---|
| LongMemEval | huggingface.co/datasets/xiaowu0162/longmemeval | Public | MIT (verify) | ✅ confirm at Phase B |
| EverMemBench | huggingface.co/datasets/EverMind-AI/evermembench (guess) | Public (per memory) | Apache 2.0 (parent repo) | 🔲 confirm dataset name |
| LoCoMo | huggingface.co/datasets/snap-research/locomo | Public | TBD | ✅ confirm at Phase F |
| Mem0 source | github.com/mem0ai/mem0 | Apache 2.0 | Apache 2.0 | ✅ public |
| Zep source | github.com/getzep/zep | Apache 2.0 | Apache 2.0 | ✅ public |
| EverOS source | github.com/EverMind-AI/EverOS | Apache 2.0 | Apache 2.0 | ✅ public per memory |
| HyperMem source | TBD | TBD | TBD | 🔲 confirm via WebSearch Phase B |

---

## 15. References

- `audits/2026-05-21-G10b-per-category-mutex-ablation.md` — per-category Wave A breakdown
- `audits/2026-05-21-G10c-per-style-mutex-ablation.md` — per-style Wave A breakdown
- `paper/paper-tecnico-nox-mem.md` §5.5 (post-G10c update) — own-baseline comparison; this spec produces §5.6
- `docs/DECISIONS.md` D43 — Q4 gate Phase 2 OPEN (threshold ≥+15% nDCG met at +18.8%)
- Memory `[[benchmark-gap-longmemeval-locomo]]` — gap cravado há semanas
- Memory `[[everos-honest-comparison-benchmark-gap]]` — EverMemBench priority crava
- Memory `[[everos-benchmark-publisher-competitor]]` — EverCore/HyperMem published numbers reference
- Memory `[[eval-harness-must-explicit-isolate-db]]` — NOX_DB_PATH guard hard rule (4-layer defense)
- Memory `[[qap-pillars-strategic-decision]]` — pilar Q closure dependency

