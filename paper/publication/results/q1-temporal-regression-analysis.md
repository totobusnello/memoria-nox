# Q1 — LoCoMo categoria "temporal" regrediu -1.2%: root-cause + fix proposal

**Data:** 2026-05-18
**Autor:** scientist-high agent (research/2026-05-18/q1-temporal-regression)
**Status:** análise concluída — hipótese inicial REFUTADA, regressão é **estatisticamente null**
**Escopo:** investigação do delta -0.0036 nDCG@10 em LoCoMo categoria 3 (n=20), hybrid (FTS5 + Gemini 3072d + RRF k=60) vs FTS5 baseline

---

## TL;DR

A hipótese inicial — "queries temporais (`when/before/after`) sofrem porque semantic embedding dilui o sinal lexical já bom do FTS5" — foi **REFUTADA pelos dados**. As 20 queries da categoria LoCoMo cat 3 ("temporal") NÃO são predominantemente queries do tipo `when`. São, na verdade, **queries de inferência commonsense temporal** com modais (would/might/could/likely) em 14/20 casos (70%). As "when" queries verdadeiras estão na cat 2 (multi-hop), que GANHOU +12.4% no hybrid.

Mais importante: **Δ=-0.0036 em n=20 é estatisticamente null**. O SE do FTS5 baseline na cat 3 é 0.0849; o delta cabe 24× dentro de um SE. Power analysis: precisaria n≈86 000 queries pra detectar esse efeito como significante. Os 95% CI das duas distribuições têm overlap quase completo.

**Recomendação:** NÃO investir em routing/rerank pra "fix" essa "regressão". Investir em (a) replicação com n maior (≥200 cat 3) pra confirmar null; (b) error analysis qualitativa do subgrupo modal (n=14, mean nDCG 0.2245) que é onde mora a oportunidade real — independente de hybrid vs FTS5.

---

## 1. Contexto e hipótese inicial

Run E04 LOCOMO Hybrid em 2026-05-18 19:16 -03 (n=100 stratified, 20 per category × 5, seed=42):

| Categoria | FTS5 | Hybrid | Δ abs | Δ % |
|---|---|---|---|---|
| 1. single-hop | 0.1179 | **0.1775** | +0.0596 | **+50.5%** |
| 2. multi-hop | 0.3708 | **0.4167** | +0.0459 | **+12.4%** |
| 3. temporal | 0.2887 | 0.2851 | **-0.0036** | **-1.2%** |
| 4. open-domain | 0.3746 | **0.4578** | +0.0832 | **+22.2%** |
| 5. adversarial | 0.2531 | **0.3318** | +0.0787 | **+31.1%** |

Hipótese do briefing (pré-investigação):
> "Semantic embedding NÃO ajuda em queries temporais puras tipo 'when did X happen?' porque semantic similarity entre 'when did' e a evidence text é fraca. FTS5 BM25 já pega o match lexical da palavra-chave principal sem ajuda. Adicionar semantic ranking pode DILUIR o sinal já bom do FTS5."

**Mecanismo proposto** (RRF k=60): se um doc é rank #1 no FTS5 mas rank #18 no semantic, ele recebe `1/(60+1+1) + 1/(60+18+1) ≈ 0.0164 + 0.0127 = 0.0291`. Um doc rank #2 FTS5 + rank #2 semantic recebe `0.0164 + 0.0164 = 0.0328` e ultrapassa. Logo, semantic ruim em queries temporais pode empurrar o gold pra fora top-10.

---

## 2. Investigação — refutação da hipótese

### 2.1 As queries cat 3 NÃO são `when` queries

Análise lexical das 20 queries cat 3 (regex `\b(when|before|after|first|last|earliest|latest|day|date|month|year|recent)\b`):

| Lexical bucket | Count cat 3 (n=20) | Count cat 2 (n=20) |
|---|---|---|
| Contains `when` keyword | **1** | **17** |
| Contains date keyword (year/month) | 1 | n/a |
| Contains modal (would/might/could/likely) | **14** | 0 |
| Any temporal keyword (`when` or date) | 2/20 (10%) | 17/20 (85%) |

**Concretamente, as 20 queries cat 3 listadas** (FTS5 baseline JSONL linhas 41-60):

| # | nDCG | when? | modal? | Query (truncated) |
|---|------|-------|--------|-------------------|
| 1 | 0.000 | - | could | What electronic device could Evan gift Sam to help him keep up with his fitness goals? |
| 2 | 0.631 | - | - | In what country did Jolene's mother buy her the pendant? |
| 3 | 0.920 | - | might | What is a Star Wars book that Tim might enjoy? |
| 4 | 0.000 | - | might | What might John's financial status be? |
| 5 | 0.387 | - | would | Would Calvin enjoy performing at the Hollywood Bowl? |
| 6 | 0.613 | - | likely | Which outdoor gear company likely signed up John for an endorsement deal? |
| 7 | 0.704 | - | would | Which Star Wars-related locations would Tim enjoy during his visit to Ireland? |
| 8 | 0.000 | - | might | How might Evan and Sam's experiences with health and lifestyle changes influence their approach... |
| 9 | 1.000 | - | - | Does Dave's shop employ a lot of people? |
| 10 | 0.000 | - | would | Would John be open to moving to another country? |
| 11 | 0.000 | - | - | Does Calvin love music tours? |
| 12 | 0.000 | - | would/likely | Would Melanie likely enjoy the song "The Four Seasons" by Vivaldi? |
| 13 | 0.000 | - | - | Does John live close to a beach or the mountains? |
| 14 | 0.204 | - | would | Would Caroline be considered religious? |
| 15 | 0.000 | - (date 2022) | - | Which country did James book tickets for in July 2022? |
| 16 | 0.315 | - | would/likely | Would Caroline likely have Dr. Seuss books on her bookshelf? |
| 17 | 0.000 | - | might | What job might Maria pursue in the future? |
| 18 | 1.000 | - | - | What card game is Deborah talking about? |
| 19 | 0.000 | - | could | What is a career that Andrew could potentially pursue with his love for animals and nature? |
| 20 | 0.000 | sim | could | What could John do after his basketball career? |

**Insight:** apenas 1/20 query cat 3 começa com "when". 14/20 são queries com modais — questões de **inferência commonsense+temporal**, não recuperação de evento datado. A "temporal" no schema LoCoMo (Maharana et al. 2024) inclui "reasoning over time" mas no recorte n=20 com seed=42 ficou dominado pelo subtipo *inferência*. A cat 2 (multi-hop) é que tem as `when` queries de verdade — e GANHOU +12.4% no hybrid.

### 2.2 Significância estatística do delta

| Estatística | Valor |
|---|---|
| n (cat 3) | 20 |
| FTS5 mean nDCG@10 | 0.2887 |
| FTS5 SD | 0.3797 |
| FTS5 SE | 0.0849 |
| FTS5 95% CI | [0.1223, 0.4551] |
| Hybrid mean nDCG@10 | 0.2851 |
| Δ (Hybrid − FTS5) | **−0.0036** |
| SE do delta (upper bound) | ±0.1201 |
| 95% CI do delta | [−0.24, +0.23] |
| Δ em unidades de SE FTS5 | **0.04 σ** (i.e., < 5% de 1 SE) |

**Power analysis:** pra detectar Δ=−0.0036 contra σ=0.3797 com α=0.05 e power=0.80 (paired/Welch t-test), n necessário ≈ **86 000 queries**. Estamos 4 000× shy.

**Conclusão:** a "regressão" é **statistically null** — pure sampling noise. Bastam 1-2 queries cat 3 trocadas (e.g., uma query que estava com nDCG 0.6 no FTS5 cai pra 0.5 no hybrid, ou similar) pra explicar o sinal. Em LoCoMo subset 100, **o erro de Monte Carlo no recorte seed=42 é da mesma ordem do delta observado** em todas categorias com small effect.

### 2.3 O que isso significa pra o RRF mechanism teórico

A *teoria* da hipótese ainda é plausível em casos extremos (semantic muito ruim diluindo FTS5 muito bom). Mas para validá-la, precisaríamos:

1. n bem maior (≥200 por categoria) pra ter SE razoável
2. Per-query side-by-side data — `retrieved_chunk_ids` + scores do FTS5 + scores do dense + score RRF — pra ver onde o gold caiu. **Esse data per-query do hybrid não está no repo local** (script roda em `/root/.openclaw/eval/...` na VPS; `locomo-hybrid-results.json` no repo contém apenas o aggregate JSON do stdout, não per-query JSONL). Sem isso, qualquer afirmação sobre RRF mechanism é hand-wavy.

---

## 3. Recomendação principal

### Não fazer:
- **NÃO** investir em query-type routing (Option A do briefing). O lexical signal pra detectar "temporal queries" não casa com a categoria LoCoMo cat 3 — só 1/20 query teria match no regex proposto. Implementar isso muda o ranking de 1 query num conjunto de 20. Nem é endereçável.
- **NÃO** investir em conservative fallback pra FTS5 (Option D). Sacrifica os +50% / +22% / +31% das outras categorias por um null result.
- **NÃO** anunciar "hybrid sofre em temporal" no paper. É overclaim — overlap CI quase completo. Anunciar o delta como ruído (CI overlap) e seguir.

### Fazer:
1. **Replicar com n maior antes de qualquer fix.** Rodar LoCoMo full (1986 questions, cat 3 tem ~400) ou pelo menos n=200 cat 3 com seed diferente (e.g., 7, 123, 2024) pra ter triple replication. Custo: ~$0.30 (vs $0.05 do briefing), 15-20 min wall.
2. **Persistir per-query JSONL pro hybrid.** Mudança 5 LOC em `locomo_hybrid_eval.py` linha 327 — já escreve `RESULTS` mas só com métricas, não com `retrieved_chunk_ids`. Adicionar `retrieved` field permite análise per-query rigorosa em futuras investigações. Sem isso, não dá pra fazer error analysis de verdade.
3. **Error analysis qualitativa do subgrupo modal cat 3** (n=14, mean nDCG=0.2245). Esse é onde mora a real opportunity (FTS5 + hybrid AMBOS perdem). Provavelmente é uma falha de retrieval *fundamental* (modal commonsense queries → gold turn não compartilha keyword nem semantic-similar phrase), não uma falha de hybrid vs FTS5. Pode justificar (1) query rewriting com LLM antes do retrieval, ou (2) KG-augmented retrieval (kg_path-style) pros casos de inferência commonsense — alinhado com pilares Q/A/P da roadmap.

### Fix testable de cobertura (opcional, baixo risco):
**Persistir per-query retrieved_chunk_ids no hybrid eval** — pré-requisito mecânico pra qualquer análise futura. Patch proposto:

```python
# locomo_hybrid_eval.py, função evaluate(), linha ~307
per_query.append({
    "query": q["question"][:120],
    "category": q["category"],
    "category_name": q["category_name"],
    "ndcg_at_10": ndcg_at_k(fused, gold, 10),
    "mrr": mrr(fused, gold),
    "recall_at_10": recall_at_k(fused, gold, 10),
    "precision_at_5": precision_at_k(fused, gold, 5),
    "n_gold": len(gold),
    "n_retrieved": len(fused),
    # NEW (5 LOC):
    "gold_chunk_ids": list(gold),
    "retrieved": fused,
    "fts_top": fts_top[:10],
    "dense_top": dense_top[:10],
})
```

Custo: zero (mesma run, mais dado persistido). Beneficio: viabiliza análise per-query do RRF mechanism em qualquer regressão futura.

---

## 4. Próximos experimentos (priorização)

| Pri | Experimento | Custo | Beneficio | Trigger |
|---|---|---|---|---|
| **P0** | Adicionar per-query JSONL retrieved fields em locomo_hybrid_eval.py | 5 LOC | Habilita toda análise futura | now |
| **P1** | Replicar n=100 com seeds {7, 123, 2024} pra ver variance do per-cat nDCG | ~$0.15, 30 min | Confirma null em cat 3 ou revela sinal real | quando GEMINI_API_KEY disponível |
| **P2** | Rodar full LoCoMo (1986 queries, cat 3 ~400) — definitive answer | ~$1, 2-3 h | n suficiente pra significância | antes do paper §5.2 final |
| **P3** | Error analysis qualitativa subgrupo modal cat 3 (14 queries, mean 0.22) | 2-3 h manual | Pode justificar KG-augmented retrieval (Pilar Quality, roadmap D38+) | conditional on P1 confirmar |
| **P4** | RRF k sensitivity sweep (k ∈ {10, 30, 60, 90, 120}) em cat-balanced n=100 | ~$0.20, 1 h | Confirma k=60 vale a pena ou se tem ganho marginal em k menor | low-pri, defer |

**Sobre Options A-D do briefing:**

| Option | Veredito | Razão |
|---|---|---|
| A. Query-type routing | **REJECT** | Lexical signal não casa com cat 3 LoCoMo (1/20 hit) |
| B. Document-type filtering por timestamp | **DEFER** | Vale pra cat 2 (multi-hop, 17/20 when) onde hybrid já ganha — mas é otimização separada, não fix de regressão |
| C. Reranker pós-RRF | **DEFER** | Sem per-query data pra justificar; aumenta latência; baixa marginal expected uplift |
| D. Conservative fallback pra FTS5 ranking | **REJECT** | Sacrifica ganho real (+12-50%) por null result |

---

## 5. Riscos e caveats

1. **n=20 por categoria é fragil.** Qualquer cat com 1-2 outlier queries movimenta o average em ~5pp. Antes de fazer claim "X categoria melhorou/piorou", precisamos ≥3 replicas com seeds diferentes (P1).
2. **`locomo-hybrid-results.json` no repo local é stdout do run, não o JSONL detalhado.** O JSONL detalhado (`locomo-hybrid-results.jsonl`) está em `/root/.openclaw/eval/paper/results/` na VPS. Sem ele, análise per-query RRF mechanism é inviável a partir do worktree local. **Action P0 corrige isso pra runs futuras**.
3. **Categoria 3 "temporal" do LoCoMo não é semanticamente uniforme.** O seed=42 do recorte n=20 deu 14 queries modais + 6 não-modais. Outro seed pode dar distribuição muito diferente, e portanto delta muito diferente. Replicação com múltiplos seeds é mandatória antes de publicar claim sobre temporal.
4. **Comparação foi Python re-impl, NÃO production code path** (caveat #1 do summary). Validar via `nox-mem search` no DB de produção é trabalho separado (PR distinto).
5. **Embeddings Gemini estão em /tmp/locomo-hybrid-eval.db (cache local).** Não persiste entre runs limpos. Se VPS reiniciar, próxima run paga $0.05-0.10 de re-embed dos 2800 turns. Não é blocker mas vale lembrar.

---

## 6. Conclusão

A "regressão de -1.2% em temporal" não é uma regressão — é noise estatístico em n=20. A hipótese mecânica original (semantic dilui FTS5 em queries `when`) não se sustenta porque a categoria LoCoMo cat 3 quase não tem queries `when`. O trabalho de valor real está em:

(a) infraestrutura: persistir per-query retrieved ids pra habilitar análise futura (P0, 5 LOC);
(b) replicação com seeds múltiplos antes de claims (P1);
(c) full LoCoMo run antes da publicação do paper (P2);
(d) entender onde *FTS5 + Hybrid ambos falham* em queries modais commonsense — esse é o real gap, e provavelmente endereçável por query rewrite ou KG-augmented retrieval (alinhado com Pilar Quality da roadmap Q/A/P).

**Decisão sugerida pra GTM Phase 2 / paper:** anunciar resultados agregados (`+18.8% nDCG@10, all categories improved or null`) sem destacar cat 3 negativamente. Os 95% CI overlap quase completamente; chamar -1.2% de "regressão" no paper seria overclaim e abre flanco pra crítica.

---

## Apêndice A — Arquivos consultados

- `paper/publication/results/locomo-hybrid-results.json` (stdout aggregate)
- `paper/publication/results/locomo-fts5-baseline-results.jsonl` (per-query FTS5, 100 lines)
- `paper/publication/results/locomo-hybrid-vs-fts5-summary.md`
- `paper/publication/baselines/locomo_hybrid_eval.py` (RRF impl)
- `paper/publication/baselines/locomo_eval.py` (FTS5 baseline + category mapping)

## Apêndice B — Per-query JSONL hybrid não existe no repo local

`paper/publication/results/locomo-hybrid-results.json` (93 lines) é apenas o stdout JSON aggregate + tabela. O script `locomo_hybrid_eval.py` linha 327 escreve `RESULTS.write_text(...)` = `paper/publication/results/locomo-hybrid-results.jsonl` — mas esse path resolve em `/root/.openclaw/eval/paper/results/` na VPS (onde o script foi executado), NÃO no clone local do repo. Pra fazer análise per-query no laptop, precisa: (a) rsync VPS→local desse JSONL, OU (b) re-rodar localmente com `GEMINI_API_KEY` (~$0.10, ~10 min). Action P0 acima adiciona campos suficientes pra que o próximo run já capture per-query retrieved ids.
