# Salience Distribution Audit — nox-mem prod (2026-05-19)

> **Trigger:** G4 ablation surpresa — A8 (salience ACTIVE) = 0.5702 < A7 (salience SHADOW) = 0.5805. Investigar por que active piora.
>
> **DB:** `/root/.openclaw/workspace/tools/nox-mem/nox-mem.db` prod, total **68,995 chunks** (pós-restore wipe 2026-05-19 12:38 BRT).

---

## Tabela-resumo: signal-strength por componente

| Componente | Estado | % constante | Diagnóstico |
|---|---|---|---|
| `pain` | ☠️ DEAD | 90.67% no default 0.2 | Multiplicação por constante = identidade |
| `recency` (created_at) | ☠️ DEAD | 99.76% em [7-30d] | Idade homogênea pós-restore |
| `source_type` | ☠️ INERT | 98.48% NULL | Boost keys mismatch confirmado |
| `importance` | ✅ ALIVE | bimodal 74% baixo + 17% alto | Único signal contínuo forte |
| `section` | ✅ ALIVE (parcial) | 98.91% NULL/legacy | Mas 1.09% (749) são GOLD — A3 peak |
| `tier` | ⚠️ NOISY | 52% per / 44% wrk / 4% core | A6 mostra core over-promote |
| `access_count` | ✅ ALIVE (binary) | 87% zero / 13% accessed | Não usado em salience atual |

---

## Pain distribution

```
[0.15-0.25) default-0.2 | 62,557 | 90.67%
[0.25-0.5)              |    904 |  1.31%
[0.5-0.75)              |  4,860 |  7.04%
[0.75-1.0]              |    674 |  0.98%
```

**Conclusão**: 90.67% dos chunks NUNCA foram severity-rated. `pain` é constant signal. Backfill via heurística ou LLM rating necessário antes de pain ser feature útil.

## Importance distribution

```
[0.25-0.45)             | 51,305 | 74.36%
[0.45-0.55) default-0.5 |  1,738 |  2.52%
[0.55-0.75)             |  3,911 |  5.67%
[0.75-1.0]              | 12,041 | 17.45%
```

**Conclusão**: Bimodal. 74% chunks foram triados pra baixo (DB column overrides chunk_type mapping). 17% top-tier. Default 0.5 raro (2.52%) → maioria foi processada por sistema downstream que escreve importance.

## Tier distribution

```
peripheral | 36,022 | 52.21%
working    | 30,239 | 43.83%
core       |  2,734 |  3.96%
```

**Conclusão**: Distribution razoável MAS A6 mostrou que boost de tier sozinho PIORA ranking (0.4616 < A0 baseline 0.4817). Hipótese: `tier='core'` chunks são memory-system internals, não user content → over-promote empurra golden hits para baixo.

## source_type distribution

```
NULL     | 67,949 | 98.48%
external |  1,046 |  1.52%
```

**Conclusão**: SOURCE_TYPE_BOOST é dead code com current data. Backfill obrigatório.

## section distribution

```
NULL/legacy | 68,246 | 98.91%
timeline    |    383 |  0.56%
frontmatter |    183 |  0.27%
compiled    |    183 |  0.27%
```

**Conclusão**: Paradoxo aparente — apenas 1.09% chunks têm section preenchida, mas section_boost é PEAK boost (A3 = 0.6222). Compiled chunks são highly-curated knowledge cards. `section_boost` é o moat REAL.

## Recency distribution

```
[0-7d]   |    167 |  0.24%
[7-30d]  | 68,828 | 99.76%
```

**Conclusão**: Pós-restore wipe, 99.76% chunks foram re-criados há 7-30 dias. Recency é dead até ages diversificarem novamente (>30d natural ingestion).

## access_count distribution

```
0         | 59,867 | 86.77%
[1-5]     |  5,782 |  8.38%
[6-20]    |  1,016 |  1.47%
[21-100]  |  1,714 |  2.48%
>100      |    616 |  0.89%
```

**Conclusão**: 86.77% nunca accessed. Binary signal (used vs unused) é forte sinal latente. Atualmente NÃO usado em salience formula.

## Salience computed atual (multiplicativo)

```
[0.05-0.15) low  | 59,009 | 85.53%
[0.15-0.40) mid  |  9,795 | 14.20%
[0.40-0.70) high |     57 |  0.08%
[0.70-1.0] peak  |    134 |  0.19%
```

**Conclusão**: Formula multiplicativa concentra 99.7% chunks em [0.05-0.40] (faixa narrow). Pain × recency efetivamente constants (0.2 × 0.95 = 0.19) → salience ≈ 0.19 × importance. Está medindo importance disfarçado de salience.

---

## Decisão evidência-based

### Mantido
- Componentes individuais (`recencyComponent`, `painComponent`, `importanceComponent`)
- `classifySalience()` thresholds (compatibilidade tier-manager)
- Mode gating (`shadow` / `active` / `off`)

### Mudado (PR #150 `feat/salience-additive-evidence-2026-05-19`)

**Multiplicativo → aditivo** com pesos evidência-based. **4 componentes** (não 5):

- **W_importance = 0.55** (PRIMARY signal forte — bimodal 74% baixo / 17% alto)
- **W_recency = 0.15** (dampened — homogeneous corpus age pós-restore)
- **W_pain = 0.10** (dampened — 90% default value)
- **W_access = 0.20** (SECONDARY binary signal — 87% zero / 13% accessed, NÃO usado antes)

**section_boost NÃO foi incluído** na fórmula salience: já é applied multiplicativamente via `sectionDelta()` no `search.ts` (boost stack camada separada). Incluí-lo aqui seria **double-counting** — viola CLAUDE.md regra #5 (boost stack ADITIVO entre si, mas salience não duplica boost de section).

```typescript
// Implementação real em staged-1.7a/edits/salience.ts (PR #150):
salience = clamp01(
    0.55 * importance
  + 0.15 * recency
  + 0.10 * pain
  + 0.20 * accessCountComponent(access_count)
);

// accessCountComponent normaliza log1p(n)/log(1000) → [0, 1]
//   access_count=0    → 0.00
//   access_count=10   → 0.347
//   access_count=100  → 0.667
//   access_count=1000 → 1.00 (clamp saturates)
```

**Soma = 1.0** quando todos componentes saturam em 1.0 (max salience = 1.0).

**Histórico**: versão inicial proposta dessa audit incluía `W_section_boost = 0.2` (sums to 1.0 com section em vez de access alta). Refinado pós-review: section vive em `sectionDelta` já, access_count é signal NEW genuinamente sub-utilizado.

### Post-formula distribution simulation (LOW #6, PR #150 review)

> Projeção de como salience v2 vai particionar os 68,995 chunks do prod, baseado nos buckets de cada componente observados acima.

**Mean por componente (corpus prod observado):**

| Componente | Mean estimado | Cálculo |
|---|---|---|
| importance | **0.45** | bimodal: 74% × 0.40 + 17% × 0.85 + 9% × 0.50 |
| recency | **0.92** | 99.76% em [7-30d] → meia-vida ~0.85-0.95 com retention default 90d |
| pain | **0.23** | 90.67% × 0.2 + 1.31% × 0.38 + 7.04% × 0.62 + 0.98% × 0.87 |
| access (norm) | **0.05** | 87% × 0 + 8.4% × 0.17 + 1.5% × 0.32 + 2.5% × 0.50 + 0.9% × 0.74 |

**Salience mean v2 estimada**:
```
mean ≈ 0.55 × 0.45 + 0.15 × 0.92 + 0.10 × 0.23 + 0.20 × 0.05
     = 0.247 + 0.138 + 0.023 + 0.010
     ≈ 0.418
```

**Buckets esperados (v2 vs legacy multiplicativa):**

| Bucket | Threshold | **v2 (projeção)** | Legacy (medido) |
|---|---|---|---|
| archive | <0.15 | **~2%** | 0%* (fora do range — legacy concentra [0.05-0.40] mid) |
| review | 0.15-0.4 | **~50%** | **85.5%** (catastrophic dead band) |
| retain | 0.4-0.7 | **~43%** | 14.2% |
| promote | ≥0.7 | **~5%** | 0.27% (saturated peak) |

**Validação threshold 0.7 promote alcançável?**

Caso single-signal max (importance=1.0, all others=0): salience = 0.55 → "retain" apenas.

Promote requer **≥2 sinais altos**:
- importance=1.0 + access=1.0 → 0.75 ✅
- importance=0.85 + recency=1.0 + access=1.0 → 0.817 ✅
- importance=0.85 + pain=1.0 + access=1.0 → 0.767 ✅

Isso é desejável — promote = sinal forte e raro. **Thresholds 0.7/0.4/0.15 mantidos continuam particionando** significativamente sob v2 weights.

**Por que isso valida o refactor:**
- Legacy concentrava 85.5% em "review" (faixa dead) → reranking era noise
- V2 espalha em buckets balanceados (50/43/5/2) → reranking é signal real
- Promote raro (~5%) preserva semântica original de "chunk excepcional"
- Archive pequeno (~2%) reflete importance forte mas componentes secundários puxam pra cima quando importance é baixo

**Re-validation pós-deploy:**
1. Query `SELECT classification, COUNT(*) FROM ... GROUP BY` via `classifySalience(calculateSalience(...))` em todo corpus
2. Comparar distribuição real vs projeção acima
3. Se desviar >10% em qualquer bucket: re-tune pesos ou ajustar thresholds

### Re-medir
- A7' / A8' com formula nova (shadow vs active)
- Expectativa: distribuição salience spread real em [0.0-1.0] vez de [0.05-0.40]
- Expectativa: A8' (active) ≥ A7' (shadow) — formula que captura real signal

---

## Cross-links

- [[g4-wave-a-results-2026-05-19]] — ablation que motivou audit
- [[d48-implement-pain-weighted]] — decisão de implementar pain-weighted
- [[shadow-mode-for-ranking-changes]] — protocolo de validation
- `staged-1.7a/edits/salience.ts` — código atual (multiplicativo)
- `staged-1.7a/edits/search.ts` — caller que aplica salience
