# Design Spec — Neural Reranker (D01-v3 candidate) — `bge-reranker-v2-m3` via vLLM Local

**Status:** Design spec — parking-lot Lab Q1, gated em (1) D49/D50 closed; (2) per-method benchmark Phase A complete
**Data:** 2026-05-21
**Branch spec:** `spec/neural-reranker-design`
**Cross-links:**
- `specs/2026-05-07-D01-cross-encoder-reranker.md` (D01 v1 CUT 2026-05-08, D01 v2 OOM 2026-05-09 — fonte do aprendizado)
- `specs/2026-05-17-E15-codegraph-inspired-improvements.md` (E15 — parking-lot pós-R03 ou paralelo)
- `specs/2026-05-21-per-method-benchmark-comparison.md` (gate dependency)
- `docs/DECISIONS.md §2` (Q5 Qwen3-Reranker DEFERRED com 5 razões — esta spec endereça 3 delas)
- `docs/ROADMAP.md` (Lab pillar, 40% capacity)
- Memory `[[neural-reranker-evolution-vector]]` (parking-lot direction)
- Memory `[[lightrag-kg-incremental-merge-pattern]]` (bge-v2-m3 recomendado por LightRAG)
- Memory `[[everos-honest-comparison-benchmark-gap]]` (target gap fechamento via EverMemBench)

---

## 1. Objective

Adicionar uma camada de **cross-encoder reranker** após o RRF fusion + boost stack do hybrid pipeline para melhorar precision do top-K. Target: **+3-8% nDCG@10 absoluto** baseado em literatura BEIR/LongMemEval (cross-encoder rerank é vetor evolutivo confirmado em retrieval research moderno).

Especificamente:
- **Engine primário:** `BAAI/bge-reranker-v2-m3` (multilingual, 568M params, suporta PT-BR explícito).
- **Serving:** **vLLM local self-hosted** — preserva pilar **Autonomy** (zero vendor lock-in, dados não saem do perímetro).
- **Mode default:** `off`. Habilitação só após ablation real (G13) provar lift ≥+3% em corpus prod (`g5.db`/`g9.db` candidato).
- **Não-objetivo:** retraining, fine-tuning, Cohere/DeepInfra como primary path.

### Por que agora é diferente do D01 v1/v2 cut

| Razão D01 cut anterior | Esta spec endereça |
|---|---|
| **v1**: BGE-base inglês → -0.21 nDCG em PT-BR | **v3**: bge-**v2-m3** multilingual com 100+ línguas (incluindo PT-BR explícito no training corpus) |
| **v2**: `@xenova/transformers` Node ONNX → 15GB RSS → OOM-kill em VPS 15GB | **v3**: **vLLM Python sidecar** ou HF serverless inference — usa memory-efficient ONNX runtime + GPU paged-attention. RAM target <2GB |
| Activate decisão prematura via "lift_score" enganoso | **v3**: ablation **offline G13 obrigatória ANTES** de shadow→active (lição cravada D01 v1) |
| Hardware footprint não medido | **v3**: Phase A explícita = benchmark de hardware + latency + custo em VPS atual |

---

## 2. Hypothesis

> Cross-encoder rerank de top-20 candidatos pós-RRF melhora nDCG@10 entre **+3% e +8%** absoluto em corpus PT-BR-heavy do nox-mem, sem custo recorrente (vLLM local), com latency p95 acrescido <100ms.

Subhipóteses falsificáveis (todas validadas via G13 ablation):
- **H1 (precision):** nDCG@10 Δ ≥ +0.03 absoluto sobre baseline hybrid+G10 atual.
- **H2 (multi-hop):** multi-hop nDCG@10 Δ ≥ +0.05 (categoria onde reranker tem maior expected benefit segundo literatura BEIR).
- **H3 (latency):** p95 reranker latency ≤ 100ms em VPS dedicado, ≤ 50ms com GPU T4.
- **H4 (PT-BR transfer):** sem regressão em queries PT-BR (Δ ≥ 0% em subset PT-BR vs subset inglês — diferente do v1 onde PT-BR sofreu -0.25).
- **H5 (Autonomy preserved):** zero chamada a vendor API; 100% inference em infra controlada.

Falsifiable na G13 ablation: se H1 falha (Δ < +0.03), CUT v3 imediato, atualizar memory `[[neural-reranker-evolution-vector]]` com "third strike — parking permanente".

---

## 3. Architecture / Pipeline Integration

### 3.1 Current pipeline (post Wave A + G10)

```
query
  ├─ FTS5 BM25 ─────────┐
  ├─ Gemini dense embed ┤── RRF fusion (k=60)
  │                     │
  └─ query_entities ────┘
        │
        ▼
  boost stack (focus + reason + temporal + section + source_type + Hard Mutex G10)
        │
        ▼
  salience formula v2 aditiva (recency × pain × importance)
        │
        ▼
  sort + slice top-K (default K=10)
        │
        ▼
  /api/search response
```

### 3.2 Proposed pipeline with reranker

```
... (igual até salience) ...
        │
        ▼
  sort + slice top-N (RERANKER_TOP_K_IN, default N=20)     ← novo
        │
        ▼
  rerankWithCrossEncoder(query, top-N) → reordena via cross-attention  ← novo
        │
        ▼
  slice top-K (RERANKER_TOP_K_OUT, default K=10)            ← novo
        │
        ▼
  /api/search response (logTelemetry includes reranker_*)
```

Off-mode = comportamento atual byte-perfect (zero overhead, zero código novo no caminho — guard `if (mode === 'off') return candidates`).

### 3.3 Serving topology

```
┌─────────────────────────────────┐         ┌─────────────────────────┐
│   nox-mem-api (Node :18802)     │ ─HTTP─► │  vllm-reranker sidecar  │
│   src/search.ts → rerank()      │         │  Python :8001            │
│   timeout 2000ms                │         │  bge-reranker-v2-m3      │
│   fail-open on error            │         │  ONNX or HF transformers │
└─────────────────────────────────┘         └─────────────────────────┘
                                                       │
                                                       ▼
                                            CPU (~500ms p95)
                                            OR GPU T4 (~50ms p95)
```

Sidecar pattern (vs in-process Node) é mandatory porque:
1. **Memory isolation** — Python process tem ONNX runtime allocator separado, V8 GC não compete. Lição direta do D01 v2 OOM.
2. **Autonomy preservada** — sidecar roda na mesma VPS (não SaaS), `127.0.0.1:8001` bind, não exposto externamente.
3. **Hot-swap** — model upgrade não requer rebuild de Node app.
4. **GPU graduation path** — se latency CPU não satisfaz, dropar GPU instance na mesma VM sem refactor app code.

---

## 4. Options Analysis — 4 providers

| Option | Provider | Latency p95 estimada | Custo | Autonomy | Recomendação |
|---|---|---|---|---|---|
| **A** | **bge-reranker-v2-m3 via vLLM local** | ~50ms (GPU T4) / ~500ms (CPU only) | Self-hosted ($0 recorrente; VPS atual ou +$0.40/h GPU rental Lambda/Vast.ai) | ✅ **Full** (100% local) | **PREFERRED** |
| B | Cohere Rerank v3 API | ~200ms (incluindo rede) | $1/1k queries (≈$14/mês a 14k qpm) | ❌ Vendor lock-in completo | Fallback only se A inviável |
| C | DeepInfra Rerank | ~300ms (rede + cold) | $0.05/1M tokens (≈$5-10/mês prod) | ⚠️ Vendor managed | **NOT recommended** |
| D | bge via Modal/Replicate serverless | ~100ms (warm) | ~$0.50/1k queries | ⚠️ Vendor managed | **NOT recommended** |

### Por que Option A é preferred

1. **Autonomy é pilar core (Q/A/P).** Cohere/DeepInfra/Modal sairiam do perímetro — incompatível com narrativa "yours by design".
2. **Custo $0 recorrente** vs $5-14/mês recorrente em vendor (paper §5.5 cost model permanece intacto).
3. **PT-BR coverage explícita** — bge-v2-m3 é trained em 100+ línguas incluindo português (vs BGE-base original do D01 v1 que era inglês-only e quebrou em PT-BR).
4. **Hardware path graduado** — start CPU-only (lento mas zero spend), upgrade GPU se ablation prova value.
5. **Reuse vLLM infra** — se P10/E15 trouxer outras LLM workloads local (Qwen3 etc), o serving stack já existe.

### Por que Options B/C/D são fallback

- **B (Cohere):** considerado apenas se Option A latency CPU >500ms inaceitável **E** GPU rental >$30/mês inviável **E** Toto explicitamente aprovar vendor dependency. Threshold alto.
- **C (DeepInfra):** mesma issue de Cohere + menos PT-BR proof. Strictly worse.
- **D (Modal/Replicate):** serverless cold-start torna latency variável (50ms warm, 5s cold). Inaceitável para SLA L2 (<2s total).

### Rejeições explícitas pra paper §5.5

| Vendor | Razão de exclusão |
|---|---|
| Cohere Rerank | $14/mo recorrente + corpus PII soft sai do perímetro + vendor lock-in viola Autonomy pillar |
| DeepInfra | mesmo problema + menos benchmark PT-BR |
| OpenAI re-ranker (deprecated) | n/a |
| Voyage rerank-2 | $0.05/1k + vendor + privacy |
| Cohere via on-prem | $$$$ enterprise license, fora de escopo |

---

## 5. Implementation Phases (gated, sequential)

### Phase A — Hardware/model benchmark (~6h)

**Objetivo:** medir custo real de serving antes de comitar Phase B.

Tasks:
1. Setup `vllm` ou `transformers` Python sidecar em VPS test environment (`/root/.openclaw/workspace/services/reranker-bench/`).
2. Download `BAAI/bge-reranker-v2-m3` (model + tokenizer).
3. Benchmark com 100 sample query×doc pairs do `entity-eval-v2.db`:
   - CPU only: medir p50/p95/p99 latency, RAM peak, throughput (pairs/sec)
   - Se GPU disponível (Lambda T4 spot $0.40/h): mesmas métricas em GPU
4. Document trade-offs em `audits/2026-05-2X-reranker-bench-phaseA.md`.

**Pass criteria Phase A:**
- RAM peak ≤ 3GB CPU mode (VPS tem 15GB total, headroom OK).
- p95 latency ≤ 800ms CPU mode (será trimmed depois com batching).
- Modelo carrega sem OOM (cravado bug D01 v2: @xenova/transformers explodiu em 15GB; vLLM Python deve ser <3GB).

**Fail criteria Phase A → CUT v3:**
- RAM > 5GB CPU mode (sinal que vLLM tem mesmo problema que xenova).
- p95 latency > 2s CPU + GPU rental >$30/mês.
- Modelo não carrega ou retorna scores degenerados em smoke test.

### Phase B — Integration em `src/search.ts` (~6h)

**Objetivo:** wire pipeline com `rerankWithCrossEncoder()`.

Tasks:
1. Create `src/lib/reranker.ts`:
   - `rerank(query, candidates, topK)` → POST `http://127.0.0.1:8001/rerank` com `{query, documents: [...]}` body
   - Timeout 2000ms (hard cap)
   - Fail-open: any error → return original candidates intactos (zero crash exposed)
   - Cache via in-memory LRU por `(query_hash, chunk_id_list_hash)` com 5min TTL (saves repeat queries no eval batch)
2. Hook em `src/search.ts` `searchHybrid()`:
   - Após salience, antes do final slice
   - Guard `if (NOX_NEURAL_RERANKER_MODE === 'off') skip`
3. Telemetry: add 6 colunas em `search_telemetry` via schema v17 migration:
   ```sql
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_mode TEXT DEFAULT 'off';
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_top_k_in INTEGER DEFAULT 0;
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_top_k_out INTEGER DEFAULT 0;
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_latency_ms INTEGER DEFAULT 0;
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_position_changes INTEGER DEFAULT 0;
   ALTER TABLE search_telemetry ADD COLUMN neural_reranker_max_score REAL DEFAULT 0;
   ```
4. Tests `src/__tests__/neural-reranker.test.ts`:
   - mode=off: rerank não chamado
   - mode=shadow: rerank chamado, ranking original retornado
   - mode=active: rerank chamado, novo ranking retornado
   - fail-open em timeout, exception, sidecar 503
   - cache hit em queries idênticas consecutivas

### Phase C — Shadow-mode toggle (~3h)

**Objetivo:** habilitar shadow logging sem afetar callers.

Tasks:
1. Env var `NOX_NEURAL_RERANKER_MODE=off|shadow|active` (default `off`).
2. Em shadow:
   - Sidecar é chamado, latency e position_changes gravados
   - Ranking final retornado = ranking original (não muta saída do `/api/search`)
3. Deploy sidecar + Node app em VPS, smoke test 50 queries.
4. Validate `/api/health.neuralReranker.status` reporta `{mode, sidecarReachable, lastLatencyMs}`.

### Phase D — Ablation eval G13 (~4h)

**Objetivo:** medir lift offline antes de promover shadow → active.

Eval setup:
- DB: `g5.db` (full prod-flavored, ~68k chunks) OU `g9.db` se mais recente disponível.
- Harness: existing eval framework (`scripts/eval-run-batch.sh` equiv).
- Variants: `--variant baseline` (sem reranker) vs `--variant rerank` (active forced em scope da run).
- N: ≥ 60 queries (consistente com G3/G5/G7 baselines).

**Pass criteria G13:**
- Aggregate nDCG@10 Δ ≥ **+3%** vs baseline → proceed Phase E.
- multi-hop nDCG@10 Δ ≥ **+5%** (categoria target).
- p95 latency adicional ≤ **+100ms** em SLA L2 (<2s total).
- error rate ≤ 0.5%.
- **PT-BR subset sem regressão** (anti D01 v1 trauma): Δ PT-BR ≥ Δ inglês × 0.7 (mesmo lift ou pouco abaixo, nunca negativo).

**Fail criteria G13 → CUT v3:**
- Aggregate Δ < +1% OR PT-BR regressão → CUT, parking permanente.
- p95 latency > +200ms → CUT (SLA violation).
- error rate > 1% → CUT (fragility).

### Phase E — Paper §5.7 + activate gate (~2h)

**Objetivo:** documentar resultado e promover shadow → active se G13 passou.

Tasks:
1. Append paper §5.7 com:
   - Engine choice rationale (Autonomy + bge-v2-m3 multilingual)
   - Phase A hardware bench numbers
   - G13 ablation table (aggregate + per-category)
   - Cost comparison vs Cohere/DeepInfra
2. Flip `NOX_NEURAL_RERANKER_MODE=shadow → active` em prod.
3. Open D52 decision template (similar a `d50-template.md`/`d51-template.md`) capturando final yes/no.

---

## 6. Schema Migration v17

`search_telemetry` ganha 6 colunas (additive, idempotent, default 0/NULL/`off`):

```sql
-- migrateToV17() em src/db.ts
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_mode TEXT DEFAULT 'off';
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_top_k_in INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_top_k_out INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_latency_ms INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_position_changes INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN neural_reranker_max_score REAL DEFAULT 0;
```

`SCHEMA_VERSION = 17`. Cada `ALTER` em try/catch tolerando "duplicate column" (mesmo padrão v13/v14/v15/v16).

**Nota:** schema v16 já foi consumido por `search_telemetry.reranker_*` columns no D01 v1 — após v1 CUT essas colunas permaneceram inertes mas presentes. **Decisão schema:** as novas colunas v17 são `neural_reranker_*` (não reusar `reranker_*` da v16) para evitar confusão telemétrica entre experiments. Colunas v16 ficam dormant + migração futura pode VACUUM se confirm unused.

---

## 7. Configurable knobs (env vars)

| Env var | Default | Descrição |
|---|---|---|
| `NOX_NEURAL_RERANKER_MODE` | `off` | `off`/`shadow`/`active` |
| `NOX_NEURAL_RERANKER_TOP_K_IN` | `20` | candidatos top-N que entram no reranker |
| `NOX_NEURAL_RERANKER_TOP_K_OUT` | `10` | top-K final pós-rerank |
| `NOX_NEURAL_RERANKER_SIDECAR_URL` | `http://127.0.0.1:8001` | endpoint do vLLM sidecar |
| `NOX_NEURAL_RERANKER_TIMEOUT_MS` | `2000` | hard timeout por chamada |
| `NOX_NEURAL_RERANKER_CACHE_TTL_S` | `300` | LRU cache TTL (saves eval reruns) |
| `NOX_NEURAL_RERANKER_LOG` | `0` | `1` = console.error log shadow/active |

---

## 8. Score Normalization Strategy

Cross-encoder scores são logits (range ~[-10, +10]) não normalizados. RRF scores são reciprocal rank em [0, ~0.03]. Combinar diretamente quebra ranking.

**Strategy escolhida:** rerank é **terminal substitution** em mode=active (não fusion). top-N candidates entram, top-K reranker output substitui ranking. Sem combine.

**Alternativa rejeitada:** weighted blend `final = α × rrf + (1-α) × rerank_score`. Rejeitada porque:
1. Adds tunable hyperparameter sem benefit claro.
2. Score scales incompatible — calibration via min-max ou z-score complica.
3. Literatura (BEIR) mostra que pure substitution em top-N pequeno (N=20) outperforma blends.

**Fallback se substitution dá problema:** Phase D pode testar `final_rank = β × rrf_rank + (1-β) × rerank_rank` (rank-space blend, scale-invariant). β=0.5 default. Saved as "G14 variant" se G13 não atinge target.

---

## 9. Risks Register

| # | Risco | Severidade | Mitigation |
|---|---|---|---|
| 1 | **Hardware OOM repeat** (D01 v2 trauma) — vLLM também consome 15GB? | High | Phase A bench obrigatória ANTES de Phase B. Pass criteria: RAM ≤3GB. |
| 2 | **PT-BR transfer fail** (D01 v1 trauma) — m3 multilingual mas pode degradar PT-BR specific | High | PT-BR subset eval em G13 com Δ ≥ 0% (não negative). CUT se PT-BR sofre. |
| 3 | **Latency CPU >500ms** | Med | Phase A measures real; if true, evaluate GPU rental (+$30/mo Lambda). Decision gate Toto explicit approval. |
| 4 | **Sidecar process crash** afeta `/api/search` availability | Med | Fail-open em qualquer error → return candidates originais. Healthcheck cron 15min alert se sidecar dead. |
| 5 | **Cache poisoning** se query_hash colide | Low | LRU keyed em `(query_hash, sorted_chunk_id_list_hash)` — colisão precisa AMBOS bater, prob ~0. |
| 6 | **Schema v17 conflict** com v16 `reranker_*` columns | Low | New columns `neural_reranker_*` prefix evita conflito. v16 columns ficam dormant. |
| 7 | **vLLM dependency complexity** (Python sidecar = new infra) | Med | Document em `docs/RUNBOOK-reranker.md`. systemd unit em `services/vllm-reranker.service`. Healthcheck em cron. |
| 8 | **Cold start sidecar pós-restart** = 30-60s warm-up | Low | Eager load no service start, healthcheck só passa após first inference. /api/search fail-open durante warm-up. |
| 9 | **Score calibration drift** entre m3 versions | Low | Pin model SHA via HF revision. Rerun G13 ablation em version bump (operational, não bloqueia v3). |
| 10 | **Eval contamination** se rerank scores leak para train data accidentalmente | Low | Reranker is read-only inference; nunca grava em corpus. |

---

## 10. Cost Model (auditado)

| Recurso | Custo CPU mode | Custo GPU mode | Cobrança |
|---|---|---|---|
| Compute (inference) | $0/mês | +$30-50/mês (T4 spot $0.40/h × ~80h/mês) | VPS atual ou Lambda/Vast.ai |
| Disk model | +570MB (bge-v2-m3) | mesmo | VPS ext4 (50GB+ livres) |
| RAM working set | +1-3GB peak | +1-2GB CPU + GPU VRAM | VPS Hostinger KVM (15GB total, atual ~8GB used) |
| Latency adicional | p50 ~300ms, p95 ~500ms | p50 ~30ms, p95 ~50ms | dentro SLA L2 (<2s) |
| Vendor risk | nenhum (Apache 2.0) | nenhum | model HF mirror gratuito |

**Comparação vendor:**

| Path | Custo/mês a 14k qpm |
|---|---|
| Option A CPU (recommended) | $0 |
| Option A GPU (if needed) | $30-50 |
| Cohere Rerank v3 | $14 |
| DeepInfra Rerank | $5-10 |

CPU mode é **cheapest absoluto** + Autonomy max. GPU mode trade-off é latency vs $30/mo. Cohere break-even em ~2 anos vs GPU rental — favorável Option A.

---

## 11. Non-goals (out of scope explicit)

- ❌ NO Cohere/DeepInfra/Voyage/Modal/Replicate em primary path.
- ❌ NO retraining bge-v2-m3 com nox-mem corpus (fine-tuning é Phase F, gated em Phase E success + Toto approval).
- ❌ NO score blending (rrf × rerank_score weighted). Pure substitution em top-N.
- ❌ NO BM25-only reranker (cross-encoder substitui re-encoding de BM25 + dense, não complementa).
- ❌ NO production deploy sem ablation G13 pass (D01 v1 lição: shadow lift_score não basta).

---

## 12. Open Questions

1. **GPU hosting:** Hostinger não oferece GPU instances. Se Phase A indica CPU latency >800ms p95, opções:
   - (a) Lambda Labs T4 spot $0.40/h dedicated (~$30/mo) — separado da VPS, requires sidecar exposed via WireGuard ou TLS tunnel
   - (b) Vast.ai cheaper option (~$0.15/h T4) but flaky availability
   - (c) Aceitar CPU latency e classificar como "Lab-only / not prod-ready"
   - **Decisão pendente:** aguarda Phase A numbers.
2. **Top-N input size:** N=20 (default proposto) ou N=50 (D01 v1 baseline)? Trade-off entre recall ceiling e latency. **Recomendação:** Phase A bench N=20, N=50, N=100 e pick smallest com nDCG plateau.
3. **Pipeline order:** Rerank ANTES ou DEPOIS de salience? Atual proposta = depois (rerank vê salience-weighted scores). Alternativa: rerank ANTES, salience como secondary tiebreaker. **Phase D variant test.**
4. **Cache strategy:** LRU in-memory (proposto) suficiente, ou precisa Redis distributed cache? Para 1.5k queries/dia in-memory basta. Reconsider se >10k qpm.
5. **bge-v2-m3 vs jina-reranker-v2-base-multilingual:** jina é menor (278M vs 568M) e também multilingual. **Decisão pendente:** Phase A pode incluir A/B test entre os dois se time permite.
6. **Sidecar deploy strategy:** systemd unit (proposed) ou docker-compose service? Docker dá mais isolation mas adiciona complexity. systemd é consistente com nox-mem-api atual.

---

## 13. Tasks (não implementar — apenas tracking)

- [ ] Spec aprovada (este doc)
- [ ] D49 closed (gate dependency)
- [ ] D50 closed (gate dependency)
- [ ] Per-method benchmark Phase A complete (gate dependency)
- [ ] Phase A: vLLM sidecar bench + RAM/latency report → `audits/2026-05-2X-reranker-bench-phaseA.md`
- [ ] Phase A pass → proceed Phase B
- [ ] Phase B: `src/lib/reranker.ts` + schema v17 + tests
- [ ] Phase C: shadow-mode deploy + healthcheck
- [ ] Phase D: G13 ablation eval (`g5.db` or `g9.db`)
- [ ] G13 pass → Phase E (paper §5.7 + activate)
- [ ] D52 template aberto pra decisão final
- [ ] Memory `[[neural-reranker-evolution-vector]]` updated com outcome

---

## 14. Definition of Done (current scope: DESIGN ONLY)

- [x] Spec aberta com phasing claro
- [x] Engine choice justificada com 4-option matrix
- [x] Autonomy rationale documentada
- [x] D01 v1/v2 cuts referenciados como aprendizado (não esquecidos)
- [x] Risk register com 10 items + mitigations
- [x] Cost model auditado vs vendor alternatives
- [x] Open questions enumerated
- [x] Non-goals explícitos
- [ ] PR aberto contra main (não merge — design only)
- [ ] specs/INDEX.md updated

**Explicitly NOT in scope this PR:**
- Phase A-E implementation (gated em D49/D50/per-method-benchmark closure)
- Any code change em `src/`
- Schema v17 migration code
- vLLM sidecar deployment

---

## 15. Reviewer Checklist

- [ ] Phasing makes sense (A bench → B impl → C shadow → D eval → E activate)?
- [ ] Pass/fail criteria objetivas em cada phase?
- [ ] D01 v1/v2 cuts properly accounted for (not repeating same mistakes)?
- [ ] Autonomy pillar preservado (vLLM local primary, vendor only fallback)?
- [ ] Cost model honest (CPU $0 + GPU $30/mo accurate)?
- [ ] Risk register cobre todos os modos de falha conhecidos?
- [ ] Schema v17 strategy (new `neural_reranker_*` columns) não conflita com v16 dormant?
- [ ] Gate dependencies (D49 + D50 + per-method-benchmark) corretas?

