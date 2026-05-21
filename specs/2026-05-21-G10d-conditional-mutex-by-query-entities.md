# Design Spec: G10d — Conditional Hard Mutex by `query_entities` Count

**Status:** Design spec — implementation-ready, gated em ablation eval
**Data:** 2026-05-21
**Autores:** Spec follow-up de G10b/G10c ablations (audits 2026-05-21)
**Cross-links:** PR #182 (Hard Mutex deploy) · `specs/2026-05-20-mutual-exclusion-section-source-type.md` (parent) · `audits/2026-05-21-G10b-per-category-mutex-ablation.md` · `audits/2026-05-21-G10c-per-style-mutex-ablation.md`
**Branch spec:** `spec/g10d-conditional-mutex-design`

---

## 1. Objective

Mitigar a regressão multi-hop **−3.95% nDCG@10 / −6.02% R@10** introduzida pelo Hard Mutex (PR #182) **sem perder** o ganho single-hop **+8.22% nDCG / +13.20% MRR** já cravado em prod.

Aggregate atual do Hard Mutex deployed:

| Eval | n | nDCG Δ% | MRR Δ% | R@10 Δ% |
|---|---:|---:|---:|---:|
| G10 | 100 | +0.79% | +2.65% | n/a |
| G10b | 100 | +0.43% | +0.82% | −1.34% |
| G10c | 100 | +0.43% | +0.82% | −1.34% |

Per-category trade-off cravado pelos audits 2026-05-21:

| Categoria | nDCG Δ% | MRR Δ% | R@10 Δ% | Veredicto |
|---|---:|---:|---:|---|
| single-hop | **+8.22%** | **+13.20%** | 0% | strong win |
| multi-hop | **−3.95%** | −2.70% | **−6.02%** | regression |
| open-domain | +2.42% | +5.56% | 0% | win |
| adversarial | −2.95% | −5.88% | 0% | regression |
| temporal | 0% | 0% | 0% | degenerate (gold N/A no corpus) |

Cross-style (G10c): a regressão multi-hop é **style-agnostic** (NL −3.91%, keyword −3.99%) — propriedade estrutural do mutex removendo chunks intermediários da chain traversal, não artifact de phrasing.

Target G10d: recuperar multi-hop nDCG ≥ −1% (de −3.95% para ≥ −1%) **enquanto preserva** single-hop nDCG ≥ +6% (de +8.22%) e aggregate ≥ atual +0.79%.

---

## 2. Hypothesis

**Conditional mutex active apenas se a query parece single-entity:**

- `query_entities ≤ 1` → mutex active (current behavior)
- `query_entities ≥ 2` → mutex disabled (preserva chain traversal signal)

Rationale: queries multi-hop por construção mencionam **≥ 2 entidades** (e.g., "How does Toto interact with Fundo Lombardia") e dependem de chunks intermediários que carregavam ambos boosts (section=compiled + source_type=entity) pré-mutex. Single-hop tipicamente menciona **1 entidade** ("Toto's role") onde o mutex elimina o double-boost que diluía o gold.

Threshold tunável via env: `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1` (default — mutex active quando entity count ≤ threshold).

---

## 3. Approach — Query Entity Detection

Três opções avaliadas. Recomendação: **Option B** (KG lookup) — best accuracy/latency trade-off.

### Option A — Lightweight regex

Detectar PascalCase tokens + named-entity patterns conhecidos.

```typescript
function countQueryEntitiesRegex(query: string): number {
  // PascalCase tokens (Toto, Fundo Lombardia, Granix)
  const pascalCase = query.match(/\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[A-ZÀ-Ý][a-zà-ÿ]+)*/gu) ?? [];
  // Quoted entities
  const quoted = query.match(/"[^"]+"|'[^']+'/g) ?? [];
  return new Set([...pascalCase, ...quoted.map(q => q.slice(1, -1))]).size;
}
```

**Pros:** zero DB calls, sub-millisecond, deterministic.
**Cons:**
- Frágil em PT-BR (lowercase nomes próprios pós-preposição: "do fundo lombardia").
- False positives em title-case substantivos comuns ("Como Funciona" conta 1 entidade).
- False negatives em entities all-lowercase ("nox-mem", "openclaw").

### Option B — KG entity lookup (RECOMMENDED)

Usar a tabela existente `kg_entities` (~402 entities cravadas) como dicionário canônico.

```typescript
// src/lib/query-entity-count.ts
import type { Database } from "better-sqlite3";

let entityIndex: Map<string, Set<string>> | null = null;
let entityIndexLoadedAt = 0;
const ENTITY_INDEX_TTL_MS = 5 * 60 * 1000; // 5 min refresh

function loadEntityIndex(db: Database.Database): Map<string, Set<string>> {
  const now = Date.now();
  if (entityIndex && now - entityIndexLoadedAt < ENTITY_INDEX_TTL_MS) {
    return entityIndex;
  }
  const rows = db
    .prepare("SELECT name, entity_type FROM kg_entities WHERE name IS NOT NULL")
    .all() as Array<{ name: string; entity_type: string }>;
  const idx = new Map<string, Set<string>>();
  for (const row of rows) {
    const key = row.name.toLowerCase().trim();
    if (!key) continue;
    if (!idx.has(key)) idx.set(key, new Set());
    idx.get(key)!.add(row.entity_type);
  }
  entityIndex = idx;
  entityIndexLoadedAt = now;
  return idx;
}

export function countQueryEntities(db: Database.Database, query: string): number {
  const idx = loadEntityIndex(db);
  const lower = query.toLowerCase();
  const matched = new Set<string>();
  // Greedy longest-match scan: entities canônicos em kg_entities incluem
  // multi-word names ("Fundo Lombardia", "Galapagos Capital"). Ordenar
  // por length desc evita "Fundo" matchear antes de "Fundo Lombardia".
  const sorted = [...idx.keys()].sort((a, b) => b.length - a.length);
  let remaining = lower;
  for (const name of sorted) {
    if (remaining.includes(name)) {
      matched.add(name);
      // Remove para não contar overlap secundário
      remaining = remaining.split(name).join(" ");
    }
  }
  return matched.size;
}

// Test hook
export function _resetEntityIndexCache(): void {
  entityIndex = null;
  entityIndexLoadedAt = 0;
}
```

**Pros:**
- Accuracy alta — entity-set é o **ground truth** do corpus.
- Latência amortizada: cache de 5min cobre milhares de queries.
- Cold-load: 402 rows × ~30 bytes = ~12KB, <5ms via prepared statement.
- Multi-language por design (kg_entities armazena nomes como aparecem em corpus, PT-BR + EN).

**Cons:**
- Não detecta entities **novas** mencionadas em queries mas não-ingeridas ainda. Aceitável: queries sobre entities desconhecidas degradam pra `count=0` → mutex active → comportamento atual.
- Greedy longest-match O(N × Q) onde N=entities, Q=query length. Para N=402, Q≤200 chars: <1ms typical.

### Option C — LLM-extracted (Gemini 2.5 flash-lite)

```typescript
async function countQueryEntitiesLLM(query: string): Promise<number> {
  const prompt = `Extract named entities from query. Return JSON {entities: [...]} only.
Query: ${query}`;
  const resp = await geminiClient.generateContent({
    model: "gemini-2.5-flash-lite",
    prompt,
    maxTokens: 100,
  });
  const json = JSON.parse(resp.text);
  return new Set(json.entities).size;
}
```

**Pros:** highest accuracy, handles novel entities, multilingual.
**Cons:**
- Latência: ~200ms p95 mesmo com flash-lite. Hot path inaceitável (search é p95 ~2.3s — adicionar 200ms = +9% latency budget).
- Custo: $0.000075/query × 1k queries/dia = $0.075/dia (marginal mas observable).
- Dep externa numa decisão de scoring → reduz reliability (Gemini API outage = mutex defaultear pra que?).

### Recomendação final

**Option B (KG lookup)** — adopta. Cache 5min cobre 99% das queries com latency negligible. Option A fica como fallback em cold-start (índice ainda não carregado). Option C descartada por latency + reliability.

---

## 4. Implementation Plan

### Step 1 — Criar `src/lib/query-entity-count.ts`

Módulo novo com:

- `countQueryEntities(db, query): number` — entry point principal (Option B).
- `_resetEntityIndexCache()` — test hook.
- Cache TTL: 5min via timestamp local.
- Fallback: se `db` é null ou `kg_entities` retorna 0 rows → return 0 (mutex defaultea active, current behavior).

Já espelhado no snippet seção 3 Option B.

### Step 2 — Modificar `sourceTypeDelta` em `staged-1.7a/edits/search.ts`

Adicionar parâmetro `queryEntityCount`:

```typescript
function sourceTypeDelta(
  sourceType: string | null | undefined,
  section: string | null | undefined,
  queryEntityCount: number,  // ← novo parâmetro
): number {
  if (DISABLE_SOURCE_TYPE_BOOST || !sourceType) return 0;

  // HARD MUTEX (G9 + G10d conditional):
  // - Mutex active só se queryEntityCount <= MUTEX_QUERY_ENTITY_THRESHOLD (default 1)
  // - Multi-entity queries (>= 2) preservam chain traversal: mutex disabled
  // - Rollback do conditional: NOX_DISABLE_CONDITIONAL_MUTEX=1 (volta pra hard mutex puro)
  // - Rollback total do mutex: NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1
  const conditionalActive =
    !DISABLE_CONDITIONAL_MUTEX &&
    queryEntityCount > MUTEX_QUERY_ENTITY_THRESHOLD;

  if (
    !DISABLE_MUTEX_SECTION_SOURCE_TYPE &&
    !DISABLE_SECTION_BOOST &&
    !conditionalActive &&  // ← if multi-entity, skip mutex
    section &&
    SECTION_BOOST[section] !== undefined
  ) {
    return 0;
  }

  const f = SOURCE_TYPE_BOOST[sourceType] ?? 1.0;
  return f - 1.0;
}
```

### Step 3 — Adicionar env flags

```typescript
// G10d conditional: threshold tunável
const MUTEX_QUERY_ENTITY_THRESHOLD = Number.parseInt(
  process.env.NOX_MUTEX_QUERY_ENTITY_THRESHOLD ?? "1",
  10,
);

// Rollback do conditional (volta pra hard mutex G9 puro)
const DISABLE_CONDITIONAL_MUTEX =
  process.env.NOX_DISABLE_CONDITIONAL_MUTEX === "1";
```

Defaults:
- `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1` → mutex active quando query tem ≤ 1 entidade.
- `NOX_DISABLE_CONDITIONAL_MUTEX=1` → bypass conditional, comportamento atual (mutex always-on).

### Step 4 — Update call sites em `search()` e `searchSemantic()`

```typescript
// FTS path (search):
import { countQueryEntities } from "./lib/query-entity-count.js";

export function search(query: string, ...): SearchResult[] {
  const db = getDb();
  const queryEntityCount = countQueryEntities(db, query);
  // ...
  for (const row of rows) {
    boostSum += sourceTypeDelta(row.source_type, row.section, queryEntityCount);
    boostSum += sectionDelta(row.section, row.section_boost);
    // ...
  }
}

// Semantic path (searchSemantic):
export async function searchSemantic(query: string, ...): Promise<SearchResult[]> {
  const db = getDb();
  const queryEntityCount = countQueryEntities(db, query);
  // ...
  boostSum += sourceTypeDelta(info?.source_type, info?.section, queryEntityCount);
  // ...
}
```

`queryEntityCount` é computado **uma vez por query** e passado pra todos os call sites (não re-computado por chunk).

### Step 5 — Telemetria

Expor count em `search_telemetry` (já tem +4 cols A0):

```sql
ALTER TABLE search_telemetry ADD COLUMN query_entity_count INTEGER;
```

E logar em `/api/search` response opcional via `?explain=1`:

```json
{
  "results": [...],
  "explain": {
    "query_entity_count": 2,
    "mutex_active_for_query": false,
    "threshold": 1
  }
}
```

Permite observability shadow-mode antes de active deploy.

### Step 6 — Tests unitários

Novo file: `staged-1.7a/tests/query-entity-count.test.ts` (5-7 cases).

```typescript
import { test, describe, beforeEach } from "node:test";
import assert from "node:assert/strict";
import Database from "better-sqlite3";
import { countQueryEntities, _resetEntityIndexCache } from "../src/lib/query-entity-count.js";

function makeFixtureDb(): Database.Database {
  const db = new Database(":memory:");
  db.exec(`
    CREATE TABLE kg_entities (
      id INTEGER PRIMARY KEY,
      name TEXT,
      entity_type TEXT
    );
    INSERT INTO kg_entities (name, entity_type) VALUES
      ('Toto', 'person'),
      ('Fundo Lombardia', 'organization'),
      ('Galapagos Capital', 'organization'),
      ('Granix', 'organization'),
      ('nox-mem', 'project');
  `);
  return db;
}

describe("countQueryEntities", () => {
  beforeEach(() => _resetEntityIndexCache());

  test("zero entities — empty query", () => {
    const db = makeFixtureDb();
    assert.equal(countQueryEntities(db, "what is happening"), 0);
  });

  test("one entity — single-hop query", () => {
    const db = makeFixtureDb();
    assert.equal(countQueryEntities(db, "what is Toto's role"), 1);
  });

  test("two entities — multi-hop query", () => {
    const db = makeFixtureDb();
    assert.equal(
      countQueryEntities(db, "how does Toto interact with Fundo Lombardia"),
      2,
    );
  });

  test("three entities", () => {
    const db = makeFixtureDb();
    assert.equal(
      countQueryEntities(db, "Toto Fundo Lombardia Galapagos relationship"),
      3,
    );
  });

  test("longest-match wins (Fundo Lombardia not Fundo+Lombardia)", () => {
    const db = makeFixtureDb();
    // Se a fixture tivesse "Fundo" como entity standalone, deveria contar 1 (longest)
    assert.equal(countQueryEntities(db, "Fundo Lombardia performance"), 1);
  });

  test("case-insensitive match", () => {
    const db = makeFixtureDb();
    assert.equal(countQueryEntities(db, "fundo lombardia performance"), 1);
  });

  test("empty kg_entities — return 0", () => {
    const db = new Database(":memory:");
    db.exec("CREATE TABLE kg_entities (name TEXT, entity_type TEXT)");
    assert.equal(countQueryEntities(db, "any query"), 0);
  });

  test("ambiguous title-case (NOT in kg_entities) — return 0", () => {
    const db = makeFixtureDb();
    // "How" é title-case mas não está em kg_entities → não conta
    assert.equal(countQueryEntities(db, "How Does It Work"), 0);
  });
});
```

### Step 7 — Update `sourceTypeDelta` tests existentes

`staged-1.7a/tests/search-boost-stack.test.ts` precisa novo grupo conditional:

```typescript
describe("sourceTypeDelta — conditional mutex (G10d)", () => {
  test("entity+compiled+queryEntityCount=1: mutex active, retorna 0", () => {
    assert.equal(sourceTypeDelta("entity", "compiled", 1), 0);
  });

  test("entity+compiled+queryEntityCount=2: mutex disabled, retorna +1.0", () => {
    assert.equal(sourceTypeDelta("entity", "compiled", 2), 1.0);
  });

  test("entity+compiled+queryEntityCount=0: mutex active (≤1), retorna 0", () => {
    assert.equal(sourceTypeDelta("entity", "compiled", 0), 0);
  });

  test("entity+null+queryEntityCount=2: mutex N/A, retorna +1.0", () => {
    assert.equal(sourceTypeDelta("entity", null, 2), 1.0);
  });

  test("NOX_DISABLE_CONDITIONAL_MUTEX=1: ignora queryEntityCount, mutex always-on", () => {
    // Setup env override + reimport
    // ...
    assert.equal(sourceTypeDelta("entity", "compiled", 5), 0);
  });

  test("NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2: mutex active até count=2", () => {
    // Setup env override + reimport
    // ...
    assert.equal(sourceTypeDelta("entity", "compiled", 2), 0);
    assert.equal(sourceTypeDelta("entity", "compiled", 3), 1.0);
  });
});
```

### Step 8 — CHANGELOG + cross-links

```markdown
## [Unreleased]
### Changed
- search: conditional Hard Mutex by query_entities count (G10d, gated em ablation)
  - mutex active só se query has ≤ NOX_MUTEX_QUERY_ENTITY_THRESHOLD entities (default 1)
  - multi-entity queries (≥2) preservam chain traversal (recover -3.95% multi-hop)
  - rollback do conditional: NOX_DISABLE_CONDITIONAL_MUTEX=1 (volta hard mutex G9)
  - cross-link: specs/2026-05-21-G10d-conditional-mutex-by-query-entities.md
```

---

## 5. Eval Plan (G10d Ablation)

### Setup

DB: `/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db` (mesmo G10b/G10c).
Driver: `entity_ablation_eval.py` (per_category + per_style nativo).
Endpoint: `http://127.0.0.1:18803/api/search` (isolated, prod 18802 untouched).
n=100 queries (5 categorias × 2 styles × 10 queries).
VPS: `root@187.77.234.79`.

### Configurações a comparar

| Config | Descrição | Env flags |
|---|---|---|
| A8' | Mutex active (G10 baseline, current prod) | (default) |
| A8d-1 | Conditional mutex, threshold=1 | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1` |
| A8d-2 | Conditional mutex, threshold=2 (grid search) | `NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2` |
| A8' off | Mutex fully disabled (control) | `NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1` |

A8' off serve como controle pra reproduzir o número G10b mutex_disabled (sanity check pipeline).

### Métricas-alvo

#### Threshold de sucesso (GO)

| Métrica | Threshold |
|---|---|
| Multi-hop nDCG@10 | **≥ −1%** (recover from −3.95%) |
| Multi-hop R@10 | **≥ −2%** (recover from −6.02%) |
| Single-hop nDCG@10 | **≥ +6%** (preserve from +8.22%) |
| Single-hop MRR | **≥ +10%** (preserve from +13.20%) |
| Aggregate nDCG@10 | **≥ +0.79%** (no worse than current G10) |
| Adversarial nDCG@10 | ≥ −2% (recover from −2.95% — bonus) |

#### Threshold de NO-GO (cancel)

- Single-hop nDCG@10 < +5% — perdeu o ganho principal.
- Aggregate nDCG@10 < 0 — degrade vs pre-mutex baseline.
- Open-domain nDCG@10 < +1% — perdeu o segundo ganho (atual +2.42%).

#### EXTEND (mais grid search)

- Aggregate ≥ +0.79% mas multi-hop ainda < −1% → testar threshold=2 ou higher.
- Single-hop perdeu mas multi-hop recuperou → trade-off perdido, considere style-conditional bolt-on (rejeitado em G10c §2 mas reabre se G10d for o ângulo certo).

### Sub-análise per-category × per-style

Audit deve reportar full matrix style × category (10 cells active vs 10 cells conditional). Atenção especial:

| Cell | Hypothesis G10d |
|---|---|
| NL single-hop | Stays +13.83% (mutex active porque count=1) |
| keyword single-hop | Stays +0% (mutex active mas BM25 já resolveu) |
| NL multi-hop | Recovers ≥ −1% (mutex disabled porque count≥2) |
| keyword multi-hop | Recovers ≥ −1% (idem) |
| keyword adversarial | Recovers ≥ −2% **IF** adversarial queries têm ≥2 entities mentioned |
| NL open-domain | Stays neutral or improves |

### Orchestrator

`audits/data-g10d/run-g10d-conditional-ablation.sh.unrun` (a commit como follow-up):

```bash
#!/bin/bash
set -euo pipefail
export NOX_DB_PATH=/root/.openclaw/workspace/eval-data/g9-g5db-2026-05-20/g9.db
export NOX_SALIENCE_MODE=active

# Run 1: A8' baseline
unset NOX_DISABLE_CONDITIONAL_MUTEX
unset NOX_MUTEX_QUERY_ENTITY_THRESHOLD
systemctl restart nox-mem-api-isolated
python entity_ablation_eval.py --n 100 --out results/g10d/a8_baseline.json

# Run 2: A8d-1 (threshold=1)
export NOX_MUTEX_QUERY_ENTITY_THRESHOLD=1
systemctl restart nox-mem-api-isolated
python entity_ablation_eval.py --n 100 --out results/g10d/a8d_t1.json

# Run 3: A8d-2 (threshold=2)
export NOX_MUTEX_QUERY_ENTITY_THRESHOLD=2
systemctl restart nox-mem-api-isolated
python entity_ablation_eval.py --n 100 --out results/g10d/a8d_t2.json

# Run 4: control (mutex fully off)
unset NOX_MUTEX_QUERY_ENTITY_THRESHOLD
export NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1
systemctl restart nox-mem-api-isolated
python entity_ablation_eval.py --n 100 --out results/g10d/a8_off.json

# Aggregate
python audits/data-g10d/aggregate.py
```

Tempo estimado: 4 runs × ~10min = ~40min total.

---

## 6. Implementation Surface Area

| File | Change | Effort |
|---|---|---|
| `src/lib/query-entity-count.ts` | NEW — entity detection + cache | ~1.5h |
| `src/search.ts` (`sourceTypeDelta`) | add `queryEntityCount` param + threshold guard | ~30min |
| `src/search.ts` (call sites) | compute count once per query, pass through | ~30min |
| `staged-1.7a/tests/query-entity-count.test.ts` | NEW — 8 test cases | ~45min |
| `staged-1.7a/tests/search-boost-stack.test.ts` | extend conditional mutex group (6 tests) | ~30min |
| `CHANGELOG.md` | entry | ~10min |
| Telemetry: `search_telemetry.query_entity_count` col + `/api/search?explain` | ~45min |
| **Total implementation** | | **~5h** |
| G10d ablation (4 runs + analysis) | | **~2h** |
| Documentation (audit + spec status update) | | **~30min** |
| **Grand total** | | **~7.5h** |

---

## 7. Rollback Plan

### Tier 1 — Disable conditional layer, keep hard mutex (1-minute deploy)

```bash
# Systemd drop-in:
echo '[Service]
Environment="NOX_DISABLE_CONDITIONAL_MUTEX=1"' | sudo tee \
  /etc/systemd/system/nox-mem-api.service.d/g10d-conditional-off.conf
sudo systemctl daemon-reload && sudo systemctl restart nox-mem-api
```

Volta pro comportamento G10 (hard mutex always-on).

### Tier 2 — Disable entire mutex (volta pra pre-PR #182)

```bash
echo '[Service]
Environment="NOX_DISABLE_MUTEX_SECTION_SOURCE_TYPE=1"' | sudo tee \
  /etc/systemd/system/nox-mem-api.service.d/mutex-off.conf
sudo systemctl daemon-reload && sudo systemctl restart nox-mem-api
```

### Tier 3 — Code revert

```bash
git revert <commit-do-conditional-mutex>
npm run build && systemctl restart nox-mem-api
```

### Condições que disparam rollback

- Aggregate nDCG@10 cai abaixo de +0.5% (perde G10 baseline).
- Single-hop nDCG@10 < +5% (perdeu ganho principal).
- Latency p95 search aumenta > 50ms (cache não amortizou).
- `kg_entities` corrupt/empty causa entity count = 0 sempre → mutex defaultea always-on (= G10 atual, não regressão real, mas observability deve flagar).

---

## 8. Risk Analysis

### Risk 1 — Entity count threshold tuning

**Cenário:** threshold=1 é arbitrário. Talvez threshold=2 ou higher seja melhor.
**Probabilidade:** Média.
**Mitigação:** G10d ablation testa threshold=1 **e** threshold=2 lado a lado. Se ambos são positivos vs A8', escolher o maior aggregate. Se threshold=2 quebra outro caso (e.g., adversarial degrada), threshold=1 wins.

### Risk 2 — Adversarial queries gaming entity detection

**Cenário:** queries adversarial mencionam múltiplas entidades como distractor pra disable mutex e diluir o gold. Atacante deliberadamente pluraliza entities pra rebaixar ranking quality.
**Probabilidade:** Baixa em production traffic. Alta em red-team contexto.
**Impacto:** Adversarial nDCG poderia regredir mais que atual −2.95%. Mas G10c já mostrou que adversarial perda é majoritariamente em **keyword adversarial** (−5.35%, possível que keyword adversarial natural-language não mencione múltiplas entities → mutex já estaria active correto).
**Mitigação:** G10d ablation mede adversarial separado. Se piora vs A8', refinar com cap: `queryEntityCount = Math.min(rawCount, 3)` evita queries com 5+ entities terem effect indistinguível.

### Risk 3 — KG lookup latency on hot path

**Cenário:** Search é p95 ~2.3s (medido 2026-05-18). Adicionar entity count check em cold cache pode adicionar 5-10ms. Em hot cache, <1ms.
**Probabilidade:** Baixa.
**Mitigação:**
- Cache TTL 5min cobre 99% das queries.
- Cold-load amortizado: primeira query após restart paga 5ms; próximas 9999 pagam <1ms.
- Worst case: cache fail → return 0 → mutex active (G10 behavior) → no regression vs baseline.

### Risk 4 — Entity index staleness

**Cenário:** `kg_entities` cresce (incremental nightly kg-extract). Cache TTL 5min pode ter index stale por até 5min.
**Probabilidade:** Alta (intencional design).
**Impacto:** Queries sobre entities recém-extraídas (últimos 5min) tratam essas entities como inexistentes → undercount → mutex active demais.
**Mitigação:** Aceitável — 5min lag é negligible vs query volume. Se críticio, expor `POST /api/kg/refresh-cache` ou hook em `kg-extract` end-of-batch.

### Risk 5 — Quebra de invariant Hard Mutex existente

**Cenário:** Hard Mutex foi cravado como propriedade simples ("section ganha sempre"). Conditional layer adiciona uma exception. Code complexity sobe.
**Probabilidade:** Alta (real).
**Impacto:** Reviewer fatigue + onboarding cost. Mais N flags em search.ts (já tem 5+).
**Mitigação:**
- Doc inline explicit no `sourceTypeDelta` referenciando este spec + G10d audit.
- Test coverage explicit (Step 6, 7) cobre ambos paths.
- Rollback tier 1 (env flag) trivial — se ficar confuso, revert é 1-line.

### Risk 6 — Single-hop ganho não preservado (G10d falha)

**Cenário:** Pode acontecer que mesmo single-hop queries tenham >=2 entities detected (e.g., "What is Toto's role at Nuvini" tem 2 entities). Então mutex disabled em queries que deveriam beneficiar → single-hop ganho diminui.
**Probabilidade:** Média.
**Mitigação:** G10d threshold=2 testa exatamente isso. Se single-hop fica >+6% com threshold=2 mas <+6% com threshold=1, threshold=2 wins.

### Resumo de riscos

| Risk | Probabilidade | Impacto | Mitigação |
|---|---|---|---|
| Threshold tuning | Média | Médio | Grid search G10d |
| Adversarial gaming | Baixa | Médio | Cap entity count |
| KG lookup latency | Baixa | Baixo | Cache 5min |
| Index staleness | Alta | Negligible | Aceitar trade-off |
| Code complexity | Alta | Baixo | Doc + tests |
| Single-hop regress | Média | Alto | G10d threshold=2 fallback |

---

## 9. Cross-links

- **PR #182** — Hard Mutex original deploy (G10 baseline)
- **`specs/2026-05-20-mutual-exclusion-section-source-type.md`** — parent spec, contexto Option 1 (Hard Mutex)
- **`audits/2026-05-21-G10b-per-category-mutex-ablation.md`** — descoberta multi-hop −3.95%
- **`audits/2026-05-21-G10c-per-style-mutex-ablation.md`** — confirma style-agnostic (NL −3.91%, KW −3.99%)
- **`staged-1.7a/edits/search.ts`** — implementação atual de `sourceTypeDelta` (linhas 164-184)
- **`staged-1.7a/edits/knowledge-graph.patch.ts`** — referência canônica de `kg_entities` query
- **`specs/d51-template.md`** — decision template gated em este ablation
- **`docs/DECISIONS.md`** — CLAUDE.md regra #5 (sem boost multiplicativo empilhável)
- **`docs/HANDOFF.md`** — entry G10d follow-up
- **`specs/INDEX.md`** — adicionar esta spec em Active section
- **Memory:** `[[g10b-multi-hop-regression]]`, `[[g10c-style-agnostic]]`, `[[g10d-conditional-mutex-design]]`

---

## 10. Open Questions

1. **`query_entity_count` vs `query_entity_density`** — devia normalizar por query length? Query curta com 2 entities é diferente de query longa com 2 entities. Inicialmente NÃO normalizar (count puro é interpretable), revisitar se G10d resultados sugerem.

2. **Entity match case-sensitivity em PT-BR** — accents? "Lombardía" vs "Lombardia"? Decisão atual: lowercase + trim, sem accent strip (perderia distinção entities). Revisitar se false negatives observados em prod.

3. **Multi-word entities greedy vs longest** — fixture testa Fundo Lombardia > Fundo. Mas e se entity "Fundo" tb existe? Greedy longest-match é safe default. Doc no test case.

4. **Threshold dinâmico por categoria** — single-hop com count=2 deveria preservar mutex, mas multi-hop com count=1 deveria disable mutex? Atualmente category detection runtime caro. Out-of-scope G10d v1; track como G10e potencial.

5. **Soft mutex em vez de hard switch** — em vez de binary "mutex on/off based on count", interpolate: `mutexStrength = 1 - (queryEntityCount - 1) / 4` clamped [0,1]. Adds knob complexity. Out-of-scope v1.

---

## 11. Effort Estimate

| Step | Estimativa |
|---|---|
| 1. `query-entity-count.ts` module | ~1.5h |
| 2. `sourceTypeDelta` mod + flags | ~1h |
| 3. Call sites update | ~30min |
| 4. Tests (Step 6 + 7) | ~1.25h |
| 5. Telemetry (col + explain endpoint) | ~45min |
| 6. CHANGELOG + docs | ~25min |
| 7. G10d ablation (4 runs) | ~1h orchestrate + ~40min compute |
| 8. Audit writeup | ~30min |
| **Total** | **~7-8h** |

Implementation trivial. Custo está em ablation + audit honestidade.

---

## 12. Decision Gate

Esta spec **NÃO autoriza implementation**. Requires:

1. **Toto sign-off** — explicit go-ahead pra spawn implementation agent.
2. **G10d ablation execução** — gate em audit results.
3. **D51 decision** — preencher template após ablation (ver `specs/d51-template.md`).

Default action sem sign-off: spec fica em Active, hard mutex G10 permanece prod, multi-hop regression continua.

---

*Spec criado: 2026-05-21. Próximo passo: aprovação Toto + spawn G10d ablation agent OR park em Active aguardando.*
