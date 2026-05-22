# Formula v2 — Design de Tuning de Weights e Grid Search

**Data:** 2026-05-20  
**Autor:** scientist agent  
**Status:** DESIGN (não executar — proposta de metodologia + candidatos)  
**Cross-links:** [[g5-wave-a-post-deploy-2026-05-19]] · [[g6-regression-investigation-2026-05-20]] · [[salience-distribution-audit-2026-05-19]]

---

## 1. Contexto e Motivação

A fórmula aditiva v2 (PR #150, `feat/salience-additive-evidence-2026-05-19`) substituiu a multiplicativa com base em evidência do corpus prod (`g5.db`, 68,995 chunks):

```
salience = 0.55·importance + 0.15·recency + 0.10·pain + 0.20·access
```

Os pesos foram **calibrados por inspeção** (audit-based), não por otimização quantitativa. G5 V3 confirmou ganho: A8 active = 0.6237 > A7 shadow = 0.6155 (Δ +1.3% nDCG@10 em `g5.db`). Porém G7 em `entity-eval.db` (500 chunks) mostrou A8 ≈ A8-off (0.5845 vs 0.5872, Δ +0.5% favorecendo off), o que levanta a questão: **os pesos são ótimos, ou apenas razoáveis?**

### 1.1 Diagnóstico dos signals atuais

| Signal | Estado no corpus prod | Peso atual | Justificativa original | Problema |
|---|---|---|---|---|
| `importance` | ✅ ALIVE — bimodal (74% low / 17% high) | 0.55 | Único signal contínuo forte | Proxy de chunk_type, não informação nova |
| `access_count` | ✅ ALIVE (binary) — 87% zero / 13% accessed | 0.20 | Signal latente não usado antes | `log1p(n)/log(1000)` é log-scale, mas 87% zero reduz impacto médio |
| `recency` | ☠️ DEAD (pós-restore) — 99.76% em [7-30d] | 0.15 | Dampened por corpus homogêneo | Naturaliza em 60-90d; curto prazo é ruído |
| `pain` | ☠️ DEAD — 90.67% no default 0.2 | 0.10 | Dampened por ausência de backfill | Sem backfill, é constante multiplicada por peso |

**Implicação crítica:** com recency ~0.92 (constante) e pain ~0.23 (constante), a fórmula atual colapsa para:

```
salience ≈ 0.55·importance + 0.15·0.92 + 0.10·0.23 + 0.20·access
         ≈ 0.55·importance + 0.138 + 0.023 + 0.20·access
         ≈ 0.55·importance + 0.161 + 0.20·access (constante aditiva ≈ 0.161)
```

Isso significa que **recency e pain adicionam um bias constante** (~0.161), não discriminação. O verdadeiro impacto é:

```
effective_salience_variance = 0.55·Var(importance) + 0.20·Var(access)
```

---

## 2. Análise de Contribuições Reais

### 2.1 Decomposição de variância (estimada)

Com base no corpus prod:

| Signal | Mean | Std Dev (estimado) | Contribution to salience Var |
|---|---|---|---|
| importance | 0.45 | ~0.22 (bimodal) | `(0.55)² × (0.22)² ≈ 0.0147` |
| recency | 0.92 | ~0.04 (quase constante) | `(0.15)² × (0.04)² ≈ 0.000036` |
| pain | 0.23 | ~0.09 | `(0.10)² × (0.09)² ≈ 0.000081` |
| access | 0.05 | ~0.12 (binary-ish) | `(0.20)² × (0.12)² ≈ 0.000576` |

**→ importance responde por ~95% da variância de salience. access responde por ~4%. recency+pain juntos <1%.**

### 2.2 Problemas de design

1. **W_PAIN = 0.10 é desperdiçado** até backfill de pain ser feito. Em `entity-eval.db` o pain médio é 0.51 (corpus curado), então pain FUNCIONA lá — o que explica a performance inferior de A8 vs A8-off em G7: o peso de pain que "ajuda" em prod curado acaba distorcendo no eval set.

2. **W_RECENCY = 0.15 é prêmio à homogeneidade** pós-restore. Quando o corpus envelhecer naturalmente (>90d), recency terá distribuição mais rica (0.3–1.0), e o peso de 0.15 ficará subótimo no outro sentido.

3. **W_ACCESS com log1p é assimétrico.** O break-even onde access supera a constante de recency+pain é em access_count ≈ 3 (log1p(3)/log(1000) ≈ 0.21). Isso é um cliff muito abrupto.

4. **section_boost ausente na salience** (por design — já aplicado em sectionDelta). Mas no eval set entity-eval.db onde 100% chunks têm section, a ausência na fórmula cria sub-discriminação.

---

## 3. Novos Signals Candidatos

### 3.1 Cross-agent boost (Hipótese H4)

**Definição:** chunks que aparecem em múltiplas agent sessions (Atlas/Boris/Cipher/Lex/Forge) recebem boost proporcional ao número de agents que os "viram".

```typescript
cross_agent_component = log1p(agents_seen_count) / log(6)  // 6 agents max
```

**Fonte de dados:** `search_telemetry` tem `session_id` mas não `agent_name` diretamente. Precisaria de coluna `agents_seen_bitmask` ou nova tabela `chunk_agent_access`.

**Expectativa:** +1-3% nDCG em cross-agent queries (estimativa conservadora da literatura de personalization boosts). **Pré-req:** dados de acesso por agent não existem hoje.

**Custo de implementação:** médio (nova coluna + backfill parcial via search_telemetry).

### 3.2 KG centrality (Hipótese H4b)

**Definição:** chunks linkados a entities de alto grau no KG recebem boost. Entity com `degree > threshold` indica conceito central no grafo.

```typescript
// JOIN chunks.kg_entity_id → kg_entities.id → COUNT(kg_relations)
kg_centrality = clamp01(entity_degree / max_degree_observed)
```

**Fonte de dados:** `kg_entities` (~402 entities) + `kg_relations` (~544 relations). Grau médio ≈ 2.7.

**Expectativa:** +0-2% para queries sobre tópicos com KG denso. Impacto limitado porque 402 entities sobre 68,995 chunks = 0.6% linkagem.

**Custo de implementação:** baixo (query SQL adicional no JOIN, sem nova infra).

### 3.3 Query-doc cosine similarity (online signal)

**Definição:** usar a similaridade de embedding da query com o chunk como multiplicador de salience.

**Problema:** isso é o que o semantic search já faz. Colocar cosine dentro da salience introduziria feedback loop (semantic score afeta salience, salience reranks semantic results). **Rejeitado por design** — viola separação search/salience.

### 3.4 Recency exponential decay (refinamento)

**Definição atual:** half-life decay `2^(-age/retention_days)`. Para retention_days=90, chunk com 45d tem recency=0.71. Para 30d de vida, recency=0.79.

**Alternativa proposta:** decay mais agressivo nas primeiras 72h para capturar "freshness news":

```typescript
recency_v2 = age <= 3 ? 1.0 : 2^(-age / retention_days)
```

**Relevância imediata:** baixa (corpus atual homogêneo em [7-30d]). Anotar para quando corpus envelhecer.

---

## 4. Grid de Candidatos (12 configs)

A tabela abaixo define as 12 configurações propostas. Todas somam ≤1.0 (a diferença vai para um bias constante implícito ou normalização).

| Config | W_IMP | W_REC | W_PAIN | W_ACC | Modificações adicionais | Hipótese testada |
|---|---|---|---|---|---|---|
| **C00 — baseline** | 0.55 | 0.15 | 0.10 | 0.20 | nenhuma | referência |
| **C01 — recency+** | 0.45 | 0.25 | 0.10 | 0.20 | nenhuma | H1: W_RECENCY 0.15→0.25 melhora temporal queries |
| **C02 — recency++** | 0.40 | 0.30 | 0.10 | 0.20 | nenhuma | H1 forte: W_RECENCY 0.30 |
| **C03 — pain+** | 0.50 | 0.15 | 0.20 | 0.15 | nenhuma | H2: W_PAIN 0.10→0.20 melhora pain-weighted ranking |
| **C04 — pain++ importance−** | 0.40 | 0.15 | 0.25 | 0.20 | nenhuma | H2 forte: pain é 2° signal |
| **C05 — equal** | 0.25 | 0.25 | 0.25 | 0.25 | nenhuma | H2: equal weights como fallback robusto |
| **C06 — importance dominant** | 0.70 | 0.10 | 0.10 | 0.10 | nenhuma | importância máxima, menor dispersão |
| **C07 — access dominant** | 0.45 | 0.10 | 0.05 | 0.40 | nenhuma | access_count como 2° signal real |
| **C08 — access sqrt** | 0.55 | 0.15 | 0.10 | 0.20 | `access = sqrt(n)/sqrt(1000)` | normalização linear vs log-scale |
| **C09 — type-conditional pain** | 0.55 | 0.15 | — | 0.20 | `pain_eff = type_in(lesson,feedback,pending) ? 0.25 : 0.05` | H3: dynamic weights por chunk_type |
| **C10 — kg centrality** | 0.50 | 0.15 | 0.10 | 0.15 | `+0.10·kg_centrality` | H4b: KG centrality como 5° signal |
| **C11 — recency+ access+** | 0.40 | 0.25 | 0.05 | 0.30 | nenhuma | rebalance para signals ALIVE diminuindo signals DEAD |

### 4.1 Racional de seleção

- **C01/C02**: testam diretamente H1. Se temporal queries (Q70-Q110 do LongMemEval) melhoram com W_RECENCY alto, confirma que o sinal está presente mas sub-pesado — relevante quando corpus envelhecer.
- **C03/C04**: testam H2 (pain-weighted). Só faz sentido quando pain backfill existir. Em corpus atual terá impacto marginal — serve para **estabelecer baseline antes do backfill** e medir custo da distorção.
- **C05**: baseline robusto sem hipótese. Bom sanity check — se C05 ganha, implica que os pesos calibrados por audit são piores que chance.
- **C06**: comprova se a dominância de importance no variance decomposition é optimal ou se a diversificação ajuda.
- **C07**: testa se access_count 0/1 (binary, ~13% de chunks) captura sinal mais forte quando amplificado.
- **C08**: compara escala log vs linear de access — log1p satura rápido (access=10 → 0.347), linear é mais gradual.
- **C09**: testa H3 (dynamic weights por type). Se ganho ≤2%, não justifica complexidade condicional.
- **C10**: testa H4b (KG centrality). Pré-req: join kg_entities em query.
- **C11**: "ALIVE signals only" — maximiza os únicos dois signals com variância real.

---

## 5. Metodologia de Eval Barata

### 5.1 Fase 1 — Screening rápido (entity-eval.db, n=100)

**Custo estimado:** ~$0.10-0.20 por config × 12 configs = **$1.20-2.40 total**  
**Wall clock:** ~20 min (parallelizável em 3 batches de 4)

```bash
# Cada config vira env vars; eval driver existente re-usa
NOX_SALIENCE_W_IMPORTANCE=0.45 \
NOX_SALIENCE_W_RECENCY=0.25 \
NOX_SALIENCE_W_PAIN=0.10 \
NOX_SALIENCE_W_ACCESS=0.20 \
python3 eval/run_salience_grid.py --config C01 --db entity-eval.db --n 100
```

**Critério de corte:** configs que ficam >0.5% abaixo de C00 em nDCG@10 são eliminadas.

**Output esperado:** 4-6 configs sobrevivem para Fase 2.

### 5.2 Fase 2 — Validação em corpus real (g5.db subset, n=40)

**Custo estimado:** ~$0.30-0.50 por config × 5 configs = **$1.50-2.50**  
**Wall clock:** ~30 min

Usar `n=40` queries estratificadas (8 por categoria: temporal / single-hop / multi-hop / open-domain / adversarial) — sufficiency threshold para detectar Δ≥1.5% com poder estatístico razoável (α=0.05, power≈0.7 baseado em variance histórica LongMemEval).

### 5.3 Fase 3 — Full eval dos top-3 (g5.db, n=100)

**Custo estimado:** ~$0.30 × 3 = **$0.90**  
**Wall clock:** ~25 min

Apenas o top-3 da Fase 2 passa para full n=100, comparação direta com A8 canônico (0.6237).

### 5.4 Custo total estimado

| Fase | Configs | n por run | Custo estimado |
|---|---|---|---|
| Screening (entity-eval) | 12 | 100 | $1.20–2.40 |
| Validation (g5.db subset) | 5 | 40 | $1.50–2.50 |
| Full eval top-3 (g5.db) | 3 | 100 | $0.90 |
| **Total** | | | **$3.60–5.80** |

> Nota: custo dominante é Gemini embedding (~$0.0001/query × queries × configs). Estimativa conservadora; custo real pode ser 30-50% menor com cache de embeddings de query.

### 5.5 Isolação obrigatória (lição PR #145 + incident 2026-05-19)

Conforme `[[eval-harness-must-explicit-isolate-db]]`:

```python
import os
os.environ["NOX_DB_PATH"] = "/path/to/eval.db"  # explícito
_check_eval_isolation()  # assert NOX_DB_PATH ≠ prod db path
```

**Nunca** importar `getDb()` / `db.ts` em eval scripts. Usar `better-sqlite3` direto com path explícito.

---

## 6. Action Items Priorizados

### P0 — Pré-requisitos de infra (antes de qualquer grid)

| Item | Descrição | Estimativa |
|---|---|---|
| **I1: Env vars para weights** | Adicionar `NOX_SALIENCE_W_IMPORTANCE`, `NOX_SALIENCE_W_RECENCY`, `NOX_SALIENCE_W_PAIN`, `NOX_SALIENCE_W_ACCESS` em `salience.ts`. Fallback para valores hardcoded atuais se não definidas. | 30 min |
| **I2: Eval driver script** | `eval/run_salience_grid.py` — loop sobre JSON de configs, chama `/api/search` com `NOX_SALIENCE_*` env override, computa nDCG@10 D2, exporta CSV de resultados | 2h |
| **I3: Grid config JSON** | `eval/salience-grid-configs.json` com as 12 configs acima em formato canonico | 30 min |

### P1 — Telemetria de componentes (debug signal)

| Item | Descrição | Estimativa |
|---|---|---|
| **I4: Per-query salience breakdown** | Adicionar `NOX_SALIENCE_DEBUG=1` → logar `{chunk_id, importance_c, recency_c, pain_c, access_c, salience_total}` em `search_telemetry` ou stderr | 1h |
| **I5: /api/health.salienceWeights** | Expor pesos efetivos em `/api/health` para auditoria em prod sem SSH | 30 min |

### P2 — Pré-requisitos de data quality (desbloqueiam C03/C04)

| Item | Descrição | Estimativa |
|---|---|---|
| **I6: Pain backfill heurístico** | Usar `inferPain(chunk_type, content)` existente em `salience.ts` para backfill via `UPDATE chunks SET pain = inferred WHERE pain = 0.2 AND pain NOT IN (rated chunks)` | 2-3h + snapshot pré-op |
| **I7: source_type backfill** | Mapear `chunk_type` → `source_type` via regex em `source_uri` (mismatch confirmado no G6 investigation) | 2h |

### P3 — Novos signals (pós-grid)

| Item | Descrição | Pré-req |
|---|---|---|
| **I8: KG centrality component** | JOIN `kg_entities.degree` em `calculateSalience()` — adicionar como 5° parâmetro opcional em `SalienceInput` | Medir degree distribution em kg_entities |
| **I9: Cross-agent boost** | Nova tabela `chunk_agent_access(chunk_id, agent_name, count)` alimentada pelo search path | Instrumentar search por agent |

---

## 7. Hipóteses Testáveis e Critérios de Falsificação

### H1 — Aumentar W_RECENCY de 0.15 → 0.25 melhora temporal queries

**Racional:** temporal queries (ex: "o que aconteceu esta semana?") dependem de freshness. W_RECENCY=0.25 amplia diferenciação entre chunks de 7d vs 30d.

**Testável via:** C01 vs C00 com queries categorizadas como `temporal` no LongMemEval.

**Falsificação:** se `nDCG@10_temporal(C01) ≤ nDCG@10_temporal(C00) + 0.5%` em g5.db subset n=40, H1 é rejeitada. O corpus pós-restore é tão homogêneo (99.76% em [7-30d]) que recency não discrimina — nenhum weight resolve isso sem dados mais velhos.

**Condição de relevância futura:** reavaliar H1 quando corpus tiver >20% de chunks com age >90d (estimativa: 3-4 meses de uso contínuo).

---

### H2 — Equal weights (0.25 each) é fallback robusto

**Racional:** se a audit-based calibration não é significativamente melhor que pesos iguais, os signals têm importância comparável e o sistema é mais resiliente a mudanças de corpus.

**Testável via:** C05 vs C00 em nDCG@10 total em entity-eval.db + g5.db.

**Falsificação:** se `nDCG@10(C05) < nDCG@10(C00) - 1.0%`, a calibração baseada em audit é superior e equal weights é descartado. Se `|nDCG@10(C05) - nDCG@10(C00)| ≤ 1.0%`, considera-se C05 como "seguro" para ambientes sem audit disponível.

---

### H3 — Dynamic weights por chunk_type têm ganho ≤2% vs custo de complexidade

**Racional:** C09 aumenta W_PAIN para `lesson/feedback/pending` (tipos com pain semântico real) e reduz para outros. Se esse ganho é ≤2% nDCG, a complexidade adicional (branching na fórmula, mais env vars, mais testes) não se justifica.

**Testável via:** C09 vs C00 em nDCG@10 total.

**Falsificação:** se `nDCG@10(C09) > nDCG@10(C00) + 2.0%`, H3 é rejeitada — ganho justifica complexidade. Threshold 2% baseado na melhoria de +1.3% que A8 active obteve sobre A7 shadow (considerado "ganho real").

---

### H4 — Adicionar `cross_agent_boost` como 5° signal melhora cross-agent queries

**Racional:** queries que envolvem conhecimento multi-agent (ex: "o que Boris sabe sobre X que Cipher não sabe") dependem de quem acessou o quê. Chunks acessados por múltiplos agents são provavelmente mais centrais ao conhecimento compartilhado.

**Testável via:** instrumentar `search_telemetry` por agent, criar `chunk_agent_access`, implementar C10-variant e medir em queries cross-agent extraídas do LongMemEval.

**Falsificação:** se coverage de cross-agent queries no eval set atual for <10% (provável) ou se acréscimo em nDCG@10 total for <1.5%, H4 permanece parkada. **Pré-requisito é infra de acesso por agent — não existe hoje.**

---

## 8. Referência de Implementação (env vars)

```typescript
// salience.ts — weights configuráveis via env (PR followup proposto)
const W_IMPORTANCE = parseFloat(process.env.NOX_SALIENCE_W_IMPORTANCE ?? "0.55");
const W_RECENCY    = parseFloat(process.env.NOX_SALIENCE_W_RECENCY    ?? "0.15");
const W_PAIN       = parseFloat(process.env.NOX_SALIENCE_W_PAIN       ?? "0.10");
const W_ACCESS     = parseFloat(process.env.NOX_SALIENCE_W_ACCESS     ?? "0.20");

// Validação: soma deve ser ≤ 1.0; aviso se > 1.0
const W_SUM = W_IMPORTANCE + W_RECENCY + W_PAIN + W_ACCESS;
if (W_SUM > 1.0 + 1e-6) {
  console.warn(`[salience] W_SUM=${W_SUM.toFixed(3)} > 1.0 — salience scores serão truncados em 1.0`);
}
```

```python
# eval/salience-grid-configs.json (schema)
[
  {"id": "C00", "W_IMP": 0.55, "W_REC": 0.15, "W_PAIN": 0.10, "W_ACC": 0.20, "notes": "baseline"},
  {"id": "C01", "W_IMP": 0.45, "W_REC": 0.25, "W_PAIN": 0.10, "W_ACC": 0.20, "notes": "H1 recency+"},
  ...
]
```

---

## 9. Cronograma Proposto

| Semana | Atividade | Depende de |
|---|---|---|
| W0 (agora) | I1 (env vars) + I2 (eval driver) + I3 (grid JSON) | — |
| W0 | Fase 1 screening — 12 configs × entity-eval.db | I1, I2, I3 |
| W1 | Fase 2 validation — top 5 × g5.db subset n=40 | Fase 1 |
| W1 | I6 (pain backfill) em staging | snapshot pré-op obrigatório |
| W2 | Fase 3 full eval — top 3 × g5.db n=100 | Fase 2 |
| W2 | Decisão: adotar winner config ou manter C00 | Fase 3 |
| W3+ | I8 (KG centrality) se C10 sobreviveu Fase 2 | Fase 3 |

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|---|---|---|
| Pain backfill distorce prod antes do eval | Alta | I6 só em staging; validar via `--dry-run` + canary pré-op |
| Grid eval usa prod DB acidentalmente | Alta | `_check_eval_isolation()` mandatório (lição incident 2026-05-19) |
| Winner config tem ganho marginalmente acima de noise | Média | Reportar p-value entre configs via bootstrap nDCG; threshold mínimo Δ≥1.5% |
| recency weight alto piora corpus pós-envelhec. | Baixa | Re-eval quando corpus tiver >20% chunks >90d |
| Corpus shift entre Fase 1 e Fase 3 | Baixa | Salvar snapshot do DB de eval antes de iniciar grid |

---

## Sumário: Top 3 Hipóteses + Custo Estimado

**Top 3 hipóteses por impacto esperado × facilidade de validação:**

1. **H1 (W_RECENCY+)**: baixo custo de implementação (apenas env var), impacto esperado +1-2% em temporal queries quando corpus envelhecer — a mais relevante estrategicamente.
2. **H2 (equal weights)**: valida se a calibração por audit é robusta ou se a arquitetura é resiliente por design — teste de sanity barato e definitivo.
3. **H3 (dynamic weights por type)**: valida a hipótese de que complexidade condicional não se justifica — se confirmada, fecha a discussão sobre tipos de chunk com permanência.

**Custo estimado full grid (12 configs × 3 fases):** ~$3.60–5.80 em Gemini calls.

**Recomendação de sequência:** implementar I1 (env vars, ~30 min) antes de qualquer eval — sem isso o grid requer rebuild a cada config.

---

*Documento gerado em 2026-05-20 como proposta de design. Não executar grid sem snapshot pré-op do eval DB e `_check_eval_isolation()` ativo.*
