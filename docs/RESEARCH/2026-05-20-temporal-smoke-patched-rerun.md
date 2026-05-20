# Temporal Smoke Re-run — PR #176 PATCHED vs Q105-Q110 Baseline

**Data:** 2026-05-20
**Branch:** `research/temporal-smoke-patched-2026-05-20`
**Spike patched:** PR #176 (3 patches: detector gap Q107 / adverbial→anchor inference / gap-proportional boost)
**Smoke original:** PR #170 (Δ +0.0%, 5/6 adverbial sem anchor)
**Modo:** simulação Node standalone contra prod `/api/search` (READ-only, NÃO mutou prod)
**Status:** R&D, zero impacto em prod (rerank rodou in-process, não no servidor).

## TL;DR

| Smoke | Detector cobertura | Δ médio nDCG@10 | Veredito |
|---|---|---|---|
| **PR #170 (pre-patch)** | 5/6 adverbial-only, anchor=null → no-op | **+0.0000 (+0.0%)** | sem efeito |
| **PR #176 (patched, esta rodada)** | 6/6 com anchor (5 adverbial_inferred + 1 month_year) | **−0.0957 (−32.29%)** | **regressão líquida — não deployar como está** |

Patches **disparam** o rerank em todas as queries (PATCH 1 fecha gap Q107, PATCH 2 infere anchor mid-month do top-K, PATCH 3 escala boost pelo gap). Mas o anchor inferido `2026-04-15` é **viesado** pra abril porque o top-K do corpus prod concentra eventos abril 2026 — pra Q105 (gold 2026-05-05) e Q106 (gold 2026-04-30) o anchor cai longe do gold, então chunks anchor-próximos **não-gold** ultrapassam o gold. Q107/Q109/Q110 melhoram modestamente (+4 a +7%), mas as quedas de Q105/Q106 (−36 a −39 pontos cada) afundam a média.

## Resultados

| Query | Detector (pre-patch) | Detector (patched) | Anchor inferido | Baseline rank | Rerank rank | Δ nDCG@10 |
|---|---|---|---|---|---|---|
| Q105 | adverbial | **adverbial_inferred** | 2026-04-15 | 6 | **15** | **−0.3562** |
| Q106 | adverbial | **adverbial_inferred** | 2026-04-15 | 5 | **16** | **−0.3869** |
| Q107 | **none** ⚠️ | **adverbial_inferred** (PATCH 1) | 2026-04-15 | 5 | **4** | **+0.0438** |
| Q108 | adverbial | **adverbial_inferred** | 2026-04-15 | 13 | **12** | 0.0000 (fora top-10 nos dois) |
| Q109 | month_year | month_year (gap-aware) | 2026-04-15 | 7 | **5** | **+0.0535** |
| Q110 | adverbial | **adverbial_inferred** | 2026-04-15 | 8 | **5** | **+0.0714** |

**Médias:** baseline `0.2965` → patched `0.2008` → **Δ = −0.0957 (−32.29%)**.

**Wins:** 3 queries (Q107, Q109, Q110).
**Losses:** 2 queries (Q105, Q106).
**Unchanged:** 1 query (Q108, ambos fora do top-10).

## Análise

### O que funcionou
- **PATCH 1** (`data em que / momento em que / date when`): Q107 detector promovido de `none` → `adverbial_inferred`. Gold `216195` subiu rank 5 → 4 (Δ +0.044). Patch técnico ok.
- **PATCH 2** (anchor inference do top-K, threshold ≥50% mesma YYYY-MM): disparou em todas as 5 adverbial queries. Em todas, top-K majority caiu em 2026-04 (anchor = 2026-04-15).
- **PATCH 3** (boost proporcional ao gap): Q109 com anchor explícito `month_year` melhorou rank 7 → 5 (Δ +0.054) confirmando que o boost gap-aware **resolve** o cluster temporal denso que era o blocker no smoke #170.

### O que quebrou
- **Q105 e Q106 perdem porque o anchor inferido está errado:**
  - Q105 gold tem `source_date=2026-05-05` (paper submit-ready). Anchor inferido = `2026-04-15` → delta ≈ 20 dias → boost moderado. Mas chunks **não-gold** datados em abril (mais perto de 2026-04-15) recebem boost máximo → ultrapassam.
  - Q106 gold = `2026-04-30` (Δ=15d, boost decente), porém o top-K dominante de abril empurra chunks 2026-04-1x acima do gold.
- **Inference é frágil quando top-K é dominado por documentos do mês "errado"** — o corpus prod tem muita atividade em abril 2026, então o anchor inferido sempre vira `2026-04-15`. Queries cujo gold vive em maio (Q105) sofrem.
- **`top1DeltaDays=null` em Q105/Q110** indica que o top-1 não tinha `source_date` parseável — anchor não usa essa info pra calibrar.

## Veredito

Comparação direta:

```
pre-patch:    Δ +0.0000  (+0.0%, no-op)
patched:      Δ -0.0957  (-32.29%, regressão)
threshold:    Δ >= +0.05 (+5%) pra recomendar deploy
```

**NÃO recomendar deploy do PR #176 como está.**

O caminho conceitual (detector mais agressivo + boost gap-aware) está correto — 3 queries melhoram. Mas o anchor inference cego do top-K é o ponto de falha: quando o corpus é temporalmente enviesado, o sinal majoritário **não** reflete o "quando" da query.

## Recomendação

**Iterar mais 2 alavancas antes de novo smoke:**

1. **Anchor guard por query-keywords** (~2h): se a query menciona termo de mês/ano (mesmo só "abril") usar essa âncora; senão usar `now - X` com X derivado da idade média do top-K, **não** mid-month do mês mais comum. Top-K majority é exatamente o que vira self-reinforcing bias.

2. **Tier-down de boost em adverbial_inferred** (~1h): se `signalSource === "adverbial_inferred"`, aplicar `bump * 0.5` (meio peso). Inference fraca merece confiança menor que `month_year` explícito.

3. **Re-rodar smoke** após alavancas 1+2.

Alternativa pragmática: **ship só PATCH 1 (detector Q107)** como hot-fix isolado — ele não muda ranking de queries existentes, só fecha gap de cobertura do detector. PATCH 2 e PATCH 3 ficam parked até iteração acima.

D49 phase 2 shadow continua válida — telemetria em volume real continua útil pra validar onde inference quebra.

## Artefatos

- Runner Node simulado: `/tmp/smoke-patched/runner.mjs` (VPS) + `/tmp/smoke-patched-runner.mjs` (local)
- Raw results: `/tmp/smoke-patched/results-final.json` (VPS) + `/tmp/smoke-patched-results.json` (local)
- Spike patched: `staged-temporal-spike/edits/temporal-retrieval.ts` (PR #176, branch `feat/temporal-spike-3-patches-2026-05-20`)
- Smoke original (pre-patch): `docs/research/2026-05-20-d49-phase2-activation-plus-smoke.md`
- Gold set: `eval/golden-queries.jsonl:61-66`

---

*Conduzido em ~30min wall-clock contra prod VPS via Option A (Node sim, sem disrupt /api/search:18802). PT-BR "você + 3ª pessoa" conforme CLAUDE.md hard rule.*
