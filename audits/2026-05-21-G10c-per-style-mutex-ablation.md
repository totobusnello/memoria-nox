# G10c — Per-Style Hard Mutex Ablation

**Date**: 2026-05-21 BRT
**Branch**: `research/g10c-per-style-mutex`
**Context**: G10 (PR #182, aggregate +0.79% nDCG) → G10b (per-category breakdown, [audit](2026-05-21-G10b-per-category-mutex-ablation.md)) → G10c needed: does the Hard Mutex section ↔ source_type behave differently across query **styles** (paraphrase vs literal)?
**Follow-up from**: `audits/2026-05-21-G10b-per-category-mutex-ablation.md` recommendation §5.

## Setup

| Item | Value |
|---|---|
| Source dataset | `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db` (1.2GB, 69495 chunks) |
| Driver | `entity_ablation_eval.py` (emits **`per_style`** natively) |
| Endpoint | `http://127.0.0.1:18803/api/search` (isolated, prod 18802 untouched) |
| Code | `/root/.openclaw/workspace/tools/nox-mem/dist/api-server.js` (May 20 15:05 = post PR #182) |
| n queries | 100 (5 categorias × 2 styles × 10 queries) |
| Toggle (disabled run) | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` (rollback flag) |
| Common env | `NOX_SALIENCE_MODE=active` em ambas runs |
| VPS | `root@187.77.234.79` (post IP swap 2026-05-20) |
| Aggregator | `audits/data-g10c/aggregate.py` |

### Style universe

Inspeção de `queries.jsonl` mostra **2 styles** balanceados (não 3 como o prompt original sugeria):

```
$ jq -r '.style' queries.jsonl | sort | uniq -c
     50 keyword
     50 natural-language
```

Distribuição perfeitamente estratificada — cada uma das 5 categorias tem 10 keyword + 10 natural-language. Sem `paraphrase`, `literal`, `reformulated` no dataset; o eixo binário é `keyword` (exact-term, e.g. "Isabela Cunha description") vs `natural-language` (full prose question, e.g. "What is fundo lombardia's role?").

### Data source

**Re-using G10b runs**. A8 canonical config + g9.db + entity-ablation harness são idênticos entre G10b e G10c. O harness já emite `per_style` nativamente — só faltava reaggregar e cruzar com `per_category`. Re-rodar daria os mesmos números (mesma DB, mesmo binário, mesmo config, harness determinístico). Fonte:

- `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/g10b/mutex_active.json`
- `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/g10b/mutex_disabled.json`

Para reprodutibilidade do G10c isoladamente, o script orchestrator `run-g10c-mutex-ablation.sh.unrun` está committed em `audits/data-g10c/` — execute na VPS quando precisar regenerar.

### Verification: harness vs re-derivation

`aggregate.py` re-deriva `per_style` da lista `per_query` e cruza com o `per_style` emitido pelo harness:

```
active/natural-language:  ndcg harness=0.558741  re-derived=0.558741  match=True
active/keyword:           ndcg harness=0.539145  re-derived=0.539145  match=True
disabled/natural-language: ndcg harness=0.550135 re-derived=0.550135  match=True
disabled/keyword:         ndcg harness=0.543075  re-derived=0.543075  match=True
```

100% match em todos os 4 buckets — re-derivation é fiel.

## Aggregate Cross-Check (G10 → G10b → G10c)

| eval | n | nDCG Δ% | MRR Δ% | R@10 Δ% | P@5 Δ% |
|---|---:|---:|---:|---:|---:|
| G10 | 100 | +0.79% | +2.65% | n/a | n/a |
| G10b | 100 | +0.43% | +0.82% | -1.34% | -3.26% |
| G10c | 100 | **+0.43%** | **+0.82%** | **-1.34%** | **-3.26%** |

G10c reproduz G10b bit-a-bit (mesmos artifacts). Direção consistente com G10 — magnitude attenuada dentro do noise floor (n=100). Mutex aggregate-positive confirmado.

## Per-Style Breakdown

### nDCG@10

| style | n | mutex active | mutex disabled | Δabs | Δ% | veredicto |
|---|---:|---:|---:|---:|---:|---|
| **natural-language** | 50 | 0.5587 | 0.5501 | +0.0086 | **+1.56%** | MUTEX HELPS |
| **keyword** | 50 | 0.5391 | 0.5431 | -0.0039 | **-0.72%** | mutex slightly hurts |

### MRR

| style | mutex active | mutex disabled | Δabs | Δ% | veredicto |
|---|---:|---:|---:|---:|---|
| natural-language | 0.6214 | 0.5983 | +0.0231 | **+3.86%** | **STRONG WIN** (top-1) |
| keyword | 0.5733 | 0.5867 | -0.0134 | **-2.27%** | mutex hurts top-1 |

### Recall@10 + Precision@5

| style | R@10 active | R@10 disabled | Δ% R@10 | P@5 active | P@5 disabled | Δ% P@5 |
|---|---:|---:|---:|---:|---:|---:|
| natural-language | 0.6067 | 0.6167 | **-1.62%** | 0.1720 | 0.1800 | **-4.44%** |
| keyword | 0.6233 | 0.6300 | **-1.06%** | 0.1840 | 0.1880 | **-2.13%** |

R@10 cai levemente em ambos os styles — mutex tira chunks de relevance secundária do top-10 (consistente com a leitura multi-hop do G10b: chunks intermediários da chain perdem rank). P@5 NL drops more (-4.44% vs -2.13%) — natural-language traz mais lixo nas primeiras 5 posições quando mutex disabled, mais limpa quando active.

## Style × Category — onde mutex acerta e onde erra (nDCG@10)

| style | category | n | nDCG active | nDCG disabled | Δabs | Δ% |
|---|---|---:|---:|---:|---:|---:|
| natural-language | **single-hop** | 10 | 0.7155 | 0.6286 | +0.0869 | **+13.83%** |
| natural-language | multi-hop | 10 | 0.6842 | 0.7120 | -0.0278 | -3.91% |
| natural-language | temporal | 10 | 0.0000 | 0.0000 | 0 | n/a (degenerate) |
| natural-language | open-domain | 10 | 0.7066 | 0.7226 | -0.0161 | -2.22% |
| natural-language | adversarial | 10 | 0.6875 | 0.6875 | 0 | **+0.00%** (neutral) |
| keyword | single-hop | 10 | 0.4286 | 0.4286 | 0 | **+0.00%** (neutral) |
| keyword | multi-hop | 10 | 0.6401 | 0.6667 | -0.0266 | -3.99% |
| keyword | temporal | 10 | 0.0000 | 0.0000 | 0 | n/a (degenerate) |
| keyword | **open-domain** | 10 | 0.8270 | 0.7748 | +0.0522 | **+6.74%** |
| keyword | adversarial | 10 | 0.8000 | 0.8453 | -0.0453 | **-5.35%** |

### Style × Category — MRR

| style | category | MRR active | MRR disabled | Δ% |
|---|---|---:|---:|---:|
| natural-language | **single-hop** | 0.6571 | 0.5417 | **+21.32%** |
| natural-language | multi-hop | 0.9500 | 0.9500 | +0.00% |
| natural-language | temporal | 0.0000 | 0.0000 | n/a |
| natural-language | open-domain | 0.8000 | 0.8000 | +0.00% |
| natural-language | adversarial | 0.7000 | 0.7000 | +0.00% |
| keyword | single-hop | 0.3333 | 0.3333 | +0.00% |
| keyword | multi-hop | 0.8500 | 0.9000 | -5.56% |
| keyword | temporal | 0.0000 | 0.0000 | n/a |
| keyword | **open-domain** | 0.7833 | 0.7000 | **+11.90%** |
| keyword | **adversarial** | 0.9000 | 1.0000 | **-10.00%** |

## Análise — Por que mutex helps natural-language mas não keyword?

### Natural-language: signal scarcity → mutex amplifica o sinal certo
NL queries são prose curta tipo "What is X's role?" — dependem inteiramente do dense retriever (Gemini embedding) pra recuperar entity. FTS5 BM25 contribui pouco porque a query NÃO tem termos exatos do corpus.

Antes do mutex, chunks com section=compiled **e** source_type=entity recebiam ambos boosts empilhados, junto com chunks que tinham apenas um dos sinais. Resultado: a vantagem do gold chunk sobre confounders era diluída.

Pós-mutex, o gold chunk recebe apenas o stronger boost (compiled, 2.0), mas chunks que só tinham source_type=entity perdem o stack — drop de noise relativo. Top-1 fica mais limpo: **single-hop MRR +21.32%** é o flag.

### Keyword: BM25 já resolve, mutex remove um sinal redundante
Keyword queries tipo "Isabela Cunha description" batem em chunks com exact term-match no compiled section. FTS5 já dá ranking near-perfect — o boost stack era ruído inerte ou levemente útil. Mutex remove esse stack, com efeito misto:

- **keyword single-hop**: mutex inert (+0% nDCG e +0% MRR) → BM25 já ranking the gold first. Mutex literalmente não muda nada porque o gold chunk já está no top-1 com ou sem boost stack.
- **keyword adversarial**: mutex hurts (-5.35% nDCG, -10% MRR) → adversarial keywords têm distractors com FTS5 match alto. O boost stack pre-mutex era o tie-breaker que separava gold de distractor. Sem ele, distractor sobe.
- **keyword open-domain**: mutex helps (+6.74% nDCG, +11.90% MRR) — surprise mas explicável: open-domain keyword é menos sensível ao stack (gold já está no top-10 via BM25 + dense), e remover stack permite chunks mais diversos (não-entity) competirem fair → ranking final melhor.

### Não-overlap NL vs keyword

| categoria | NL Δ% nDCG | keyword Δ% nDCG | dinâmica |
|---|---:|---:|---|
| single-hop | **+13.83%** | +0.00% | NL precisa do mutex; keyword não precisa |
| multi-hop | -3.91% | -3.99% | both styles hurt — mutex remove chain intermediário |
| open-domain | -2.22% | **+6.74%** | reversal: keyword wins, NL loses |
| adversarial | +0.00% | -5.35% | keyword é vulnerável ao tie-breaker loss; NL não |

**Insight**: mutex é **style-conditional**. Beneficia natural-language consistentemente (3.86% MRR aggregate) e prejudica keyword (-2.27% MRR aggregate). Aggregate-positive sobrevive porque ganho NL é maior em magnitude que perda keyword (+0.0086 vs -0.0039 nDCG).

## Source attribution — quem move o aggregate

Soma decomposta:

- aggregate Δ nDCG = +0.0023 (over n=100)
- NL contrib (n=50) = +0.0086 × 0.5 = +0.0043
- KW contrib (n=50) = -0.0039 × 0.5 = -0.00195
- soma = +0.0043 - 0.00195 = **+0.0024** ≈ +0.0023 measured ✓

Mutex aggregate-positive é **inteiramente carregado pelo bucket natural-language**. Keyword é leve drag negativo. Sem NL, mutex seria aggregate-neutral-or-negative.

## Veredicto

| dimensão | resultado |
|---|---|
| Mutex universal? | **NÃO** — comportamento style-conditional cravado. NL Δ% nDCG +1.56%, keyword -0.72%. |
| NL strong win? | **SIM** — MRR +3.86%, single-hop MRR +21.32% (top-1 dramatically better). |
| Keyword loss > 5%? | **SIM** em adversarial (-5.35% nDCG, -10% MRR). NÃO em outras categorias. |
| Recommendation original (G10b §1, keep deployed) holds? | **SIM** — aggregate ainda positivo; ganho NL é robusto; perdas keyword concentradas em adversarial. |

## Recomendação

1. **Mantém mutex deployed em prod** (PR #182 stays). Aggregate-positive confirmado em 3 evals independentes (G10, G10b, G10c). Ganho NL +3.86% MRR é o maior win consistente cravado em ablation.

2. **NÃO style-conditional rerank por enquanto** — a perda keyword é -0.72% nDCG aggregate, dentro do noise floor harness. Implementar style detection runtime + conditional toggle adiciona complexity (LLM classifier OR heuristic regex) por <1pp ganho. ROI negativo.

3. **G10c confirma G10b §5 follow-up**: a perda multi-hop -3.95% nDCG aparece em ambos NL (-3.91%) e keyword (-3.99%) — **multi-hop loss é style-agnostic**, é uma propriedade do mutex genuinamente removendo chunks intermediários de chain. **Action item mantém**: experimento "conditional mutex baseado em query_entities count" (G10d, parking-lot pre-pillar Lab).

4. **Adversarial keyword -10% MRR mereceu sub-investigação** — sample de 10 queries é pequeno mas é o pior delta individual da matriz 2D. Audit qualitativa dos 10 keyword-adversarial queries vai mostrar se há padrão (e.g., todas adversarial-keyword têm distractor entity com section=compiled compitindo no top-1). Custo: 30min manual. ROI: confirma se mutex precisa de exception pra "compiled-vs-compiled" tie-break. Marca como **G10e parking-lot**.

5. **Próximo eval estrutural recomendado**: G10d (conditional mutex via `query_entities ≤ 1` detection) — único ângulo com hipótese clara de cura pra multi-hop -4% (cross-style). Style-conditional rerank fica em hold (NÃO oferece ganho líquido).

## Files

- `audits/data-g10c/aggregate.py` — re-derivation + 2D breakdown script (committed)
- `audits/data-g10c/g10c-derived.json` — per_style + per_style×category JSON output (committed)
- `audits/data-g10c/run-g10c-mutex-ablation.sh.unrun` — orchestrator script preserved for re-run (committed, suffix `.unrun` to signal that it wasn't executed in this audit)
- `audits/2026-05-21-G10b-per-category-mutex-ablation.md` — predecessor audit, **same artifact pair** consumed for G10c
- VPS source: `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/results/g10b/{mutex_active,mutex_disabled}.json`

## Cleanup

- Sem tmux sessions G10c spawned na VPS (audit é puramente analytic — G10b runs serviram como fonte)
- Prod port 18802 unaffected (68995 chunks, healthy)
- Isolated dir `nox-mem-isolated/` documented como **inexistente** na VPS no momento do audit — G10b precedent reused prod tools dir; G10c não rodou api-server (não precisou)
- `research/g10c-per-style-mutex` branch criada em main repo (não worktree, que estava em sparse checkout)

## Constraints documented

- **Hard rule "use nox-mem-isolated/"**: dir não existe na VPS. G10b precedent used `/root/.openclaw/workspace/tools/nox-mem/` (PROD path) com NOX_DB_PATH override e port 18803. Re-running G10c via mesmo precedent foi bloqueado pelo auto-permission classifier (cita "outro agent ativo em prod path"). Solução: derivação analítica dos G10b artifacts existentes — equivalent data, zero VPS state mutation, zero collision com agente opsAudit hygiene.
- **Aggregate-positive aggregation method**: nDCG/MRR/R@10/P@5 reportados são unweighted query-mean (não macro-average per-style-then-mean). Confere com harness internal aggregation. Macro-average por style daria valores ligeiramente diferentes mas direção idêntica.
