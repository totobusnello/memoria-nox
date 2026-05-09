# D01 — Cross-encoder Reranker (Shadow)

> Adiciona cross-encoder local (BGE-reranker-base via `@xenova/transformers` ONNX-in-Node) como camada pós-RRF do hybrid pipeline. Reordena top-N=50 candidatos via cross-attention query×chunk e devolve top-K=10. Default `off`; padrão obrigatório de shadow→active gated em 7d telemetria. Quebra o teto empírico de nDCG@10=0.5831 (R01c-v1.1) ao trazer relevância contextual além de BM25+vetor independente.

> ## ⛔ VERDICT: CUT v1 (2026-05-08 ~12:20 BRT)
> Offline eval com `NOX_RERANKER_MODE=active` 3-run sobre R01c-v1.1 (n=65 incluindo Q105-Q109 scan-gate) retornou:
> - **nDCG@10: 0.3718 ± 0.002** vs hybrid baseline 0.5831 ± 0.0046 → **Δ = −0.2113** ❌
> - **MRR: 0.3969** vs 0.5445 → Δ = −0.1476
> - **Recall@10: 0.5154** vs 0.7667 → Δ = −0.2513
> - **Decisão: CUT** (Δ ≤ 0 critério → cut). Set `NOX_RERANKER_MODE=off` em .env, api restarted.
>
> **Root cause hypothesis:** BGE-reranker-base treinado em corpora inglês não transfere pra PT-BR domain corpus. Reordenação no top-50 com sinal cross-attention degradado scramble ranking útil do RRF.
>
> **D01-v2 candidato (deferred):** trocar pra `BAAI/bge-reranker-v2-m3` (multilingual, suporta PT-BR explícito) OR `Cohere Rerank API` (vendor mas comprovadamente PT-BR-aware). Avaliar 2026-Q3.
>
> **Aprendizado:** shadow telemetry mostrou avg lift_score 0.341 (parecia promissor!) mas position_changes 12.6/query traduziu em retrieval pior — métrica de "lift" é ENGANOSA quando o reranker tem domain mismatch. **Sempre validar com offline nDCG eval ANTES de promover shadow→active.**
>
> **Aprendizado #2 (memory leak experimental — 2026-05-09):** tentativa de fix periodic dispose+reload (`callCount` + `maybeReloadModel`) não funcionou: `Tensor.dispose()/BatchEncoding.dispose()` não existem em `@xenova/transformers v2.17.2`, só `Model.dispose()` (que libera InferenceSession via handler.dispose). Ainda assim, ONNX Runtime arena allocations leak interno (native code, fora do alcance V8 GC). Patch revertido — código source limpo na branch main, callCount/maybeReloadModel removed. Decisão: NÃO investir mais em fix de leak para v1 dado que **lift é negativo (-0.2113)** — sem lift, leak fix não justifica esforço. Quando D01-v2 multilingual vier (BGE-v2-m3 ou Cohere), perfil de leak/concurrency será diferente, partir de stub clean é mais simples.

**Status:** ⛔ CUT v1 (2026-05-08, see verdict). Source-of-truth limpo 2026-05-09 (sem dead code).

---

## D01-v2 attempt (2026-05-09 19:40 BRT) — OOM-killed

Tentativa de mudar para `onnx-community/bge-reranker-v2-m3-ONNX` (multilingual, suporta PT-BR explícito) via env override `NOX_RERANKER_MODEL`. Eval crashou em ~2min:

```
Out of memory: Killed process 821997 (node.real)
total-vm:47749900kB, anon-rss:15173680kB, file-rss:3160kB, shmem-rss:0kB
```

Process consumiu **15GB RSS** durante load do modelo (568M params, mesmo quantized). VPS tem 15GB RAM total → OOM-kill imediato.

**Root cause:** v2-m3 é 2× maior que v1-base (278M). Stack `@xenova/transformers` em Node carrega tensors em V8 heap + ONNX Runtime arenas, multiplicando memory footprint. Quantized variant não basta nessa VPS.

### D01-v2 CUT — opções restantes pra D01-v3 (deferred)

| Path | Custo | Qualidade | Vendor | Complexidade |
|---|---|---|---|---|
| **Cohere Rerank API** | ~$0.50/mo eval traffic, $5-10/mo prod batch | Multilingual proven 100+ langs | ✅ Cohere SaaS | Baixa (~50 LOC engine class + API key) |
| **VPS upgrade** | +$X/mo Hostinger | mantém local v2-m3 | ❌ | Zero (just bigger box) |
| **Sidecar Python** | $0 | onnxruntime-python mais memory-efficient que @xenova | ❌ | Alta (infra nova) |
| **Smaller multilingual** | $0 | jina-reranker-v2-base ~278M | ❌ | Média (test memory profile primeiro) |
| **Archive entirely** | $0 | nenhum reranker | — | Zero — deferir até evidência forte |

**Decisão:** D01-v2 CUT (OOM blocked). D01-v3 candidato deferred — espera (a) evidência de query patterns que claramente precisam de re-ranking ou (b) demanda explícita de Toto. Por enquanto **0.5831 nDCG hybrid baseline mantido como teto operacional**.
**Data:** 2026-05-07
**ID:** D01
**Vision §:** §11 Wave 2 — re-ranking layer
**Esforço estimado:** 4–6h impl + 7d shadow + 0.3h activate
**Dependências:**
- ✅ Hybrid pipeline (FTS5 BM25 + Gemini semantic + RRF k=60) operacional
- ✅ Schema v15 + migration framework idempotente
- ✅ `search_telemetry` (ts/query_hash/latency_ms/etc) populando há 6 meses
- ✅ `@xenova/transformers ^2.17.2` no package.json (já instalado em outro contexto)
**Bloqueia:** —
**Cross-ref:**
- `docs/DECISIONS.md §2` (Q5 Qwen3-Reranker-0.6B llama-server **DEFERRED com 5 razões**, não cortado)
- `docs/DECISIONS.md §3.3` (regra crítica #5: shadow-mode 7d obrigatório antes de aplicar ranking change)
- `specs/2026-05-06-E05b-reason-ranking-boost.md` (mesmo padrão modes/telemetria/cap)
- `specs/2026-05-06-E13-temporal-aware-ranking.md` (formato spec recente)

---

## Problema

R01c-v1.1 (n=60, 3-run mean) reportou **hybrid nDCG@10 = 0.5831 ± 0.0046**. Gate D01 original era ≥0.6, hoje 0.5831. Análise pós-baseline:

| Sintoma observado | Magnitude | Causa estrutural |
|---|---|---|
| BM25 recall ceiling | 92% queries não surfaçam gold via FTS5 | ranker lexical sem semântica de pares query-doc |
| Vetor independente | top-10 muitas vezes em mesma vizinhança topical mas off-target | embedding monolítico sem cross-attention |
| RRF naive (k=60) | empata candidatos topicamente próximos sem distinguir relevância fina | fusion sem reranker condicional |

**Q5 (Qwen3-Reranker-0.6B local via llama-server) está DEFERRED por 5 razões em DECISIONS.md §2.** Esta D01 endereça **3 das 5 razões** (ROI mensurável, sem latência fora SLA, sem infra heavy nova) ao trocar engine pra **BGE-reranker-base in-process via ONNX/transformers.js**.

**Hipótese:** cross-encoder rerank do top-50 → top-10 empurra nDCG@10 entre **+0.03 e +0.10** (literatura BEIR mostra 0.05-0.15 lift comum). Gate ativação ≥+0.03 absoluto.

---

## Engine choice — BGE-reranker-base (`Xenova/bge-reranker-base`)

### Por que esse modelo

| Critério | BGE-reranker-base | Cohere Rerank v3 | Voyage rerank-2 | Qwen3-Reranker-0.6B (Q5) |
|---|---|---|---|---|
| Recurring cost | $0 | $1/1k queries | $0.05/1k | $0 (local) |
| Vendor lock-in | nenhum (Apache 2.0, ~85MB ONNX) | Cohere API | Voyage API | nenhum |
| Latency (50 pairs CPU) | ~80–200ms p50 | ~120ms (rede) | ~120ms (rede) | ~150-300ms |
| Infra footprint | 0 (in-process Node) | 0 | 0 | llama-server +2-3GB RAM |
| Multilingual PT/EN | sim (treinado MS-MARCO multilingual) | sim | sim | sim |
| Privacidade | 100% local | sai do perímetro | sai do perímetro | local |

**Rejeição explícita Cohere/Voyage:**
- Cost recorrente em workload com 14k+ queries/mês = $14+/mês recorrente (paper §5.5 cost model rompe)
- Privacy: corpus contém entidades/lições/decisions com PII soft (Toto, clientes Granix); pedir sair do perímetro contradiz storage-local-first stance
- Vendor coupling: paper cita stack TS+SQLite+Gemini-embeddings; adicionar 4o vendor (Cohere/Voyage) no critical path quebra a narrativa "lean ops"

**Engine final:** `@xenova/transformers` (ONNX runtime in Node, 45MB + ~85MB modelo). Já é peer dependency do projeto. Sem GPU. Sem Python subprocess.

### Trade-offs aceitos

- **~266MB disk** (model_quantized.onnx em `node_modules/@xenova/transformers/.cache/Xenova/bge-reranker-base/onnx/`). **Atualização vs. spec inicial:** o ONNX quantizado é 266MB, não ~85MB como inicialmente projetado — ainda dentro do orçamento operacional (VPS Hostinger tem 50GB+ livres) mas pesa 3× mais que estimativa em ~/.cache provisioning
- +384ms warm latency p50 medido (50 pares query×doc, MacBook M3 Pro CPU)
- Cold start: ~2–4s primeiro request por proc (lazy load + ONNX session bind). Mitigação: warm-up no boot do `nox-mem-api`
- CPU-only (suficiente p/ 50 pares); GPU acceleration possível depois via `onnxruntime-node-gpu` (não escopo D01)
- **xenova text-classification pipeline NÃO suporta `text_pair`** (passa pares como string única, tokenizer ignora pair). Implementação usa low-level `AutoTokenizer` + `AutoModelForSequenceClassification.from_pretrained({quantized: true})` com batch tokenization. Smoke real validado 2026-05-07 com 3 chunks: cross-encoder corretamente promoveu chunk relevante e demote chunk de ruído (pasta cooking)

---

## Pipeline integration

```
hybrid()
  ├─ FTS5 BM25 batches
  ├─ Gemini semantic batch
  ├─ RRF fusion (k=60)
  ├─ applyFocusBoost (E04a)
  ├─ applyReasonBoost (E05b)
  ├─ sort+slice top-N (RERANKER_TOP_K_IN, default 50)         ← novo
  ├─ rerank(query, candidates) → reordena via cross-encoder    ← novo D01
  ├─ slice top-K (RERANKER_TOP_K_OUT, default 10)              ← novo
  └─ telemetry.log(reranker_*, position_changes, lift_score)
```

`searchHybrid()` em `src/search.ts` ganha hook após `applyReasonBoost`. **Off-mode = comportamento atual byte-perfect** (zero overhead, zero código novo no caminho).

### Modes (env `NOX_RERANKER_MODE`)

| Valor | Comportamento |
|---|---|
| `off` (default) | no-op. Ranking pós-RRF intacto. |
| `shadow` | rerank executa, telemetria gravada, **ranking final retornado é o original** (não muta). Permite comparar lift sem afetar callers. |
| `active` | rerank substitui ranking. Top-K final = top-K do reranker. |

Fail-open: model load falha, ONNX timeout >2s, exception qualquer → log + retorna ranking original (off-mode behaviour). Zero crash exposto.

### Configurable knobs

| Env var | Default | Descrição |
|---|---|---|
| `NOX_RERANKER_MODE` | `off` | `off`/`shadow`/`active` |
| `NOX_RERANKER_TOP_K_IN` | `50` | quantos candidatos top-N entram no reranker |
| `NOX_RERANKER_TOP_K_OUT` | `10` | top-K final pós-rerank |
| `NOX_RERANKER_MODEL` | `Xenova/bge-reranker-base` | HF repo (ex: `Xenova/bge-reranker-large` p/ comparar) |
| `NOX_RERANKER_TIMEOUT_MS` | `2000` | hard timeout por chamada de rerank |
| `NOX_RERANKER_LOG` | `0` | `1` = console.error log shadow/active |
| `TRANSFORMERS_CACHE` | (auto) | sobrescreve cache dir (default: `node_modules/@xenova/transformers/.cache/`). Em prod VPS recomenda-se `~/.cache/huggingface/` ou `/var/cache/nox-mem-models/`. |

---

## Schema migration v16

`search_telemetry` ganha 6 colunas (additive, idempotent, default 0/NULL):

```sql
ALTER TABLE search_telemetry ADD COLUMN reranker_mode TEXT DEFAULT 'off';
ALTER TABLE search_telemetry ADD COLUMN reranker_top_k_in INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN reranker_top_k_out INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN reranker_latency_ms INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN reranker_position_changes INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN reranker_lift_score REAL DEFAULT 0;
```

`SCHEMA_VERSION = 16`. Cada `ALTER` em try/catch tolerando `duplicate column` (mesmo padrão v13/v14/v15).

### Métricas em telemetria

- `reranker_mode`: `'off'|'shadow'|'active'` snapshot
- `reranker_top_k_in`: |candidates pre-rerank| (≤NOX_RERANKER_TOP_K_IN)
- `reranker_top_k_out`: |result final| (≤NOX_RERANKER_TOP_K_OUT)
- `reranker_latency_ms`: tempo só do reranker (excluindo hybrid pipeline)
- `reranker_position_changes`: count de chunks que mudaram posição entre top-K_OUT original e top-K_OUT pós-rerank
- `reranker_lift_score`: |sum(orig_pos − new_pos) / K_OUT|, normalizado [0,1]; mede "deslocamento médio" (proxy de Spearman simplificado, computável em shadow sem golden)

---

## Lift score computation (shadow-friendly)

Sem golden, não dá pra calcular nDCG diretamente. Mas dá pra medir movimento estrutural do ranking:

```
orig_top_K = candidates[0..K_OUT]                         // pré-rerank, ordenados por rrfScore
new_top_K  = rerank(query, candidates[0..K_IN])[0..K_OUT] // pós-rerank

position_changes = |{ id ∈ orig ∪ new : orig.indexOf(id) ≠ new.indexOf(id) }|

lift_score = mean(|orig.indexOf(id) − new.indexOf(id)|) / K_OUT  para id ∈ orig ∩ new
           // valores [0,1]; 0 = sem mudança; 0.5 = swaps moderados; 1 = top virou bottom
```

Em eval, comparamos shadow run `lift_score` médio com nDCG@10 delta pós-`active`. Se lift baixo + nDCG alto = reranker discrimina cirurgicamente. Se lift alto + nDCG baixo = reranker está embaralhando ruidosamente.

---

## Tests (`__tests__/reranker.test.ts`)

Mock `pipeline()` (xenova) pra validar lógica sem download de 85MB:

1. `mode=off`: rerank não chamado, retorna candidates intactos (deep equality)
2. `mode=shadow`: rerank chamado, telemetria gravada com mode='shadow', resultado final = original (não muta)
3. `mode=active`: rerank chamado, resultado final = output do reranker, telemetria com mode='active'
4. `position_changes`: dado mock que troca pos 0↔1, expect 2 changes
5. `lift_score`: dado mock determinístico, expect valor calculado correto
6. fail-open: mock pipeline lança exceção → retorna candidates originais, mode='off' efetivo, no crash
7. timeout: mock pipeline timeout >NOX_RERANKER_TIMEOUT_MS → fail-open, latency_ms registrado
8. K_IN clip: candidates.length=20 + K_IN=50 → rerank vê 20 (não pad)
9. K_OUT clip: candidates.length=50 + K_OUT=10 → final.length=10
10. queryEntitiesCount-style empty: candidates=[] → no-op, latency_ms=0

**Smoke real opcional** (não no test suite, manual): query "edge typing nox-mem" + 10 chunks reais, validar que rerank load do modelo funciona end-to-end. Documentado em §"Smoke local" abaixo.

---

## Activate gate (após 7d shadow)

| Critério | Threshold | Justificativa |
|---|---|---|
| Δ nDCG@10 (active vs hybrid baseline R01c-v1.1) | ≥ +0.03 absoluto | mínimo pra justificar +50–200ms p95 + 85MB model footprint |
| Δ MRR | ≥ +0.05 | sanity check no headline metric |
| p95 reranker_latency_ms | < 500ms | preserva SLA L2 (`<2s` total) |
| % shadow runs sem erro | ≥ 99.5% | fail-open robustez |
| ≥ 100 queries logged em shadow | hard gate | n suficiente pra eval |

**Pass:** flip `NOX_RERANKER_MODE=shadow → active` + restart `nox-mem-api`. R01c-v1.2 baseline rerun.

**Catastrophic** (Δ nDCG ≤ -0.01 ou p95 ≥1000ms ou error rate ≥1%): rollback `mode=off` + investigar (provavelmente model mismatch, ou TOP_K_IN mal calibrado pra corpus heavy-tail).

---

## Cost model (auditado)

| Recurso | Custo | Cobrança |
|---|---|---|
| Embed/inference compute | $0/mês | local CPU |
| Disk model | +266MB quantized ONNX (one-time) | VPS ext4 |
| RAM working set | +200-400MB peak (ONNX session) | VPS Hostinger KVM 4 (16GB total, atual ~6GB) |
| Latency adicional | p50 ~80–150ms, p95 ~200–500ms | dentro SLA L2 |
| Vendor risk | nenhum | Apache 2.0, model hospedado HF (mirror gratuito) |

**Comparação Cohere Rerank v3** (pra justificar no paper §5.5): Cohere @ $1/1k = ~$14/mês a 14k qpm. BGE local = $0/mês recorrente. Break-even em 6 dias se considerar $0.20/h × 6h impl = $1.20 sunk cost. Net savings de ~$165/ano + privacy preservation.

---

## Smoke local (não-eval)

Pós-build, validar que modelo carrega + retorna scores plausíveis:

```bash
cd /root/.openclaw/workspace/tools/nox-mem
NOX_RERANKER_MODE=active node -e "
import('./dist/lib/reranker.js').then(async (m) => {
  const candidates = [
    { id: 1, score: 1.0, rrfScore: 1.0, source_file: 'a.md', chunk_type: 'concept',
      chunk_text: 'edge typing reduces relation_reason cardinality from free-form to enum closed', source_date: null, match_type: 'fts' },
    { id: 2, score: 0.9, rrfScore: 0.9, source_file: 'b.md', chunk_type: 'concept',
      chunk_text: 'random unrelated text about cooking', source_date: null, match_type: 'fts' },
  ];
  const out = await m.rerank('edge typing nox-mem', candidates, 2);
  console.log('result:', out.map(r => ({id: r.id, score: r.score, txt: r.chunk_text.slice(0,40)})));
});
"
```

Esperado: chunk id=1 fica em pos 0 (relevante), id=2 em pos 1.

---

## Risk register

| # | Risco | Mit. |
|---|---|---|
| 1 | Cold start 2-4s no primeiro request por proc | Warm-up no boot do `nox-mem-api` (eager load no NOX_RERANKER_MODE!=off) |
| 2 | Model download HF flaky em deploy | Usar `TRANSFORMERS_CACHE=/var/cache/nox-mem-models/` + pre-warm em build step |
| 3 | TOP_K_IN=50 cobre só 50% recall em queries head-of-tail | Telemetria: track `gold_in_top_50` se eval rodar; ajustar K_IN |
| 4 | ONNX runtime crash em CPU específico (AVX2 ausente) | fail-open silencia; runtime check `onnxruntime` ABIs antes activate |
| 5 | tokenizer overflow em chunks longos (>512 tokens) | truncate query+chunk pair na entrada; xenova pipeline já trunca por padrão |
| 6 | shadow-mode log volume (1.5k queries/d × 6 cols) | search_telemetry indexed em ts; cron quarterly purge >180d |

---

## Tasks

- [ ] Spec aprovado (este doc)
- [ ] `migrateToV16()` em `src/db.ts` — 6 ALTER TABLE additive idempotent
- [ ] `src/lib/reranker.ts` — lazy-load pipeline, modes off/shadow/active, fail-open, timeout, telemetry helpers
- [ ] `src/__tests__/reranker.test.ts` — 10 cases mockados (acima)
- [ ] Hook em `src/search.ts` `searchHybrid()` — após `applyReasonBoost`, antes do final slice
- [ ] `logTelemetry()` em search.ts ganha 6 args reranker_*
- [ ] CLI `eval run-batch --variant rerank` (alias=hybrid+shadow→active forçado em escopo da run)
- [ ] `npm run build` + `npm test` — 10/10 reranker tests pass
- [ ] Smoke local com query mock (não rodar contra corpus golden — VPS only)
- [ ] Commit local no nox-workspace (NÃO push, sync deferred)
- [ ] Sync VPS deferido (Toto manual)

---

## Definition of Done (current scope: impl + spec + tests local)

- [x] Engine decision documentada (§Engine choice)
- [ ] Schema v16 migration aplica idempotente em test DB
- [ ] `reranker.ts` exporta `rerank()`, `getMode()`, `getTopKIn()`, `getTopKOut()`, summary type
- [ ] `searchHybrid()` chama reranker condicionalmente; off-mode preserva pipeline byte-perfect
- [ ] 10/10 reranker tests pass (mocked pipeline)
- [ ] `--variant rerank` na CLI eval roda hybrid + força reranker active **na run** sem persistir env
- [ ] `tsc` clean (zero erro/warning novo)
- [ ] Spec apontada por DECISIONS.md (append nova D31 explicando D01 escopo + engine)

**Out-of-scope desta sessão (gated to VPS):**
- Eval contra golden corpus (R01c-v1.2)
- Activate gate (7d shadow window)
- Pre-warm strategy no `nox-mem-api` boot
