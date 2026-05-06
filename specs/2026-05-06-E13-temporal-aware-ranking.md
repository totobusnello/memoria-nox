# E13 — Temporal-aware Ranking

> Inverte `section_boost` pra section=`timeline` quando query é temporal (`quando`, `que dia`, `primeira/última`, `deployado`, etc). Hoje timeline é demotada (×0.8) — exatamente onde a info temporal mora — e queries temporais sofrem nDCG ~0.466 vs concept 0.656. Quick win: detector regex + condicional simples no pipeline existente.

**Status:** Design spec
**Data:** 2026-05-06
**ID:** E13 (novo, additive ao roadmap)
**Vision §:** §11 Wave 1 (extension de section_boost)
**Esforço estimado:** 30min spec + 1h impl + 30min tests + 7d shadow + 0.3h activate
**Dependências:**
- ✅ G02 section_boost active (pipeline já consulta `section`)
- ✅ R01b cured queries (2 temporal queries Q70/Q71 ambas em section=timeline)
**Bloqueia:** —
**Cross-ref:** `specs/2026-05-06-E05b-reason-ranking-boost.md` (mesmo padrão shadow); regra crítica #5 (aditivo)

---

## Problema

R01c Run #9 reportou nDCG@10 temporal = 0.233. **Análise revelou**:

| Query | Gold ID | Position | nDCG | Issue |
|---|---|---|---|---|
| Q70 "quando o salience foi ativado" | 117852 | **3rd** | 0.5 | gold em section=timeline (×0.8 demote) |
| Q71 "qual a primeira lição do incident reindex 2026-04-25" | 117767 | **4th** | 0.431 | gold em section=timeline (×0.8 demote) |
| Q87 "quando o E05 foi deployado" | **[]** | — | 0.0 | **gold vazio (não curado)** |
| Q88 "quando subiu schema v12" | **[]** | — | 0.0 | **gold vazio (não curado)** |

**Achado #1:** 2/4 queries temporais têm `expected_chunk_ids=[]`. **27% das queries cured** (16/60) têm gold vazio — média categoria está enviesada pra baixo.
- Real temporal nDCG (cured-only): `(0.5 + 0.431) / 2 = 0.466`, não 0.233.

**Achado #2:** 100% dos gold chunks temporais estão em `section='timeline'`. Distribution geral:

| Category | Gold em timeline | Outras sections |
|---|---|---|
| **temporal** | 2/2 cured (100%) | 0 |
| concept | 1/29 (3%) | 28 |
| decision | 0/8 | 5 (compiled/frontmatter) + 3 NULL |
| procedure | 1/17 (6%) | 16 |

**Conclusão:** queries temporais são desproporcionalmente penalizadas pelo `SECTION_BOOST.timeline = 0.8`. O design "compiled é truth, timeline é history" é correto pra queries factuais ("o que é nox-mem?") mas inverte pra queries temporais ("quando nox-mem foi ativado?"). Pra essas, **timeline IS truth**.

---

## Solução: temporal-aware section boost

### Detector de query temporal

```typescript
// src/lib/temporal-detector.ts
const TEMPORAL_PATTERNS = [
  /\b(quando|que\s+dia|que\s+data|qual\s+(?:data|dia)|em\s+que\s+(?:dia|data))\b/iu,
  /\b(primeir[ao]|últim[ao]|inicial)\b/iu,
  /\b(deploy(?:ado|ed|amento)|ativad[ao]|subiu|lançad[ao]|started|aconteceu|inici(?:ou|ado))\b/iu,
  /\b\d{4}-\d{2}-\d{2}\b/, // ISO date in query
];

export function isTemporalQuery(query: string): boolean {
  if (!query || query.length < 3) return false;
  return TEMPORAL_PATTERNS.some((re) => re.test(query));
}
```

### Section boost override

Atual:
```typescript
const SECTION_BOOST = {
  compiled: 2.0,
  frontmatter: 1.5,
  timeline: 0.8,  // demote
  // null/legacy = 1.0
};
```

Proposto (aplicado SOMENTE quando `isTemporalQuery(query)`):
```typescript
const SECTION_BOOST_TEMPORAL = {
  compiled: 1.0,    // neutro (truth atual ainda relevante)
  frontmatter: 0.9, // levemente demote (estrutural)
  timeline: 1.4,    // **promove** — é onde a info temporal vive
  // null/legacy = 1.0
};
```

**Não é multiplicador adicional sobre o existente** (regra #5 — não empilhar). É uma tabela alternativa que substitui o lookup quando `isTemporal=true`.

### Pipeline integration

`src/search.ts` `applySectionBoost()` ganha parâmetro `isTemporal`:

```typescript
function applySectionBoost(
  score: number,
  section: string | null,
  sectionBoost: number | null,
  isTemporal: boolean
): { finalScore: number; shadowScore: number } {
  let sb = typeof sectionBoost === "number" ? sectionBoost : 1.0;
  // E13 (2026-05-06): temporal queries invertem timeline demotion
  if (isTemporal && section) {
    const override = SECTION_BOOST_TEMPORAL[section as keyof typeof SECTION_BOOST_TEMPORAL];
    if (override !== undefined) sb = override;
  }
  // ... rest unchanged
}
```

`searchHybrid()`, `search()`, `searchSemantic()` calculam `isTemporal` 1× e propagam:

```typescript
const isTemporal = isTemporalQuery(query);
// passa pra applySectionBoost em ambos FTS e semantic loops
```

---

## Modes (env var)

| `NOX_TEMPORAL_BOOST_MODE` | Comportamento |
|---|---|
| `off` (default) | sem mudança — retorna comportamento atual |
| `shadow` | computa override + log delta, **não muta finalScore** |
| `active` | aplica override no ranking |

Mesmo padrão de E05b/E04a/section_boost original. Failsafe: parse error → `off`.

---

## Schema migration v14

`search_telemetry` ganha 2 colunas (additive):

```sql
ALTER TABLE search_telemetry ADD COLUMN was_temporal_query INTEGER DEFAULT 0;
ALTER TABLE search_telemetry ADD COLUMN temporal_boost_mode TEXT DEFAULT 'off';
```

Permite eval comparativo: avg nDCG por bucket `was_temporal_query=0/1` × mode.

---

## Tests (`__tests__/temporal-detector.test.ts`)

10 cases:
1. `isTemporalQuery("quando o salience foi ativado")` → true
2. `isTemporalQuery("o que é nox-mem")` → false
3. `isTemporalQuery("primeira lição do incident")` → true
4. `isTemporalQuery("deployment automatizado")` → false (contém "deploy" mas só radical, sem `-ado/-ed/-amento` modifier)
5. `isTemporalQuery("query com 2026-04-25")` → true (ISO date)
6. `isTemporalQuery("")` → false
7. `isTemporalQuery("queue?")` → false (3 chars min, mas "queue" não bate)
8. `isTemporalQuery("Quando subiu schema v12?")` → true (case-insensitive)
9. `isTemporalQuery("relação entre A e B")` → false
10. `isTemporalQuery("ativado")` → true (single token modifier)

Adicional: integração teste search → seleciona section=timeline em query temporal vs neutra (com env active).

---

## Activate gate (após 7d shadow)

| Critério | Threshold |
|---|---|
| Δ nDCG@10 temporal (cured-only Q70+Q71) | ≥ +0.10 (alvo: 0.466 → 0.566) |
| Δ nDCG@10 não-temporal | ≥ -0.005 (no regressão) |
| % queries detectadas como temporal | 5%-25% (sanity range) |
| 0 search timeouts | hard |

**Pass:** flip `NOX_TEMPORAL_BOOST_MODE=active`, restart, R01c re-baseline.

**Catastrophic** (qualquer strong cat -2pp+): rollback + investigar regex (provavelmente `deploy` matching demais).

---

## Quick win paralelo: curar 16 gold-vazios

Independente do shadow E13, **golden corpus tem 27% queries com gold vazio** — métricas globais enviesadas:

| Category | Total | Empty | % |
|---|---|---|---|
| concept | 15 | 3 | 20% |
| procedure | 13 | 4 | 31% |
| entity | 11 | 4 | 36% |
| temporal | 4 | 2 | 50% |
| (others) | 17 | 4 | 24% |

**Recomendação:** Toto cura 16 queries em batches de 4 durante o shadow window 7d. Cada cura ~30min (search manual + select gold IDs). Total ~8h cognitive floor spread Mai 7-13.

Bonus: re-rodar R01c pós-cura → métricas honestas (esperado nDCG global +5pp+ sem qualquer mudança de código).

---

## Risk register

| # | Risco | Mit. |
|---|---|---|
| 1 | Regex temporal pega falsos positivos (ex: "deploy" em query não-temporal) | shadow 7d telemetria + ajuste padrão |
| 2 | Promove timeline em query factual → degrada concept/procedure | gate hard regression -0.5pp não-temporal |
| 3 | n=2 cured temporal queries — eval underpowered | mitigação direta: curar Q87/Q88 antes do gate (~1h Toto) |
| 4 | section=NULL chunks (legacy) ficam neutros — pode esconder ganho | aceitar; rerun com data backfill futuro |

---

## Rollout

| # | Step | Esforço | Owner |
|---|---|---|---|
| 1 | Spec review (este doc) | 5min | Toto |
| 2 | Curar Q87 + Q88 gold (Toto manual) | ~1h | Toto |
| 3 | Impl `temporal-detector.ts` + tests | 1h | Claude |
| 4 | Plug em `search.ts` (3 callsites) | 30min | Claude |
| 5 | Schema migration v14 | 15min | Claude |
| 6 | Deploy shadow VPS | 10min | Claude |
| 7 | Wait 7d (~2026-05-13 = mesmo gate de E05b) | passive | — |
| 8 | R01c shadow run + análise + decision | 30min | Claude+Toto |

**Total ativo:** ~3h (1h Toto cura + 2h impl). Compatível com calendar window E05b.

---

## Definition of Done

- [ ] Spec aprovado
- [ ] Q87+Q88 gold curados (Toto)
- [ ] `temporal-detector.ts` 10/10 tests
- [ ] Schema v14 aplicado VPS
- [ ] Shadow rodando ≥7d com ≥100 queries logged
- [ ] R01c shadow comparison delta por categoria
- [ ] Activate gate avaliado em 2026-05-13
- [ ] Decisão registrada `docs/DECISIONS.md`
- [ ] ROADMAP linha E13 ✅ DONE ou ⏸ KEPT-SHADOW
