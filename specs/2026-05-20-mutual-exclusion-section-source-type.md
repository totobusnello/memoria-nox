# Design Spec: Mutual Exclusion `sectionDelta` ↔ `sourceTypeDelta`

**Status:** DRAFT  
**Data:** 2026-05-20  
**Autores:** Spec baseado nos resultados do G8 (PR #177)  
**Cross-links:** PR #154 (SOURCE_TYPE_BOOST wiring) · PR #177 (G8 ablation) · `docs/HANDOFF.md#night-2026-05-20`  
**Branch spec:** `specs/mutual-exclusion-section-source-2026-05-20`

---

## 1. Problema

### 1.1 Achado empírico (G8, 2026-05-20)

O G8 rodou com `entity-eval-v2.db` re-ingerido com `source_type = entity` consistente com prod pós-backfill (PR #151). Resultados:

| Config | nDCG@10 | Δ vs A8 |
|---|---|---|
| A0 — sem boosts | 0.4816 | — |
| A5 — `source_type` only | 0.4944 | — |
| **A8 — canonical full stack** | **0.5798** | baseline |
| A10 — full minus `source_type` | **0.5845** | **+0.81%** |

Veredicto: **A8 < A10 em −0.81%**. Com `source_type_boost` ativo no stack completo, o desempenho piora. Sem ele, melhora.

### 1.2 Causa raiz

Entity chunks (compiled/frontmatter/timeline) recebem dois boosts simultâneos:

1. **`sectionDelta`** via `SECTION_BOOST[section]`: `compiled=2.0`, `frontmatter=1.5`, `timeline=0.8`
2. **`sourceTypeDelta`** via `SOURCE_TYPE_BOOST["entity"] = 2.0`

O padrão aditivo (`boostSum += sourceTypeDelta + sectionDelta`) faz com que um chunk `compiled` de entidade some:

```
boostSum += (2.0 - 1.0)  // sourceTypeDelta → +1.0
boostSum += (2.0 - 1.0)  // sectionDelta    → +1.0
// total boostSum contribution = +2.0 para esses chunks
```

Chunks sem `section` mas com `source_type=entity` somam apenas +1.0. Isso cria uma **disparidade artificial** onde os próprios entity chunks mais confiáveis (compiled) ficam sobre-promovidos em relação a todo o resto — inclusive outros chunks relevantes sem `section` — matando diversidade no top-K.

### 1.3 Impacto por categoria (G8)

| Categoria | A8 vs A10 |
|---|---|
| open-domain | **−3.5 pp** (regressão) |
| multi-hop | +1.4 pp (ganho) |
| entity-lookup | ~0 (neutro) |

Open-domain é o volume maior da base; a regressão é a métrica que importa.

---

## 2. Análise das 4 Opções

### Comparativo geral

| Critério | Option 1 (Hard mutex) | Option 2 (Soft attenuation) | Option 3 (Trim values) | Option 4 (Section cede) |
|---|---|---|---|---|
| Resolve o double-boost? | Sim, totalmente | Parcialmente | Parcialmente | Parcialmente |
| Complexidade de implementação | Baixa (4 linhas) | Média (1 parâmetro extra + fator) | Nenhuma (só constantes) | Média |
| Reversibilidade | Total (env flag) | Parcial (env flag + fator) | Parcial (constantes versão) | Parcial |
| Risco open-domain regress | Baixo (mutex claro) | Médio (fator arbitrário) | Médio (sem garantia) | Alto (reverte sinal mais confiável) |
| Explicabilidade | Alta | Média | Alta | Baixa |
| Alinhamento com CLAUDE.md regra #5 | Total (sem stack multiplicativo) | Parcial | Total | Parcial |
| Ablation simples? | Sim (A11 = A8 + mutex) | Não (exige grid search) | Sim | Não |

### Option 1 — Hard Mutex (chunk-level)

```typescript
function sourceTypeDelta(
  sourceType: string | null | undefined,
  section: string | null | undefined,
): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;
  // MUTEX: se chunk já tem section_boost ativo, source_type não contribui
  if (section && SECTION_BOOST[section] !== undefined && !DISABLE_SECTION_BOOST) return 0;
  const f = SOURCE_TYPE_BOOST[sourceType] ?? 1.0;
  return f - 1.0;
}
```

**Lógica:** `section` é um sinal mais granular e confiável que `source_type`. Se sabemos a seção (compiled/frontmatter/timeline), o tipo do arquivo (entity) já está implícito. Ceder a `sectionDelta` a prioridade elimina completamente o double-boost.

**Limitação:** chunks de `source_type=lesson` sem `section` (chunks de arquivos .md genéricos de lições) perdem o boost `lesson=1.8` quando tiverem `section` preenchido — mas isso é raro: apenas entity files têm `section` preenchido no schema V10. Lesson files não têm `section`.

### Option 2 — Soft Attenuation

```typescript
function sourceTypeDelta(
  sourceType: string | null | undefined,
  section: string | null | undefined,
): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;
  const f = SOURCE_TYPE_BOOST[sourceType] ?? 1.0;
  const sectionActive =
    section && SECTION_BOOST[section] !== undefined && !DISABLE_SECTION_BOOST;
  const attenuation = sectionActive ? 0.3 : 1.0;
  return (f - 1.0) * attenuation;
}
```

**Lógica:** mantém o sinal de `source_type` mas o atenua quando `section` está ativo.

**Problema:** o fator `0.3` é arbitrário. Exige grid search (G11+) para calibrar. Sem ablation empírica, pode ser pior que o mutex ou que o trim simples. Adiciona um parâmetro de tuning sem base nos dados atuais.

### Option 3 — Trim Values

Reduzir os valores que causam conflito:

```typescript
const SOURCE_TYPE_BOOST: Record<string, number> = {
  entity: 1.3,  // era 2.0 — evita empilhamento com compiled=2.0
  lesson: 1.2,  // era 1.8
  // ... rest unchanged
};
```

**Lógica:** se os valores absolutos são menores, o double-boost é menos severo.

**Problema:** não resolve o problema estruturalmente. Com `entity=1.3` e `compiled=2.0`, o boostSum ainda é `+0.3 + +1.0 = +1.3` para entity-compiled chunks vs `+1.0` para compiled-sem-entity. A disparidade persiste, só menor. Requer nova ablation para calibrar os thresholds certos, sem garantia de convergência. É uma heurística, não um fix.

### Option 4 — Section Cede

Se `source_type` for "alto" (entity/lesson), `sectionDelta` recua:

```typescript
function sectionDelta(section, sectionBoostCol, sourceType): number {
  const sourceIsHighBoost =
    sourceType && SOURCE_TYPE_BOOST[sourceType] !== undefined &&
    SOURCE_TYPE_BOOST[sourceType]! > 1.0 && !DISABLE_SOURCE_TYPE_BOOST;
  if (sourceIsHighBoost) return 0;
  // ... resto normal
}
```

**Problema:** `section` é o sinal mais confiável e granular do schema V10. Ceder `sectionDelta` para um sinal de menor granularidade (`source_type`) é semanticamente errado. `compiled` de um entity file é o ground-truth mais curado do corpus; abrir mão desse boost é contra-intuitivo. Descartado.

---

## 3. Recomendação

**Option 1 — Hard Mutex** é a escolha certa.

**Rationale:**

1. **Resolve o problema estruturalmente.** O double-boost é completamente eliminado, não atenuado ou disfarçado.

2. **`section` é sinal de maior granularidade.** O schema V10 adiciona `section` precisamente para sub-classificar chunks dentro de entity files. Se `section` está preenchido, sabemos que o chunk é `compiled`, `frontmatter` ou `timeline` — informação mais rica que saber apenas que é `source_type=entity`. O sinal mais granular ganha.

3. **Zero risco de regressão em non-entity chunks.** Na prática, apenas entity files (749 chunks = 1.1% do corpus) têm `section` preenchido. Os 98.9% restantes continuam recebendo `sourceTypeDelta` normalmente — inclusive `lesson=1.8`, `skill=1.5`, etc. Open-domain não é afetado.

4. **Ablation simples.** G10 pode comparar diretamente A8 (canonical) vs A11 (A8 + mutex) usando o mesmo `entity-eval-v2.db`. Um único ponto de comparação.

5. **Explicabilidade máxima.** "Se sabemos a seção, o tipo de arquivo é redundante" é uma regra que qualquer revisor entende imediatamente.

6. **Alinha com CLAUDE.md regra #5 (sem stacking multiplicativo).** O mutex é o equivalente lógico de "não empilhe boosts sobre o mesmo sinal".

---

## 4. Implementation Plan

### Step 1 — Modificar assinatura de `sourceTypeDelta` em `search.ts`

Adicionar o parâmetro `section` e a guarda de mutex:

```typescript
function sourceTypeDelta(
  sourceType: string | null | undefined,
  section: string | null | undefined,  // ← novo parâmetro
): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;
  // MUTEX: section é sinal mais granular — se ativo, source_type é redundante
  if (section && SECTION_BOOST[section] !== undefined && !DISABLE_SECTION_BOOST) return 0;
  const f = SOURCE_TYPE_BOOST[sourceType] ?? 1.0;
  return f - 1.0;
}
```

### Step 2 — Atualizar call sites em `search.ts`

Dois call sites a atualizar (FTS path + semantic path):

```typescript
// FTS path (função search()):
boostSum += sourceTypeDelta(row.source_type, row.section);  // era: sourceTypeDelta(row.source_type)

// Semantic path (função searchSemantic()):
boostSum += sourceTypeDelta(boost.source_type, boost.section);  // era: sourceTypeDelta(boost.source_type)
```

### Step 3 — Adicionar env flag de override

Para rollback granular sem alterar código:

```typescript
const MUTEX_SECTION_SOURCE_TYPE =
  process.env.NOX_MUTEX_SECTION_SOURCE_TYPE !== "0";
// default: ON (mutex ativo)
// rollback: NOX_MUTEX_SECTION_SOURCE_TYPE=0 → comportamento pré-mutex
```

Modificar a guarda:

```typescript
if (
  MUTEX_SECTION_SOURCE_TYPE &&
  section && SECTION_BOOST[section] !== undefined && !DISABLE_SECTION_BOOST
) return 0;
```

### Step 4 — Atualizar testes em `search-boost-stack.test.ts`

Ver seção 5 (Test Cases). Adicionar grupo `MUTEX` ao test file existente.

### Step 5 — Documentar em `CHANGELOG.md` e cross-link

Entry em `CHANGELOG.md`:
```
## [Unreleased]
### Changed
- search: hard mutex sectionDelta ↔ sourceTypeDelta (G8 finding, -0.81% double-boost)
  chunks com section preenchido não acumulam sourceTypeDelta (NOX_MUTEX_SECTION_SOURCE_TYPE=0 para rollback)
```

---

## 5. Test Cases

### Matrix de combos relevantes

| Chunk | `source_type` | `section` | `sourceTypeDelta` esperado | `sectionDelta` esperado | Descrição |
|---|---|---|---|---|---|
| A | `entity` | `compiled` | **0.0 (mutex)** | +1.0 | entity file, truth section |
| B | `entity` | `frontmatter` | **0.0 (mutex)** | +0.5 | entity file, YAML metadata |
| C | `entity` | `timeline` | **0.0 (mutex)** | −0.2 | entity file, event log |
| D | `entity` | `null` | **+1.0** | 0.0 | entity sem section (edge case raro) |
| E | `lesson` | `null` | +0.8 | 0.0 | lesson file normal |
| F | `lesson` | `compiled` | **0.0 (mutex)** | +1.0 | improvável na prática, mas definido |
| G | `note` | `null` | 0.0 (factor=1.0 → delta=0) | 0.0 | baseline, sem boost |
| H | `ocr-cache` | `null` | −0.3 | 0.0 | penalidade ocr-cache |
| I | `external` | `null` | −0.2 | 0.0 | penalidade external |
| J | `null` | `compiled` | 0.0 | +1.0 | source_type ausente, section presente |
| K | `null` | `null` | 0.0 | 0.0 | sem boost algum |
| L | `entity` | `compiled` | 0.0 (mutex) | +1.0 | **total boostSum entity-compiled = +1.0 (era +2.0)** |

### Casos de boundary (flags de disable)

| Cenário | Flags | Resultado esperado |
|---|---|---|
| Mutex ON, section-boost OFF | `NOX_DISABLE_SECTION_BOOST=1` | mutex não ativa (section OFF), source_type boost normal |
| Mutex OFF explícito | `NOX_MUTEX_SECTION_SOURCE_TYPE=0` | comportamento pré-mutex: ambos acumulam |
| source_type boost OFF | `NOX_DISABLE_SOURCE_TYPE_BOOST=1` | sourceTypeDelta=0 independente de section |
| Ambos OFF | `NOX_DISABLE_SECTION_BOOST=1 NOX_DISABLE_SOURCE_TYPE_BOOST=1` | ambos retornam 0 |

### Exemplo de test em Node:test

```typescript
describe("sourceTypeDelta — mutex com sectionDelta", () => {
  it("entity+compiled: sourceTypeDelta retorna 0 (mutex)", () => {
    const result = sourceTypeDelta("entity", "compiled");
    assert.strictEqual(result, 0);
  });

  it("entity+null: sourceTypeDelta retorna +1.0 (sem mutex)", () => {
    const result = sourceTypeDelta("entity", null);
    assert.strictEqual(result, 1.0);
  });

  it("lesson+null: sourceTypeDelta retorna +0.8", () => {
    const result = sourceTypeDelta("lesson", null);
    assert.strictEqual(result, 0.8);
  });

  it("ocr-cache+null: sourceTypeDelta retorna -0.3", () => {
    const result = sourceTypeDelta("ocr-cache", null);
    assert.strictEqual(result, -0.3);
  });

  it("entity+compiled: boostSum total = +1.0 (era +2.0)", () => {
    const boostSum = sourceTypeDelta("entity", "compiled") + sectionDelta("compiled", null);
    assert.strictEqual(boostSum, 1.0);  // só sectionDelta +1.0
  });

  it("NOX_MUTEX_SECTION_SOURCE_TYPE=0: mutex desabilitado, ambos acumulam", () => {
    // setup: process.env.NOX_MUTEX_SECTION_SOURCE_TYPE = "0"
    // reimport ou mockar MUTEX_SECTION_SOURCE_TYPE
    const boostSum = sourceTypeDeltaNoMutex("entity", "compiled") + sectionDelta("compiled", null);
    assert.strictEqual(boostSum, 2.0);  // pré-mutex
  });
});
```

---

## 6. Eval Plan (G10)

### Objetivo

Confirmar que A11 (A8 + mutex) > A8 canonical em nDCG@10, e que não há regressão em open-domain.

### Setup

```bash
# Usar o mesmo entity-eval-v2.db do G8 (não re-ingerir)
# Apenas modificar search.ts e re-rodar harness

export NOX_DB_PATH=/tmp/evals/g10/entity-eval-v2.db
export NOX_DISABLE_TIER_BOOST=1    # mesmo do G8
export NOX_SALIENCE_MODE=active    # mesmo do G8
# NOX_MUTEX_SECTION_SOURCE_TYPE padrão (1 = ON)
```

### Configurações a comparar

| Config | Descrição | Flags adicionais |
|---|---|---|
| A8 | Canonical G8 (baseline) | nenhuma |
| A11 | A8 + mutex ON | deploy mutex code |
| A11b | A8 + mutex OFF | `NOX_MUTEX_SECTION_SOURCE_TYPE=0` |

`A11b` serve para verificar que a env flag funciona corretamente e que os números voltam a A8.

### Métricas alvo

| Métrica | Mínimo aceitável | Ideal |
|---|---|---|
| nDCG@10 A11 vs A8 | > 0 (qualquer ganho) | ≥ +0.5% |
| nDCG@10 A11 open-domain | ≥ A8 open-domain | sem regressão |
| nDCG@10 A11b vs A8 | ≈ 0 (env flag funciona) | < ±0.1% |

### Falha de critério

Se A11 < A8 em qualquer categoria relevante (especialmente open-domain), investigar:
- chunk D (entity + section=null): são chunks legítimos? Quantos existem?
- O `SECTION_BOOST[section]` fallback via `sectionBoostCol` está sendo ativado quando `section=null` mas `section_boost` coluna está preenchida? Se sim, o mutex usa `section` mas ignora o fallback — checar se chunks com `section_boost > 0` mas `section = null` existem em prod.

---

## 7. Rollback Plan

### Rollback zero-deploy (imediato)

```bash
# Na VPS, via systemd drop-in override:
echo '[Service]
Environment="NOX_MUTEX_SECTION_SOURCE_TYPE=0"' | sudo tee /etc/systemd/system/nox-mem-api.service.d/mutex-off.conf
sudo systemctl daemon-reload && sudo systemctl restart nox-mem-api
```

Isso reverte ao comportamento pré-mutex sem rebuild. Verificar via:

```bash
curl http://127.0.0.1:18802/api/health | jq '.searchConfig'
# ou consultar via endpoint quando exposto
```

### Rollback via código (se env flag não suficiente)

```bash
git revert <commit-do-mutex>
npm run build && systemctl restart nox-mem-api
```

### Condições que disparam rollback

- A11 mostra regressão ≥ −1% em qualquer categoria vs A8
- Spike de queries sem resultado (`/api/health.search_telemetry top_chunk_ids = []`) após deploy
- Canary `check-schema-invariants.sh` reporta anomalia em distribuição de section

---

## 8. Risk Analysis

### Risk 1 — Chunks entity sem section (Chunk D)

**Probabilidade:** Baixa. Apenas entity files têm `section` populado via `ingestEntityFile`. Chunks não-entity com `source_type=entity` pós-backfill podem existir se o backfill não estava perfeitamente acurado.

**Impacto:** Se existirem, esses chunks recebem `sourceTypeDelta=+1.0` (como antes). Não é regressão.

**Mitigação:** Auditoria pré-deploy: `SELECT COUNT(*) FROM chunks WHERE source_type='entity' AND section IS NULL`.

### Risk 2 — Open-domain regress maior que o esperado

**Probabilidade:** Baixa. Chunks open-domain tipicamente têm `source_type=note` (delta=0) ou `source_type=personal-doc` (delta=+0.2), sem `section`. O mutex não os afeta.

**Impacto:** Se o problema era só double-boost em entity (1.1% do corpus), remover o double-boost não pode piorar open-domain — só pode melhorar (menos noise sobre-promovido).

**Mitigação:** G10 ablation valida empiricamente antes de merge em main.

### Risk 3 — Interaction com sectionDelta fallback via `sectionBoostCol`

**Cenário:** Chunk tem `section=null` mas `section_boost=2.0` (coluna preenchida diretamente pelo ingester sem setar `section`). Mutex usa `section IS NULL` → não ativa → `sourceTypeDelta` retorna valor normal. Mas `sectionDelta` lê o fallback `sectionBoostCol` e retorna +1.0.

**Resultado:** Double-boost persiste para esses chunks.

**Probabilidade:** Muito baixa. O `ingestEntityFile` seta sempre `section` junto com `section_boost`. Verificar via audit: `SELECT COUNT(*) FROM chunks WHERE section IS NULL AND section_boost > 1.0`.

**Mitigação se existirem:** Ampliar o guard do mutex para também checar `sectionBoostCol > 1.0` quando `section=null`.

### Risk 4 — Regressão em multi-hop queries

G8 já mostrou `multi-hop +1.4pp` com source_type active. O mutex reduz o sinal de entity para multi-hop queries que dependem de entity chunks. Potencial trade-off: open-domain ganha, multi-hop perde parcialmente.

**Probabilidade:** Média para multi-hop.

**Mitigação:** G10 mede multi-hop separadamente. Se regress > +1.4pp (ou seja, piora mais do que G8 ganhou), considerar Option 2 (soft attenuation) apenas para multi-hop com A/B flag.

### Resumo de riscos

| Risk | Probabilidade | Impacto | Ação |
|---|---|---|---|
| Chunks entity sem section | Baixa | Nulo | Audit pré-deploy |
| Open-domain regress | Muito baixa | Alto | G10 ablation |
| Interaction sectionBoostCol | Muito baixa | Médio | Audit pré-deploy |
| Multi-hop regress parcial | Média | Baixo-médio | G10 per-category |

---

## 9. Cross-links

- **PR #154** — `SOURCE_TYPE_BOOST` wiring original; introduziu `source_type entity=2.0`
- **PR #177** — G8 ablation que cravou o double-boost (`A8 < A10 em -0.81%`)
- **`docs/HANDOFF.md`** — section `Night 2026-05-20`, subsection `G8 cravado`
- **`staged-1.7a/edits/search.ts`** — implementação atual de `sourceTypeDelta` e `sectionDelta`
- **`staged-1.7a/tests/search-boost-stack.test.ts`** — test file existente a estender
- **`docs/DECISIONS.md`** — CLAUDE.md regra #5 (sem boost multiplicativo empilhável)
- **`specs/INDEX.md`** — adicionar esta spec como `active` em `G-lab`

---

## 10. Effort Estimate

| Step | Estimativa |
|---|---|
| Modificar `sourceTypeDelta` (Step 1-3) | ~30 min |
| Atualizar tests (Step 4) | ~45 min |
| G10 ablation (comparar A8 vs A11) | ~20 min (mesmo harness, mesma DB) |
| CHANGELOG + cross-links (Step 5) | ~15 min |
| **Total** | **~110 min** |

Effort total: ~2h. Implementação trivial; o custo está na ablation G10 de validação.

---

*Spec criado: 2026-05-20. Próximo passo: implementar em `staged-G10/` e rodar ablation antes de merge em main.*
