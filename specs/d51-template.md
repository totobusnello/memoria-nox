# D51 Template — G10d Conditional Mutex (query_entities ≤ 1 gate)

> **Status:** TEMPLATE pré-aberto 2026-05-21. Decisão D51 vai ser tomada após G10d spec design (PR pending) + G10d ablation eval (post-spec).

---

## Contexto

D48 saga (G3 → G11) closed clean 2026-05-20 com Hard Mutex (PR #182) KEEP DEPLOYED. G10b/G10c per-category/per-style breakdowns revealed:

- WIN: single-hop (+8.22% nDCG), open-domain (+2.42%), natural-language (+1.56%)
- **REGRESSION (style-agnostic):** multi-hop -3.95% nDCG, -6.02% R@10
- KW × adversarial -5.35% (worst individual, n=10 small)

G10d hypothesis: **Conditional mutex active só se `query_entities ≤ 1`** preserva single-hop win e recovera multi-hop regression.

Pseudocode:
```typescript
function sourceTypeDelta(sourceType, section, queryEntityCount): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;
  const conditionalActive = queryEntityCount <= MUTEX_QUERY_ENTITY_THRESHOLD;  // default 1
  if (conditionalActive && section && SECTION_BOOST[section] !== undefined && !DISABLE_SECTION_BOOST) {
    return 0;  // mutex still applies
  }
  return (SOURCE_TYPE_BOOST[sourceType] ?? 1.0) - 1.0;
}
```

---

## Critérios de decisão D51

D51 vai DEPENDER de 2 fontes de evidência:

### 1. G10d ablation eval (g9.db, n=100)

| Categoria | Threshold pra GO | Threshold pra NO-GO |
|---|---|---|
| **multi-hop nDCG@10 Δ%** (recovery) | **≥ -1%** (currently -3.95%) | < -3% |
| **multi-hop R@10 Δ%** (recovery) | **≥ -2%** (currently -6.02%) | < -4% |
| **single-hop nDCG@10 Δ%** (preserve) | **≥ +6%** (currently +8.22%) | < +5% |
| **aggregate nDCG@10 Δ%** | **≥ +0.5%** (current +0.43-0.79%) | < 0% |
| **adversarial nDCG@10 Δ%** | ≥ -3% (mutex on adversarial already -2.95%) | < -5% |

### 2. Implementation cost vs benefit

| Cost | Benefit |
|---|---|
| Entity-count helper (~50 LOC) + 3-5 tests | Multi-hop +3-5pp recovery em 20% das queries |
| ~10ms latency add (KG lookup) | Net retrieval value goes from +0.0117 (G10b) → +0.025 (target) |

---

## Decisão proposta (preencher após dados)

| Field | Value |
|---|---|
| Data | YYYY-MM-DD |
| G10d multi-hop Δ% nDCG | TBD |
| G10d multi-hop Δ% R@10 | TBD |
| G10d single-hop Δ% nDCG | TBD |
| G10d aggregate Δ% nDCG | TBD |
| Entity count threshold | 1 (default) / 2 / 3 (grid search) |
| **Decisão** | **ACTIVE / GRID-SEARCH / OPT-IN / OFF** |
| Rationale | TBD |
| Action items | TBD |

---

## Implementação se ACTIVE

1. Implement `src/lib/query-entity-count.ts` — KG entity lookup
2. Modify `src/search.ts:sourceTypeDelta()` — add queryEntityCount parameter
3. Add 5+ unit tests covering edge cases
4. Deploy via Wave (scp → build → restart)
5. Smoke test in prod (verify backward-compat com Hard Mutex)
6. Update paper §5.5 com G10d numbers + decision
7. Memory `[[g10d-conditional-mutex-active]]`

## Implementação se GRID-SEARCH

1. Run G10d-grid: threshold 1/2/3/4 ablation
2. Pick threshold com best multi-hop recovery × single-hop preservation curve
3. Re-deliberar D51 com grid winner

## Implementação se OPT-IN

1. Keep code com flag `NOX_ENABLE_CONDITIONAL_MUTEX=1`
2. Document caso de uso (queries multi-entity heavy)
3. No paper update

## Implementação se OFF

1. Keep current Hard Mutex (D48 closure)
2. Document multi-hop regression como known trade-off
3. Memory `[[g10d-conditional-mutex-rejected]]`

---

## Rollback paths (defesa em camadas)

1. `NOX_DISABLE_CONDITIONAL_MUTEX=1` reverts to Hard Mutex (current G10 deployed)
2. `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` reverts to no-mutex (G10b A8)
3. `NOX_DISABLE_SOURCE_TYPE_BOOST=1` reverts to A10 (no source_type)

Triple rollback layer mantém composability + safety.

---

## Cross-links

- D48 — saga complete (DECISIONS.md not explicit, audits + paper §5.5)
- D49/D50 — temporal path (parallel decision track, independent)
- G10b — `audits/2026-05-21-G10b-per-category-mutex-ablation.md`
- G10c — `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
- G10d spec — `specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md` (pending agent PR)
- Memory `[[g10b-per-category-mutex-2026-05-21]]`, `[[g10c-per-style-2026-05-21]]`
